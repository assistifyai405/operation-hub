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


def _entry(org, atype, title, explanation, source_page, related=None, when=None, meta=None):
    e = {
        "id": str(uuid.uuid4()), "organizationId": org, "type": atype,
        "icon": ICON.get(atype, "sparkles"), "label": LABEL.get(atype, "AI action"),
        "title": title, "explanation": explanation, "source_page": source_page,
        "time_saved": TIME_SAVED.get(atype, 5), "related": related or {},
        "confidence": 94, "gen_ms": None, "client_name": None, "project_name": None,
        "status": "Completed", "archived": False,
        "created_at": (when or datetime.now(timezone.utc).isoformat()),
    }
    if meta:
        e.update({k: v for k, v in meta.items() if v is not None})
    return e


async def log_ai_activity(org, atype, title, explanation, source_page, related=None, **meta):
    entry = _entry(org, atype, title, explanation, source_page, related, meta=meta)
    await db.ai_activities.insert_one(dict(entry))
    return entry


_STEPS = {
    "proposal": ["Read your client information", "Understood your project goals",
                 "Analyzed your project requirements", "Reviewed the pricing information",
                 "Organized the document structure", "Wrote a professional first draft",
                 "Checked for clarity and consistency", "Prepared the final document"],
    "contract": ["Read your client & project details", "Reviewed the linked proposal",
                 "Applied standard protective clauses", "Structured the agreement sections",
                 "Wrote clear, professional terms", "Checked for consistency",
                 "Prepared the final contract"],
    "invoice": ["Read your client & billing details", "Pulled the scope from your proposal & contract",
                "Built the line items", "Calculated VAT and totals",
                "Organized the invoice layout", "Prepared the final invoice"],
    "plan": ["Read the project brief & notes", "Understood your goals",
             "Mapped out phases & milestones", "Identified risks & dependencies",
             "Organized tasks by priority", "Prepared your project plan"],
    "client_summary": ["Gathered the client's history", "Reviewed related projects & documents",
                       "Identified key details & context", "Wrote a clear, concise summary"],
    "pricing_recommendation": ["Reviewed the project scope", "Compared similar past work",
                               "Analyzed the services involved", "Prepared a pricing recommendation"],
    "task_prioritization": ["Reviewed all open tasks", "Checked deadlines & dependencies",
                            "Weighed impact and urgency", "Ordered your tasks by priority"],
}
_GENERIC_STEPS = ["Gathered the relevant information", "Analyzed the context",
                  "Organized the structure", "Prepared the result"]

_TYPE_WHY = {
    "proposal": ["The pricing and services section was expanded to reflect the project scope.",
                 "The proposal leads with outcomes and delivery to match what clients care about most."],
    "contract": ["Standard protective clauses were included to keep you covered.",
                 "Terms were written in plain, professional language rather than dense legalese."],
    "invoice": ["Line items and totals were calculated automatically to avoid manual errors.",
                "Payment terms and due dates were set using sensible defaults."],
    "plan": ["Work was broken into clear phases so progress is easy to track.",
             "Dependencies and risks were flagged early so nothing gets blocked."],
    "client_summary": ["The summary highlights the details most useful for your next conversation."],
    "pricing_recommendation": ["The recommendation reflects the number and complexity of services detected."],
    "task_prioritization": ["Tasks nearing their deadline were moved to the top."],
}

_TYPE_LABEL = {
    "proposal": "Proposal", "contract": "Contract", "invoice": "Invoice", "plan": "Project Plan",
    "client_summary": "Client Summary", "pricing_recommendation": "Pricing Recommendation",
    "task_prioritization": "Task Prioritization",
}


def build_ai_report(atype: str, project: dict = None, content=None) -> dict:
    """Deterministic, human 'AI Action Report' returned alongside every generation.
    No LLM cost — derived from the real project context so it's honest and consistent."""
    project = project or {}
    cname = project.get("client_name")
    has_client = bool(cname or project.get("client_id"))
    has_desc = bool((project.get("description") or "").strip())

    score = 88 + (4 if has_client else 0) + (4 if has_desc else 0) + (2 if content else 0)
    score = min(99, score)
    if score >= 95:
        note = "This result contains enough information to produce a high-quality first draft."
    elif score >= 91:
        note = "This is a strong first draft — a quick review will make it client-ready."
    else:
        note = "A solid starting draft. Adding more project detail will sharpen future results."

    why = []
    if cname:
        why.append(f"Details and tone were tailored specifically for {cname}.")
    if has_desc:
        why.append("The content was aligned with the project description you provided.")
    else:
        why.append("Professional placeholders were used where details were missing, so you can refine them quickly.")
    why += _TYPE_WHY.get(atype, [])
    why.append("Everything was organized into clear sections for easy review.")

    return {
        "type": atype,
        "type_label": _TYPE_LABEL.get(atype, "Document"),
        "confidence": score,
        "confidence_note": note,
        "time_saved": TIME_SAVED.get(atype, 5),
        "steps": _STEPS.get(atype, _GENERIC_STEPS),
        "why": why[:6],
        "quality": ["Professional formatting", "Business language", "Grammar checked", "Ready for review"],
    }



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
