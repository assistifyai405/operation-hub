import re
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from core import db, ai_service
from ai_service import extract_json
from dependencies import current_org
import ai_activity as aia

router = APIRouter(prefix="/api/ai")


def _now():
    return datetime.now(timezone.utc)


def _iso_days_ago(days):
    return (_now() - timedelta(days=days)).isoformat()


# ---------------- Activity feed ----------------
@router.get("/activities")
async def list_activities(org: str = Depends(current_org), scope: str = "today", limit: int = 20):
    await aia.ensure_backfill(org)
    query = {"organizationId": org}
    if scope == "today":
        query["created_at"] = {"$gte": _now().strftime("%Y-%m-%dT00:00:00+00:00")}
    items = await db.ai_activities.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items


@router.get("/activities/history")
async def activity_history(org: str = Depends(current_org)):
    await aia.ensure_backfill(org)
    items = await db.ai_activities.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(500)
    today = _now().strftime("%Y-%m-%d")
    yesterday = (_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (_now() - timedelta(days=7)).strftime("%Y-%m-%d")
    groups = {"Today": [], "Yesterday": [], "This Week": [], "Earlier": []}
    for it in items:
        d = (it.get("created_at") or "")[:10]
        if d == today:
            groups["Today"].append(it)
        elif d == yesterday:
            groups["Yesterday"].append(it)
        elif d >= week_ago:
            groups["This Week"].append(it)
        else:
            groups["Earlier"].append(it)
    total_saved = sum(it.get("time_saved", 0) for it in items)
    return {"groups": [{"label": k, "items": v} for k, v in groups.items() if v],
            "total": len(items), "total_time_saved": total_saved}


# ---------------- Time saved ----------------
@router.get("/time-saved")
async def time_saved(org: str = Depends(current_org)):
    await aia.ensure_backfill(org)
    async def _sum(since=None):
        q = {"organizationId": org}
        if since:
            q["created_at"] = {"$gte": since}
        rows = await db.ai_activities.find(q, {"_id": 0, "time_saved": 1}).to_list(5000)
        return sum(a.get("time_saved", 0) for a in rows)
    today0 = _now().strftime("%Y-%m-%dT00:00:00+00:00")
    return {
        "today": await _sum(today0),
        "week": await _sum(_iso_days_ago(7)),
        "month": await _sum(_iso_days_ago(30)),
        "lifetime": await _sum(),
        "count": await db.ai_activities.count_documents({"organizationId": org}),
    }


# ---------------- Proactive insights (rules + cached LLM polish) ----------------
async def _compute_facts(org: str):
    base = {"organizationId": org}
    today = _now().strftime("%Y-%m-%d")
    facts = []
    # Overdue / unpaid invoices
    invs = await db.ai_invoices.find({**base, "status": {"$in": ["Sent", "Overdue"]}},
                                     {"_id": 0, "invoice_number": 1, "status": 1, "total": 1, "content": 1, "project_id": 1}).to_list(50)
    for inv in invs:
        due = (inv.get("content") or {}).get("due_date")
        overdue_days = None
        if due and str(due) < today:
            try:
                overdue_days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(str(due)[:10], "%Y-%m-%d")).days
            except Exception:
                overdue_days = None
        if inv.get("status") == "Overdue" or overdue_days:
            facts.append({"type": "invoice_overdue", "severity": "high", "icon": "receipt",
                          "subject": inv.get("invoice_number") or "An invoice", "days": overdue_days,
                          "amount": inv.get("total"), "link": f"/projects/{inv.get('project_id')}?tab=invoice",
                          "default": f"Invoice {inv.get('invoice_number') or ''} is {('%d days ' % overdue_days) if overdue_days else ''}overdue. Sending a polite payment reminder today usually gets the fastest response.".replace("  ", " ").strip()})
    # Stale sent proposals -> follow up
    stale = await db.ai_proposals.find({**base, "status": "Sent", "updated_at": {"$lt": _iso_days_ago(3)}},
                                       {"_id": 0, "title": 1, "project_id": 1, "updated_at": 1}).to_list(20)
    pmap = {p["id"]: p["name"] for p in await db.projects.find(base, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
    for pr in stale:
        nm = pmap.get(pr.get("project_id"), "a client")
        facts.append({"type": "proposal_followup", "severity": "medium", "icon": "file-text",
                      "subject": nm, "link": f"/projects/{pr.get('project_id')}?tab=proposal",
                      "default": f"Your proposal for {nm} was sent a few days ago with no reply yet. Based on similar deals, a short follow-up today has the highest chance of a response."})
    # Tasks due today or overdue
    open_tasks = await db.tasks.find({**base, "done": False}, {"_id": 0, "due": 1}).to_list(500)
    due_now = [t for t in open_tasks if t.get("due") and str(t["due"]) <= today]
    if due_now:
        facts.append({"type": "tasks_today", "severity": "medium", "icon": "check-square",
                      "count": len(due_now), "link": "/tasks",
                      "default": f"You have {len(due_now)} task{'s' if len(due_now) != 1 else ''} due today or overdue. Clearing these keeps your projects on track."})
    # Blocked / stalled projects (in progress, no recent activity)
    active = await db.projects.find({**base, "status": {"$in": ["In Progress", "Review"]}}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    for pj in active[:20]:
        last = await db.activities.find_one({"organizationId": org, "project_id": pj["id"]}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
        if not last or (last.get("created_at") or "") < _iso_days_ago(7):
            facts.append({"type": "project_stalled", "severity": "low", "icon": "folder-kanban",
                          "subject": pj["name"], "link": f"/projects/{pj['id']}",
                          "default": f"{pj['name']} hasn't had any activity in over a week and may be blocked. Worth a quick check-in."})
            break  # surface at most one stalled project
    return facts[:6]


async def _polish(org: str, facts: list):
    if not facts:
        return []
    raw = [f["default"] for f in facts]
    key = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    cached = await db.ai_insight_cache.find_one({"organizationId": org, "key": key}, {"_id": 0})
    if cached and cached.get("expires_at", "") > _now().isoformat():
        return cached["polished"]
    polished = raw
    try:
        system = ("You refine short business assistant messages. Return ONLY a JSON array of strings, "
                  "same length and order as input. Keep each under 240 chars, warm, human, professional, "
                  "non-technical. Always explain WHY the action matters. Do not invent facts.")
        out = await ai_service.complete(system, json.dumps(raw), session_id=f"insights-{org}")
        parsed = extract_json(out)
        if isinstance(parsed, list) and len(parsed) == len(raw):
            polished = [str(x) for x in parsed]
    except Exception:
        logging.exception("insight polish failed; using rule copy")
    await db.ai_insight_cache.update_one(
        {"organizationId": org, "key": key},
        {"$set": {"organizationId": org, "key": key, "polished": polished,
                  "expires_at": (_now() + timedelta(hours=6)).isoformat()}}, upsert=True)
    return polished


@router.get("/insights")
async def insights(org: str = Depends(current_org)):
    facts = await _compute_facts(org)
    polished = await _polish(org, facts)
    out = []
    for i, f in enumerate(facts):
        out.append({
            "id": f["type"] + "-" + str(i), "type": f["type"], "severity": f.get("severity", "medium"),
            "icon": f.get("icon", "sparkles"), "explanation": polished[i] if i < len(polished) else f["default"],
            "link": f.get("link", "/dashboard"),
            "action_label": {"invoice_overdue": "Review invoice", "proposal_followup": "Send follow-up",
                             "tasks_today": "View tasks", "project_stalled": "Open project"}.get(f["type"], "View"),
        })
    return out


# ---------------- Intelligent notifications ----------------
@router.get("/notifications")
async def ai_notifications(org: str = Depends(current_org)):
    await aia.ensure_backfill(org)
    facts = await _compute_facts(org)
    polished = await _polish(org, facts)
    items = []
    for i, f in enumerate(facts):
        items.append({"kind": "insight", "icon": f.get("icon", "sparkles"), "severity": f.get("severity"),
                      "title": {"invoice_overdue": "Payment overdue", "proposal_followup": "Suggested follow-up ready",
                                "tasks_today": "Priority tasks detected", "project_stalled": "Project may be blocked"}.get(f["type"], "Assistify insight"),
                      "message": polished[i] if i < len(polished) else f["default"], "link": f.get("link"),
                      "created_at": _now().isoformat()})
    recent = await db.ai_activities.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(6)
    for a in recent:
        items.append({"kind": "completion", "icon": a.get("icon"), "severity": "done",
                      "title": a.get("label"), "message": a.get("title"),
                      "link": (a.get("related") or {}).get("project_id") and f"/projects/{a['related']['project_id']}",
                      "created_at": a.get("created_at")})
    return items



# ================= AI Workspace =================
def _range_query(rng: str):
    if rng == "today":
        return {"$gte": _now().strftime("%Y-%m-%dT00:00:00+00:00")}
    if rng == "week":
        return {"$gte": _iso_days_ago(7)}
    if rng == "month":
        return {"$gte": _iso_days_ago(30)}
    return None


@router.get("/workspace/stats")
async def workspace_stats(org: str = Depends(current_org)):
    await aia.ensure_backfill(org)
    rows = await db.ai_activities.find({"organizationId": org}, {"_id": 0}).to_list(5000)
    total = len(rows)
    total_saved = sum(r.get("time_saved", 0) for r in rows)
    week_ago, month_ago = _iso_days_ago(7), _iso_days_ago(30)
    week_count = sum(1 for r in rows if (r.get("created_at") or "") >= week_ago)
    month_count = sum(1 for r in rows if (r.get("created_at") or "") >= month_ago)
    confs = [r.get("confidence") for r in rows if r.get("confidence")]
    avg_conf = round(sum(confs) / len(confs)) if confs else 0
    gens = [r.get("gen_ms") for r in rows if r.get("gen_ms")]
    avg_gen = round(sum(gens) / len(gens)) if gens else 0
    by_type, by_day = {}, {}
    for r in rows:
        t = r.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1
        d = (r.get("created_at") or "")[:10]
        if d:
            by_day[d] = by_day.get(d, 0) + 1
    busiest = max(by_day.items(), key=lambda x: x[1]) if by_day else None
    spark = [{"date": (_now() - timedelta(days=i)).strftime("%Y-%m-%d"),
              "count": by_day.get((_now() - timedelta(days=i)).strftime("%Y-%m-%d"), 0)}
             for i in range(6, -1, -1)]
    return {
        "total_actions": total, "total_time_saved": total_saved,
        "week_count": week_count, "month_count": month_count,
        "avg_confidence": avg_conf, "avg_gen_ms": avg_gen,
        "by_type": [{"type": t, "label": aia.LABEL.get(t, t), "icon": aia.ICON.get(t, "sparkles"), "count": c}
                    for t, c in sorted(by_type.items(), key=lambda x: -x[1])],
        "busiest_day": {"date": busiest[0], "count": busiest[1]} if busiest else None,
        "sparkline": spark,
    }


@router.get("/workspace/search")
async def workspace_search(org: str = Depends(current_org), q: str = "", type: str = "",
                           range: str = "all", sort: str = "newest", limit: int = 200):
    await aia.ensure_backfill(org)
    query = {"organizationId": org}
    if type:
        query["type"] = type
    rq = _range_query(range)
    if rq:
        query["created_at"] = rq
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"title": rx}, {"explanation": rx}, {"client_name": rx}, {"project_name": rx}]
    items = await db.ai_activities.find(query, {"_id": 0}).to_list(2000)
    if sort == "most_saved":
        items.sort(key=lambda x: -(x.get("time_saved") or 0))
    elif sort == "oldest":
        items.sort(key=lambda x: (x.get("created_at") or ""))
    else:
        items.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)
    return {"total": len(items), "items": items[:limit],
            "types": [{"type": t, "label": aia.LABEL[t], "icon": aia.ICON[t]} for t in aia.LABEL]}


@router.get("/workspace/versions")
async def workspace_versions(org: str = Depends(current_org)):
    pmap = {p["id"]: p["name"] for p in
            await db.projects.find({"organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
    out = []
    for atype, coll in [("proposal", "ai_proposals"), ("contract", "ai_contracts"), ("invoice", "ai_invoices")]:
        docs = await db[coll].find({"organizationId": org}, {"_id": 0}).to_list(500)
        for d in docs:
            hist = d.get("history", [])
            if len(hist) > 1:
                out.append({
                    "key": f"{atype}:{d.get('project_id')}", "type": atype,
                    "icon": aia.ICON.get(atype), "label": aia.LABEL.get(atype),
                    "project_id": d.get("project_id"), "project_name": pmap.get(d.get("project_id"), "Project"),
                    "title": d.get("title"), "current_version": d.get("version"),
                    "link": f"/projects/{d.get('project_id')}?tab={atype}",
                    "versions": [{"version": h.get("version"), "created_at": h.get("created_at"),
                                  "status": h.get("status"), "title": h.get("title")} for h in hist][::-1],
                })
    grouped = {}
    for pl in await db.plans.find({"organizationId": org}, {"_id": 0}).to_list(1000):
        grouped.setdefault(pl.get("project_id"), []).append(pl)
    for pid, arr in grouped.items():
        if len(arr) > 1:
            arr.sort(key=lambda x: x.get("version", 0))
            out.append({
                "key": f"plan:{pid}", "type": "plan", "icon": aia.ICON.get("plan"), "label": aia.LABEL.get("plan"),
                "project_id": pid, "project_name": pmap.get(pid, "Project"),
                "title": f"{pmap.get(pid, 'Project')} — Plan", "current_version": arr[-1].get("version"),
                "link": f"/projects/{pid}?tab=plan",
                "versions": [{"version": a.get("version"), "created_at": a.get("created_at"),
                              "status": "Saved", "title": None} for a in arr][::-1],
            })
    out.sort(key=lambda x: -(x.get("current_version") or 0))
    return out
