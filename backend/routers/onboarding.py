"""WOW Onboarding — the first-run "hire your AI employee" experience.

Backs the 8-step full-screen onboarding: company setup (+ optional website analysis),
AI discovery, Knowledge Brain business-profile generation, smart automation
recommendations, labeled demo workspace seeding, first-success and a persistent
checklist. Everything is org-scoped and reuses existing engines (memory profile,
automation templates, demo seed).
"""
import re
import json
import uuid
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from core import db, now_iso, ai_service
from ai_service import extract_json
from dependencies import current_user, current_org

router = APIRouter(prefix="/api/onboarding")

DEMO_COLLECTIONS = ["clients", "projects", "tasks", "leads", "memories", "ai_activities",
                    "ai_proposals", "ai_contracts", "ai_invoices", "plans", "activities"]


# ---------------------------------------------------------------------------
# Save & continue later (persisted onboarding state)
# ---------------------------------------------------------------------------
class StateBody(BaseModel):
    step: int = 0
    data: dict = Field(default_factory=dict)
    completed: Optional[bool] = None


@router.get("/state")
async def get_state(user: dict = Depends(current_user)):
    st = user.get("onboarding_state") or {"step": 0, "data": {}}
    return {"step": st.get("step", 0), "data": st.get("data", {}),
            "completed": user.get("onboardingCompleted", False),
            "demo_seeded": user.get("demo_seeded", False),
            "flags": user.get("onboarding_flags", {})}


@router.post("/state")
async def save_state(body: StateBody, user: dict = Depends(current_user)):
    upd = {"onboarding_state": {"step": body.step, "data": body.data, "savedAt": now_iso()}, "updatedAt": now_iso()}
    if body.completed is not None:
        upd["onboardingCompleted"] = body.completed
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    return {"ok": True}


@router.post("/restart")
async def restart(user: dict = Depends(current_user)):
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"onboardingCompleted": False, "onboarding_state": {"step": 0, "data": {}}, "updatedAt": now_iso()}})
    return {"ok": True}


class FlagBody(BaseModel):
    key: str


@router.post("/flag")
async def set_flag(body: FlagBody, user: dict = Depends(current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {f"onboarding_flags.{body.key}": True, "updatedAt": now_iso()}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Website analysis (Step 2)
# ---------------------------------------------------------------------------
class WebsiteBody(BaseModel):
    url: str


WEBSITE_SYSTEM = (
    "You are a business analyst. From the website text provided, extract concise facts about the company. "
    "Return ONLY JSON: {\"company_name\": string, \"industry\": string, \"services\": string (comma-separated), "
    "\"target_customers\": string, \"summary\": string (1-2 sentences)}. If something isn't clear, use an empty string. "
    "Do not invent specifics that aren't supported by the text."
)


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@router.post("/analyze-website")
async def analyze_website(body: WebsiteBody, org: str = Depends(current_org)):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a website URL")
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (compatible; AssistifyBot/1.0)"}) as c:
            r = await c.get(url)
            r.raise_for_status()
            text = _strip_html(r.text)[:6000]
    except Exception as e:
        logging.info(f"website analyze fetch failed: {e}")
        return {"ok": False, "reason": "We couldn't reach that site — no problem, just fill in the details below.", "fields": {}}
    if len(text) < 40:
        return {"ok": False, "reason": "That site didn't have enough readable content — please fill in the details below.", "fields": {}}
    try:
        raw = await ai_service.complete(WEBSITE_SYSTEM, f"WEBSITE TEXT:\n{text}", session_id=f"onb-web-{org}")
        fields = extract_json(raw)
    except Exception as e:
        logging.info(f"website analyze llm failed: {e}")
        return {"ok": False, "reason": "Analysis is busy right now — please fill in the details below.", "fields": {}}
    return {"ok": True, "fields": {
        "company_name": fields.get("company_name", ""), "industry": fields.get("industry", ""),
        "main_services": fields.get("services", ""), "target_customers": fields.get("target_customers", ""),
        "summary": fields.get("summary", "")}}


# ---------------------------------------------------------------------------
# Company profile + Knowledge Brain generation (Steps 3-4)
# ---------------------------------------------------------------------------
class CompanyBody(BaseModel):
    company_name: str = ""
    industry: str = ""
    website: str = ""
    employees: str = ""
    main_services: str = ""
    target_customers: str = ""
    language: str = "en"
    country: str = ""
    logo: str = ""


PROFILE_SYSTEM = (
    "You are Assistify's onboarding analyst. From the company info, produce a concise, specific business profile that "
    "personalizes the AI's future writing. Return ONLY JSON with keys: company_summary (2-3 sentences), industry, "
    "services (array of short strings), communication_style (one sentence), proposal_style (one sentence), "
    "brand_voice (one sentence), writing_style (one sentence), suggested_memories (array of 4-6 "
    "{\"title\": short imperative, \"category\": one of ['Business','Writing Style','Pricing','Services','Brand Voice','Preferences','Customers'], "
    "\"content\": one sentence}). Base everything on the provided info; keep it grounded and useful."
)


@router.post("/profile")
async def generate_profile(body: CompanyBody, user: dict = Depends(current_user)):
    org = user["organizationId"]
    # 1) persist company info on the organization
    org_fields = {"name": body.company_name.strip() or None, "industry": body.industry, "website": body.website,
                  "employees": body.employees, "services": body.main_services, "target_customers": body.target_customers,
                  "country": body.country, "language": body.language, "logo": body.logo, "updatedAt": now_iso()}
    org_fields = {k: v for k, v in org_fields.items() if v is not None}
    await db.organizations.update_one({"id": org}, {"$set": org_fields})
    if body.language:
        await db.users.update_one({"id": user["id"]}, {"$set": {"language": body.language}})

    # 2) generate the business profile with the LLM (grounded on the form)
    ctx = body.model_dump()
    try:
        raw = await ai_service.complete(PROFILE_SYSTEM, f"COMPANY INFO (JSON):\n{json.dumps(ctx, default=str)}", session_id=f"onb-profile-{org}")
        sections = extract_json(raw)
    except Exception as e:
        logging.info(f"onboarding profile llm failed: {e}")
        # Deterministic fallback so onboarding never breaks.
        svc = [s.strip() for s in (body.main_services or "").split(",") if s.strip()] or ["Consulting"]
        sections = {
            "company_summary": f"{body.company_name or 'Your company'} is a {body.industry or 'services'} business serving {body.target_customers or 'its clients'}.",
            "industry": body.industry, "services": svc,
            "communication_style": "Clear, warm and professional.",
            "proposal_style": "Outcome-led, concise, and easy to scan.",
            "brand_voice": "Confident, helpful and human.",
            "writing_style": "Short paragraphs and scannable bullet points.",
            "suggested_memories": [
                {"title": f"Core services: {', '.join(svc[:3])}", "category": "Services", "content": f"The business focuses on {', '.join(svc)}."},
                {"title": "Warm, professional tone", "category": "Brand Voice", "content": "Client communication is confident, helpful and human."},
                {"title": "Prefers scannable formatting", "category": "Writing Style", "content": "Uses short paragraphs and bullet points over dense text."},
            ],
        }

    doc = {"organizationId": org, "sections": sections, "generated_at": now_iso(), "source": "onboarding"}
    await db.business_profiles.update_one({"organizationId": org}, {"$set": doc}, upsert=True)

    # 3) seed Knowledge Brain memories from the profile (REAL memories — not demo)
    CATS = ["Business", "Writing Style", "Pricing", "Customers", "Projects", "Processes",
            "Frequently Used Terms", "Products", "Services", "Brand Voice", "Policies", "Preferences", "Relationships"]
    seeded = 0
    for m in (sections.get("suggested_memories") or [])[:6]:
        title = (m.get("title") or "").strip()
        if not title:
            continue
        cat = m.get("category") if m.get("category") in CATS else "Business"
        exists = await db.memories.find_one({"organizationId": org, "title": title}, {"_id": 0, "id": 1})
        if exists:
            continue
        await db.memories.insert_one({
            "id": str(uuid.uuid4()), "organizationId": org, "title": title, "category": cat,
            "content": m.get("content", ""), "keywords": [], "confidence": 82, "source": "Onboarding",
            "times_used": 0, "pinned": False, "learning_enabled": True,
            "created_at": now_iso(), "updated_at": now_iso()})
        seeded += 1

    await db.users.update_one({"id": user["id"]}, {"$set": {"onboarding_flags.profile": True}})
    return {"ok": True, "sections": sections, "memories_seeded": seeded,
            "automations": _recommended_automations()}


class ProfileEdit(BaseModel):
    sections: dict


@router.put("/profile")
async def update_profile(body: ProfileEdit, org: str = Depends(current_org)):
    await db.business_profiles.update_one({"organizationId": org},
                                          {"$set": {"sections": body.sections, "generated_at": now_iso()}}, upsert=True)
    return {"ok": True}


def _recommended_automations():
    return [
        {"key": "t_proposal_not_sent", "name": "Proposal follow-up", "description": "Nudge clients when a proposal sits unsent.", "time_saved": 9},
        {"key": "t_invoice_overdue", "name": "Invoice reminders", "description": "Prepare polite payment reminders for overdue invoices.", "time_saved": 6},
        {"key": "t_contract_unsigned", "name": "Contract reminders", "description": "Follow up on contracts awaiting signature.", "time_saved": 8},
        {"key": "t_new_client", "name": "New client onboarding", "description": "Create an onboarding checklist for every new client.", "time_saved": 5},
        {"key": "t_project_completed", "name": "Project completion workflow", "description": "Prepare the final invoice when a project completes.", "time_saved": 6},
    ]


# ---------------------------------------------------------------------------
# Demo workspace (Step 6)
# ---------------------------------------------------------------------------
@router.post("/seed-demo")
async def seed_demo(user: dict = Depends(current_user)):
    org = user["organizationId"]
    existing = await db.clients.count_documents({"organizationId": org, "is_demo": True})
    if existing == 0:
        import server as S
        await S._seed_demo_data(org)
    await db.users.update_one({"id": user["id"]}, {"$set": {"demo_seeded": True}})
    return {"ok": True, **(await _demo_counts(org))}


async def _demo_counts(org):
    counts = {}
    for coll in ("clients", "projects", "leads", "ai_activities"):
        counts[coll] = await db[coll].count_documents({"organizationId": org, "is_demo": True})
    counts["approvals"] = await db.automation_approvals.count_documents({"organizationId": org, "status": "pending"})
    return {"counts": counts}


@router.get("/demo-status")
async def demo_status(org: str = Depends(current_org)):
    n = await db.clients.count_documents({"organizationId": org, "is_demo": True})
    return {"has_demo": n > 0, **(await _demo_counts(org))}


@router.delete("/demo-data")
async def clear_demo_data(user: dict = Depends(current_user)):
    org = user["organizationId"]
    removed = {}
    for coll in DEMO_COLLECTIONS:
        r = await db[coll].delete_many({"organizationId": org, "is_demo": True})
        if r.deleted_count:
            removed[coll] = r.deleted_count
    # demo-derived automation approvals & logs no longer point at real entities
    await db.automation_approvals.delete_many({"organizationId": org})
    await db.automation_logs.delete_many({"organizationId": org})
    await db.users.update_one({"id": user["id"]}, {"$set": {"demo_seeded": False}})
    return {"ok": True, "removed": removed}


# ---------------------------------------------------------------------------
# Persistent checklist
# ---------------------------------------------------------------------------
CHECKLIST = [
    {"key": "profile", "label": "Complete your company profile", "to": "/onboarding"},
    {"key": "client", "label": "Create your first client", "to": "/clients"},
    {"key": "proposal", "label": "Create your first proposal", "to": "/projects"},
    {"key": "invoice", "label": "Generate your first invoice", "to": "/projects"},
    {"key": "workspace", "label": "Explore the AI Workspace", "to": "/ai-workspace"},
    {"key": "brain", "label": "Open your Knowledge Brain", "to": "/knowledge-brain"},
]


@router.get("/checklist")
async def checklist(user: dict = Depends(current_user)):
    org = user["organizationId"]
    flags = user.get("onboarding_flags", {})
    profile = await db.business_profiles.find_one({"organizationId": org}, {"_id": 0, "sections": 1})
    state = {
        "profile": bool((profile or {}).get("sections")) or bool(flags.get("profile")),
        "client": (await db.clients.count_documents({"organizationId": org, "is_demo": {"$ne": True}})) > 0,
        "proposal": (await db.ai_proposals.count_documents({"organizationId": org, "is_demo": {"$ne": True}})) > 0,
        "invoice": (await db.ai_invoices.count_documents({"organizationId": org, "is_demo": {"$ne": True}})) > 0,
        "workspace": bool(flags.get("workspace")),
        "brain": bool(flags.get("brain")),
    }
    items = [{**c, "done": state.get(c["key"], False)} for c in CHECKLIST]
    done = sum(1 for i in items if i["done"])
    return {"items": items, "done": done, "total": len(items),
            "percent": round(done / len(items) * 100), "completed": user.get("onboardingCompleted", False)}
