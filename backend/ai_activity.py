"""Global AI Activity engine — records every AI-generated action, estimates time
saved, and powers the dashboard feed, AI History, notifications and proactive insights."""
import uuid
from datetime import datetime, timezone

from core import db

# Estimated minutes saved per AI action type.
TIME_SAVED = {
    "proposal": 23, "contract": 12, "invoice": 6, "email": 9, "plan": 15,
    "client_summary": 8, "project_analysis": 10, "task_prioritization": 5,
    "pricing_recommendation": 7, "data_analysis": 10,
}

# lucide-react icon name per type (frontend maps name -> component).
ICON = {
    "proposal": "file-text", "contract": "scroll-text", "invoice": "receipt",
    "email": "mail", "plan": "list-checks", "client_summary": "users",
    "project_analysis": "folder-kanban", "task_prioritization": "check-square",
    "pricing_recommendation": "badge-dollar-sign", "data_analysis": "bar-chart-3",
}

# Human, non-technical label per type.
LABEL = {
    "proposal": "Proposal generated", "contract": "Contract drafted", "invoice": "Invoice prepared",
    "email": "Email drafted", "plan": "Project plan created", "client_summary": "Client summarized",
    "project_analysis": "Project analyzed", "task_prioritization": "Tasks prioritized",
    "pricing_recommendation": "Pricing recommendation", "data_analysis": "Data analyzed",
}


def _entry(org, atype, title, explanation, source_page, related=None, when=None):
    return {
        "id": str(uuid.uuid4()), "organizationId": org, "type": atype,
        "icon": ICON.get(atype, "sparkles"), "label": LABEL.get(atype, "AI action"),
        "title": title, "explanation": explanation, "source_page": source_page,
        "time_saved": TIME_SAVED.get(atype, 5), "related": related or {},
        "created_at": (when or datetime.now(timezone.utc).isoformat()),
    }


async def log_ai_activity(org, atype, title, explanation, source_page, related=None):
    entry = _entry(org, atype, title, explanation, source_page, related)
    await db.ai_activities.insert_one(dict(entry))
    return entry


async def ensure_backfill(org: str):
    """One-time backfill of AI activities from existing generated docs so History
    and lifetime time-saved aren't empty on day one."""
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0, "ai_backfilled": 1})
    if org_doc and org_doc.get("ai_backfilled"):
        return
    projects = await db.projects.find({"organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(500)
    pname = {p["id"]: p["name"] for p in projects}
    entries = []
    async for d in db.ai_proposals.find({"organizationId": org}, {"_id": 0, "project_id": 1, "updated_at": 1, "created_at": 1}):
        nm = pname.get(d.get("project_id"), "a project")
        entries.append(_entry(org, "proposal", f"Proposal generated for {nm}",
                              f"Assistify drafted a full client proposal for {nm}, saving you the manual writing work.",
                              "Project Workspace", {"project_id": d.get("project_id")}, d.get("updated_at") or d.get("created_at")))
    async for d in db.ai_contracts.find({"organizationId": org}, {"_id": 0, "project_id": 1, "updated_at": 1, "created_at": 1}):
        nm = pname.get(d.get("project_id"), "a project")
        entries.append(_entry(org, "contract", f"Contract drafted for {nm}",
                              f"Assistify prepared a service agreement for {nm} with standard protective clauses.",
                              "Project Workspace", {"project_id": d.get("project_id")}, d.get("updated_at") or d.get("created_at")))
    async for d in db.ai_invoices.find({"organizationId": org}, {"_id": 0, "project_id": 1, "invoice_number": 1, "updated_at": 1, "created_at": 1}):
        nm = pname.get(d.get("project_id"), "a project")
        entries.append(_entry(org, "invoice", f"Invoice prepared for {nm}",
                              f"Assistify built invoice {d.get('invoice_number') or ''} for {nm}, with line items and totals calculated for you.".replace("  ", " "),
                              "Project Workspace", {"project_id": d.get("project_id")}, d.get("updated_at") or d.get("created_at")))
    async for d in db.plans.find({"organizationId": org}, {"_id": 0, "project_id": 1, "updated_at": 1, "created_at": 1}):
        nm = pname.get(d.get("project_id"), "a project")
        entries.append(_entry(org, "plan", f"Project plan created for {nm}",
                              f"Assistify analyzed {nm} and produced a structured delivery plan.",
                              "Project Workspace", {"project_id": d.get("project_id")}, d.get("updated_at") or d.get("created_at")))
    if entries:
        await db.ai_activities.insert_many([dict(e) for e in entries])
    await db.organizations.update_one({"id": org}, {"$set": {"ai_backfilled": True}})
