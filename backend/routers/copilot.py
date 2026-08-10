import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from core import db, now_iso, log_activity, ai_service
from ai_service import extract_json
from dependencies import current_org

router = APIRouter(prefix="/api")

# ==================================================================
# ASSISTIFY COPILOT 2.0 — Unified AI Command Center
# ==================================================================
COPILOT_TOOLS = ["create_client", "create_project", "generate_plan", "generate_proposal", "generate_contract", "generate_invoice"]

COPILOT_SYSTEM = (
    "You are Assistify Copilot, the AI command center for a business operating system. "
    "You have read access to the user's real workspace data (provided as context) and can perform actions via tools. "
    "Analyze the user's message and respond with a SINGLE valid JSON object only (no markdown, no prose outside JSON) with this schema:\n"
    '{\n'
    '  "reply": "a concise, helpful natural-language reply. For questions, ANSWER using the provided workspace data.",\n'
    '  "action": null OR {\n'
    '     "tool": one of ["create_client","create_project","generate_plan","generate_proposal","generate_contract","generate_invoice"],\n'
    '     "params": { relevant params, e.g. name, client_name, project_name, status, description, contact, email, phone },\n'
    '     "preview": ["short bullet strings describing exactly what will be created, e.g. \'1 Client: Nike\'"]\n'
    '  }\n'
    '}\n'
    "Rules: Use action ONLY when the user clearly wants to CREATE or GENERATE something. "
    "For questions, analysis, summaries, searches or listing (overdue invoices, behind-schedule projects, top clients, activity), set action to null and answer in reply using the DATA. "
    "For generate_* tools, identify the target project by name from the data and put project_name in params. "
    "Never invent data that isn't in the context. Be concise and professional."
)


async def _copilot_snapshot(org: str) -> str:
    base = {"organizationId": org}
    # Keep accurate totals via counts; send only a bounded, relevant slice of each list to the LLM.
    clients = await db.clients.find(base, {"_id": 0, "id": 1, "name": 1, "contact": 1, "email": 1, "value": 1}).sort("value", -1).to_list(20)
    total_clients = await db.clients.count_documents(base)
    projects = await db.projects.find(base, {"_id": 0, "id": 1, "name": 1, "status": 1, "due": 1, "progress": 1, "client_id": 1}).sort("updated_at", -1).to_list(25)
    total_projects = await db.projects.count_documents(base)
    cmap = {c["id"]: c["name"] for c in clients}
    for p in projects:
        p["client_name"] = cmap.get(p.get("client_id"))
    open_tasks = await db.tasks.count_documents({**base, "done": False})
    done_tasks = await db.tasks.count_documents({**base, "done": True})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    overdue_tasks = await db.tasks.find({**base, "done": False, "due": {"$lt": today, "$ne": None}},
                                        {"_id": 0, "title": 1, "due": 1, "project_id": 1}).sort("due", 1).to_list(10)
    # Prioritise unpaid/overdue invoices; they drive most Copilot questions.
    invoices = await db.ai_invoices.find(base, {"_id": 0, "invoice_number": 1, "status": 1, "total": 1, "content": 1}).sort("updated_at", -1).to_list(30)
    total_invoices = await db.ai_invoices.count_documents(base)
    inv_summary = [{"number": i.get("invoice_number"), "status": i.get("status"), "total": i.get("total"), "due": (i.get("content") or {}).get("due_date")} for i in invoices]
    activities = await db.activities.find(base, {"_id": 0, "message": 1, "created_at": 1}).sort("created_at", -1).to_list(8)
    snapshot = {
        "today": today,
        "counts": {
            "clients": total_clients, "projects": total_projects, "open_tasks": open_tasks, "completed_tasks": done_tasks,
            "proposals": await db.ai_proposals.count_documents(base), "contracts": await db.ai_contracts.count_documents(base),
            "invoices": total_invoices,
        },
        "note": "Lists below are a bounded slice (top clients by value, most-recent projects/invoices, soonest-overdue tasks). Use 'counts' for totals.",
        "clients": [{"name": c["name"], "contact": c.get("contact"), "value": c.get("value", 0)} for c in clients],
        "projects": [{"name": p["name"], "status": p.get("status"), "due": p.get("due"), "progress": p.get("progress", 0), "client": p.get("client_name")} for p in projects],
        "overdue_tasks": overdue_tasks,
        "invoices": inv_summary,
        "recent_activity": [{"message": a["message"], "when": a["created_at"][:10]} for a in activities],
    }
    return json.dumps(snapshot, default=str)


class CopilotMessage(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str


class CopilotExecute(BaseModel):
    session_id: str
    action_id: Optional[str] = None


COPILOT_ACTION_TTL_MIN = 30


async def _log_copilot_action(org: str, project_id, message: str):
    await db.activities.insert_one({
        "id": str(uuid.uuid4()), "project_id": project_id, "organizationId": org,
        "type": "copilot_action", "message": message, "created_at": now_iso(),
    })


async def _store_pending_action(session_id: str, org: str, tool: str, params: dict, preview: list) -> str:
    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.copilot_pending_actions.insert_one({
        "id": aid, "session_id": session_id, "organizationId": org,
        "tool": tool, "params": params or {}, "preview": preview or [],
        "consumed": False, "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=COPILOT_ACTION_TTL_MIN)).isoformat(),
    })
    return aid


@router.post("/copilot/message")
async def copilot_message(payload: CopilotMessage, org: str = Depends(current_org)):
    snapshot = await _copilot_snapshot(org)
    await db.copilot_messages.insert_one({"id": str(uuid.uuid4()), "session_id": payload.session_id,
                                          "organizationId": org, "role": "user", "content": payload.message, "created_at": now_iso()})
    prompt = f"WORKSPACE DATA (JSON):\n{snapshot}\n\nUSER MESSAGE:\n{payload.message}\n\nRespond with the JSON object."
    try:
        raw = await ai_service.complete(COPILOT_SYSTEM, prompt, session_id=f"copilot-{payload.session_id}")
        result = extract_json(raw)
    except json.JSONDecodeError:
        result = {"reply": "I had trouble understanding that. Could you rephrase?", "action": None}
    except Exception as e:
        logging.exception("copilot failed")
        from ai_service import public_ai_error
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Copilot is unavailable right now. Please try again."))

    reply = result.get("reply", "I'm not sure how to help with that.")
    raw_action = result.get("action")
    action = None
    if raw_action and raw_action.get("tool") in COPILOT_TOOLS:
        tool = raw_action["tool"]
        params = raw_action.get("params", {}) or {}
        preview = raw_action.get("preview", []) or []
        # Persist the pending action server-side; client can only reference it by token.
        aid = await _store_pending_action(payload.session_id, org, tool, params, preview)
        action = {"tool": tool, "params": params, "preview": preview,
                  "action_id": aid, "requires_confirmation": True}
    await db.copilot_messages.insert_one({"id": str(uuid.uuid4()), "session_id": payload.session_id,
                                          "organizationId": org, "role": "assistant", "content": reply,
                                          "action": action, "created_at": now_iso()})
    return {"reply": reply, "action": action, "session_id": payload.session_id}


async def _resolve_project(org: str, params: dict):
    pid = params.get("project_id")
    if pid:
        p = await db.projects.find_one({"id": pid, "organizationId": org}, {"_id": 0})
        if p:
            return p
    name = (params.get("project_name") or params.get("name") or "").strip().lower()
    if name:
        projs = await db.projects.find({"organizationId": org}, {"_id": 0}).to_list(200)
        for p in projs:
            if p["name"].strip().lower() == name:
                return p
        for p in projs:
            if name in p["name"].strip().lower():
                return p
    return None


@router.post("/copilot/execute")
async def copilot_execute(payload: CopilotExecute, org: str = Depends(current_org)):
    # Never trust a client-supplied action. Execute ONLY a previously-proposed,
    # server-stored pending action, scoped to this org + session, referenced by token.
    import server  # lazy import: generators/models live in the app module
    if not payload.action_id:
        raise HTTPException(status_code=400, detail="Missing action confirmation token.")
    pending = await db.copilot_pending_actions.find_one(
        {"id": payload.action_id, "session_id": payload.session_id, "organizationId": org})
    if not pending:
        raise HTTPException(status_code=404, detail="This action is no longer available. Please ask the Copilot again.")
    if pending.get("consumed"):
        raise HTTPException(status_code=409, detail="This action was already executed.")
    if pending.get("expires_at") and datetime.now(timezone.utc).isoformat() > pending["expires_at"]:
        raise HTTPException(status_code=410, detail="This action expired. Please ask the Copilot again.")
    # Atomically claim the action to prevent double-execution / race conditions.
    claim = await db.copilot_pending_actions.update_one(
        {"id": payload.action_id, "organizationId": org, "consumed": False},
        {"$set": {"consumed": True, "consumed_at": now_iso()}})
    if claim.modified_count != 1:
        raise HTTPException(status_code=409, detail="This action was already executed.")

    tool = pending["tool"]
    params = pending.get("params", {}) or {}
    if tool not in COPILOT_TOOLS:
        raise HTTPException(status_code=400, detail="Unknown action")

    if tool == "create_client":
        obj = server.Client(name=params.get("name") or "New Client", contact=params.get("contact", ""),
                            email=params.get("email", ""), phone=params.get("phone", ""),
                            value=float(params.get("value", 0) or 0), status=params.get("status", "Active"))
        doc = obj.model_dump(); doc["organizationId"] = org
        await db.clients.insert_one(doc)
        await _log_copilot_action(org, None, f'Copilot created client "{obj.name}"')
        result = {"reply": f'Created client "{obj.name}".', "navigate": "/clients", "created": {"type": "client", "id": obj.id, "name": obj.name}}

    elif tool == "create_project":
        client_id = None
        cname = (params.get("client_name") or "").strip().lower()
        if cname:
            clients = await db.clients.find({"organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(200)
            match = next((c for c in clients if c["name"].strip().lower() == cname), None) or next((c for c in clients if cname in c["name"].strip().lower()), None)
            client_id = match["id"] if match else None
        obj = server.Project(name=params.get("name") or params.get("project_name") or "New Project", client_id=client_id,
                            status=params.get("status", "In Progress"), description=params.get("description", ""))
        doc = obj.model_dump(); doc["organizationId"] = org
        await db.projects.insert_one(doc)
        await log_activity(obj.id, "project_created", f'Project "{obj.name}" was created')
        await _log_copilot_action(org, obj.id, f'Copilot created project "{obj.name}"')
        result = {"reply": f'Created project "{obj.name}".', "navigate": f"/projects/{obj.id}", "created": {"type": "project", "id": obj.id, "name": obj.name}}

    else:
        project = await _resolve_project(org, params)
        if not project:
            raise HTTPException(status_code=404, detail="I couldn't find that project. Please specify an existing project.")
        pid = project["id"]
        try:
            if tool == "generate_plan":
                gen = await server.generate_plan(pid, org)
                await server.save_plan(pid, server.PlanSave(sections=gen["sections"]), org)
                tab, msg = "plan", "AI project plan"
            elif tool == "generate_proposal":
                gen = await server.generate_proposal(pid, org)
                await server.save_proposal(pid, server.ProposalContent(title=gen["title"], content=gen["content"]), org)
                tab, msg = "proposal", "proposal"
            elif tool == "generate_contract":
                gen = await server.generate_contract(pid, org)
                await server._save_contract(pid, server.ContractContent(title=gen["title"], content=gen["content"]), org, "contract_saved", "Contract v{version} was saved")
                tab, msg = "contract", "service agreement"
            elif tool == "generate_invoice":
                gen = await server.generate_invoice(pid, org)
                await server._save_invoice(pid, server.InvoiceSave(invoice_number=gen["invoice_number"], title=gen["title"], content=gen["content"], line_items=gen["line_items"]), org, "invoice_saved", "Invoice {number} v{version} was saved")
                tab, msg = "invoice", "invoice"
        except HTTPException:
            raise
        except Exception as e:
            logging.exception("copilot generate failed")
            from ai_service import public_ai_error
            raise HTTPException(status_code=502, detail=public_ai_error(e, "Generation failed. Please try again."))
        await _log_copilot_action(org, pid, f'Copilot generated a {msg} for "{project["name"]}"')
        result = {"reply": f'Generated a {msg} for "{project["name"]}".', "navigate": f"/projects/{pid}?tab={tab}", "created": {"type": tool, "project": project["name"]}}
        if tab == "plan":
            result["navigate"] = f"/projects/{pid}?tab=proposal"

    await db.copilot_messages.insert_one({"id": str(uuid.uuid4()), "session_id": payload.session_id,
                                          "organizationId": org, "role": "assistant", "content": result["reply"], "created_at": now_iso()})
    return result


@router.get("/copilot/history/{session_id}")
async def copilot_history(session_id: str, org: str = Depends(current_org)):
    return await db.copilot_messages.find({"session_id": session_id, "organizationId": org}, {"_id": 0}).sort("created_at", 1).to_list(500)


@router.get("/copilot/suggestions")
async def copilot_suggestions(org: str = Depends(current_org)):
    base = {"organizationId": org}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    out = []
    overdue_inv = await db.ai_invoices.count_documents({**base, "status": {"$in": ["Sent", "Overdue"]}})
    if overdue_inv:
        out.append({"icon": "receipt", "text": f"{overdue_inv} invoice(s) awaiting payment", "prompt": "Which invoices are unpaid or overdue?"})
    tasks = await db.tasks.find({**base, "done": False}, {"_id": 0, "due": 1}).to_list(500)
    overdue_tasks = sum(1 for t in tasks if t.get("due") and str(t["due"]) < today)
    due_tomorrow = sum(1 for t in tasks if str(t.get("due")) == tomorrow)
    if overdue_tasks:
        out.append({"icon": "alert", "text": f"{overdue_tasks} overdue task(s)", "prompt": "Show me my overdue tasks"})
    if due_tomorrow:
        out.append({"icon": "clock", "text": f"{due_tomorrow} task(s) due tomorrow", "prompt": "What tasks are due tomorrow?"})
    behind = await db.projects.count_documents({**base, "status": {"$in": ["In Progress", "Review"]}})
    if behind:
        out.append({"icon": "folder", "text": "Review project progress", "prompt": "Which projects are behind schedule?"})
    out.append({"icon": "sparkles", "text": "Summarize today's activity", "prompt": "Summarize today's activity"})
    out.append({"icon": "users", "text": "My highest-value clients", "prompt": "Show my highest value clients"})
    return out[:6]
