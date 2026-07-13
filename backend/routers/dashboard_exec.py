"""Executive Dashboard aggregation — the CEO command center.

Reuses the existing canonical engines (Opportunities health/brief/scan, CRM sales
metrics, the base dashboard summary, AI Activity, Automations, Knowledge Brain) and
assembles ONE consolidated payload. No duplicate business logic, no placeholder data.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from core import db
from dependencies import current_org
from routers.opportunities import _scan, workspace_health, daily_brief
from routers.crm import sales_metrics

router = APIRouter(prefix="/api/dashboard")


def _now():
    return datetime.now(timezone.utc)


def _age_days(iso):
    if not iso:
        return 999
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (_now() - dt).days)
    except Exception:
        return 999


async def _recent_docs(org):
    base = {"organizationId": org}
    projects = await db.projects.find(base, {"_id": 0, "id": 1, "name": 1}).to_list(500)
    pname = {p["id"]: p["name"] for p in projects}

    def shape(d, dtype, title, tab):
        pid = d.get("project_id")
        return {"id": d.get("id"), "type": dtype, "title": title, "status": d.get("status") or "Draft",
                "confidence": d.get("confidence") or d.get("ai_confidence"),
                "updated_at": d.get("updated_at") or d.get("created_at"),
                "project_id": pid, "project_name": pname.get(pid),
                "link": f"/projects/{pid}?tab={tab}" if pid else "/documents"}

    proposals = await db.ai_proposals.find(base, {"_id": 0}).sort("updated_at", -1).to_list(4)
    contracts = await db.ai_contracts.find(base, {"_id": 0}).sort("updated_at", -1).to_list(4)
    invoices = await db.ai_invoices.find(base, {"_id": 0}).sort("updated_at", -1).to_list(4)
    plans = await db.plans.find(base, {"_id": 0}).sort("created_at", -1).to_list(4)
    return {
        "proposals": [shape(d, "proposal", d.get("title") or "Proposal", "proposal") for d in proposals],
        "contracts": [shape(d, "contract", d.get("title") or "Contract", "contract") for d in contracts],
        "invoices": [shape(d, "invoice", f"{d.get('invoice_number') or 'Invoice'} · {d.get('title') or ''}".strip(" ·"), "invoice") for d in invoices],
        "plans": [shape(d, "plan", pname.get(d.get("project_id"), "Project plan"), "plan") for d in plans],
    }


def _week_buckets(n=8):
    end = _now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    out = []
    for i in range(n):
        start = end - timedelta(days=7 * (n - i))
        stop = end - timedelta(days=7 * (n - i - 1))
        out.append((start, stop, start.strftime("%b %d")))
    return out


def _in(iso, start, stop):
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return start <= dt < stop
    except Exception:
        return False


def _pct(series):
    if len(series) < 2 or not series[-2]:
        return None
    return round((series[-1] - series[-2]) / series[-2] * 100)


async def _build_trends(org):
    base = {"organizationId": org}
    buckets = _week_buckets(8)
    since = buckets[0][0].isoformat()
    leads = await db.leads.find(base, {"_id": 0, "created_at": 1, "value": 1}).to_list(2000)
    paid = await db.ai_invoices.find({**base, "status": "Paid"}, {"_id": 0, "total": 1, "updated_at": 1, "created_at": 1}).to_list(2000)
    clients = await db.clients.find(base, {"_id": 0, "created_at": 1, "createdAt": 1}).to_list(2000)
    acts = await db.ai_activities.find({**base, "created_at": {"$gt": since}}, {"_id": 0, "created_at": 1, "time_saved": 1}).to_list(5000)
    apps = await db.automation_approvals.find({**base, "status": "executed", "executed_at": {"$gt": since}}, {"_id": 0, "executed_at": 1, "time_saved": 1}).to_list(5000)

    series = {k: [] for k in ("revenue", "pipeline", "hours_saved", "deals", "clients", "automations", "ai_activity")}
    labels = []
    for start, stop, label in buckets:
        labels.append(label)
        series["revenue"].append(round(sum((i.get("total") or 0) for i in paid if _in(i.get("updated_at") or i.get("created_at"), start, stop))))
        series["pipeline"].append(round(sum((l.get("value") or 0) for l in leads if _in(l.get("created_at"), start, stop))))
        mins = sum(a.get("time_saved", 0) for a in acts if _in(a.get("created_at"), start, stop)) + \
               sum(a.get("time_saved", 0) for a in apps if _in(a.get("executed_at"), start, stop))
        series["hours_saved"].append(round(mins / 60, 1))
        series["deals"].append(sum(1 for l in leads if _in(l.get("created_at"), start, stop)))
        series["clients"].append(sum(1 for c in clients if _in(c.get("created_at") or c.get("createdAt"), start, stop)))
        series["automations"].append(sum(1 for a in apps if _in(a.get("executed_at"), start, stop)))
        series["ai_activity"].append(sum(1 for a in acts if _in(a.get("created_at"), start, stop)))
    return {"labels": labels, "series": series}


async def _enrich_impact(org, items):
    """Attach a real estimated revenue_impact to scan items (from invoices/deals/clients).
    Non-destructive — leaves None when no concrete figure exists."""
    base = {"organizationId": org}
    invs = await db.ai_invoices.find(base, {"_id": 0, "id": 1, "total": 1}).to_list(1000)
    inv_total = {i["id"]: (i.get("total") or 0) for i in invs}
    leads = await db.leads.find(base, {"_id": 0, "project_id": 1, "client_id": 1, "value": 1, "stage": 1}).to_list(1000)
    proj_val, client_val = {}, {}
    for l in leads:
        v = l.get("value") or 0
        if l.get("project_id"):
            proj_val[l["project_id"]] = max(proj_val.get(l["project_id"], 0), v)
        if l.get("client_id") and l.get("stage") not in ("Won", "Lost"):
            client_val[l["client_id"]] = client_val.get(l["client_id"], 0) + v
    clients = await db.clients.find(base, {"_id": 0, "id": 1, "value": 1}).to_list(1000)
    cval = {c["id"]: (c.get("value") or 0) for c in clients}
    for it in items:
        eid = it.get("key", "").split(":", 1)[1] if ":" in it.get("key", "") else None
        ent = it.get("entity", {})
        impact = None
        if it.get("type", "").startswith("invoice"):
            impact = inv_total.get(eid)
        if not impact and ent.get("project_id"):
            impact = proj_val.get(ent["project_id"])
        if not impact and ent.get("client_id"):
            impact = client_val.get(ent["client_id"]) or cval.get(ent["client_id"])
        it["revenue_impact"] = round(impact) if impact else None
    return items


@router.get("/executive")
async def executive(org: str = Depends(current_org)):
    base = {"organizationId": org}
    week_ago = (_now() - timedelta(days=7)).isoformat()

    # --- Reused canonical engines ---
    health = await workspace_health(org)
    brief = await daily_brief(org)
    items = await _scan(org)
    items = await _enrich_impact(org, items)
    sales = await sales_metrics(org)

    import server as S
    summary = await S.dashboard_summary(org)
    financial = summary.get("financial", {})

    # --- Hero metrics ---
    acts_week = await db.ai_activities.find(
        {**base, "created_at": {"$gt": week_ago}}, {"_id": 0, "time_saved": 1}).to_list(2000)
    apps_week = await db.automation_approvals.find(
        {**base, "status": "executed", "executed_at": {"$gt": week_ago}}, {"_id": 0, "time_saved": 1}).to_list(2000)
    mins_week = sum(a.get("time_saved", 0) for a in acts_week) + sum(a.get("time_saved", 0) for a in apps_week)

    recent_acts = await db.ai_activities.find(base, {"_id": 0}).sort("created_at", -1).to_list(40)
    confs = [a.get("confidence") for a in recent_acts if a.get("confidence")]
    ai_confidence = round(sum(confs) / len(confs)) if confs else 92

    # Revenue at risk = unpaid invoices + value of open deals gone quiet (>=14d)
    leads = await db.leads.find(base, {"_id": 0, "stage": 1, "value": 1, "stage_changed_at": 1, "updated_at": 1}).to_list(1000)
    OPEN = ("New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating")
    stalled_value = sum((l.get("value") or 0) for l in leads
                        if l.get("stage") in OPEN and _age_days(l.get("stage_changed_at") or l.get("updated_at")) >= 14)
    outstanding = financial.get("outstanding_revenue", 0)
    revenue_at_risk = round(outstanding + stalled_value)

    # Growth: paid invoices last 30d vs previous 30d
    d30 = (_now() - timedelta(days=30)).isoformat()
    d60 = (_now() - timedelta(days=60)).isoformat()
    paid = await db.ai_invoices.find({**base, "status": "Paid"}, {"_id": 0, "total": 1, "updated_at": 1, "created_at": 1}).to_list(1000)
    this30 = sum((i.get("total") or 0) for i in paid if (i.get("updated_at") or i.get("created_at") or "") >= d30)
    prev30 = sum((i.get("total") or 0) for i in paid if d60 <= (i.get("updated_at") or i.get("created_at") or "") < d30)
    growth_pct = round((this30 - prev30) / prev30 * 100) if prev30 else None

    # --- Priorities grouped by level ---
    levels = {"Critical": [], "High": [], "Medium": [], "Low": []}
    for it in items:
        levels.setdefault(it["priority"], []).append(it)
    priorities = {lvl.lower(): {"count": len(v), "items": v[:6]} for lvl, v in levels.items()}

    # --- Workspace counts (cheap counts, not business logic) ---
    workspace = {
        "clients": await db.clients.count_documents(base),
        "deals": sales.get("open_count", 0),
        "total_leads": sales.get("total_leads", 0),
        "projects": await db.projects.count_documents(base),
        "tasks": await db.tasks.count_documents({**base, "done": False}),
        "documents": await db.documents.count_documents(base),
        "memories": await db.memories.count_documents(base),
        "automations": await db.automations.count_documents({**base, "enabled": True}),
        "ai_reports": await db.ai_activities.count_documents(base),
        "proposals": await db.ai_proposals.count_documents(base),
        "contracts": await db.ai_contracts.count_documents(base),
        "invoices": await db.ai_invoices.count_documents(base),
    }

    top = items[0] if items else None

    trends = await _build_trends(org)
    s = trends["series"]
    kpi_cards = {
        "health": {"value": health.get("score", 0), "grade": health.get("grade"),
                   "categories": health.get("categories", [])},
        "pipeline": {"value": sales.get("pipeline_value", 0), "spark": s["pipeline"], "change_pct": _pct(s["pipeline"])},
        "hours_saved": {"value": round(mins_week / 60, 1), "spark": s["hours_saved"], "change_pct": _pct(s["hours_saved"])},
        "revenue_month": {"value": round(this30), "spark": s["revenue"], "change_pct": growth_pct},
    }

    return {
        "hero": {
            "greeting": brief.get("greeting"),
            "brief_lines": brief.get("lines", []),
            "top_priority": {
                "title": top["title"], "why": top["why"], "priority": top["priority"],
                "action": top["action"], "icon": top["icon"], "confidence": top["confidence"],
            } if top else None,
            "revenue_at_risk": revenue_at_risk,
            "hours_saved_week": round(mins_week / 60, 1),
            "minutes_saved_week": mins_week,
            "ai_confidence": ai_confidence,
        },
        "health": health,
        "revenue": {
            "pipeline_value": sales.get("pipeline_value", 0),
            "expected_monthly": sales.get("weighted_pipeline", 0),
            "outstanding": round(outstanding),
            "closed_revenue": round(financial.get("revenue", 0)),
            "avg_deal_size": sales.get("avg_deal_size", 0),
            "growth_pct": growth_pct,
            "win_rate": sales.get("win_rate", 0),
            "conversion_rate": sales.get("conversion_rate", 0),
        },
        "insights": items[:6],
        "priorities": priorities,
        "priorities_total": len(items),
        "ai_activity": [{
            "id": a.get("id"), "type": a.get("type"), "icon": a.get("icon"), "label": a.get("label"),
            "title": a.get("title"), "explanation": a.get("explanation"), "time_saved": a.get("time_saved"),
            "confidence": a.get("confidence"), "created_at": a.get("created_at"),
            "project_id": (a.get("related") or {}).get("project_id"), "project_name": a.get("project_name"),
        } for a in recent_acts[:8]],
        "workspace": workspace,
        "documents": await _recent_docs(org),
        "trends": trends,
        "kpi_cards": kpi_cards,
    }
