"""AI Automation Engine — Assistify proactively monitors the workspace, detects
useful events, prepares actions and (only for safe internal actions the user opted
into) executes them. Enabled by default in "Prepare for approval" mode, always with
full user control (master pause, per-automation toggle, execution modes) and total
transparency (every prepared/executed action is explained and logged).

Safety model (enforced server-side):
  - suggest  : detect + recommend only. Never prepares or executes.
  - prepare  : (DEFAULT) prepares drafts/tasks; user must approve before anything runs.
  - auto     : only SAFE INTERNAL actions run automatically. External/client-facing,
               generative and destructive actions are ALWAYS downgraded to an approval
               request even when the automation is set to auto.

Evaluation is lazy + throttled (re-scans on load, ~every 2 min) plus a manual "Run now".
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from core import db, now_iso, log_activity
from dependencies import current_org

router = APIRouter(prefix="/api/automation")

THROTTLE_SECONDS = 120

# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------
SAFE_INTERNAL = {"create_task", "add_note", "change_internal_status", "notify_user", "add_to_brief"}
EXTERNAL = {"prepare_email", "prepare_followup"}
GENERATIVE = {"generate_proposal", "generate_contract", "generate_invoice"}
DESTRUCTIVE = {"archive_project"}

ACTION_META = {
    "create_task":            {"label": "Create a task",            "risk": "low",    "time": 5,  "icon": "check-square", "kind": "internal"},
    "add_note":               {"label": "Add a note",               "risk": "low",    "time": 3,  "icon": "file-text",    "kind": "internal"},
    "change_internal_status": {"label": "Update internal status",   "risk": "low",    "time": 3,  "icon": "refresh-cw",   "kind": "internal"},
    "notify_user":            {"label": "Notify you",               "risk": "low",    "time": 2,  "icon": "bell",         "kind": "internal"},
    "add_to_brief":           {"label": "Add to your AI Brief",     "risk": "low",    "time": 2,  "icon": "sparkles",     "kind": "internal"},
    "prepare_email":          {"label": "Prepare an email",         "risk": "medium", "time": 9,  "icon": "mail",         "kind": "external"},
    "prepare_followup":       {"label": "Prepare a follow-up",      "risk": "medium", "time": 9,  "icon": "mail",         "kind": "external"},
    "generate_proposal":      {"label": "Generate a proposal draft","risk": "medium", "time": 23, "icon": "file-text",    "kind": "generative"},
    "generate_contract":      {"label": "Generate a contract draft","risk": "medium", "time": 12, "icon": "scroll-text",  "kind": "generative"},
    "generate_invoice":       {"label": "Prepare an invoice draft", "risk": "medium", "time": 6,  "icon": "receipt",      "kind": "generative"},
    "archive_project":        {"label": "Archive the project",      "risk": "high",   "time": 4,  "icon": "archive",      "kind": "destructive"},
}

TRIGGER_META = {
    "proposal_not_sent":   {"label": "Proposal not sent",          "desc": "A proposal has been ready but not sent for X days.", "days": 5,  "icon": "file-text"},
    "proposal_no_reply":   {"label": "Proposal sent, no reply",    "desc": "A sent proposal hasn't had a reply for X days.",      "days": 5,  "icon": "mail"},
    "contract_unsigned":   {"label": "Contract unsigned",          "desc": "A contract is awaiting signature for X days.",        "days": 3,  "icon": "scroll-text"},
    "invoice_due_soon":    {"label": "Invoice due soon",           "desc": "An invoice is due within X days.",                    "days": 3,  "icon": "receipt"},
    "invoice_overdue":     {"label": "Invoice overdue",            "desc": "An invoice is past its due date and unpaid.",         "days": 0,  "icon": "receipt"},
    "client_inactive":     {"label": "Client inactive",            "desc": "No activity with a client for X days.",               "days": 21, "icon": "users"},
    "lead_needs_followup": {"label": "Lead needs follow-up",       "desc": "An open lead has gone quiet for X days.",             "days": 7,  "icon": "trending-up"},
    "project_no_task":     {"label": "Project has no next task",   "desc": "An active project has no open task.",                 "days": 0,  "icon": "folder-kanban"},
    "project_blocked":     {"label": "Project appears blocked",    "desc": "An active project has stalled for X days.",           "days": 14, "icon": "folder-kanban"},
    "contract_signed":     {"label": "Contract signed",            "desc": "A contract was just signed — prepare the project.",   "days": 0,  "icon": "scroll-text"},
    "project_completed":   {"label": "Project completed",          "desc": "A project was completed — prepare the invoice.",      "days": 0,  "icon": "check-square"},
    "new_client":          {"label": "New client added",           "desc": "A client was added within the last X days.",          "days": 3,  "icon": "users"},
    "task_overdue":        {"label": "Task overdue",               "desc": "A task is past its due date.",                        "days": 0,  "icon": "check-square"},
}

CONDITION_FIELDS = [
    {"field": "status",         "label": "Status",           "type": "text"},
    {"field": "value",          "label": "Value",            "type": "number"},
    {"field": "priority",       "label": "Priority",         "type": "text"},
    {"field": "days_inactive",  "label": "Days inactive",    "type": "number"},
    {"field": "invoice_amount", "label": "Invoice amount",   "type": "number"},
    {"field": "lead_score",     "label": "Lead score",       "type": "number"},
    {"field": "tags",           "label": "Tags",             "type": "text"},
    {"field": "owner",          "label": "Owner",            "type": "text"},
    {"field": "client",         "label": "Client name",      "type": "text"},
    {"field": "project",        "label": "Project name",     "type": "text"},
]
CONDITION_OPS = [
    {"op": "eq", "label": "equals"}, {"op": "ne", "label": "is not"},
    {"op": "gt", "label": "greater than"}, {"op": "gte", "label": "at least"},
    {"op": "lt", "label": "less than"}, {"op": "lte", "label": "at most"},
    {"op": "contains", "label": "contains"},
]


# ---------------------------------------------------------------------------
# Templates (seeded, enabled by default)
# ---------------------------------------------------------------------------
def _tpl(key, name, description, trigger, days, actions, mode="prepare"):
    return {"key": key, "name": name, "description": description,
            "trigger": {"type": trigger, "days": days}, "conditions": [],
            "actions": actions, "default_mode": mode}


TEMPLATES = [
    _tpl("t_proposal_not_sent", "Proposal not sent after 5 days",
         "When a proposal has been ready but unsent for 5+ days, prepare a note to send it.",
         "proposal_not_sent", 5, [{"type": "prepare_followup", "config": {}}, {"type": "notify_user", "config": {}}]),
    _tpl("t_proposal_no_reply", "Proposal not viewed after 5 days",
         "When a sent proposal hasn't had a reply in 5+ days, prepare a friendly follow-up.",
         "proposal_no_reply", 5, [{"type": "prepare_followup", "config": {}}]),
    _tpl("t_contract_unsigned", "Contract unsigned",
         "When a contract has been awaiting signature, prepare a reminder to the client.",
         "contract_unsigned", 3, [{"type": "prepare_email", "config": {"kind": "contract_reminder"}}]),
    _tpl("t_invoice_due_soon", "Invoice due soon",
         "When an invoice is due within 3 days, prepare a gentle payment reminder.",
         "invoice_due_soon", 3, [{"type": "prepare_email", "config": {"kind": "invoice_due"}}]),
    _tpl("t_invoice_overdue", "Invoice overdue",
         "When an invoice is overdue, prepare a payment reminder.",
         "invoice_overdue", 0, [{"type": "prepare_email", "config": {"kind": "invoice_overdue"}}, {"type": "notify_user", "config": {}}]),
    _tpl("t_client_inactive", "Client inactive",
         "When a client has gone quiet for 21+ days, prepare a check-in.",
         "client_inactive", 21, [{"type": "prepare_followup", "config": {}}]),
    _tpl("t_lead_followup", "Lead needs follow-up",
         "When an open lead has been quiet for 7+ days, create a follow-up task.",
         "lead_needs_followup", 7, [{"type": "create_task", "config": {"priority": "High"}}, {"type": "prepare_followup", "config": {}}]),
    _tpl("t_project_no_task", "Project has no next task",
         "When an active project has no open task, create a next task. (Safe to run automatically.)",
         "project_no_task", 0, [{"type": "create_task", "config": {"priority": "Medium"}}]),
    _tpl("t_project_blocked", "Project appears blocked",
         "When an active project has stalled for 14+ days, notify you and add a note.",
         "project_blocked", 14, [{"type": "notify_user", "config": {}}, {"type": "add_note", "config": {}}]),
    _tpl("t_contract_signed", "Contract signed → prepare project",
         "When a contract is signed, create the project kickoff tasks.",
         "contract_signed", 0, [{"type": "create_task", "config": {"priority": "High", "title": "Kick off project — contract signed"}}]),
    _tpl("t_project_completed", "Project completed → prepare invoice",
         "When a project is completed, prepare the final invoice draft.",
         "project_completed", 0, [{"type": "generate_invoice", "config": {}}]),
    _tpl("t_new_client", "New client → onboarding workflow",
         "When a new client is added, create an onboarding task checklist.",
         "new_client", 3, [{"type": "create_task", "config": {"priority": "Medium", "title": "Send welcome & onboarding to {client}"}}]),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _days_until(datestr):
    if not datestr:
        return None
    try:
        dt = datetime.fromisoformat(str(datestr)[:10])
        return (dt.date() - _now().date()).days
    except Exception:
        return None


DEFAULT_SETTINGS = {
    "enabled": True,
    "paused_until": None,
    "default_mode": "prepare",
    "safe_internal_auto": True,
    "notifications": {"email": False, "product": True, "approvals": True, "executions": True},
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00"},
    "timezone": "UTC",
    "approval_prefs": {"require_external": True, "require_destructive": True, "require_generative": True},
}


async def ensure_automation_setup(org: str):
    """Idempotently provision default settings + the template automations for an org."""
    s = await db.automation_settings.find_one({"organizationId": org}, {"_id": 0})
    if not s:
        s = {"organizationId": org, **DEFAULT_SETTINGS, "last_evaluated_at": None,
             "created_at": now_iso(), "updated_at": now_iso()}
        await db.automation_settings.insert_one(dict(s))
    existing = await db.automations.count_documents({"organizationId": org, "source": "template"})
    if existing == 0:
        for t in TEMPLATES:
            doc = {
                "id": str(uuid.uuid4()), "organizationId": org, "source": "template",
                "template_key": t["key"], "name": t["name"], "description": t["description"],
                "enabled": True, "mode": t["default_mode"],
                "trigger": t["trigger"], "conditions": t["conditions"], "actions": t["actions"],
                "status": "Active", "last_run": None, "next_evaluation": None,
                "runs_count": 0, "time_saved_total": 0,
                "created_at": now_iso(), "updated_at": now_iso(),
            }
            await db.automations.insert_one(dict(doc))


async def _get_settings(org):
    await ensure_automation_setup(org)
    s = await db.automation_settings.find_one({"organizationId": org}, {"_id": 0})
    return s


def _paused(settings):
    pu = settings.get("paused_until")
    if not pu:
        return False
    try:
        return datetime.fromisoformat(pu.replace("Z", "+00:00")) > _now()
    except Exception:
        return False


def _in_quiet_hours(settings):
    qh = settings.get("quiet_hours") or {}
    if not qh.get("enabled"):
        return False
    try:
        h = _now().hour + _now().minute / 60
        start = float(qh["start"].split(":")[0]) + float(qh["start"].split(":")[1]) / 60
        end = float(qh["end"].split(":")[0]) + float(qh["end"].split(":")[1]) / 60
        if start <= end:
            return start <= h < end
        return h >= start or h < end
    except Exception:
        return False


async def _log(org, automation_id, automation_name, event, message, detail=None):
    await db.automation_logs.insert_one({
        "id": str(uuid.uuid4()), "organizationId": org, "automation_id": automation_id,
        "automation_name": automation_name, "event": event, "message": message,
        "detail": detail or {}, "created_at": now_iso()})


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
async def _gather(org):
    base = {"organizationId": org}
    projects = await db.projects.find(base, {"_id": 0}).to_list(500)
    pmap = {p["id"]: p for p in projects}
    clients = await db.clients.find(base, {"_id": 0}).to_list(500)
    cmap = {c["id"]: c for c in clients}
    leads = await db.leads.find(base, {"_id": 0}).to_list(500)
    invoices = await db.ai_invoices.find(base, {"_id": 0}).to_list(500)
    proposals = await db.ai_proposals.find(base, {"_id": 0}).to_list(500)
    contracts = await db.ai_contracts.find(base, {"_id": 0}).to_list(500)
    tasks = await db.tasks.find(base, {"_id": 0}).to_list(2000)
    open_by_proj = {}
    for t in tasks:
        if not t.get("done"):
            open_by_proj[t.get("project_id")] = open_by_proj.get(t.get("project_id"), 0) + 1
    return {"base": base, "projects": projects, "pmap": pmap, "clients": clients,
            "cmap": cmap, "leads": leads, "invoices": invoices, "proposals": proposals,
            "contracts": contracts, "tasks": tasks, "open_by_proj": open_by_proj}


def _cname(ctx, cid):
    return (ctx["cmap"].get(cid) or {}).get("name")


def _match(entity_type, entity_id, entity_name, ctx, project_id=None, client_id=None, fields=None, extra=None):
    return {
        "entity_type": entity_type, "entity_id": entity_id, "entity_name": entity_name,
        "project_id": project_id, "project_name": (ctx["pmap"].get(project_id) or {}).get("name") if project_id else None,
        "client_id": client_id, "client_name": _cname(ctx, client_id) if client_id else None,
        "fields": fields or {}, "context": extra or {},
    }


async def _detect(a, ctx):
    ttype = a.get("trigger", {}).get("type")
    days = int(a.get("trigger", {}).get("days") or TRIGGER_META.get(ttype, {}).get("days", 0))
    out = []
    today = _now().strftime("%Y-%m-%d")

    if ttype == "proposal_not_sent":
        for p in ctx["proposals"]:
            age = _age_days(p.get("updated_at") or p.get("created_at"))
            if p.get("status") in ("Draft", "Generated") and age >= days:
                out.append(_match("proposal", p.get("id"), p.get("title") or "Proposal", ctx,
                                  project_id=p.get("project_id"), client_id=p.get("client_id"),
                                  fields={"status": p.get("status"), "days_inactive": age},
                                  extra={"age": age}))
    elif ttype == "proposal_no_reply":
        for p in ctx["proposals"]:
            age = _age_days(p.get("updated_at") or p.get("created_at"))
            if p.get("status") == "Sent" and age >= days:
                out.append(_match("proposal", p.get("id"), p.get("title") or "Proposal", ctx,
                                  project_id=p.get("project_id"), client_id=p.get("client_id"),
                                  fields={"status": "Sent", "days_inactive": age}, extra={"age": age}))
    elif ttype == "contract_unsigned":
        for c in ctx["contracts"]:
            age = _age_days(c.get("updated_at") or c.get("created_at"))
            if c.get("status") in ("Generated", "Sent") and age >= days:
                out.append(_match("contract", c.get("id"), c.get("title") or "Contract", ctx,
                                  project_id=c.get("project_id"), client_id=c.get("client_id"),
                                  fields={"status": c.get("status"), "days_inactive": age}, extra={"age": age}))
    elif ttype in ("invoice_due_soon", "invoice_overdue"):
        for inv in ctx["invoices"]:
            st = inv.get("status")
            if st == "Paid":
                continue
            due = (inv.get("content") or {}).get("due_date") or inv.get("due_date")
            dleft = _days_until(due)
            amount = inv.get("total") or 0
            if ttype == "invoice_due_soon" and dleft is not None and 0 <= dleft <= days:
                out.append(_match("invoice", inv.get("id"), inv.get("invoice_number") or inv.get("title") or "Invoice", ctx,
                                  project_id=inv.get("project_id"), client_id=inv.get("client_id"),
                                  fields={"status": st, "invoice_amount": amount},
                                  extra={"due": due, "days_left": dleft, "amount": amount}))
            if ttype == "invoice_overdue" and ((st == "Overdue") or (due and str(due)[:10] < today and st in ("Sent", "Overdue"))):
                out.append(_match("invoice", inv.get("id"), inv.get("invoice_number") or inv.get("title") or "Invoice", ctx,
                                  project_id=inv.get("project_id"), client_id=inv.get("client_id"),
                                  fields={"status": st, "invoice_amount": amount},
                                  extra={"due": due, "days_overdue": _age_days(due) if due else 0, "amount": amount}))
    elif ttype == "client_inactive":
        for c in ctx["clients"]:
            cid = c["id"]
            cproj = [p["id"] for p in ctx["projects"] if p.get("client_id") == cid]
            recent = 0
            if cproj:
                cutoff = (_now() - timedelta(days=days)).isoformat()
                recent = await db.activities.count_documents({**ctx["base"], "project_id": {"$in": cproj}, "created_at": {"$gt": cutoff}})
            if c.get("status") == "Active" and recent == 0:
                out.append(_match("client", cid, c.get("name"), ctx, client_id=cid,
                                  fields={"status": c.get("status"), "tags": c.get("tags", []), "owner": c.get("owner", ""), "value": c.get("value", 0), "days_inactive": days},
                                  extra={"days": days}))
    elif ttype == "lead_needs_followup":
        for l in ctx["leads"]:
            age = _age_days(l.get("stage_changed_at") or l.get("updated_at") or l.get("created_at"))
            if l.get("stage") not in ("Won", "Lost") and age >= days:
                out.append(_match("lead", l.get("id"), l.get("title") or "Lead", ctx,
                                  project_id=l.get("project_id"), client_id=l.get("client_id"),
                                  fields={"status": l.get("stage"), "value": l.get("value", 0), "days_inactive": age,
                                          "lead_score": l.get("score") or l.get("lead_score") or 0, "tags": l.get("tags", []), "owner": l.get("owner", "")},
                                  extra={"age": age, "stage": l.get("stage"), "contact_name": l.get("contact_name"), "email": l.get("email")}))
    elif ttype == "project_no_task":
        for p in ctx["projects"]:
            if p.get("status") in ("In Progress", "Review", "Planning") and ctx["open_by_proj"].get(p["id"], 0) == 0:
                out.append(_match("project", p["id"], p.get("name"), ctx, project_id=p["id"], client_id=p.get("client_id"),
                                  fields={"status": p.get("status")}, extra={}))
    elif ttype == "project_blocked":
        for p in ctx["projects"]:
            if p.get("status") not in ("In Progress", "Review", "Planning"):
                continue
            last = await db.activities.find_one({**ctx["base"], "project_id": p["id"]}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
            inactive = _age_days((last or {}).get("created_at") or p.get("updated_at"))
            if inactive >= days:
                out.append(_match("project", p["id"], p.get("name"), ctx, project_id=p["id"], client_id=p.get("client_id"),
                                  fields={"status": p.get("status"), "days_inactive": inactive}, extra={"days": inactive}))
    elif ttype == "contract_signed":
        for c in ctx["contracts"]:
            if c.get("status") == "Signed" and _age_days(c.get("updated_at")) <= 7:
                out.append(_match("contract", c.get("id"), c.get("title") or "Contract", ctx,
                                  project_id=c.get("project_id"), client_id=c.get("client_id"),
                                  fields={"status": "Signed"}, extra={}))
    elif ttype == "project_completed":
        for p in ctx["projects"]:
            if p.get("status") == "Completed" and _age_days(p.get("updated_at")) <= 14:
                # skip if an invoice already exists for this project
                has_inv = any(i.get("project_id") == p["id"] for i in ctx["invoices"])
                if not has_inv:
                    out.append(_match("project", p["id"], p.get("name"), ctx, project_id=p["id"], client_id=p.get("client_id"),
                                      fields={"status": "Completed"}, extra={}))
    elif ttype == "new_client":
        for c in ctx["clients"]:
            if _age_days(c.get("createdAt") or c.get("created_at")) <= days:
                out.append(_match("client", c["id"], c.get("name"), ctx, client_id=c["id"],
                                  fields={"status": c.get("status"), "tags": c.get("tags", []), "owner": c.get("owner", "")}, extra={}))
    elif ttype == "task_overdue":
        for t in ctx["tasks"]:
            if not t.get("done") and t.get("due") and str(t.get("due"))[:10] < today:
                out.append(_match("task", t.get("id"), t.get("title") or "Task", ctx,
                                  project_id=t.get("project_id"),
                                  fields={"status": "Overdue", "priority": t.get("priority", "")}, extra={"due": t.get("due")}))
    return out


def _cond_pass(conditions, m):
    fields = m.get("fields", {})
    for c in conditions or []:
        field, op, val = c.get("field"), c.get("op"), c.get("value")
        actual = fields.get(field)
        if field == "client":
            actual = m.get("client_name")
        elif field == "project":
            actual = m.get("project_name")
        try:
            if op in ("gt", "gte", "lt", "lte"):
                a = float(actual or 0); b = float(val)
                if op == "gt" and not a > b: return False
                if op == "gte" and not a >= b: return False
                if op == "lt" and not a < b: return False
                if op == "lte" and not a <= b: return False
            elif op == "eq":
                if str(actual or "").lower() != str(val or "").lower(): return False
            elif op == "ne":
                if str(actual or "").lower() == str(val or "").lower(): return False
            elif op == "contains":
                hay = actual if isinstance(actual, list) else [str(actual or "")]
                if not any(str(val or "").lower() in str(h).lower() for h in hay): return False
        except Exception:
            return False
    return True


# ---------------------------------------------------------------------------
# Draft preparation (deterministic — fast, free, honest; fully editable)
# ---------------------------------------------------------------------------
def _draft_email(kind, m):
    cn = m.get("client_name") or m.get("context", {}).get("contact_name") or "there"
    pn = m.get("project_name") or "your project"
    if kind == "contract_reminder":
        return {"subject": f"Quick note on the {pn} agreement",
                "body": f"Hi {cn},\n\nJust following up on the service agreement for {pn} — whenever you have a moment to review and sign, we're ready to get started.\n\nHappy to answer any questions.\n\nBest regards"}
    if kind == "invoice_due":
        amt = m.get("context", {}).get("amount")
        return {"subject": f"Upcoming invoice for {pn}",
                "body": f"Hi {cn},\n\nA friendly reminder that the invoice{f' of ${amt:,.0f}' if amt else ''} for {pn} is due soon. Please let us know if you have any questions.\n\nThank you!"}
    if kind == "invoice_overdue":
        amt = m.get("context", {}).get("amount")
        od = m.get("context", {}).get("days_overdue")
        return {"subject": f"Payment reminder — {pn}",
                "body": f"Hi {cn},\n\nOur records show the invoice{f' of ${amt:,.0f}' if amt else ''} for {pn} is now {od or 'a few'} days past due. Could you let us know when we can expect payment? Happy to help if anything's unclear.\n\nThank you."}
    return {"subject": f"Following up — {pn}",
            "body": f"Hi {cn},\n\nJust checking in regarding {pn}. Let me know if there's anything you need from us.\n\nBest regards"}


def _prepare_action_payload(action, m):
    atype = action.get("type")
    cfg = action.get("config") or {}
    cn = m.get("client_name") or m.get("context", {}).get("contact_name") or ""
    pn = m.get("project_name") or ""
    if atype in ("prepare_email", "prepare_followup"):
        kind = cfg.get("kind") or "followup"
        return {"email": _draft_email(kind, m)}
    if atype == "create_task":
        title = (cfg.get("title") or "").replace("{client}", cn or "the client").replace("{project}", pn or "the project")
        if not title:
            title = f"Follow up on {m.get('entity_name')}"
        return {"task": {"title": title, "priority": cfg.get("priority", "Medium"), "project_id": m.get("project_id")}}
    if atype == "add_note":
        return {"note": cfg.get("note") or f"Automation flagged: {m.get('entity_name')} needs attention."}
    if atype == "change_internal_status":
        return {"status": cfg.get("status", "In Progress")}
    if atype == "notify_user":
        return {"message": cfg.get("message") or f"{m.get('entity_name')} needs your attention."}
    if atype == "add_to_brief":
        return {"brief": f"{m.get('entity_name')}"}
    return {}


def _action_kind(atype):
    return ACTION_META.get(atype, {}).get("kind", "internal")


def _is_safe(atype):
    return atype in SAFE_INTERNAL


def _human_trigger(a, m):
    tl = TRIGGER_META.get(a.get("trigger", {}).get("type"), {}).get("label", "A workspace event")
    ctx = m.get("context", {})
    if "age" in ctx:
        return f"{tl} ({ctx['age']} days)"
    if "days_overdue" in ctx:
        return f"{tl} ({ctx['days_overdue']} days overdue)"
    if "days_left" in ctx:
        return f"{tl} (due in {ctx['days_left']} days)"
    return tl


def _why(a, m):
    ttype = a.get("trigger", {}).get("type")
    whys = {
        "proposal_not_sent": "A ready proposal that sits unsent loses momentum — sending it promptly keeps the deal warm.",
        "proposal_no_reply": "A short, well-timed follow-up meaningfully increases reply and win rates.",
        "contract_unsigned": "Work can't safely start until the contract is signed — a nudge protects your timeline and payment.",
        "invoice_due_soon": "A gentle heads-up before the due date makes on-time payment far more likely.",
        "invoice_overdue": "Overdue invoices are the #1 cause of cash-flow gaps — a polite reminder usually gets paid fastest.",
        "client_inactive": "Regular touchpoints keep clients warm and surface repeat work before competitors do.",
        "lead_needs_followup": "Leads go cold quickly — a timely follow-up keeps the opportunity alive.",
        "project_no_task": "Without a clear next task, projects quietly stall. Adding one keeps it moving.",
        "project_blocked": "A stalled project ties up focus — flagging it early prevents a bigger slip.",
        "contract_signed": "Kicking off immediately after signing sets a professional tone and momentum.",
        "project_completed": "Invoicing right after completion shortens the time to getting paid.",
        "new_client": "A prompt, structured onboarding makes a strong first impression.",
        "task_overdue": "Overdue tasks are the earliest signal a project is slipping.",
    }
    return whys.get(ttype, "Assistify detected this is worth acting on now.")


def _build_approval(org, a, m, effective_mode, settings):
    """Build the approval doc from an automation + matched entity. Returns (doc, will_execute)."""
    actions_out = []
    max_risk = "low"
    order = {"low": 0, "medium": 1, "high": 2}
    for action in a.get("actions", []):
        atype = action["type"]
        meta = ACTION_META.get(atype, {})
        payload = _prepare_action_payload(action, m) if effective_mode != "suggest" else {}
        actions_out.append({
            "type": atype, "label": meta.get("label", atype), "config": action.get("config", {}),
            "payload": payload, "risk": meta.get("risk", "low"), "kind": meta.get("kind", "internal"),
            "icon": meta.get("icon", "sparkles"), "time_saved": meta.get("time", 5),
        })
        if order.get(meta.get("risk", "low"), 0) > order.get(max_risk, 0):
            max_risk = meta.get("risk", "low")

    # Can this run automatically? Only if effective mode is auto AND every action is safe-internal
    # AND the org's approval prefs don't force confirmation for the action kinds present.
    prefs = settings.get("approval_prefs", {})
    kinds = {x["kind"] for x in actions_out}
    forces = (("external" in kinds and prefs.get("require_external", True)) or
              ("generative" in kinds and prefs.get("require_generative", True)) or
              ("destructive" in kinds and prefs.get("require_destructive", True)))
    all_safe = all(_is_safe(x["type"]) for x in actions_out)
    will_execute = (effective_mode == "auto") and all_safe and not forces and settings.get("safe_internal_auto", True)

    total_time = sum(x["time_saved"] for x in actions_out)
    act_labels = ", ".join(x["label"].lower() for x in actions_out)
    what = f"{a['name']}: {act_labels} for {m.get('entity_name')}"
    data_used = []
    if m.get("client_name"): data_used.append(f"Client: {m['client_name']}")
    if m.get("project_name"): data_used.append(f"Project: {m['project_name']}")
    data_used.append(f"Trigger: {TRIGGER_META.get(a.get('trigger', {}).get('type'), {}).get('label', 'event')}")

    status = "suggested" if effective_mode == "suggest" else ("executed" if will_execute else "pending")
    doc = {
        "id": str(uuid.uuid4()), "organizationId": org,
        "automation_id": a["id"], "automation_name": a["name"], "template_key": a.get("template_key"),
        "dedup": f"{a['id']}:{m.get('entity_id')}",
        "title": what, "what": what, "why": _why(a, m),
        "trigger": _human_trigger(a, m),
        "expected_result": _expected(a, actions_out, m),
        "time_saved": total_time, "risk_level": max_risk,
        "mode": effective_mode, "auto_executed": will_execute,
        "actions": actions_out, "data_used": data_used,
        "entity": {"type": m.get("entity_type"), "id": m.get("entity_id"), "name": m.get("entity_name"),
                   "project_id": m.get("project_id"), "client_id": m.get("client_id"),
                   "project_name": m.get("project_name"), "client_name": m.get("client_name")},
        "status": status, "created_at": now_iso(), "decided_at": None, "executed_at": None,
    }
    return doc, will_execute


def _expected(a, actions_out, m):
    parts = []
    for x in actions_out:
        t = x["type"]
        if t in ("prepare_email", "prepare_followup"):
            parts.append("A ready-to-send email draft you can review, edit and send")
        elif t == "create_task":
            parts.append(f"A new task: “{(x['payload'].get('task') or {}).get('title', 'follow-up')}”")
        elif t == "add_note":
            parts.append("A note added to the project")
        elif t == "notify_user":
            parts.append("A notification for you")
        elif t == "change_internal_status":
            parts.append(f"Status updated to {(x['payload'].get('status') or 'the next stage')}")
        elif t == "generate_invoice":
            parts.append("A draft invoice with line items and totals")
        elif t == "generate_proposal":
            parts.append("A draft proposal you can review")
        elif t == "generate_contract":
            parts.append("A draft contract you can review")
        elif t == "add_to_brief":
            parts.append("An item added to your daily AI Brief")
    return "; ".join(parts) or "A prepared action for your review."


# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------
async def _evaluate(org, force=False):
    settings = await _get_settings(org)
    result = {"prepared": 0, "executed": 0, "suggested": 0, "skipped_reason": None}
    if not settings.get("enabled"):
        result["skipped_reason"] = "disabled"
        await db.automation_settings.update_one({"organizationId": org}, {"$set": {"last_evaluated_at": now_iso()}})
        return result
    if _paused(settings):
        result["skipped_reason"] = "paused"
        await db.automation_settings.update_one({"organizationId": org}, {"$set": {"last_evaluated_at": now_iso()}})
        return result

    quiet = _in_quiet_hours(settings)
    ctx = await _gather(org)
    autos = await db.automations.find({"organizationId": org, "enabled": True}, {"_id": 0}).to_list(500)
    now = now_iso()
    nexteval = (_now() + timedelta(seconds=THROTTLE_SECONDS)).isoformat()

    for a in autos:
        eff_mode = a.get("mode") or settings.get("default_mode", "prepare")
        try:
            matches = await _detect(a, ctx)
        except Exception:
            logging.exception("automation detect failed")
            matches = []
        for m in matches:
            if not _cond_pass(a.get("conditions", []), m):
                continue
            dedup = f"{a['id']}:{m.get('entity_id')}"
            exists = await db.automation_approvals.find_one(
                {"organizationId": org, "dedup": dedup, "status": {"$in": ["pending", "suggested"]}}, {"_id": 0, "id": 1})
            if exists:
                continue
            doc, will_execute = _build_approval(org, a, m, eff_mode, settings)
            # Quiet hours: never auto-execute; hold as pending instead.
            if will_execute and quiet:
                will_execute = False
                doc["status"] = "pending"
                doc["auto_executed"] = False
            await db.automation_approvals.insert_one(dict(doc))
            await _log(org, a["id"], a["name"], "trigger_detected",
                       f"Detected: {doc['trigger']} on {m.get('entity_name')}", {"approval_id": doc["id"]})
            if eff_mode == "suggest":
                result["suggested"] += 1
                await _log(org, a["id"], a["name"], "conditions_evaluated",
                           f"Recommendation ready for {m.get('entity_name')} (suggest-only)", {"approval_id": doc["id"]})
            elif will_execute:
                await _log(org, a["id"], a["name"], "action_prepared",
                           f"Prepared {doc['what']}", {"approval_id": doc["id"]})
                ok = await _execute_actions(org, doc)
                result["executed"] += 1
                await _log(org, a["id"], a["name"], "executed" if ok else "failed",
                           f"Automatically ran: {doc['what']}" if ok else f"Failed to run: {doc['what']}",
                           {"approval_id": doc["id"]})
                await db.automations.update_one({"id": a["id"], "organizationId": org},
                                                {"$inc": {"runs_count": 1, "time_saved_total": doc["time_saved"]}})
            else:
                result["prepared"] += 1
                await _log(org, a["id"], a["name"], "action_prepared",
                           f"Prepared for your approval: {doc['what']}", {"approval_id": doc["id"]})
        await db.automations.update_one({"id": a["id"], "organizationId": org},
                                        {"$set": {"last_run": now, "next_evaluation": nexteval}})

    await db.automation_settings.update_one({"organizationId": org}, {"$set": {"last_evaluated_at": now}})
    return result


async def _maybe_evaluate(org):
    """Throttled: only re-evaluate if last run was more than THROTTLE_SECONDS ago."""
    settings = await _get_settings(org)
    last = settings.get("last_evaluated_at")
    if last and _age_seconds(last) < THROTTLE_SECONDS:
        return
    try:
        await _evaluate(org)
    except Exception:
        logging.exception("automation evaluate failed")


def _age_seconds(iso):
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (_now() - dt).total_seconds()
    except Exception:
        return 1e9


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
async def _execute_actions(org, approval):
    ok = True
    for x in approval.get("actions", []):
        try:
            await _execute_one(org, x, approval)
        except Exception:
            logging.exception("automation action execute failed")
            ok = False
    return ok


async def _execute_one(org, action, approval):
    atype = action["type"]
    payload = action.get("payload") or {}
    ent = approval.get("entity", {})
    if atype == "create_task":
        t = payload.get("task") or {}
        doc = {"id": str(uuid.uuid4()), "organizationId": org, "title": t.get("title", "Follow-up"),
               "priority": t.get("priority", "Medium"), "project_id": t.get("project_id") or ent.get("project_id"),
               "done": False, "created_at": now_iso()}
        await db.tasks.insert_one(dict(doc))
        if doc["project_id"]:
            await log_activity(doc["project_id"], "task_created", f'Task "{doc["title"]}" was created by automation')
    elif atype == "add_note":
        pid = ent.get("project_id")
        if pid:
            p = await db.projects.find_one({"id": pid, "organizationId": org}, {"_id": 0, "notes": 1})
            note = (payload.get("note") or "")
            existing = (p or {}).get("notes") or ""
            await db.projects.update_one({"id": pid, "organizationId": org},
                                         {"$set": {"notes": (existing + "\n\n" + note).strip(), "updated_at": now_iso()}})
    elif atype == "change_internal_status":
        pid = ent.get("project_id")
        if pid:
            await db.projects.update_one({"id": pid, "organizationId": org},
                                         {"$set": {"status": payload.get("status", "In Progress"), "updated_at": now_iso()}})
    elif atype == "notify_user":
        await db.automation_notifications.insert_one({
            "id": str(uuid.uuid4()), "organizationId": org, "message": payload.get("message", ""),
            "entity": ent, "read": False, "created_at": now_iso()})
    elif atype == "add_to_brief":
        await db.automation_brief.insert_one({
            "id": str(uuid.uuid4()), "organizationId": org, "text": payload.get("brief", ""),
            "entity": ent, "created_at": now_iso()})
    elif atype in ("prepare_email", "prepare_followup"):
        # Create a real outbound email draft (never silent-send unless explicitly allowed).
        email_payload = (payload.get("email") or {})
        subject = email_payload.get("subject") or "Follow-up"
        body = email_payload.get("body") or ""
        # Resolve recipient from linked client / entity
        to_email = None
        cid = ent.get("client_id") or (ent.get("id") if ent.get("type") == "client" else None)
        if cid:
            client = await db.clients.find_one({"id": cid, "organizationId": org}, {"_id": 0, "email": 1})
            to_email = (client or {}).get("email")
        if not to_email and ent.get("type") == "contact" and ent.get("id"):
            contact = await db.contacts.find_one({"id": ent["id"], "organizationId": org}, {"_id": 0, "email": 1})
            to_email = (contact or {}).get("email")
        if not to_email:
            # Fall back to any email embedded in action payload
            to_email = email_payload.get("to") or email_payload.get("email")
        if not to_email:
            logging.warning("automation email skipped — no recipient for approval %s", approval.get("id"))
            return

        # Deduplicate by automation approval + action type
        existing = await db.outbound_emails.find_one({
            "organizationId": org,
            "automationApprovalId": approval.get("id"),
            "source": "automation",
            "status": {"$nin": ["cancelled"]},
        }, {"_id": 0, "id": 1})
        if existing:
            return

        from routers.emails import create_outbound_email, get_org_email_settings, perform_send

        org_email = await get_org_email_settings(org)
        # Actor: org owner (system) for audit trail
        owner = await db.users.find_one(
            {"organizationId": org, "role": "owner"},
            {"_id": 0},
        ) or await db.users.find_one({"organizationId": org}, {"_id": 0})
        if not owner:
            return

        status = "pending_approval" if org_email.get("approvalRequired") else "draft"
        original = {"subject": subject, "textBody": body, "htmlBody": ""}
        doc = await create_outbound_email(
            org_id=org,
            user=owner,
            to=[to_email],
            subject=subject,
            text_body=body,
            source="automation",
            automation_id=approval.get("automation_id"),
            automation_approval_id=approval.get("id"),
            client_id=ent.get("client_id"),
            lead_id=ent.get("lead_id"),
            contact_id=ent.get("contact_id"),
            original_ai=original,
            status=status,
        )
        # Link back on approval
        await db.automation_approvals.update_one(
            {"id": approval.get("id"), "organizationId": org},
            {"$set": {"outboundEmailId": doc["id"], "updated_at": now_iso()}},
        )
        # Auto-send only when explicitly enabled at org level AND approval not required
        # AND automation mode was auto — still never bypass global/org sending gates inside perform_send
        if (
            not org_email.get("approvalRequired")
            and org_email.get("autoSendFromAutomation")
            and approval.get("auto_executed")
        ):
            # Mark approved/not_required then attempt send (may still be blocked by EMAIL_SENDING_ENABLED)
            await db.outbound_emails.update_one(
                {"id": doc["id"], "organizationId": org},
                {"$set": {"status": "approved", "approvalStatus": "not_required", "updatedAt": now_iso()}},
            )
            refreshed = await db.outbound_emails.find_one({"id": doc["id"], "organizationId": org}, {"_id": 0})
            try:
                await perform_send(refreshed, owner)
            except Exception:
                logging.exception("automation auto-send blocked or failed for %s", doc["id"])
    elif atype in ("generate_proposal", "generate_contract", "generate_invoice"):
        pid = ent.get("project_id")
        if pid:
            import server as S
            fn = {"generate_proposal": S.generate_proposal, "generate_contract": S.generate_contract,
                  "generate_invoice": S.generate_invoice}[atype]
            await fn(pid, org)


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------
@router.get("/settings")
async def get_settings(org: str = Depends(current_org)):
    s = await _get_settings(org)
    s["paused"] = _paused(s)
    return s


class SettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    default_mode: Optional[str] = None
    safe_internal_auto: Optional[bool] = None
    notifications: Optional[dict] = None
    quiet_hours: Optional[dict] = None
    timezone: Optional[str] = None
    approval_prefs: Optional[dict] = None


@router.patch("/settings")
async def update_settings(body: SettingsUpdate, org: str = Depends(current_org)):
    await ensure_automation_setup(org)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "default_mode" in upd and upd["default_mode"] not in ("suggest", "prepare", "auto"):
        raise HTTPException(status_code=400, detail="Invalid default mode")
    upd["updated_at"] = now_iso()
    await db.automation_settings.update_one({"organizationId": org}, {"$set": upd})
    if "enabled" in upd:
        await _log(org, None, "All automations", "disabled" if not upd["enabled"] else "enabled",
                   "Automations turned off" if not upd["enabled"] else "Automations turned on")
    s = await _get_settings(org)
    s["paused"] = _paused(s)
    return s


class PauseBody(BaseModel):
    duration: str  # 1h | tomorrow | 1w | forever


@router.post("/pause")
async def pause_all(body: PauseBody, org: str = Depends(current_org)):
    await ensure_automation_setup(org)
    now = _now()
    until = {
        "1h": now + timedelta(hours=1),
        "tomorrow": (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
        "1w": now + timedelta(weeks=1),
        "forever": now + timedelta(days=3650),
    }.get(body.duration)
    if not until:
        raise HTTPException(status_code=400, detail="Invalid pause duration")
    await db.automation_settings.update_one({"organizationId": org},
                                            {"$set": {"paused_until": until.isoformat(), "updated_at": now_iso()}})
    await _log(org, None, "All automations", "paused", f"Automations paused ({body.duration})")
    s = await _get_settings(org)
    s["paused"] = _paused(s)
    return s


@router.post("/resume")
async def resume_all(org: str = Depends(current_org)):
    await ensure_automation_setup(org)
    await db.automation_settings.update_one({"organizationId": org},
                                            {"$set": {"paused_until": None, "updated_at": now_iso()}})
    await _log(org, None, "All automations", "enabled", "Automations resumed")
    s = await _get_settings(org)
    s["paused"] = _paused(s)
    return s


# ---------------------------------------------------------------------------
# Automations (rules)
# ---------------------------------------------------------------------------
@router.get("/automations")
async def list_automations(org: str = Depends(current_org)):
    await _maybe_evaluate(org)
    autos = await db.automations.find({"organizationId": org}, {"_id": 0}).sort("created_at", 1).to_list(500)
    for a in autos:
        a["trigger_label"] = TRIGGER_META.get(a.get("trigger", {}).get("type"), {}).get("label", a.get("trigger", {}).get("type"))
        a["trigger_icon"] = TRIGGER_META.get(a.get("trigger", {}).get("type"), {}).get("icon", "zap")
        a["action_labels"] = [ACTION_META.get(x["type"], {}).get("label", x["type"]) for x in a.get("actions", [])]
        a["pending_count"] = await db.automation_approvals.count_documents(
            {"organizationId": org, "automation_id": a["id"], "status": "pending"})
    return autos


class AutomationBody(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    trigger: dict
    conditions: List[dict] = Field(default_factory=list)
    actions: List[dict] = Field(default_factory=list)
    mode: str = "prepare"
    enabled: bool = True


@router.post("/automations")
async def create_automation(body: AutomationBody, org: str = Depends(current_org)):
    await ensure_automation_setup(org)
    if body.trigger.get("type") not in TRIGGER_META:
        raise HTTPException(status_code=400, detail="Unknown trigger type")
    if body.mode not in ("suggest", "prepare", "auto"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    for act in body.actions:
        if act.get("type") not in ACTION_META:
            raise HTTPException(status_code=400, detail=f"Unknown action: {act.get('type')}")
    doc = {"id": str(uuid.uuid4()), "organizationId": org, "source": "custom", "template_key": None,
           "name": body.name, "description": body.description, "enabled": body.enabled, "mode": body.mode,
           "trigger": body.trigger, "conditions": body.conditions, "actions": body.actions,
           "status": "Active", "last_run": None, "next_evaluation": None,
           "runs_count": 0, "time_saved_total": 0, "created_at": now_iso(), "updated_at": now_iso()}
    await db.automations.insert_one(dict(doc))
    await _log(org, doc["id"], doc["name"], "enabled", f'Automation "{doc["name"]}" created')
    return doc


@router.put("/automations/{aid}")
async def update_automation(aid: str, body: AutomationBody, org: str = Depends(current_org)):
    ex = await db.automations.find_one({"id": aid, "organizationId": org}, {"_id": 0})
    if not ex:
        raise HTTPException(status_code=404, detail="Automation not found")
    if body.trigger.get("type") not in TRIGGER_META:
        raise HTTPException(status_code=400, detail="Unknown trigger type")
    upd = {"name": body.name, "description": body.description, "trigger": body.trigger,
           "conditions": body.conditions, "actions": body.actions, "mode": body.mode,
           "enabled": body.enabled, "updated_at": now_iso()}
    await db.automations.update_one({"id": aid, "organizationId": org}, {"$set": upd})
    return {**ex, **upd}


class ToggleBody(BaseModel):
    enabled: bool


@router.patch("/automations/{aid}/toggle")
async def toggle_automation(aid: str, body: ToggleBody, org: str = Depends(current_org)):
    ex = await db.automations.find_one({"id": aid, "organizationId": org}, {"_id": 0, "name": 1})
    if not ex:
        raise HTTPException(status_code=404, detail="Automation not found")
    await db.automations.update_one({"id": aid, "organizationId": org},
                                    {"$set": {"enabled": body.enabled, "status": "Active" if body.enabled else "Paused", "updated_at": now_iso()}})
    await _log(org, aid, ex.get("name"), "enabled" if body.enabled else "disabled",
               f'Automation "{ex.get("name")}" {"enabled" if body.enabled else "disabled"}')
    return {"ok": True, "enabled": body.enabled}


class ModeBody(BaseModel):
    mode: str


@router.patch("/automations/{aid}/mode")
async def set_mode(aid: str, body: ModeBody, org: str = Depends(current_org)):
    if body.mode not in ("suggest", "prepare", "auto"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    r = await db.automations.update_one({"id": aid, "organizationId": org},
                                        {"$set": {"mode": body.mode, "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Automation not found")
    return {"ok": True, "mode": body.mode}


@router.delete("/automations/{aid}")
async def delete_automation(aid: str, org: str = Depends(current_org)):
    ex = await db.automations.find_one({"id": aid, "organizationId": org}, {"_id": 0, "name": 1})
    if not ex:
        raise HTTPException(status_code=404, detail="Automation not found")
    await db.automations.delete_one({"id": aid, "organizationId": org})
    await db.automation_approvals.delete_many({"organizationId": org, "automation_id": aid, "status": {"$in": ["pending", "suggested"]}})
    await _log(org, aid, ex.get("name"), "disabled", f'Automation "{ex.get("name")}" deleted')
    return {"ok": True}


@router.get("/builder-options")
async def builder_options(org: str = Depends(current_org)):
    return {
        "triggers": [{"type": k, **v} for k, v in TRIGGER_META.items()],
        "conditions": {"fields": CONDITION_FIELDS, "ops": CONDITION_OPS},
        "actions": [{"type": k, **v} for k, v in ACTION_META.items()],
        "modes": [
            {"value": "suggest", "label": "Suggest only", "desc": "Detect and recommend — never prepares or runs."},
            {"value": "prepare", "label": "Prepare for approval", "desc": "Prepare drafts; you confirm before anything runs."},
            {"value": "auto", "label": "Fully automatic", "desc": "Safe internal actions run automatically; risky actions still need approval."},
        ],
    }


# ---------------------------------------------------------------------------
# Approval Center
# ---------------------------------------------------------------------------
@router.get("/approvals")
async def list_approvals(status: str = "pending", org: str = Depends(current_org)):
    await _maybe_evaluate(org)
    q = {"organizationId": org}
    if status and status != "all":
        q["status"] = status
    items = await db.automation_approvals.find(q, {"_id": 0}).sort("created_at", -1).to_list(300)
    counts = {}
    for st in ("pending", "suggested", "executed", "rejected", "failed"):
        counts[st] = await db.automation_approvals.count_documents({"organizationId": org, "status": st})
    return {"items": items, "counts": counts,
            "total_time_saved": sum(i.get("time_saved", 0) for i in items if i.get("status") == "pending")}


@router.post("/approvals/{apid}/approve")
async def approve(apid: str, org: str = Depends(current_org)):
    ap = await db.automation_approvals.find_one({"id": apid, "organizationId": org}, {"_id": 0})
    if not ap:
        raise HTTPException(status_code=404, detail="Approval not found")
    if ap.get("status") not in ("pending",):
        raise HTTPException(status_code=409, detail="This action is no longer pending")
    await _log(org, ap.get("automation_id"), ap.get("automation_name"), "approved",
               f"You approved: {ap.get('what')}", {"approval_id": apid})
    ok = await _execute_actions(org, ap)
    new_status = "executed" if ok else "failed"
    await db.automation_approvals.update_one({"id": apid, "organizationId": org},
                                             {"$set": {"status": new_status, "decided_at": now_iso(), "executed_at": now_iso()}})
    await _log(org, ap.get("automation_id"), ap.get("automation_name"), new_status,
               f"Executed: {ap.get('what')}" if ok else f"Failed to execute: {ap.get('what')}", {"approval_id": apid})
    if ok:
        await db.automations.update_one({"id": ap.get("automation_id"), "organizationId": org},
                                        {"$inc": {"runs_count": 1, "time_saved_total": ap.get("time_saved", 0)}})
    return {"ok": ok, "status": new_status}


@router.post("/approvals/{apid}/reject")
async def reject(apid: str, org: str = Depends(current_org)):
    ap = await db.automation_approvals.find_one({"id": apid, "organizationId": org}, {"_id": 0})
    if not ap:
        raise HTTPException(status_code=404, detail="Approval not found")
    await db.automation_approvals.update_one({"id": apid, "organizationId": org},
                                             {"$set": {"status": "rejected", "decided_at": now_iso()}})
    await _log(org, ap.get("automation_id"), ap.get("automation_name"), "rejected",
               f"You rejected: {ap.get('what')}", {"approval_id": apid})
    return {"ok": True}


@router.post("/approvals/{apid}/prepare")
async def prepare_suggestion(apid: str, org: str = Depends(current_org)):
    """Convert a suggest-only recommendation into a prepared, approvable action."""
    ap = await db.automation_approvals.find_one({"id": apid, "organizationId": org}, {"_id": 0})
    if not ap:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if ap.get("status") != "suggested":
        raise HTTPException(status_code=409, detail="Not a suggestion")
    a = await db.automations.find_one({"id": ap.get("automation_id"), "organizationId": org}, {"_id": 0})
    actions_out = []
    for act in (a or {}).get("actions", []):
        meta = ACTION_META.get(act["type"], {})
        m = {"entity_name": ap["entity"].get("name"), "client_name": ap["entity"].get("client_name"),
             "project_name": ap["entity"].get("project_name"), "project_id": ap["entity"].get("project_id"),
             "context": {}}
        actions_out.append({"type": act["type"], "label": meta.get("label", act["type"]),
                            "config": act.get("config", {}), "payload": _prepare_action_payload(act, m),
                            "risk": meta.get("risk", "low"), "kind": meta.get("kind", "internal"),
                            "icon": meta.get("icon", "sparkles"), "time_saved": meta.get("time", 5)})
    await db.automation_approvals.update_one({"id": apid, "organizationId": org},
                                             {"$set": {"status": "pending", "actions": actions_out}})
    await _log(org, ap.get("automation_id"), ap.get("automation_name"), "action_prepared",
               f"Prepared from recommendation: {ap.get('what')}", {"approval_id": apid})
    return {"ok": True}


class EditApproval(BaseModel):
    actions: List[dict]


@router.put("/approvals/{apid}")
async def edit_approval(apid: str, body: EditApproval, org: str = Depends(current_org)):
    r = await db.automation_approvals.update_one({"id": apid, "organizationId": org, "status": "pending"},
                                                 {"$set": {"actions": body.actions, "updated_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pending approval not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# History + summary
# ---------------------------------------------------------------------------
EVENT_LABEL = {
    "trigger_detected": "Trigger detected", "conditions_evaluated": "Conditions evaluated",
    "action_prepared": "Action prepared", "approved": "Approved", "rejected": "Rejected",
    "executed": "Executed", "failed": "Failed", "disabled": "Disabled", "enabled": "Enabled", "paused": "Paused",
}


@router.get("/logs")
async def list_logs(limit: int = 100, org: str = Depends(current_org)):
    logs = await db.automation_logs.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 300))
    for l in logs:
        l["event_label"] = EVENT_LABEL.get(l.get("event"), l.get("event"))
    return {"items": logs}


@router.post("/run")
async def run_now(org: str = Depends(current_org)):
    res = await _evaluate(org, force=True)
    return {"ok": True, **res}


@router.get("/summary")
async def summary(org: str = Depends(current_org)):
    await _maybe_evaluate(org)
    s = await _get_settings(org)
    pending = await db.automation_approvals.count_documents({"organizationId": org, "status": "pending"})
    suggested = await db.automation_approvals.count_documents({"organizationId": org, "status": "suggested"})
    active = await db.automations.count_documents({"organizationId": org, "enabled": True})
    total = await db.automations.count_documents({"organizationId": org})
    executed = await db.automation_approvals.count_documents({"organizationId": org, "status": "executed"})
    autos = await db.automations.find({"organizationId": org}, {"_id": 0, "time_saved_total": 1}).to_list(500)
    time_saved = sum(a.get("time_saved_total", 0) for a in autos)
    return {"enabled": s.get("enabled"), "paused": _paused(s), "paused_until": s.get("paused_until"),
            "default_mode": s.get("default_mode"), "pending": pending, "suggested": suggested,
            "active_automations": active, "total_automations": total,
            "executed_count": executed, "time_saved_total": time_saved}


# ---------------------------------------------------------------------------
# Demo seeding
# ---------------------------------------------------------------------------
async def seed_demo_automations(org: str):
    """Provision defaults + template automations, then run one evaluation so the
    demo Approval Center & History show value immediately."""
    await ensure_automation_setup(org)
    try:
        await _evaluate(org, force=True)
    except Exception:
        logging.exception("demo automation seed evaluate failed")
