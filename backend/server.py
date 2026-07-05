from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

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
