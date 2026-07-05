from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from ai_service import AIService, extract_json
from proposal_config import PROPOSAL_SECTIONS, PROPOSAL_STATUSES, PROPOSAL_SYSTEM, build_proposal_prompt
from contract_config import CONTRACT_SECTIONS, CONTRACT_STATUSES, CONTRACT_SYSTEM, build_contract_prompt
from invoice_config import INVOICE_STATUSES, INVOICE_FIELDS, INVOICE_SYSTEM, build_invoice_prompt
from proposal_export import build_pdf, build_docx
from invoice_export import build_invoice_pdf, build_invoice_docx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
ai_service = AIService(api_key=EMERGENT_LLM_KEY)

app = FastAPI()
api_router = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def log_activity(project_id: Optional[str], atype: str, message: str):
    if not project_id:
        return
    await db.activities.insert_one({
        "id": str(uuid.uuid4()), "project_id": project_id,
        "type": atype, "message": message, "created_at": now_iso(),
    })


# ------------------- AI Agents (personas) -------------------
AGENTS = {
    "copilot": {
        "id": "copilot", "name": "Assistify Copilot", "role": "General Business Assistant",
        "description": "Your all-round operator for planning, drafting and quick answers.",
        "avatar": "https://images.unsplash.com/photo-1674027444485-cec3da58eef4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwxfHxmdXR1cmlzdGljJTIwYXJ0aWZpY2lhbCUyMGludGVsbGlnZW5jZSUyMGdsb3dpbmclMjBjb3JlfGVufDB8fHx8MTc4MzIzOTg1OHww&ixlib=rb-4.1.0&q=85",
        "accent": "violet",
        "system_message": "You are Assistify Copilot, a sharp, concise business operating assistant for entrepreneurs. Help with planning, tasks, clients and general operations. Keep answers practical and action-oriented.",
    },
    "sales": {
        "id": "sales", "name": "Sales Strategist", "role": "Revenue & Deals",
        "description": "Crafts outreach, pricing strategy and closes deals.",
        "avatar": "https://images.unsplash.com/photo-1689443111130-6e9c7dfd8f9e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "emerald",
        "system_message": "You are the Sales Strategist for Assistify OS. You specialize in outbound outreach, cold email copy, pricing strategy, objection handling and deal closing. Be persuasive, concise and results-driven.",
    },
    "writer": {
        "id": "writer", "name": "Proposal Writer", "role": "Docs & Proposals",
        "description": "Writes crisp proposals, SOWs and client documents.",
        "avatar": "https://images.unsplash.com/photo-1689443111384-1cf214df988a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "blue",
        "system_message": "You are the Proposal Writer for Assistify OS. You write polished, well-structured business proposals, scopes of work and client-facing documents. Use clear headings and professional tone.",
    },
    "analyst": {
        "id": "analyst", "name": "Data Analyst", "role": "Insights & Metrics",
        "description": "Turns numbers into clear business insights.",
        "avatar": "https://images.unsplash.com/photo-1689443111070-2c1a1110fe82?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwyfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "amber",
        "system_message": "You are the Data Analyst for Assistify OS. You interpret business metrics, revenue trends and KPIs, and give clear, quantified insights and recommendations.",
    },
}


# ------------------- Chat Models -------------------
class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = "copilot"
    message: str


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent_id: str
    role: str
    content: str
    timestamp: str = Field(default_factory=now_iso)


# ------------------- CRUD Models -------------------
class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    contact: str = ""
    email: str = ""
    value: float = 0
    status: str = "Active"


class Client(ClientCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    client_id: Optional[str] = None
    status: str = "In Progress"
    progress: int = 0
    due: str = ""
    members: int = 1
    description: str = ""
    notes: str = ""


class Project(ProjectCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    project_id: Optional[str] = None
    priority: str = "Medium"
    done: bool = False
    due: str = ""


class Task(TaskCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


class DocumentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = "Doc"
    size: str = "—"
    project_id: Optional[str] = None
    url: str = ""


class Document(DocumentCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


class ProposalCreate(BaseModel):
    title: str = Field(..., min_length=1)
    amount: str = ""
    status: str = "Draft"
    content: str = ""
    project_id: Optional[str] = None


class Proposal(ProposalCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


# ------------------- Base Routes -------------------
@api_router.get("/")
async def root():
    return {"message": "Assistify OS API"}


@api_router.get("/agents")
async def list_agents():
    return [{k: v for k, v in a.items() if k != "system_message"} for a in AGENTS.values()]


@api_router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    return await db.chat_messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(1000)


@api_router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    agent = AGENTS.get(req.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    user_msg = ChatMessage(session_id=req.session_id, agent_id=req.agent_id, role="user", content=req.message)
    await db.chat_messages.insert_one(user_msg.model_dump())

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY, session_id=req.session_id, system_message=agent["system_message"],
    ).with_model("openai", "gpt-5.4")

    async def event_generator():
        full = ""
        try:
            async for event in chat.stream_message(UserMessage(text=req.message)):
                if isinstance(event, TextDelta):
                    full += event.content
                    yield f"data: {json.dumps({'delta': event.content})}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as e:
            logging.exception("stream error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if full:
                bot_msg = ChatMessage(session_id=req.session_id, agent_id=req.agent_id, role="assistant", content=full)
                await db.chat_messages.insert_one(bot_msg.model_dump())
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------- Clients CRUD -------------------
async def client_with_counts(c: dict):
    c["projects"] = await db.projects.count_documents({"client_id": c["id"]})
    return c


@api_router.get("/clients")
async def list_clients():
    clients = await db.clients.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for c in clients:
        await client_with_counts(c)
    return clients


@api_router.post("/clients", response_model=Client)
async def create_client(payload: ClientCreate):
    obj = Client(**payload.model_dump())
    await db.clients.insert_one(obj.model_dump())
    return obj


@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, payload: ClientCreate):
    res = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = {**res, **payload.model_dump()}
    await db.clients.update_one({"id": client_id}, {"$set": payload.model_dump()})
    return Client(**updated)


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str):
    res = await db.clients.delete_one({"id": client_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.projects.update_many({"client_id": client_id}, {"$set": {"client_id": None}})
    return {"ok": True}


# ------------------- Projects CRUD -------------------
async def enrich_project(p: dict):
    p["client_name"] = None
    if p.get("client_id"):
        c = await db.clients.find_one({"id": p["client_id"]}, {"_id": 0, "name": 1})
        p["client_name"] = c["name"] if c else None
    return p


@api_router.get("/projects")
async def list_projects():
    projects = await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for p in projects:
        await enrich_project(p)
    return projects


@api_router.get("/projects/{project_id}")
async def get_project(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await enrich_project(p)
    return p


@api_router.post("/projects", response_model=Project)
async def create_project(payload: ProjectCreate):
    obj = Project(**payload.model_dump())
    await db.projects.insert_one(obj.model_dump())
    await log_activity(obj.id, "project_created", f'Project "{obj.name}" was created')
    return obj


@api_router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, payload: ProjectCreate):
    res = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Project not found")
    updated = {**res, **payload.model_dump()}
    await db.projects.update_one({"id": project_id}, {"$set": payload.model_dump()})
    return Project(**updated)


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    res = await db.projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.tasks.update_many({"project_id": project_id}, {"$set": {"project_id": None}})
    await db.documents.delete_many({"project_id": project_id})
    await db.proposals.delete_many({"project_id": project_id})
    await db.plans.delete_many({"project_id": project_id})
    await db.ai_proposals.delete_many({"project_id": project_id})
    await db.ai_contracts.delete_many({"project_id": project_id})
    await db.ai_invoices.delete_many({"project_id": project_id})
    await db.activities.delete_many({"project_id": project_id})
    return {"ok": True}


# ------------------- Tasks CRUD -------------------
async def enrich_task(t: dict):
    t["project_name"] = None
    t["client_name"] = None
    if t.get("project_id"):
        p = await db.projects.find_one({"id": t["project_id"]}, {"_id": 0, "name": 1, "client_id": 1})
        if p:
            t["project_name"] = p["name"]
            if p.get("client_id"):
                c = await db.clients.find_one({"id": p["client_id"]}, {"_id": 0, "name": 1})
                t["client_name"] = c["name"] if c else None
    return t


@api_router.get("/tasks")
async def list_tasks(project_id: Optional[str] = None):
    q = {"project_id": project_id} if project_id else {}
    tasks = await db.tasks.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for t in tasks:
        await enrich_task(t)
    return tasks


@api_router.post("/tasks", response_model=Task)
async def create_task(payload: TaskCreate):
    obj = Task(**payload.model_dump())
    await db.tasks.insert_one(obj.model_dump())
    await log_activity(obj.project_id, "task_created", f'Task "{obj.title}" was created')
    if obj.done:
        await log_activity(obj.project_id, "task_completed", f'Task "{obj.title}" was completed')
    return obj


@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, payload: TaskCreate):
    res = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = {**res, **payload.model_dump()}
    await db.tasks.update_one({"id": task_id}, {"$set": payload.model_dump()})
    if payload.done and not res.get("done"):
        await log_activity(payload.project_id, "task_completed", f'Task "{payload.title}" was completed')
    return Task(**updated)


@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    res = await db.tasks.delete_one({"id": task_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}


# ------------------- Documents CRUD -------------------
@api_router.get("/documents")
async def list_documents(project_id: Optional[str] = None):
    q = {"project_id": project_id} if project_id else {}
    return await db.documents.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/documents", response_model=Document)
async def create_document(payload: DocumentCreate):
    obj = Document(**payload.model_dump())
    await db.documents.insert_one(obj.model_dump())
    await log_activity(obj.project_id, "document_uploaded", f'Document "{obj.name}" was uploaded')
    return obj


@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    res = await db.documents.delete_one({"id": document_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


# ------------------- Proposals CRUD -------------------
@api_router.get("/proposals")
async def list_proposals(project_id: Optional[str] = None):
    q = {"project_id": project_id} if project_id else {}
    return await db.proposals.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/proposals", response_model=Proposal)
async def create_proposal(payload: ProposalCreate):
    obj = Proposal(**payload.model_dump())
    await db.proposals.insert_one(obj.model_dump())
    await log_activity(obj.project_id, "proposal_generated", f'Proposal "{obj.title}" was generated')
    return obj


@api_router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str):
    res = await db.proposals.delete_one({"id": proposal_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"ok": True}


# ------------------- Activities -------------------
@api_router.get("/activities")
async def list_activities(project_id: str):
    return await db.activities.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ------------------- AI Project Planner -------------------
PLAN_SECTIONS = [
    "executive_summary", "business_goal", "technical_requirements", "recommended_plan",
    "milestones", "suggested_tasks", "estimated_timeline", "risks", "next_actions",
]

PLANNER_SYSTEM = (
    "You are an elite AI project planner for Assistify OS. Given full project context, you produce "
    "a rigorous, actionable project plan. You ALWAYS respond with a single valid JSON object and nothing else "
    "(no markdown fences, no prose outside JSON)."
)


class PlanSave(BaseModel):
    sections: dict


class Plan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    version: int
    sections: dict
    created_at: str = Field(default_factory=now_iso)


async def build_project_context(project: dict) -> str:
    pid = project["id"]
    tasks = await db.tasks.find({"project_id": pid}, {"_id": 0}).to_list(1000)
    docs = await db.documents.find({"project_id": pid}, {"_id": 0}).to_list(1000)
    acts = await db.activities.find({"project_id": pid}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    task_lines = "\n".join([f"- [{'x' if t.get('done') else ' '}] {t['title']} (priority: {t.get('priority','Medium')}, due: {t.get('due') or 'none'})" for t in tasks]) or "None"
    doc_lines = "\n".join([f"- {d['name']} ({d.get('type','Doc')})" for d in docs]) or "None"
    act_lines = "\n".join([f"- {a['message']} ({a['created_at'][:10]})" for a in acts]) or "None"
    return (
        f"PROJECT NAME: {project.get('name')}\n"
        f"CLIENT: {project.get('client_name') or 'No client'}\n"
        f"CURRENT STATUS: {project.get('status')}\n"
        f"PROGRESS: {project.get('progress', 0)}%\n"
        f"DEADLINE: {project.get('due') or 'Not set'}\n"
        f"TEAM SIZE: {project.get('members', 1)}\n"
        f"DESCRIPTION: {project.get('description') or 'No description provided'}\n"
        f"NOTES: {project.get('notes') or 'No notes'}\n\n"
        f"EXISTING TASKS:\n{task_lines}\n\n"
        f"DOCUMENTS:\n{doc_lines}\n\n"
        f"ACTIVITY TIMELINE:\n{act_lines}\n"
    )


def parse_plan_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    data = json.loads(t)
    return {k: data.get(k, "" if k in ("executive_summary", "business_goal", "estimated_timeline") else []) for k in PLAN_SECTIONS}


@api_router.post("/projects/{project_id}/plan/generate")
async def generate_plan(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await enrich_project(p)
    context = await build_project_context(p)

    prompt = (
        f"Analyze the following project and generate a complete project plan.\n\n{context}\n\n"
        "Return ONLY a JSON object with EXACTLY these keys:\n"
        '{\n'
        '  "executive_summary": "2-4 sentence string",\n'
        '  "business_goal": "1-3 sentence string",\n'
        '  "technical_requirements": ["array of requirement strings"],\n'
        '  "recommended_plan": ["array of phase strings, e.g. \'Phase 1: Discovery — ...\'"],\n'
        '  "milestones": ["array of milestone strings, each like \'Milestone name — target\'"],\n'
        '  "suggested_tasks": ["array of task strings, each prefixed with priority like \'High: task title\'"],\n'
        '  "estimated_timeline": "string summarizing overall timeline and per-phase durations",\n'
        '  "risks": ["array of risk/challenge strings"],\n'
        '  "next_actions": ["array of concrete next action strings"]\n'
        '}\n'
        "Be specific and tailored to the actual project context above. Output JSON only."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY, session_id=f"planner-{project_id}-{uuid.uuid4()}",
        system_message=PLANNER_SYSTEM,
    ).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp if isinstance(resp, str) else str(resp)
        sections = parse_plan_json(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable plan. Please regenerate.")
    except Exception as e:
        logging.exception("plan generation failed")
        raise HTTPException(status_code=502, detail=f"Plan generation failed: {e}")
    return {"sections": sections}


@api_router.get("/projects/{project_id}/plans")
async def list_plans(project_id: str):
    return await db.plans.find({"project_id": project_id}, {"_id": 0}).sort("version", -1).to_list(1000)


@api_router.post("/projects/{project_id}/plans", response_model=Plan)
async def save_plan(project_id: str, payload: PlanSave):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    version = await db.plans.count_documents({"project_id": project_id}) + 1
    obj = Plan(project_id=project_id, version=version, sections=payload.sections)
    await db.plans.insert_one(obj.model_dump())
    await log_activity(project_id, "plan_generated", f"AI project plan v{version} was saved")
    return obj


# ------------------- AI Proposal Writer -------------------
class ProposalContent(BaseModel):
    title: str = "Untitled Proposal"
    status: str = "Draft"
    content: dict = Field(default_factory=dict)


async def _get_ai_proposal(project_id: str):
    return await db.ai_proposals.find_one({"project_id": project_id}, {"_id": 0})


@api_router.post("/projects/{project_id}/proposal/generate")
async def generate_proposal(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await enrich_project(p)
    context = await build_project_context(p)

    # Fold in the latest AI plan if one exists (richer context, no manual copy/paste)
    latest_plan = await db.plans.find_one({"project_id": project_id}, {"_id": 0}, sort=[("version", -1)])
    if latest_plan:
        secs = latest_plan.get("sections", {})
        context += "\n\nLATEST AI PROJECT PLAN:\n" + json.dumps(secs)[:4000]

    prompt = build_proposal_prompt(context)
    try:
        content = await ai_service.complete_json(PROPOSAL_SYSTEM, prompt, PROPOSAL_SECTIONS, session_id=f"proposal-{project_id}-{uuid.uuid4()}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable proposal. Please regenerate.")
    except Exception as e:
        logging.exception("proposal generation failed")
        raise HTTPException(status_code=502, detail=f"Proposal generation failed: {e}")

    await log_activity(project_id, "proposal_generated", f'Proposal for "{p.get("name")}" was generated')
    default_title = f"{p.get('name')} — Proposal"
    return {"title": default_title, "content": content}


@api_router.get("/projects/{project_id}/proposal")
async def get_proposal(project_id: str):
    return await _get_ai_proposal(project_id)


@api_router.get("/projects/{project_id}/proposal/versions")
async def proposal_versions(project_id: str):
    doc = await _get_ai_proposal(project_id)
    return doc.get("history", []) if doc else []


@api_router.post("/projects/{project_id}/proposal")
async def save_proposal(project_id: str, payload: ProposalContent):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.status not in PROPOSAL_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    existing = await _get_ai_proposal(project_id)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    version_entry = {
        "version": version, "title": payload.title, "status": payload.status,
        "content": payload.content, "created_at": now,
    }
    if existing:
        history = existing.get("history", []) + [version_entry]
        await db.ai_proposals.update_one({"project_id": project_id}, {"$set": {
            "title": payload.title, "status": payload.status, "content": payload.content,
            "version": version, "history": history, "updated_at": now,
        }})
    else:
        doc = {
            "id": str(uuid.uuid4()), "title": payload.title, "project_id": project_id,
            "client_id": p.get("client_id"), "status": payload.status, "content": payload.content,
            "version": version, "history": [version_entry], "created_at": now, "updated_at": now,
        }
        await db.ai_proposals.insert_one(doc)
    await log_activity(project_id, "proposal_saved", f"Proposal v{version} was saved")
    return await _get_ai_proposal(project_id)


@api_router.post("/projects/{project_id}/proposal/restore/{version}")
async def restore_proposal(project_id: str, version: int):
    existing = await _get_ai_proposal(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await save_proposal(project_id, ProposalContent(title=match["title"], status=match["status"], content=match["content"]))


def _export_or_404(project_id, proposal):
    if not proposal:
        raise HTTPException(status_code=404, detail="Save the proposal before exporting")


def _safe_filename(name: str) -> str:
    ascii_name = "".join(c if (c.isalnum() or c in " -_") else "_" for c in (name or "proposal"))
    return ascii_name.strip().replace(" ", "_")[:60] or "proposal"


@api_router.get("/projects/{project_id}/proposal/export/pdf")
async def export_proposal_pdf(project_id: str):
    proposal = await _get_ai_proposal(project_id)
    _export_or_404(project_id, proposal)
    data = build_pdf(proposal)
    await log_activity(project_id, "proposal_exported", "Proposal exported as PDF")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/proposal/export/docx")
async def export_proposal_docx(project_id: str):
    proposal = await _get_ai_proposal(project_id)
    _export_or_404(project_id, proposal)
    data = build_docx(proposal)
    await log_activity(project_id, "proposal_exported", "Proposal exported as DOCX")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


@api_router.get("/proposal/sections")
async def proposal_sections():
    return {"sections": PROPOSAL_SECTIONS, "statuses": PROPOSAL_STATUSES}


# ------------------- AI Contract Generator -------------------
class ContractContent(BaseModel):
    title: str = "Untitled Contract"
    status: str = "Draft"
    content: dict = Field(default_factory=dict)


async def _get_ai_contract(project_id: str):
    return await db.ai_contracts.find_one({"project_id": project_id}, {"_id": 0})


async def _build_contract_context(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await enrich_project(p)
    context = await build_project_context(p)

    proposal_id = None
    client = None
    if p.get("client_id"):
        client = await db.clients.find_one({"id": p["client_id"]}, {"_id": 0})
    if client:
        context += (
            f"\n\nCLIENT DETAILS:\nCompany: {client.get('name')}\n"
            f"Primary contact: {client.get('contact') or 'N/A'}\n"
            f"Email: {client.get('email') or 'N/A'}\nAddress: [CLIENT ADDRESS]\n"
        )

    proposal = await _get_ai_proposal(project_id)
    if proposal:
        proposal_id = proposal.get("id")
        c = proposal.get("content", {})
        context += (
            "\n\nAPPROVED PROPOSAL (source of truth for deliverables/pricing):\n"
            f"Deliverables: {json.dumps(c.get('deliverables', []))}\n"
            f"Timeline: {json.dumps(c.get('timeline', ''))}\n"
            f"Pricing: {json.dumps(c.get('pricing_placeholder', ''))}\n"
            f"Payment schedule: {json.dumps(c.get('payment_schedule', []))}\n"
            f"Scope: {json.dumps(c.get('project_scope', []))}\n"
        )

    latest_plan = await db.plans.find_one({"project_id": project_id}, {"_id": 0}, sort=[("version", -1)])
    if latest_plan:
        context += "\n\nLATEST AI PROJECT PLAN:\n" + json.dumps(latest_plan.get("sections", {}))[:3000]

    return p, context, proposal_id


@api_router.post("/projects/{project_id}/contract/generate")
async def generate_contract(project_id: str):
    p, context, proposal_id = await _build_contract_context(project_id)
    prompt = build_contract_prompt(context)
    try:
        content = await ai_service.complete_json(CONTRACT_SYSTEM, prompt, CONTRACT_SECTIONS, session_id=f"contract-{project_id}-{uuid.uuid4()}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable contract. Please regenerate.")
    except Exception as e:
        logging.exception("contract generation failed")
        raise HTTPException(status_code=502, detail=f"Contract generation failed: {e}")

    await log_activity(project_id, "contract_generated", f'Service agreement for "{p.get("name")}" was generated')
    return {"title": f"{p.get('name')} — Service Agreement", "content": content, "proposal_id": proposal_id}


@api_router.get("/projects/{project_id}/contract")
async def get_contract(project_id: str):
    return await _get_ai_contract(project_id)


@api_router.get("/projects/{project_id}/contract/versions")
async def contract_versions(project_id: str):
    doc = await _get_ai_contract(project_id)
    return doc.get("history", []) if doc else []


async def _save_contract(project_id: str, payload: ContractContent, activity_type: str, activity_msg_fmt: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.status not in CONTRACT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    existing = await _get_ai_contract(project_id)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    entry = {"version": version, "title": payload.title, "status": payload.status, "content": payload.content, "created_at": now}
    if existing:
        history = existing.get("history", []) + [entry]
        await db.ai_contracts.update_one({"project_id": project_id}, {"$set": {
            "title": payload.title, "status": payload.status, "content": payload.content,
            "version": version, "history": history, "updated_at": now,
        }})
    else:
        proposal = await _get_ai_proposal(project_id)
        doc = {
            "id": str(uuid.uuid4()), "title": payload.title, "project_id": project_id,
            "client_id": p.get("client_id"), "proposal_id": proposal.get("id") if proposal else None,
            "status": payload.status, "content": payload.content, "version": version,
            "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_contracts.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg_fmt.format(version=version))
    return await _get_ai_contract(project_id)


@api_router.post("/projects/{project_id}/contract")
async def save_contract(project_id: str, payload: ContractContent):
    return await _save_contract(project_id, payload, "contract_saved", "Contract v{version} was saved")


@api_router.post("/projects/{project_id}/contract/restore/{version}")
async def restore_contract(project_id: str, version: int):
    existing = await _get_ai_contract(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await _save_contract(
        project_id, ContractContent(title=match["title"], status=match["status"], content=match["content"]),
        "contract_restored", f"Contract restored from v{version} as v{{version}}",
    )


@api_router.get("/projects/{project_id}/contract/export/pdf")
async def export_contract_pdf(project_id: str):
    contract = await _get_ai_contract(project_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Save the contract before exporting")
    data = build_pdf(contract, CONTRACT_SECTIONS, "Service Agreement")
    await log_activity(project_id, "contract_exported", "Contract exported as PDF")
    fname = _safe_filename(contract.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/contract/export/docx")
async def export_contract_docx(project_id: str):
    contract = await _get_ai_contract(project_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Save the contract before exporting")
    data = build_docx(contract, CONTRACT_SECTIONS, "Service Agreement")
    await log_activity(project_id, "contract_exported", "Contract exported as DOCX")
    fname = _safe_filename(contract.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


@api_router.get("/contract/sections")
async def contract_sections():
    return {"sections": CONTRACT_SECTIONS, "statuses": CONTRACT_STATUSES}


# ------------------- AI Invoice Generator -------------------
from datetime import timedelta


class InvoiceSave(BaseModel):
    invoice_number: str = ""
    title: str = "Untitled Invoice"
    status: str = "Draft"
    content: dict = Field(default_factory=dict)
    line_items: list = Field(default_factory=list)


async def _get_ai_invoice(project_id: str):
    return await db.ai_invoices.find_one({"project_id": project_id}, {"_id": 0})


def _compute_invoice(line_items: list, vat_rate: float):
    items = []
    subtotal = 0.0
    for li in (line_items or []):
        qty = float(li.get("quantity", 0) or 0)
        price = float(li.get("unit_price", 0) or 0)
        amount = round(qty * price, 2)
        subtotal += amount
        items.append({"description": li.get("description", ""), "quantity": qty, "unit_price": price, "amount": amount})
    subtotal = round(subtotal, 2)
    vat_amount = round(subtotal * float(vat_rate or 0) / 100, 2)
    total = round(subtotal + vat_amount, 2)
    return items, subtotal, vat_amount, total


async def _next_invoice_number():
    count = await db.ai_invoices.count_documents({})
    return f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{count + 1:04d}"


@api_router.post("/projects/{project_id}/invoice/generate")
async def generate_invoice(project_id: str):
    p, context, proposal_id = await _build_contract_context(project_id)
    contract = await _get_ai_contract(project_id)
    if contract:
        context += "\n\nSIGNED/DRAFT CONTRACT PAYMENT TERMS:\n" + json.dumps(contract.get("content", {}).get("payment_terms", []))

    prompt = build_invoice_prompt(context)
    try:
        raw = await ai_service.complete(INVOICE_SYSTEM, prompt, session_id=f"invoice-{project_id}-{uuid.uuid4()}")
        data = extract_json(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable invoice. Please regenerate.")
    except Exception as e:
        logging.exception("invoice generation failed")
        raise HTTPException(status_code=502, detail=f"Invoice generation failed: {e}")

    vat_rate = float(data.get("vat_rate", 0) or 0)
    items, subtotal, vat_amount, total = _compute_invoice(data.get("line_items", []), vat_rate)

    client = await db.clients.find_one({"id": p["client_id"]}, {"_id": 0}) if p.get("client_id") else None
    issue = datetime.now(timezone.utc)
    due = issue + timedelta(days=14)
    content = {
        "client_name": (client or {}).get("contact") or (client or {}).get("name") or "",
        "company": (client or {}).get("name") or "",
        "billing_address": data.get("billing_address", "[CLIENT ADDRESS]"),
        "project_name": p.get("name", ""),
        "description": data.get("description", ""),
        "payment_terms": data.get("payment_terms", "Net 14"),
        "notes": data.get("notes", ""),
        "bank_details": data.get("bank_details", "[BANK DETAILS]"),
        "issue_date": issue.strftime("%Y-%m-%d"),
        "due_date": due.strftime("%Y-%m-%d"),
        "vat_rate": vat_rate,
    }
    await log_activity(project_id, "invoice_generated", f'Invoice for "{p.get("name")}" was generated')
    return {
        "invoice_number": await _next_invoice_number(), "title": f"{p.get('name')} — Invoice",
        "content": content, "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
        "proposal_id": proposal_id, "contract_id": contract.get("id") if contract else None,
    }


@api_router.get("/projects/{project_id}/invoice")
async def get_invoice(project_id: str):
    return await _get_ai_invoice(project_id)


@api_router.get("/projects/{project_id}/invoice/versions")
async def invoice_versions(project_id: str):
    doc = await _get_ai_invoice(project_id)
    return doc.get("history", []) if doc else []


async def _save_invoice(project_id: str, payload: InvoiceSave, activity_type: str, activity_msg: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.status not in INVOICE_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    vat_rate = float(payload.content.get("vat_rate", 0) or 0)
    items, subtotal, vat_amount, total = _compute_invoice(payload.line_items, vat_rate)
    content = {**payload.content, "vat_rate": vat_rate}

    existing = await _get_ai_invoice(project_id)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    inv_number = payload.invoice_number or (existing["invoice_number"] if existing else await _next_invoice_number())
    entry = {
        "version": version, "invoice_number": inv_number, "title": payload.title, "status": payload.status,
        "content": content, "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total, "created_at": now,
    }
    if existing:
        history = existing.get("history", []) + [entry]
        await db.ai_invoices.update_one({"project_id": project_id}, {"$set": {
            "invoice_number": inv_number, "title": payload.title, "status": payload.status, "content": content,
            "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
            "version": version, "history": history, "updated_at": now,
        }})
    else:
        proposal = await _get_ai_proposal(project_id)
        contract = await _get_ai_contract(project_id)
        doc = {
            "id": str(uuid.uuid4()), "invoice_number": inv_number, "title": payload.title, "project_id": project_id,
            "client_id": p.get("client_id"), "proposal_id": proposal.get("id") if proposal else None,
            "contract_id": contract.get("id") if contract else None, "status": payload.status, "content": content,
            "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
            "version": version, "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_invoices.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg.format(version=version, number=inv_number))
    return await _get_ai_invoice(project_id)


@api_router.post("/projects/{project_id}/invoice")
async def save_invoice(project_id: str, payload: InvoiceSave):
    return await _save_invoice(project_id, payload, "invoice_saved", "Invoice {number} v{version} was saved")


@api_router.post("/projects/{project_id}/invoice/restore/{version}")
async def restore_invoice(project_id: str, version: int):
    existing = await _get_ai_invoice(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    payload = InvoiceSave(invoice_number=match["invoice_number"], title=match["title"],
                          status=match["status"], content=match["content"], line_items=match["line_items"])
    return await _save_invoice(project_id, payload, "invoice_restored", "Invoice restored from v" + str(version) + " as v{version}")


@api_router.get("/projects/{project_id}/invoice/export/pdf")
async def export_invoice_pdf(project_id: str):
    invoice = await _get_ai_invoice(project_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Save the invoice before exporting")
    data = build_invoice_pdf(invoice)
    await log_activity(project_id, "invoice_exported", "Invoice exported as PDF")
    fname = _safe_filename(invoice.get("invoice_number") or invoice.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/invoice/export/docx")
async def export_invoice_docx(project_id: str):
    invoice = await _get_ai_invoice(project_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Save the invoice before exporting")
    data = build_invoice_docx(invoice)
    await log_activity(project_id, "invoice_exported", "Invoice exported as DOCX")
    fname = _safe_filename(invoice.get("invoice_number") or invoice.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


@api_router.get("/invoice/config")
async def invoice_config():
    return {"fields": INVOICE_FIELDS, "statuses": INVOICE_STATUSES}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
