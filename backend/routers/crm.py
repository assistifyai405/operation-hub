"""AI CRM & Sales Pipeline — Leads (deals), pipeline Kanban, AI Sales Assistant,
customer timelines, follow-ups, global CRM search and sales metrics. Built on the
existing Clients/Projects/Proposals/Contracts/Invoices — no duplicate data models.
"""
import re
import json
import uuid
import hashlib
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, now_iso, log_activity, ai_service
from ai_service import extract_json
from dependencies import current_org

router = APIRouter(prefix="/api/crm")

STAGES = ["New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating", "Won", "Lost"]
OPEN_STAGES = STAGES[:5]
STAGE_PROB = {"New": 10, "Qualified": 25, "Meeting Scheduled": 45, "Proposal Sent": 60,
              "Negotiating": 80, "Won": 100, "Lost": 0}


def _now():
    return datetime.now(timezone.utc)


def _age_days(iso):
    if not iso:
        return 0
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (_now() - dt).days)
    except Exception:
        return 0


def _lead_score(lead):
    stage = lead.get("stage", "New")
    if stage == "Won":
        return 100
    if stage == "Lost":
        return 0
    prob = lead.get("probability") if lead.get("probability") is not None else STAGE_PROB.get(stage, 10)
    val = lead.get("value") or 0
    vfac = min(100, (val / 20000) * 100)
    fresh = max(0, 100 - _age_days(lead.get("updated_at") or lead.get("created_at")) * 4)
    return round(0.55 * prob + 0.25 * vfac + 0.20 * fresh)


def _ai_confidence(lead):
    have = sum(1 for k in ("value", "expected_close", "client_id", "notes", "email") if lead.get(k))
    return min(96, 70 + have * 5)


def _decorate(lead):
    lead["score"] = _lead_score(lead)
    lead["probability"] = lead.get("probability") if lead.get("probability") is not None else STAGE_PROB.get(lead.get("stage"), 10)
    lead["ai_confidence"] = _ai_confidence(lead)
    lead["color"] = ("green" if lead["score"] >= 70 else "yellow" if lead["score"] >= 45 else "orange" if lead["score"] >= 25 else "red")
    return lead


async def _client_name(org, cid):
    if not cid:
        return None
    c = await db.clients.find_one({"id": cid, "organizationId": org}, {"_id": 0, "name": 1})
    return c.get("name") if c else None


# ============================ Leads ============================
class LeadCreate(BaseModel):
    title: str = Field(..., min_length=1)
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    stage: str = "New"
    value: float = 0
    probability: Optional[int] = None
    expected_close: str = ""
    owner: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    source: str = ""
    notes: str = ""
    tags: List[str] = Field(default_factory=list)


@router.get("/leads")
async def list_leads(org: str = Depends(current_org)):
    leads = await db.leads.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for l in leads:
        _decorate(l)
        l["client_name"] = await _client_name(org, l.get("client_id"))
    return leads


@router.get("/pipeline")
async def pipeline(org: str = Depends(current_org), q: str = "", owner: str = "", sort: str = "score"):
    leads = await db.leads.find({"organizationId": org}, {"_id": 0}).to_list(1000)
    for l in leads:
        _decorate(l)
        l["client_name"] = await _client_name(org, l.get("client_id"))
    if q:
        ql = q.lower()
        leads = [l for l in leads if ql in (l.get("title", "") + " " + (l.get("client_name") or "") + " " + l.get("contact_name", "") + " " + l.get("email", "")).lower()]
    if owner:
        leads = [l for l in leads if l.get("owner") == owner]
    keyfn = {"score": lambda x: -x["score"], "value": lambda x: -(x.get("value") or 0),
             "close": lambda x: (x.get("expected_close") or "9999")}.get(sort, lambda x: -x["score"])
    leads.sort(key=keyfn)
    columns = []
    for st in STAGES:
        items = [l for l in leads if l.get("stage") == st]
        columns.append({"stage": st, "count": len(items),
                        "value": sum(l.get("value") or 0 for l in items), "items": items})
    return {"columns": columns, "stages": STAGES}


@router.post("/leads")
async def create_lead(payload: LeadCreate, org: str = Depends(current_org)):
    if payload.stage not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    doc = payload.model_dump()
    doc.update({"id": str(uuid.uuid4()), "organizationId": org, "created_at": now_iso(),
                "updated_at": now_iso(), "stage_changed_at": now_iso(),
                "stage_history": [{"stage": payload.stage, "at": now_iso()}]})
    await db.leads.insert_one(doc)
    doc.pop("_id", None)
    _decorate(doc)
    doc["client_name"] = await _client_name(org, doc.get("client_id"))
    return doc


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, payload: LeadCreate, org: str = Depends(current_org)):
    existing = await db.leads.find_one({"id": lead_id, "organizationId": org}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")
    upd = payload.model_dump()
    upd["updated_at"] = now_iso()
    hist = existing.get("stage_history", [])
    if payload.stage != existing.get("stage"):
        upd["stage_changed_at"] = now_iso()
        hist = hist + [{"stage": payload.stage, "at": now_iso()}]
    upd["stage_history"] = hist
    await db.leads.update_one({"id": lead_id, "organizationId": org}, {"$set": upd})
    merged = {**existing, **upd}
    _decorate(merged)
    merged["client_name"] = await _client_name(org, merged.get("client_id"))
    return merged


class StageBody(BaseModel):
    stage: str


@router.patch("/leads/{lead_id}/stage")
async def move_stage(lead_id: str, body: StageBody, org: str = Depends(current_org)):
    if body.stage not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    lead = await db.leads.find_one({"id": lead_id, "organizationId": org}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    hist = lead.get("stage_history", []) + [{"stage": body.stage, "at": now_iso()}]
    await db.leads.update_one({"id": lead_id, "organizationId": org},
                              {"$set": {"stage": body.stage, "stage_changed_at": now_iso(),
                                        "updated_at": now_iso(), "stage_history": hist}})
    lead["stage"] = body.stage
    lead["updated_at"] = now_iso()
    _decorate(lead)
    lead["client_name"] = await _client_name(org, lead.get("client_id"))
    return lead


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, org: str = Depends(current_org)):
    res = await db.leads.delete_one({"id": lead_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, org: str = Depends(current_org)):
    lead = await db.leads.find_one({"id": lead_id, "organizationId": org}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    _decorate(lead)
    lead["client_name"] = await _client_name(org, lead.get("client_id"))
    lead["timeline"] = await _lead_timeline(org, lead)
    lead["followups"] = _followups(lead)
    return lead


@router.post("/leads/{lead_id}/convert")
async def convert_lead(lead_id: str, org: str = Depends(current_org)):
    lead = await db.leads.find_one({"id": lead_id, "organizationId": org}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    pid = lead.get("project_id")
    if not pid:
        pid = str(uuid.uuid4())
        await db.projects.insert_one({
            "id": pid, "organizationId": org, "name": lead.get("title"),
            "client_id": lead.get("client_id"), "status": "In Progress", "progress": 0,
            "due": lead.get("expected_close", ""), "members": 1,
            "description": lead.get("notes", ""), "notes": "", "created_at": now_iso()})
        await log_activity(pid, "project_created", f'Project "{lead.get("title")}" created from lead')
        await db.leads.update_one({"id": lead_id, "organizationId": org},
                                  {"$set": {"project_id": pid, "updated_at": now_iso()}})
    return {"ok": True, "project_id": pid}


# ============================ Follow-ups ============================
def _followups(lead):
    stage, out = lead.get("stage"), []
    age = _age_days(lead.get("stage_changed_at") or lead.get("updated_at"))
    def f(kind, label, why):
        out.append({"kind": kind, "label": label, "why": why})
    if stage == "New":
        f("email", "Send intro / qualifying email", "Reach out while interest is fresh.")
    elif stage == "Qualified":
        f("meeting", "Schedule a discovery meeting", "Book time to understand their needs.")
    elif stage == "Meeting Scheduled":
        f("call", "Prepare & confirm the meeting", "A confirmed, prepared meeting converts better.")
    elif stage == "Proposal Sent":
        f("proposal", "Follow up on the proposal", "Proposals go cold fast without a nudge.")
        if age >= 3:
            f("email", "Send a proposal reminder", f"Sent {age} days ago with no reply.")
    elif stage == "Negotiating":
        f("contract", "Send the contract to close", "You're close — make it easy to sign.")
    if age >= 10 and stage in OPEN_STAGES:
        f("email", "Re-engage — deal is going quiet", f"No stage change in {age} days.")
    return out


# ============================ Timeline ============================
async def _lead_timeline(org, lead):
    events = []
    def add(etype, title, icon, when, meta=None):
        events.append({"type": etype, "title": title, "icon": icon, "when": when, "meta": meta or {}})
    add("lead_created", "Lead created", "target", lead.get("created_at"))
    for h in lead.get("stage_history", []):
        add("stage", f"Moved to {h['stage']}", "arrow-right", h.get("at"))
    pid = lead.get("project_id")
    if pid:
        for p in await db.ai_proposals.find({"project_id": pid, "organizationId": org}, {"_id": 0}).to_list(50):
            add("proposal", f"Proposal {p.get('status', '')}".strip(), "file-text", p.get("updated_at") or p.get("created_at"))
        for c in await db.ai_contracts.find({"project_id": pid, "organizationId": org}, {"_id": 0}).to_list(50):
            add("contract", f"Contract {c.get('status', '')}".strip(), "scroll-text", c.get("updated_at") or c.get("created_at"))
        for i in await db.ai_invoices.find({"project_id": pid, "organizationId": org}, {"_id": 0}).to_list(50):
            add("invoice", f"Invoice {i.get('status', '')}".strip(), "receipt", i.get("updated_at") or i.get("created_at"))
        for a in await db.activities.find({"project_id": pid, "organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(50):
            add("activity", a.get("message", "Activity"), "clock", a.get("created_at"))
        for a in await db.ai_activities.find({"organizationId": org, "related.project_id": pid}, {"_id": 0}).to_list(50):
            add("ai", a.get("title", "AI action"), "sparkles", a.get("created_at"))
    events = [e for e in events if e.get("when")]
    events.sort(key=lambda x: x["when"], reverse=True)
    return events[:60]


async def _contact_timeline(org, client_id):
    projects = await db.projects.find({"client_id": client_id, "organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(200)
    pids = [p["id"] for p in projects]
    events = []
    def add(etype, title, icon, when):
        if when:
            events.append({"type": etype, "title": title, "icon": icon, "when": when})
    for lead in await db.leads.find({"client_id": client_id, "organizationId": org}, {"_id": 0}).to_list(100):
        add("lead", f"Lead: {lead.get('title')}", "target", lead.get("created_at"))
    if pids:
        for a in await db.activities.find({"project_id": {"$in": pids}, "organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(80):
            add("activity", a.get("message", "Activity"), "clock", a.get("created_at"))
        for a in await db.ai_activities.find({"organizationId": org, "related.project_id": {"$in": pids}}, {"_id": 0}).to_list(80):
            add("ai", a.get("title", "AI action"), "sparkles", a.get("created_at"))
    events.sort(key=lambda x: x["when"], reverse=True)
    return events[:60]


# ============================ AI Sales brief ============================
async def _lead_ai_context(org, lead):
    ctx = {"lead": {k: lead.get(k) for k in ("title", "stage", "value", "probability", "expected_close", "notes", "contact_name", "email", "source")}}
    if lead.get("client_id"):
        c = await db.clients.find_one({"id": lead["client_id"], "organizationId": org}, {"_id": 0})
        if c:
            ctx["client"] = {k: c.get(k) for k in ("name", "industry", "company_size", "website", "notes", "value", "status")}
    pid = lead.get("project_id")
    if pid:
        props = await db.ai_proposals.find({"project_id": pid, "organizationId": org}, {"_id": 0, "status": 1, "title": 1}).to_list(10)
        cons = await db.ai_contracts.find({"project_id": pid, "organizationId": org}, {"_id": 0, "status": 1}).to_list(10)
        invs = await db.ai_invoices.find({"project_id": pid, "organizationId": org}, {"_id": 0, "status": 1}).to_list(10)
        ctx["documents"] = {"proposals": props, "contracts": cons, "invoices": invs}
    ctx["days_in_stage"] = _age_days(lead.get("stage_changed_at") or lead.get("updated_at"))
    return ctx


BRIEF_SYSTEM = (
    "You are Assistify's AI Sales Assistant. Given a sales lead and its context, produce a sharp, realistic sales brief. "
    "Return ONLY a JSON object with keys: relationship_summary (string), conversation_summary (string), "
    "missing_info (array of short strings), suggested_followup (string), objections (array of short strings), "
    "deal_health (one of 'Healthy','At Risk','Critical'), win_probability (integer 0-100), "
    "urgency (one of 'Low','Medium','High'), risk_level (one of 'Low','Medium','High'), next_best_action (string). "
    "Be concise and specific to the data. Do not invent facts that contradict the context."
)


@router.post("/leads/{lead_id}/ai-brief")
async def lead_ai_brief(lead_id: str, org: str = Depends(current_org), refresh: bool = False):
    lead = await db.leads.find_one({"id": lead_id, "organizationId": org}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    _decorate(lead)
    ctx = await _lead_ai_context(org, lead)
    sig = hashlib.md5(json.dumps(ctx, sort_keys=True, default=str).encode()).hexdigest()
    if not refresh:
        cached = await db.lead_ai_briefs.find_one({"lead_id": lead_id, "organizationId": org, "sig": sig}, {"_id": 0})
        if cached:
            return cached["brief"]
    prompt = f"LEAD CONTEXT (JSON):\n{json.dumps(ctx, default=str)}"
    try:
        raw = await ai_service.complete(BRIEF_SYSTEM, prompt, session_id=f"sales-{lead_id}")
        brief = extract_json(raw)
    except Exception as e:
        logging.exception("lead ai brief failed")
        raise HTTPException(status_code=502, detail=f"AI Sales Assistant is unavailable: {e}")
    brief.setdefault("win_probability", lead.get("probability", 0))
    brief["generated_at"] = now_iso()
    await db.lead_ai_briefs.update_one({"lead_id": lead_id, "organizationId": org},
                                       {"$set": {"lead_id": lead_id, "organizationId": org, "sig": sig, "brief": brief, "created_at": now_iso()}},
                                       upsert=True)
    return brief


# ============================ Contacts (enriched clients) ============================
@router.get("/contacts")
async def list_contacts(org: str = Depends(current_org)):
    clients = await db.clients.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    leads = await db.leads.find({"organizationId": org}, {"_id": 0}).to_list(1000)
    lead_by_client = {}
    for l in leads:
        lead_by_client.setdefault(l.get("client_id"), []).append(l)
    out = []
    for c in clients:
        cl = lead_by_client.get(c["id"], [])
        openl = [l for l in cl if l.get("stage") in OPEN_STAGES]
        c["projects_count"] = await db.projects.count_documents({"client_id": c["id"], "organizationId": org})
        c["open_leads"] = len(openl)
        c["pipeline_value"] = sum(l.get("value") or 0 for l in openl)
        last = await db.activities.find_one({"organizationId": org, "project_id": {"$in": [p["id"] for p in await db.projects.find({"client_id": c["id"], "organizationId": org}, {"_id": 0, "id": 1}).to_list(200)]}}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
        c["last_activity"] = last.get("created_at") if last else c.get("created_at")
        out.append(c)
    return out


@router.get("/contacts/{client_id}")
async def get_contact(client_id: str, org: str = Depends(current_org)):
    c = await db.clients.find_one({"id": client_id, "organizationId": org}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    projects = await db.projects.find({"client_id": client_id, "organizationId": org}, {"_id": 0}).to_list(200)
    pids = [p["id"] for p in projects]
    leads = await db.leads.find({"client_id": client_id, "organizationId": org}, {"_id": 0}).to_list(200)
    for l in leads:
        _decorate(l)
    c["projects"] = projects
    c["leads"] = leads
    c["proposals"] = await db.ai_proposals.find({"project_id": {"$in": pids}, "organizationId": org}, {"_id": 0, "id": 1, "title": 1, "status": 1, "project_id": 1}).to_list(100) if pids else []
    c["contracts"] = await db.ai_contracts.find({"project_id": {"$in": pids}, "organizationId": org}, {"_id": 0, "id": 1, "status": 1, "project_id": 1}).to_list(100) if pids else []
    c["invoices"] = await db.ai_invoices.find({"project_id": {"$in": pids}, "organizationId": org}, {"_id": 0, "id": 1, "invoice_number": 1, "status": 1, "total": 1, "project_id": 1}).to_list(100) if pids else []
    c["timeline"] = await _contact_timeline(org, client_id)
    c["pipeline_value"] = sum(l.get("value") or 0 for l in leads if l.get("stage") in OPEN_STAGES)
    return c


CONTACT_SUMMARY_SYSTEM = (
    "You are Assistify's AI relationship analyst. Given a client/company and their history, write a concise "
    "relationship summary. Return ONLY JSON: {\"summary\": string (2-3 sentences), \"strengths\": array of short strings, "
    "\"risks\": array of short strings, \"next_best_action\": string}. Be specific to the data; don't invent facts."
)


@router.post("/contacts/{client_id}/ai-summary")
async def contact_ai_summary(client_id: str, org: str = Depends(current_org), refresh: bool = False):
    c = await db.clients.find_one({"id": client_id, "organizationId": org}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    if not refresh and c.get("ai_summary"):
        return c["ai_summary"]
    projects = await db.projects.find({"client_id": client_id, "organizationId": org}, {"_id": 0, "name": 1, "status": 1, "id": 1}).to_list(50)
    pids = [p["id"] for p in projects]
    leads = await db.leads.find({"client_id": client_id, "organizationId": org}, {"_id": 0, "title": 1, "stage": 1, "value": 1}).to_list(50)
    invs = await db.ai_invoices.find({"project_id": {"$in": pids}, "organizationId": org}, {"_id": 0, "status": 1, "total": 1}).to_list(50) if pids else []
    ctx = {"client": {k: c.get(k) for k in ("name", "industry", "company_size", "website", "notes", "value", "status")},
           "projects": projects, "leads": leads, "invoices": invs}
    prompt = f"CLIENT CONTEXT (JSON):\n{json.dumps(ctx, default=str)}"
    try:
        raw = await ai_service.complete(CONTACT_SUMMARY_SYSTEM, prompt, session_id=f"contact-{client_id}")
        summary = extract_json(raw)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI relationship analyst is unavailable: {e}")
    summary["generated_at"] = now_iso()
    await db.clients.update_one({"id": client_id, "organizationId": org}, {"$set": {"ai_summary": summary}})
    return summary


# ============================ Global CRM search ============================
@router.get("/search")
async def crm_search(q: str, org: str = Depends(current_org)):
    if not q or len(q) < 1:
        return {"results": []}
    rx = {"$regex": re.escape(q), "$options": "i"}
    base = {"organizationId": org}
    results = []
    for c in await db.clients.find({**base, "$or": [{"name": rx}, {"contact": rx}, {"email": rx}, {"notes": rx}, {"industry": rx}, {"website": rx}]}, {"_id": 0}).to_list(20):
        results.append({"type": "contact", "icon": "users", "title": c["name"], "subtitle": c.get("industry") or c.get("email") or "Company", "link": f"/crm/{c['id']}"})
    for l in await db.leads.find({**base, "$or": [{"title": rx}, {"contact_name": rx}, {"email": rx}, {"notes": rx}]}, {"_id": 0}).to_list(20):
        results.append({"type": "lead", "icon": "target", "title": l["title"], "subtitle": f"{l.get('stage')} · deal", "link": "/pipeline"})
    for p in await db.projects.find({**base, "$or": [{"name": rx}, {"description": rx}, {"notes": rx}]}, {"_id": 0}).to_list(20):
        results.append({"type": "project", "icon": "folder-kanban", "title": p["name"], "subtitle": p.get("status") or "Project", "link": f"/projects/{p['id']}"})
    for p in await db.ai_proposals.find({**base, "title": rx}, {"_id": 0}).to_list(15):
        results.append({"type": "proposal", "icon": "file-text", "title": p.get("title") or "Proposal", "subtitle": f"Proposal · {p.get('status')}", "link": f"/projects/{p.get('project_id')}?tab=proposal"})
    for i in await db.ai_invoices.find({**base, "invoice_number": rx}, {"_id": 0}).to_list(15):
        results.append({"type": "invoice", "icon": "receipt", "title": i.get("invoice_number") or "Invoice", "subtitle": f"Invoice · {i.get('status')}", "link": f"/projects/{i.get('project_id')}?tab=invoice"})
    return {"results": results, "total": len(results)}


# ============================ Sales metrics ============================
@router.get("/sales-metrics")
async def sales_metrics(org: str = Depends(current_org)):
    leads = await db.leads.find({"organizationId": org}, {"_id": 0}).to_list(1000)
    for l in leads:
        _decorate(l)
    open_leads = [l for l in leads if l.get("stage") in OPEN_STAGES]
    won = [l for l in leads if l.get("stage") == "Won"]
    lost = [l for l in leads if l.get("stage") == "Lost"]
    pipeline_value = sum(l.get("value") or 0 for l in open_leads)
    weighted = sum((l.get("value") or 0) * (l.get("probability") or 0) / 100 for l in open_leads)
    week = (_now() + timedelta(days=7)).strftime("%Y-%m-%d")
    today = _now().strftime("%Y-%m-%d")
    closing = [l for l in open_leads if l.get("expected_close") and today <= str(l["expected_close"])[:10] <= week]
    attention = sorted([l for l in open_leads if _age_days(l.get("stage_changed_at") or l.get("updated_at")) >= 7], key=lambda x: -x["score"])[:6]
    win_rate = round(len(won) / max(1, len(won) + len(lost)) * 100)
    avg_deal = round(sum(l.get("value") or 0 for l in won) / len(won)) if won else 0
    conv = round(len(won) / max(1, len(leads)) * 100)
    insights = []
    if closing:
        insights.append(f"{len(closing)} deal(s) worth ${sum(l.get('value') or 0 for l in closing):,.0f} are expected to close this week.")
    if attention:
        insights.append(f"{len(attention)} open deal(s) have gone quiet for a week or more — a nudge could revive them.")
    hot = [l for l in open_leads if l["score"] >= 70]
    if hot:
        insights.append(f"{len(hot)} high-scoring lead(s) are hot right now — prioritize these.")
    if not insights:
        insights.append("Your pipeline is quiet. Add new leads or advance existing ones to keep momentum.")
    return {
        "pipeline_value": pipeline_value, "weighted_pipeline": round(weighted),
        "open_count": len(open_leads), "closing_this_week": closing,
        "leads_needing_attention": attention, "win_rate": win_rate,
        "avg_deal_size": avg_deal, "conversion_rate": conv,
        "won_count": len(won), "lost_count": len(lost), "total_leads": len(leads),
        "ai_insights": insights,
        "stage_breakdown": [{"stage": s, "count": len([l for l in leads if l.get("stage") == s]),
                             "value": sum(l.get("value") or 0 for l in leads if l.get("stage") == s)} for s in STAGES],
    }
