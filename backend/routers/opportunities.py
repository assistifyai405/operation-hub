"""AI Opportunities & Recommendations engine — Assistify proactively scans the
workspace, surfaces prioritized recommendations with one-click actions, a daily
brief and an overall Workspace Health score. Read-mostly; the only mutations are
snooze (dismiss) and archive-project.
"""
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, now_iso, log_activity
from dependencies import current_org

router = APIRouter(prefix="/api/opportunities")


def _now():
    return datetime.now(timezone.utc)


def _days_ago_iso(d):
    return (_now() - timedelta(days=d)).isoformat()


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


# type -> config: base score, minutes saved, confidence, icon, action(label, kind, tab, command)
CFG = {
    "invoice_overdue":     dict(base=84, t=6, conf=95, icon="receipt",       label="Payment reminder recommended",   action=("Send payment reminder", "assistant", "invoice", "email")),
    "contract_unsigned":   dict(base=66, t=8, conf=90, icon="scroll-text",   label="Contract awaiting signature",     action=("Review contract", "navigate", "contract", None)),
    "deal_stale":          dict(base=62, t=8, conf=88, icon="trending-up",   label="Stale pipeline deal",             action=("Open pipeline", "navigate_pipeline", None, None)),
    "task_overdue":        dict(base=60, t=5, conf=94, icon="check-square",  label="Overdue task",                    action=("View tasks", "navigate_tasks", None, None)),
    "proposal_unsent":     dict(base=58, t=9, conf=88, icon="file-text",     label="Proposal ready to send",          action=("Review & send proposal", "navigate", "proposal", None)),
    "follow_up":           dict(base=55, t=9, conf=85, icon="mail",          label="Follow-up recommended",           action=("Generate follow-up email", "assistant", "proposal", "email")),
    "project_inactive":    dict(base=52, t=6, conf=84, icon="folder-kanban", label="Project is inactive",             action=("Review or archive project", "archive", "overview", None)),
    "client_not_contacted":dict(base=46, t=8, conf=80, icon="users",         label="Client needs attention",          action=("Open client", "navigate_client", None, None)),
    "proposal_improve":    dict(base=44, t=7, conf=82, icon="file-text",     label="Proposal could be improved",      action=("Improve proposal", "assistant", "proposal", "improve")),
    "project_no_task":     dict(base=40, t=5, conf=88, icon="check-square",  label="Project has no next task",        action=("Schedule next task", "navigate", "tasks", None)),
    "project_no_deadline": dict(base=36, t=4, conf=85, icon="calendar",      label="Missing project deadline",        action=("Set a deadline", "navigate", "overview", None)),
    "duplicate_documents": dict(base=34, t=5, conf=78, icon="copy",          label="Possible duplicate documents",    action=("Review documents", "navigate", "proposals", None)),
    "client_missing_info": dict(base=30, t=4, conf=90, icon="users",         label="Missing client information",      action=("Complete client details", "navigate_client", None, None)),
}

_PRIO = [(80, "Critical", "red"), (60, "High", "orange"), (35, "Medium", "yellow"), (0, "Low", "green")]


def _prio(score):
    for th, name, color in _PRIO:
        if score >= th:
            return name, color
    return "Low", "green"


async def _scan(org: str):
    base = {"organizationId": org}
    today = _now().strftime("%Y-%m-%d")
    projects = await db.projects.find(base, {"_id": 0}).to_list(500)
    pmap = {p["id"]: p for p in projects}
    clients = await db.clients.find(base, {"_id": 0}).to_list(500)
    cmap = {c["id"]: c for c in clients}
    dismissed = {d["key"] for d in await db.opportunity_dismissals.find(
        {**base, "until": {"$gt": _now().isoformat()}}, {"_id": 0, "key": 1}).to_list(500)}

    items = []

    def add(atype, entity_id, title, explanation, why, extra_score=0, project=None, client=None):
        key = f"{atype}:{entity_id}"
        if key in dismissed:
            return
        cfg = CFG[atype]
        score = max(0, min(100, cfg["base"] + extra_score))
        prio, color = _prio(score)
        label, kind, tab, command = cfg["action"]
        link = None
        if kind == "navigate" and project:
            link = f"/projects/{project}?tab={tab}"
        elif kind == "assistant" and project:
            link = f"/projects/{project}?tab={tab}&assist={command}"
        elif kind == "archive" and project:
            link = f"/projects/{project}"
        elif kind == "navigate_client":
            link = "/clients"
        elif kind == "navigate_tasks":
            link = "/tasks"
        elif kind == "navigate_pipeline":
            link = "/pipeline"
        items.append({
            "id": str(uuid.uuid4()), "key": key, "type": atype, "title": title,
            "explanation": explanation, "why": why, "time_saved": cfg["t"],
            "confidence": cfg["conf"], "score": score, "priority": prio, "color": color,
            "icon": cfg["icon"],
            "action": {"label": label, "kind": kind, "link": link, "command": command,
                       "project_id": project, "client_id": client},
            "entity": {"project_id": project, "project_name": pmap.get(project, {}).get("name") if project else None,
                       "client_id": client, "client_name": cmap.get(client, {}).get("name") if client else None},
        })

    # ---- Invoices ----
    invoices = await db.ai_invoices.find(base, {"_id": 0}).to_list(500)
    for inv in invoices:
        st = inv.get("status")
        due = (inv.get("content") or {}).get("due_date")
        pid = inv.get("project_id")
        pname = pmap.get(pid, {}).get("name", "a project")
        overdue = st == "Overdue" or (due and str(due)[:10] < today and st in ("Sent", "Overdue"))
        if overdue and st != "Paid":
            od = _age_days(due) if due else 0
            add("invoice_overdue", inv.get("id"),
                f"Invoice {inv.get('invoice_number') or ''} is overdue".replace("  ", " ").strip(),
                f"Invoice for {pname} is past its due date{f' by {od} days' if od else ''} and still unpaid.",
                "Overdue invoices are the #1 cause of cash-flow gaps — a polite reminder today usually gets paid fastest.",
                extra_score=min(15, od), project=pid, client=pmap.get(pid, {}).get("client_id"))

    # ---- Contracts ----
    contracts = await db.ai_contracts.find(base, {"_id": 0}).to_list(500)
    for c in contracts:
        if c.get("status") in ("Generated", "Sent") and _age_days(c.get("updated_at")) >= 3:
            pid = c.get("project_id")
            pname = pmap.get(pid, {}).get("name", "a project")
            add("contract_unsigned", c.get("id"),
                f"Contract for {pname} is unsigned",
                f"The service agreement for {pname} has been waiting {_age_days(c.get('updated_at'))} days without a signature.",
                "Work often can't safely start until the contract is signed — following up protects your timeline and payment.",
                extra_score=min(14, _age_days(c.get("updated_at"))), project=pid, client=pmap.get(pid, {}).get("client_id"))

    # ---- Proposals ----
    proposals = await db.ai_proposals.find(base, {"_id": 0}).to_list(500)
    seen_titles = {}
    for p in proposals:
        pid = p.get("project_id")
        pname = pmap.get(pid, {}).get("name", "a project")
        st = p.get("status")
        age = _age_days(p.get("updated_at") or p.get("created_at"))
        if st in ("Draft", "Generated") and age >= 5:
            add("proposal_unsent", p.get("id"),
                f"Proposal for {pname} not sent yet",
                f"This proposal has been ready for {age} days but hasn't been sent to the client.",
                "Every day a ready proposal sits unsent is a day the deal cools — sending it now keeps momentum.",
                extra_score=min(18, age - 5), project=pid, client=pmap.get(pid, {}).get("client_id"))
        elif st == "Sent" and age >= 3:
            add("follow_up", p.get("id"),
                f"Follow up on the {pname} proposal",
                f"Your proposal for {pname} was sent {age} days ago with no recorded reply.",
                "A short, well-timed follow-up meaningfully increases reply and win rates.",
                extra_score=min(12, age - 3), project=pid, client=pmap.get(pid, {}).get("client_id"))
        # weak / improvable proposal (few sections filled)
        content = p.get("content") or {}
        filled = sum(1 for v in content.values() if v and (v if not isinstance(v, list) else len(v)))
        if st in ("Draft", "Generated") and content and filled < max(3, len(content) // 2):
            add("proposal_improve", p.get("id"),
                f"Strengthen the {pname} proposal",
                f"Several sections of the {pname} proposal look thin or empty.",
                "A fuller, sharper proposal reads as more professional and converts better.",
                project=pid, client=pmap.get(pid, {}).get("client_id"))
        # duplicate titles
        t = (p.get("title") or "").strip().lower()
        if t:
            if t in seen_titles:
                add("duplicate_documents", p.get("id"),
                    f"Possible duplicate proposal: {p.get('title')}",
                    f"More than one proposal shares the title \"{p.get('title')}\".",
                    "Duplicates cause confusion and version mistakes — worth consolidating.",
                    project=pid, client=pmap.get(pid, {}).get("client_id"))
            seen_titles[t] = True

    # ---- Projects ----
    active_states = ("In Progress", "Review", "Planning")
    for p in projects:
        if p.get("status") in ("Completed", "Archived", "Cancelled"):
            continue
        pid = p["id"]
        open_tasks = await db.tasks.count_documents({**base, "project_id": pid, "done": False})
        if p.get("status") in active_states and open_tasks == 0:
            add("project_no_task", pid, f"{p['name']} has no next task",
                f"{p['name']} is active but has no open tasks defined.",
                "Without a clear next task, projects quietly stall. Adding one keeps it moving.",
                project=pid, client=p.get("client_id"))
        if not p.get("due"):
            add("project_no_deadline", pid, f"{p['name']} has no deadline",
                f"{p['name']} doesn't have a target completion date.",
                "A deadline creates accountability and helps you plan capacity.",
                project=pid, client=p.get("client_id"))
        last = await db.activities.find_one({**base, "project_id": pid}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
        last_when = last.get("created_at") if last else p.get("updated_at")
        inactive_days = _age_days(last_when)
        if p.get("status") in active_states and inactive_days >= 14:
            add("project_inactive", pid, f"{p['name']} looks inactive",
                f"No activity on {p['name']} in {inactive_days} days.",
                "Stalled projects tie up focus. A quick review — or archiving — frees you up.",
                extra_score=min(16, inactive_days - 14), project=pid, client=p.get("client_id"))

    # ---- Overdue tasks ----
    open_tasks = await db.tasks.find({**base, "done": False, "due": {"$nin": [None, ""]}}, {"_id": 0}).to_list(500)
    for t in open_tasks:
        due = str(t.get("due") or "")[:10]
        if due and due < today:
            od = _age_days(due)
            pid = t.get("project_id")
            add("task_overdue", t.get("id"),
                f"Overdue: {t.get('title') or 'Task'}",
                f"This task was due {od} day{'s' if od != 1 else ''} ago"
                + (f" on {pmap.get(pid, {}).get('name')}" if pid and pmap.get(pid) else "") + ".",
                "Clearing overdue work protects delivery dates and client trust.",
                extra_score=min(18, od), project=pid, client=pmap.get(pid, {}).get("client_id") if pid else None)

    # ---- Stale pipeline deals ----
    OPEN_STAGES = ("New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating")
    leads = await db.leads.find(base, {"_id": 0}).to_list(500)
    for lead in leads:
        if lead.get("stage") not in OPEN_STAGES:
            continue
        idle = _age_days(lead.get("stage_changed_at") or lead.get("updated_at") or lead.get("created_at"))
        if idle < 14:
            continue
        title = lead.get("title") or cmap.get(lead.get("client_id"), {}).get("name") or "Untitled deal"
        value = lead.get("value") or 0
        add("deal_stale", lead.get("id"),
            f"Stale deal: {title}",
            f"No stage movement in {idle} days"
            + (f" · ${int(value):,} in pipeline" if value else "") + ".",
            "Quiet deals cool quickly — a short check-in often restarts momentum.",
            extra_score=min(16, idle - 14), project=lead.get("project_id"), client=lead.get("client_id"))

    # ---- Clients ----
    for c in clients:
        cid = c["id"]
        missing = [f for f in ("email", "contact", "phone") if not (c.get(f) or "").strip()]
        if missing:
            add("client_missing_info", cid, f"Complete {c['name']}'s details",
                f"{c['name']} is missing: {', '.join(missing)}.",
                "Complete contact details mean faster invoicing, sending and follow-up — no chasing information later.",
                client=cid)
        # not contacted: no proposal/invoice/activity referencing this client's projects recently
        cproj = [pp["id"] for pp in projects if pp.get("client_id") == cid]
        recent = 0
        if cproj:
            recent = await db.activities.count_documents({**base, "project_id": {"$in": cproj}, "created_at": {"$gt": _days_ago_iso(21)}})
        if c.get("status") == "Active" and recent == 0:
            add("client_not_contacted", cid, f"{c['name']} hasn't heard from you recently",
                f"There's been no recorded activity with {c['name']} in over three weeks.",
                "Regular touchpoints keep clients warm and surface repeat work before competitors do.",
                client=cid)

    items.sort(key=lambda x: (-x["score"], -x["time_saved"]))
    return items


@router.get("")
async def list_opportunities(org: str = Depends(current_org)):
    items = await _scan(org)
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for it in items:
        counts[it["priority"].lower()] += 1
    return {"items": items, "total": len(items),
            "total_time_saved": sum(i["time_saved"] for i in items),
            "counts": counts, "generated_at": now_iso()}


@router.get("/brief")
async def daily_brief(org: str = Depends(current_org)):
    items = await _scan(org)
    hour = _now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], 0)
        by_type[it["type"]] += 1
    lines = []
    def pl(n, s, p):
        return f"{n} {s if n == 1 else p}"
    inv = by_type.get("invoice_overdue", 0)
    if inv:
        lines.append({"icon": "receipt", "text": pl(inv, "invoice requires", "invoices require") + " attention"})
    ready = by_type.get("proposal_unsent", 0)
    if ready:
        lines.append({"icon": "file-text", "text": pl(ready, "proposal is", "proposals are") + " ready to send"})
    fu = by_type.get("follow_up", 0)
    if fu:
        lines.append({"icon": "mail", "text": pl(fu, "follow-up", "follow-ups") + " recommended"})
    idle = by_type.get("client_not_contacted", 0)
    if idle:
        lines.append({"icon": "users", "text": pl(idle, "client needs", "clients need") + " a touch-base"})
    inact = by_type.get("project_inactive", 0)
    if inact:
        lines.append({"icon": "folder-kanban", "text": pl(inact, "project looks", "projects look") + " inactive"})
    overdue_tasks = by_type.get("task_overdue", 0)
    if overdue_tasks:
        lines.append({"icon": "check-square", "text": pl(overdue_tasks, "task is", "tasks are") + " overdue"})
    stale = by_type.get("deal_stale", 0)
    if stale:
        lines.append({"icon": "trending-up", "text": pl(stale, "pipeline deal is", "pipeline deals are") + " going cold"})
    if not lines:
        # Distinguish empty workspace from genuinely healthy workspace
        n_cli = await db.clients.count_documents({"organizationId": org})
        n_proj = await db.projects.count_documents({"organizationId": org})
        n_tasks = await db.tasks.count_documents({"organizationId": org})
        n_leads = await db.leads.count_documents({"organizationId": org})
        if any([n_cli, n_proj, n_tasks, n_leads]):
            lines.append({"icon": "sparkles", "text": "Your workspace is in great shape — nothing needs urgent attention."})
        else:
            lines.append({"icon": "sparkles", "text": "Add a client or project to start seeing live workspace insights."})
    return {"greeting": greeting, "lines": lines[:5],
            "total_time_saved": sum(i["time_saved"] for i in items),
            "total": len(items), "top": items[:3]}


@router.get("/health")
async def workspace_health(org: str = Depends(current_org)):
    base = {"organizationId": org}
    items = await _scan(org)
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], 0)
        by_type[it["type"]] += 1

    def cat(score, reasons):
        return {"score": max(0, min(100, round(score))), "reasons": reasons}

    n_inv = await db.ai_invoices.count_documents(base)
    n_con = await db.ai_contracts.count_documents(base)
    n_proj = await db.projects.count_documents(base)
    n_cli = await db.clients.count_documents(base)
    n_tasks = await db.tasks.count_documents(base)
    n_leads = await db.leads.count_documents(base)
    recent_activity = await db.activities.count_documents({**base, "created_at": {"$gt": _days_ago_iso(7)}})
    has_workspace_data = any([n_inv, n_con, n_proj, n_cli, n_tasks, n_leads, recent_activity])

    if not has_workspace_data:
        return {
            "score": None,
            "grade": "No data yet",
            "has_workspace_data": False,
            "categories": [],
            "top_reasons": ["Add clients, projects or deals to start measuring workspace health."],
        }

    cats = {}
    over = by_type.get("invoice_overdue", 0)
    cats["Invoices"] = cat(100 - (over / max(1, n_inv)) * 100 if n_inv else 100,
                           [f"{over} overdue invoice(s)"] if over else ["All invoices on track"])
    unsigned = by_type.get("contract_unsigned", 0)
    cats["Contracts"] = cat(100 - (unsigned / max(1, n_con)) * 100 if n_con else 100,
                            [f"{unsigned} contract(s) unsigned"] if unsigned else ["No contracts awaiting signature"])
    proj_issues = by_type.get("project_inactive", 0) + by_type.get("project_no_task", 0) + by_type.get("project_no_deadline", 0)
    cats["Projects"] = cat(100 - (proj_issues * 12), _reasons([
        (by_type.get("project_inactive", 0), "inactive"), (by_type.get("project_no_task", 0), "without a next task"),
        (by_type.get("project_no_deadline", 0), "without a deadline")], "project") or ["Projects are healthy"])
    cli_issues = by_type.get("client_missing_info", 0) + by_type.get("client_not_contacted", 0)
    cats["Clients"] = cat(100 - (cli_issues * 10), _reasons([
        (by_type.get("client_not_contacted", 0), "flagged for a check-in"), (by_type.get("client_missing_info", 0), "with missing details")], "client") or ["Client records look good"])
    task_over = by_type.get("task_overdue", 0)
    cats["Tasks"] = cat(100 - (task_over * 14) if n_tasks else 100,
                        [f"{task_over} overdue task(s)"] if task_over else ["No overdue tasks"])
    stale = by_type.get("deal_stale", 0)
    cats["Pipeline"] = cat(100 - (stale * 12) if n_leads else 100,
                           [f"{stale} stale deal(s)"] if stale else ["Pipeline looks active"])
    cats["Activity"] = cat(min(100, 40 + recent_activity * 12),
                           [f"{recent_activity} action(s) in the last 7 days"] if recent_activity else ["No activity in the last 7 days"])
    outstanding = len(items)
    cats["Outstanding work"] = cat(100 - outstanding * 6,
                                   [f"{outstanding} open recommendation(s)"] if outstanding else ["Nothing outstanding"])

    overall = round(sum(c["score"] for c in cats.values()) / len(cats))
    grade = "Excellent" if overall >= 90 else ("Good" if overall >= 75 else ("Fair" if overall >= 55 else "Needs attention"))
    low = sorted([(k, v) for k, v in cats.items()], key=lambda x: x[1]["score"])[:3]
    return {"score": overall, "grade": grade, "has_workspace_data": True,
            "categories": [{"name": k, **v} for k, v in cats.items()],
            "top_reasons": [r for k, v in low if v["score"] < 100 for r in v["reasons"]][:4]}


def _reasons(pairs, noun):
    out = []
    for n, suffix in pairs:
        if n:
            out.append(f"{n} {noun if n == 1 else noun + 's'} {suffix}")
    return out


class DismissBody(BaseModel):
    key: str


@router.post("/dismiss")
async def dismiss_opportunity(body: DismissBody, org: str = Depends(current_org)):
    await db.opportunity_dismissals.update_one(
        {"organizationId": org, "key": body.key},
        {"$set": {"organizationId": org, "key": body.key,
                  "until": (_now() + timedelta(days=7)).isoformat(), "created_at": now_iso()}},
        upsert=True)
    return {"ok": True}


@router.post("/archive-project/{project_id}")
async def archive_project(project_id: str, org: str = Depends(current_org)):
    p = await db.projects.find_one({"id": project_id, "organizationId": org}, {"_id": 0, "name": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.projects.update_one({"id": project_id, "organizationId": org},
                                 {"$set": {"status": "Archived", "updated_at": now_iso()}})
    await log_activity(project_id, "project_archived", f'Project "{p.get("name")}" was archived')
    return {"ok": True, "status": "Archived"}
