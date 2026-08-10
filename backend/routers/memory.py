"""AI Memory & Knowledge Brain — Assistify learns structured knowledge from the
workspace and reuses it to improve future AI output. Learns from user edits
(approvals/rejections), distills memories, builds an evolving business profile and
insights, and injects relevant memories back into the AI Assistant + generators.
"""
import re
import json
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, now_iso, ai_service
from ai_service import extract_json
from dependencies import current_org

router = APIRouter(prefix="/api/memory")

CATEGORIES = ["Business", "Writing Style", "Pricing", "Customers", "Projects", "Processes",
              "Frequently Used Terms", "Products", "Services", "Brand Voice", "Policies",
              "Preferences", "Relationships"]

CAT_ICON = {"Business": "building", "Writing Style": "file-text", "Pricing": "badge-dollar-sign",
            "Customers": "users", "Projects": "folder-kanban", "Processes": "list-checks",
            "Frequently Used Terms": "sparkles", "Products": "receipt", "Services": "sparkles",
            "Brand Voice": "sparkles", "Policies": "scroll-text", "Preferences": "sparkles",
            "Relationships": "users"}

LEARN_THRESHOLD = 4


def _parse_flexible(raw):
    """Parse LLM output that may be a JSON array or object, possibly fenced."""
    t = (raw or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    t = t.strip()
    a, ae = t.find("["), t.rfind("]")
    o, oe = t.find("{"), t.rfind("}")
    if a != -1 and (o == -1 or a < o):
        return json.loads(t[a:ae + 1])
    if o != -1:
        return json.loads(t[o:oe + 1])
    return json.loads(t)


def _now():
    return datetime.now(timezone.utc)


def _decorate(m):
    m["icon"] = CAT_ICON.get(m.get("category"), "sparkles")
    return m


# ---------------- Smart reuse (used by assistant + generators) ----------------
async def top_memories(org, limit=8, categories=None):
    q = {"organizationId": org, "learning_enabled": {"$ne": False}}
    if categories:
        q["category"] = {"$in": categories}
    mems = await db.memories.find(q, {"_id": 0}).to_list(500)
    mems.sort(key=lambda m: (not m.get("pinned"), -(m.get("confidence") or 0), -(m.get("times_used") or 0)))
    return mems[:limit]


async def build_memory_prompt(org, categories=None, limit=8):
    """Formatted suffix injected into AI prompts. No side effects."""
    mems = await top_memories(org, limit, categories)
    if not mems:
        return ""
    lines = [f"- [{m['category']}] {m['title']}: {m.get('content', '')}" for m in mems]
    return ("\n\nKNOWN BUSINESS PREFERENCES & LEARNED KNOWLEDGE (reuse where relevant, "
            "match the user's established style and terminology):\n" + "\n".join(lines))


async def build_memory_context(org, categories=None, limit=8):
    """Like build_memory_prompt but records usage (call from interactive flows)."""
    mems = await top_memories(org, limit, categories)
    if mems:
        ids = [m["id"] for m in mems]
        await db.memories.update_many({"organizationId": org, "id": {"$in": ids}},
                                      {"$inc": {"times_used": 1}, "$set": {"last_used_at": now_iso()}})
    if not mems:
        return ""
    lines = [f"- [{m['category']}] {m['title']}: {m.get('content', '')}" for m in mems]
    return ("\n\nKNOWN BUSINESS PREFERENCES & LEARNED KNOWLEDGE (reuse and honor these):\n" + "\n".join(lines))


# ---------------- Memory CRUD ----------------
class MemoryBody(BaseModel):
    title: str = Field(..., min_length=1)
    category: str = "Business"
    content: str = ""
    keywords: List[str] = Field(default_factory=list)
    confidence: int = 80
    source: str = "Manual"


async def _memory_doc(payload, org):
    return {"id": str(uuid.uuid4()), "organizationId": org, "title": payload.title,
            "category": payload.category, "content": payload.content, "keywords": payload.keywords,
            "confidence": max(0, min(100, payload.confidence)), "source": payload.source,
            "times_used": 0, "pinned": False, "learning_enabled": True,
            "created_at": now_iso(), "updated_at": now_iso()}


@router.get("/memories")
async def list_memories(org: str = Depends(current_org), category: str = "", q: str = "", sort: str = "recent"):
    query = {"organizationId": org}
    if category:
        query["category"] = category
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"title": rx}, {"content": rx}, {"category": rx}, {"keywords": rx}]
    mems = await db.memories.find(query, {"_id": 0}).to_list(1000)
    keyfn = {"recent": lambda m: m.get("updated_at") or "", "used": lambda m: m.get("times_used") or 0,
             "confidence": lambda m: m.get("confidence") or 0, "created": lambda m: m.get("created_at") or ""}.get(sort, lambda m: m.get("updated_at") or "")
    mems.sort(key=keyfn, reverse=True)
    mems.sort(key=lambda m: not m.get("pinned"))
    for m in mems:
        _decorate(m)
    return mems


@router.get("/stats")
async def memory_stats(org: str = Depends(current_org)):
    mems = await db.memories.find({"organizationId": org}, {"_id": 0}).to_list(2000)
    for m in mems:
        _decorate(m)
    today = _now().strftime("%Y-%m-%d")
    by_cat = {}
    for m in mems:
        by_cat[m["category"]] = by_cat.get(m["category"], 0) + 1
    most_used = sorted(mems, key=lambda m: -(m.get("times_used") or 0))[:5]
    newest = sorted(mems, key=lambda m: m.get("created_at") or "", reverse=True)[:5]
    learned_today = [m for m in mems if (m.get("created_at") or "")[:10] == today]
    recently_updated = sorted(mems, key=lambda m: m.get("updated_at") or "", reverse=True)[:5]
    unanalyzed = await db.learning_events.count_documents({"organizationId": org, "analyzed": {"$ne": True}})
    return {"total": len(mems), "categories": CATEGORIES,
            "by_category": [{"category": c, "count": by_cat.get(c, 0), "icon": CAT_ICON.get(c, "sparkles")} for c in CATEGORIES if by_cat.get(c)],
            "avg_confidence": round(sum(m.get("confidence", 0) for m in mems) / len(mems)) if mems else 0,
            "total_uses": sum(m.get("times_used", 0) for m in mems),
            "most_used": most_used, "newest": newest, "learned_today": learned_today,
            "recently_updated": recently_updated, "pending_learning": unanalyzed}


@router.post("/memories")
async def create_memory(payload: MemoryBody, org: str = Depends(current_org)):
    doc = await _memory_doc(payload, org)
    await db.memories.insert_one(dict(doc))
    return _decorate(doc)


@router.put("/memories/{mem_id}")
async def update_memory(mem_id: str, payload: MemoryBody, org: str = Depends(current_org)):
    ex = await db.memories.find_one({"id": mem_id, "organizationId": org}, {"_id": 0})
    if not ex:
        raise HTTPException(status_code=404, detail="Memory not found")
    upd = {"title": payload.title, "category": payload.category, "content": payload.content,
           "keywords": payload.keywords, "confidence": max(0, min(100, payload.confidence)),
           "updated_at": now_iso()}
    await db.memories.update_one({"id": mem_id, "organizationId": org}, {"$set": upd})
    return _decorate({**ex, **upd})


@router.delete("/memories/{mem_id}")
async def delete_memory(mem_id: str, org: str = Depends(current_org)):
    res = await db.memories.delete_one({"id": mem_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


class PinBody(BaseModel):
    pinned: bool


@router.patch("/memories/{mem_id}/pin")
async def pin_memory(mem_id: str, body: PinBody, org: str = Depends(current_org)):
    r = await db.memories.update_one({"id": mem_id, "organizationId": org}, {"$set": {"pinned": body.pinned, "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True, "pinned": body.pinned}


class LearnToggle(BaseModel):
    learning_enabled: bool


@router.patch("/memories/{mem_id}/learning")
async def toggle_learning(mem_id: str, body: LearnToggle, org: str = Depends(current_org)):
    r = await db.memories.update_one({"id": mem_id, "organizationId": org}, {"$set": {"learning_enabled": body.learning_enabled, "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True, "learning_enabled": body.learning_enabled}


class MergeBody(BaseModel):
    ids: List[str]
    title: str
    category: str
    content: str = ""


@router.post("/memories/merge")
async def merge_memories(body: MergeBody, org: str = Depends(current_org)):
    mems = await db.memories.find({"id": {"$in": body.ids}, "organizationId": org}, {"_id": 0}).to_list(50)
    if len(mems) < 2:
        raise HTTPException(status_code=400, detail="Select at least two memories to merge")
    content = body.content or " ".join(m.get("content", "") for m in mems)
    keywords = list({k for m in mems for k in (m.get("keywords") or [])})
    conf = round(sum(m.get("confidence", 0) for m in mems) / len(mems))
    uses = sum(m.get("times_used", 0) for m in mems)
    doc = {"id": str(uuid.uuid4()), "organizationId": org, "title": body.title, "category": body.category,
           "content": content, "keywords": keywords, "confidence": conf, "source": "Merged",
           "times_used": uses, "pinned": any(m.get("pinned") for m in mems), "learning_enabled": True,
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.memories.insert_one(dict(doc))
    await db.memories.delete_many({"id": {"$in": body.ids}, "organizationId": org})
    return _decorate(doc)


# ---------------- Learning ----------------
class LearnEvent(BaseModel):
    kind: str  # approval | rejection | edit
    doc_type: str = ""
    section: str = ""
    before: str = ""
    after: str = ""
    command: str = ""


@router.post("/learn/event")
async def log_learn_event(payload: LearnEvent, org: str = Depends(current_org)):
    await db.learning_events.insert_one({
        "id": str(uuid.uuid4()), "organizationId": org, "kind": payload.kind,
        "doc_type": payload.doc_type, "section": payload.section,
        "before": (payload.before or "")[:2000], "after": (payload.after or "")[:2000],
        "command": payload.command, "analyzed": False, "created_at": now_iso()})
    pending = await db.learning_events.count_documents({"organizationId": org, "analyzed": {"$ne": True}})
    learned = 0
    if pending >= LEARN_THRESHOLD:
        try:
            learned = await _analyze_events(org)
        except Exception:
            logging.exception("auto learn analyze failed")
    return {"ok": True, "pending": pending, "learned": learned}


LEARN_SYSTEM = (
    "You are Assistify's learning engine. You are given a batch of edit events where a user changed AI-generated "
    "text (approvals = they kept/applied a change, rejections = they undid it). Infer durable preferences about how "
    "this business likes its writing, pricing, structure, tone and terminology. "
    "Return ONLY a JSON array (max 5) of memory objects: "
    "{\"title\": short imperative pattern e.g. 'Prefers concise introductions', \"category\": one of "
    f"{CATEGORIES}, \"content\": one-sentence explanation, \"confidence\": integer 55-95, "
    "\"keywords\": array of 1-3 short strings}. Only include patterns clearly supported by the events."
)


async def _analyze_events(org):
    events = await db.learning_events.find({"organizationId": org, "analyzed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(20)
    if not events:
        return 0
    payload = [{"kind": e["kind"], "doc_type": e.get("doc_type"), "section": e.get("section"),
                "command": e.get("command"), "before": e.get("before", "")[:600], "after": e.get("after", "")[:600]} for e in events]
    raw = await ai_service.complete(LEARN_SYSTEM, f"EDIT EVENTS (JSON):\n{json.dumps(payload, default=str)}", session_id=f"learn-{org}")
    data = _parse_flexible(raw)
    items = data if isinstance(data, list) else data.get("memories", [])
    created = 0
    for it in items[:5]:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        cat = it.get("category") if it.get("category") in CATEGORIES else "Preferences"
        existing = await db.memories.find_one({"organizationId": org, "title": {"$regex": f"^{re.escape(title)}$", "$options": "i"}}, {"_id": 0, "id": 1, "confidence": 1})
        if existing:
            await db.memories.update_one({"id": existing["id"], "organizationId": org},
                                         {"$set": {"confidence": min(98, (existing.get("confidence", 70)) + 4),
                                                   "content": it.get("content", ""), "updated_at": now_iso()}})
        else:
            doc = {"id": str(uuid.uuid4()), "organizationId": org, "title": title, "category": cat,
                   "content": it.get("content", ""), "keywords": it.get("keywords", []),
                   "confidence": max(55, min(95, int(it.get("confidence", 70)))), "source": "Learned from your edits",
                   "times_used": 0, "pinned": False, "learning_enabled": True,
                   "created_at": now_iso(), "updated_at": now_iso()}
            await db.memories.insert_one(dict(doc))
            created += 1
    await db.learning_events.update_many({"organizationId": org, "id": {"$in": [e["id"] for e in events]}}, {"$set": {"analyzed": True}})
    return created


@router.post("/learn/analyze")
async def analyze_learning(org: str = Depends(current_org)):
    try:
        n = await _analyze_events(org)
    except Exception as e:
        from ai_service import public_ai_error
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Learning engine unavailable. Please try again."))
    return {"ok": True, "learned": n}


# ---------------- Business Profile ----------------
PROFILE_SYSTEM = (
    "You are Assistify's business analyst. From the workspace data and learned memories, produce an evolving "
    "business profile. Return ONLY JSON with keys: company_summary, services (array), target_audience, industries "
    "(array), typical_pricing, communication_style, proposal_style, contract_style, invoice_preferences, "
    "business_goals (array). Keep each concise and specific to the data. Don't invent facts."
)


@router.get("/business-profile")
async def get_business_profile(org: str = Depends(current_org)):
    p = await db.business_profiles.find_one({"organizationId": org}, {"_id": 0})
    return p or {"sections": None}


@router.post("/business-profile")
async def generate_business_profile(org: str = Depends(current_org)):
    base = {"organizationId": org}
    clients = await db.clients.find(base, {"_id": 0, "name": 1, "industry": 1, "value": 1}).to_list(200)
    projects = await db.projects.find(base, {"_id": 0, "name": 1, "description": 1, "status": 1}).to_list(200)
    invoices = await db.ai_invoices.find(base, {"_id": 0, "total": 1}).to_list(200)
    leads = await db.leads.find(base, {"_id": 0, "value": 1, "stage": 1}).to_list(200)
    mems = await top_memories(org, 20)
    ctx = {"clients": clients[:40], "projects": projects[:40],
           "invoice_totals": [i.get("total") for i in invoices][:40],
           "lead_values": [l.get("value") for l in leads][:40],
           "memories": [{"category": m["category"], "title": m["title"], "content": m.get("content")} for m in mems]}
    try:
        raw = await ai_service.complete(PROFILE_SYSTEM, f"WORKSPACE DATA (JSON):\n{json.dumps(ctx, default=str)}", session_id=f"profile-{org}")
        sections = extract_json(raw)
    except Exception as e:
        from ai_service import public_ai_error
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Business analyst unavailable. Please try again."))
    doc = {"organizationId": org, "sections": sections, "generated_at": now_iso()}
    await db.business_profiles.update_one({"organizationId": org}, {"$set": doc}, upsert=True)
    doc.pop("_id", None)
    return doc


# ---------------- AI Insights ----------------
INSIGHT_SYSTEM = (
    "You are Assistify's pattern analyst. From the data + memories, generate 3-5 concrete, useful business insights "
    "in the style of 'You usually win proposals when...', 'You often adjust pricing by...', 'Most successful projects "
    "include...', 'You communicate more formally with...'. Return ONLY a JSON array of "
    "{\"insight\": string, \"explanation\": string (why/what it's based on), \"icon\": one of "
    "['file-text','badge-dollar-sign','folder-kanban','users','sparkles']}. Base them on the data; if data is thin, "
    "give sensible directional insights and say they'll sharpen as more work is done."
)


@router.get("/insights")
async def memory_insights(org: str = Depends(current_org), refresh: bool = False):
    if not refresh:
        cached = await db.memory_insights_cache.find_one({"organizationId": org}, {"_id": 0})
        if cached and cached.get("created_at", "") > (_now() - timedelta(hours=12)).isoformat():
            return cached["insights"]
    base = {"organizationId": org}
    leads = await db.leads.find(base, {"_id": 0, "stage": 1, "value": 1, "source": 1}).to_list(300)
    projects = await db.projects.find(base, {"_id": 0, "status": 1}).to_list(300)
    mems = await top_memories(org, 20)
    ctx = {"leads_by_stage": {s: len([l for l in leads if l.get("stage") == s]) for s in set(l.get("stage") for l in leads)},
           "won_values": [l.get("value") for l in leads if l.get("stage") == "Won"],
           "projects_total": len(projects),
           "memories": [{"category": m["category"], "title": m["title"]} for m in mems]}
    try:
        raw = await ai_service.complete(INSIGHT_SYSTEM, f"DATA (JSON):\n{json.dumps(ctx, default=str)}", session_id=f"mem-insights-{org}")
        data = _parse_flexible(raw)
        insights = data if isinstance(data, list) else data.get("insights", [])
    except Exception as e:
        from ai_service import public_ai_error
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Pattern analyst unavailable. Please try again."))
    await db.memory_insights_cache.update_one({"organizationId": org},
                                              {"$set": {"organizationId": org, "insights": insights, "created_at": now_iso()}}, upsert=True)
    return insights


# ---------------- Search + Ask ----------------
@router.get("/search")
async def search_memories(q: str, org: str = Depends(current_org)):
    if not q:
        return {"results": []}
    rx = {"$regex": re.escape(q), "$options": "i"}
    mems = await db.memories.find({"organizationId": org, "$or": [{"title": rx}, {"content": rx}, {"keywords": rx}, {"category": rx}]}, {"_id": 0}).to_list(50)
    for m in mems:
        _decorate(m)
    mems.sort(key=lambda m: -(m.get("confidence") or 0))
    return {"results": mems, "total": len(mems)}


class AskBody(BaseModel):
    question: str


@router.post("/ask")
async def ask_brain(body: AskBody, org: str = Depends(current_org)):
    mems = await db.memories.find({"organizationId": org}, {"_id": 0}).to_list(200)
    if not mems:
        return {"answer": "I haven't learned anything about your business yet. As you use Assistify and edit AI output, I'll build up knowledge here.", "used": []}
    corpus = [{"title": m["title"], "category": m["category"], "content": m.get("content", "")} for m in mems]
    system = ("You are Assistify's Knowledge Brain. Answer the user's question using ONLY the provided memories about "
              "their business. Be concise and specific. If the memories don't cover it, say what you do and don't know.")
    prompt = f"MEMORIES (JSON):\n{json.dumps(corpus, default=str)}\n\nQUESTION: {body.question}"
    try:
        answer = await ai_service.complete(system, prompt, session_id=f"ask-brain-{org}")
    except Exception as e:
        from ai_service import public_ai_error
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Knowledge Brain unavailable. Please try again."))
    return {"answer": answer.strip(), "used": len(mems)}
