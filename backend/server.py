from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import re
import json
import time
import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from ai_service import AIService, extract_json
from proposal_config import PROPOSAL_SECTIONS, PROPOSAL_STATUSES, PROPOSAL_SYSTEM, build_proposal_prompt
from contract_config import CONTRACT_SECTIONS, CONTRACT_STATUSES, CONTRACT_SYSTEM, build_contract_prompt
from invoice_config import INVOICE_STATUSES, INVOICE_FIELDS, INVOICE_SYSTEM, build_invoice_prompt
from proposal_export import build_pdf, build_docx
from invoice_export import build_invoice_pdf, build_invoice_docx
import auth as A
import storage as S

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
ai_service = AIService(api_key=EMERGENT_LLM_KEY)

app = FastAPI()
api_router = APIRouter(prefix="/api")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/api/auth"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def log_activity(project_id: Optional[str], atype: str, message: str):
    if not project_id:
        return
    proj = await db.projects.find_one({"id": project_id}, {"_id": 0, "organizationId": 1})
    await db.activities.insert_one({
        "id": str(uuid.uuid4()), "project_id": project_id,
        "organizationId": (proj or {}).get("organizationId"),
        "type": atype, "message": message, "created_at": now_iso(),
    })


# ==================================================================
# AUTHENTICATION
# ==================================================================
def public_user(u: dict) -> dict:
    return {
        "id": u["id"], "firstName": u.get("firstName", ""), "lastName": u.get("lastName", ""),
        "email": u["email"], "emailVerified": u.get("emailVerified", False),
        "avatar": u.get("avatar", ""), "role": u.get("role", "owner"),
        "organizationId": u.get("organizationId"), "timezone": u.get("timezone", "UTC"),
        "language": u.get("language", "en"), "createdAt": u.get("createdAt"),
        "updatedAt": u.get("updatedAt"), "lastLogin": u.get("lastLogin"),
        "onboardingCompleted": u.get("onboardingCompleted", True),
    }


async def current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = A.decode_token(token)
    except A.jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except A.jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def current_org(user: dict = Depends(current_user)) -> str:
    return user["organizationId"]


async def require_project(project_id: str, org: str) -> dict:
    p = await db.projects.find_one({"id": project_id, "organizationId": org}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


# --- simple in-memory rate limiter (per process) ---
_rl_store: dict = {}


def rate_limit(key: str, max_calls: int, window_s: int):
    now = time.time()
    calls = [t for t in _rl_store.get(key, []) if now - t < window_s]
    if len(calls) >= max_calls:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    calls.append(now)
    _rl_store[key] = calls


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- auth models ---
class RegisterRequest(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=60)
    lastName: str = Field(default="", max_length=60)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    company: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: bool = True


class ForgotRequest(BaseModel):
    email: str


class ResetRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    avatar: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    company: Optional[str] = None


class ChangePassword(BaseModel):
    currentPassword: str
    newPassword: str = Field(..., min_length=8, max_length=128)


def _set_refresh_cookie(response: Response, token: str, remember: bool):
    max_age = A.REFRESH_TOKEN_DAYS * 86400 if remember else 86400
    response.set_cookie(key=REFRESH_COOKIE, value=token, httponly=True, secure=True,
                        samesite="none", max_age=max_age, path=COOKIE_PATH)


def _set_access_cookie(response: Response, access: str):
    # Enables direct-link authenticated downloads (PDF/DOCX exports via window.open)
    response.set_cookie(key="access_token", value=access, httponly=True, secure=True,
                        samesite="none", max_age=A.ACCESS_TOKEN_MINUTES * 60, path="/api")


async def _create_session(user: dict, request: Request, remember: bool):
    jti = A.gen_id()
    now = now_iso()
    expires = datetime.now(timezone.utc) + timedelta(days=A.REFRESH_TOKEN_DAYS if remember else 1)
    await db.sessions.insert_one({
        "id": A.gen_id(), "userId": user["id"], "jti": jti,
        "userAgent": request.headers.get("user-agent", ""), "ip": _client_ip(request),
        "createdAt": now, "lastUsedAt": now, "expiresAt": expires.isoformat(),
        "revoked": False, "remember": remember,
    })
    access = A.create_access_token(user["id"], user["email"], user["organizationId"])
    refresh = A.create_refresh_token(user["id"], jti, remember)
    return access, refresh


def _dev_link(path: str, token: str) -> str:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return f"{base}{path}?token={token}"


@api_router.post("/auth/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    rate_limit(f"register:{_client_ip(request)}", 10, 3600)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    now = now_iso()
    org_id = A.gen_id()
    org_name = payload.company.strip() or f"{payload.firstName}'s Organization"
    user_id = A.gen_id()
    await db.organizations.insert_one({
        "id": org_id, "name": org_name, "ownerId": user_id, "createdAt": now, "updatedAt": now,
    })
    user = {
        "id": user_id, "firstName": payload.firstName.strip(), "lastName": payload.lastName.strip(),
        "email": email, "passwordHash": A.hash_password(payload.password), "emailVerified": False,
        "avatar": "", "role": "owner", "organizationId": org_id, "timezone": "UTC", "language": "en",
        "createdAt": now, "updatedAt": now, "lastLogin": now, "onboardingCompleted": False,
    }
    await db.users.insert_one(user)

    # Email verification (dev mode: log + return link)
    vtoken = A.gen_token()
    await db.email_verification_tokens.insert_one({
        "token": vtoken, "userId": user_id, "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=2), "created_at": now,
    })
    verify_link = _dev_link("/verify-email", vtoken)
    logger.info(f"[EMAIL:VERIFY] {email} -> {verify_link}")

    access, refresh = await _create_session(user, request, True)
    _set_refresh_cookie(response, refresh, True)
    _set_access_cookie(response, access)
    return {"user": public_user(user), "accessToken": access, "verificationLink": verify_link}


@api_router.post("/auth/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    email = payload.email.strip().lower()
    ip = _client_ip(request)
    identifier = f"{ip}:{email}"

    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < datetime.fromisoformat(locked_until):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in a few minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not A.verify_password(payload.password, user["passwordHash"]):
        count = (attempt.get("count", 0) if attempt else 0) + 1
        update = {"count": count, "last_attempt": now_iso()}
        if count >= 5:
            update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    await db.users.update_one({"id": user["id"]}, {"$set": {"lastLogin": now_iso()}})
    user["lastLogin"] = now_iso()

    access, refresh = await _create_session(user, request, payload.remember)
    _set_refresh_cookie(response, refresh, payload.remember)
    _set_access_cookie(response, access)
    return {"user": public_user(user), "accessToken": access}


@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = A.decode_token(token)
    except A.jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    session = await db.sessions.find_one({"jti": payload["jti"], "userId": payload["sub"], "revoked": False})
    if not session:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # rotate refresh token
    new_jti = A.gen_id()
    remember = session.get("remember", True)
    await db.sessions.update_one({"jti": payload["jti"]}, {"$set": {"jti": new_jti, "lastUsedAt": now_iso()}})
    access = A.create_access_token(user["id"], user["email"], user["organizationId"])
    new_refresh = A.create_refresh_token(user["id"], new_jti, remember)
    _set_refresh_cookie(response, new_refresh, remember)
    _set_access_cookie(response, access)
    return {"user": public_user(user), "accessToken": access}


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            payload = A.decode_token(token)
            await db.sessions.update_one({"jti": payload.get("jti")}, {"$set": {"revoked": True}})
        except Exception:
            pass
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
    response.delete_cookie("access_token", path="/api")
    return {"ok": True}


@api_router.get("/auth/me")
async def get_me(user: dict = Depends(current_user)):
    return public_user(user)


@api_router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotRequest, request: Request):
    rate_limit(f"forgot:{_client_ip(request)}", 5, 900)
    email = payload.email.strip().lower()
    user = await db.users.find_one({"email": email})
    generic = {"ok": True, "message": "If an account exists, a reset link has been sent."}
    if not user:
        return generic
    token = A.gen_token()
    await db.password_reset_tokens.insert_one({
        "token": token, "userId": user["id"], "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "created_at": now_iso(),
    })
    reset_link = _dev_link("/reset-password", token)
    logger.info(f"[EMAIL:RESET] {email} -> {reset_link}")
    return {**generic, "resetLink": reset_link}


@api_router.post("/auth/reset-password")
async def reset_password(payload: ResetRequest):
    rec = await db.password_reset_tokens.find_one({"token": payload.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or already-used reset link")
    expires = rec["expires_at"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="This reset link has expired")
    await db.users.update_one({"id": rec["userId"]}, {"$set": {
        "passwordHash": A.hash_password(payload.password), "updatedAt": now_iso()}})
    await db.password_reset_tokens.update_one({"token": payload.token}, {"$set": {"used": True}})
    await db.sessions.update_many({"userId": rec["userId"]}, {"$set": {"revoked": True}})
    return {"ok": True, "message": "Password updated. Please sign in."}


@api_router.post("/auth/verify-email")
async def verify_email(body: dict):
    token = (body or {}).get("token")
    if not token:
        raise HTTPException(status_code=422, detail="Missing token")
    rec = await db.email_verification_tokens.find_one({"token": token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link")
    expires = rec["expires_at"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="This verification link has expired")
    await db.users.update_one({"id": rec["userId"]}, {"$set": {"emailVerified": True, "updatedAt": now_iso()}})
    await db.email_verification_tokens.update_one({"token": token}, {"$set": {"used": True}})
    return {"ok": True, "message": "Email verified"}


@api_router.post("/auth/resend-verification")
async def resend_verification(user: dict = Depends(current_user)):
    if user.get("emailVerified"):
        return {"ok": True, "message": "Email already verified"}
    token = A.gen_token()
    await db.email_verification_tokens.insert_one({
        "token": token, "userId": user["id"], "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=2), "created_at": now_iso(),
    })
    link = _dev_link("/verify-email", token)
    logger.info(f"[EMAIL:VERIFY] {user['email']} -> {link}")
    return {"ok": True, "verificationLink": link}


@api_router.patch("/auth/profile")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(current_user)):
    updates = {}
    for f in ["firstName", "lastName", "avatar", "timezone", "language"]:
        v = getattr(payload, f)
        if v is not None:
            updates[f] = v
    if updates:
        updates["updatedAt"] = now_iso()
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    if payload.company is not None and payload.company.strip():
        await db.organizations.update_one({"id": user["organizationId"]},
                                          {"$set": {"name": payload.company.strip(), "updatedAt": now_iso()}})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return public_user(fresh)


@api_router.post("/auth/change-password")
async def change_password(payload: ChangePassword, user: dict = Depends(current_user)):
    if not A.verify_password(payload.currentPassword, user["passwordHash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "passwordHash": A.hash_password(payload.newPassword), "updatedAt": now_iso()}})
    return {"ok": True, "message": "Password changed"}


@api_router.get("/auth/organization")
async def get_organization(user: dict = Depends(current_user)):
    org = await db.organizations.find_one({"id": user["organizationId"]}, {"_id": 0})
    return org


ONBOARDING_STEPS = [
    ("client", "clients"), ("project", "projects"), ("plan", "plans"),
    ("proposal", "ai_proposals"), ("contract", "ai_contracts"), ("invoice", "ai_invoices"),
]


@api_router.get("/onboarding")
async def get_onboarding(user: dict = Depends(current_user)):
    org = user["organizationId"]
    checklist = {}
    for key, coll in ONBOARDING_STEPS:
        checklist[key] = (await db[coll].count_documents({"organizationId": org})) > 0
    done = sum(1 for v in checklist.values() if v)
    percent = round(done / len(ONBOARDING_STEPS) * 100)
    return {
        "completed": user.get("onboardingCompleted", True),
        "checklist": checklist, "done": done, "total": len(ONBOARDING_STEPS), "percent": percent,
    }


@api_router.post("/onboarding/complete")
async def complete_onboarding(user: dict = Depends(current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"onboardingCompleted": True, "updatedAt": now_iso()}})
    return {"ok": True}


@api_router.get("/auth/sessions")
async def list_sessions(user: dict = Depends(current_user)):
    sessions = await db.sessions.find({"userId": user["id"], "revoked": False}, {"_id": 0, "jti": 0}).sort("lastUsedAt", -1).to_list(50)
    return sessions


@api_router.delete("/auth/sessions/{session_id}")
async def revoke_session(session_id: str, user: dict = Depends(current_user)):
    await db.sessions.update_one({"id": session_id, "userId": user["id"]}, {"$set": {"revoked": True}})
    return {"ok": True}


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
    phone: str = ""
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
async def list_agents(user: dict = Depends(current_user)):
    return [{k: v for k, v in a.items() if k != "system_message"} for a in AGENTS.values()]


@api_router.get("/chat/history/{session_id}")
async def chat_history(session_id: str, org: str = Depends(current_org)):
    return await db.chat_messages.find({"session_id": session_id, "organizationId": org}, {"_id": 0}).sort("timestamp", 1).to_list(1000)


@api_router.post("/chat/stream")
async def chat_stream(req: ChatRequest, org: str = Depends(current_org)):
    agent = AGENTS.get(req.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    user_msg = ChatMessage(session_id=req.session_id, agent_id=req.agent_id, role="user", content=req.message)
    um = user_msg.model_dump()
    um["organizationId"] = org
    await db.chat_messages.insert_one(um)

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
                bm = bot_msg.model_dump()
                bm["organizationId"] = org
                await db.chat_messages.insert_one(bm)
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------- Clients CRUD -------------------
async def client_with_counts(c: dict, org: str):
    c["projects"] = await db.projects.count_documents({"client_id": c["id"], "organizationId": org})
    return c


@api_router.get("/clients")
async def list_clients(org: str = Depends(current_org)):
    clients = await db.clients.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for c in clients:
        await client_with_counts(c, org)
    return clients


@api_router.post("/clients", response_model=Client)
async def create_client(payload: ClientCreate, org: str = Depends(current_org)):
    obj = Client(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.clients.insert_one(doc)
    return obj


@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, payload: ClientCreate, org: str = Depends(current_org)):
    res = await db.clients.find_one({"id": client_id, "organizationId": org}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = {**res, **payload.model_dump()}
    await db.clients.update_one({"id": client_id, "organizationId": org}, {"$set": payload.model_dump()})
    return Client(**{k: v for k, v in updated.items() if k in Client.model_fields})


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, org: str = Depends(current_org)):
    res = await db.clients.delete_one({"id": client_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.projects.update_many({"client_id": client_id, "organizationId": org}, {"$set": {"client_id": None}})
    return {"ok": True}


# ------------------- Projects CRUD -------------------
async def enrich_project(p: dict, org: str):
    p["client_name"] = None
    if p.get("client_id"):
        c = await db.clients.find_one({"id": p["client_id"], "organizationId": org}, {"_id": 0, "name": 1})
        p["client_name"] = c["name"] if c else None
    return p


@api_router.get("/projects")
async def list_projects(org: str = Depends(current_org)):
    projects = await db.projects.find({"organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for p in projects:
        await enrich_project(p, org)
    return projects


@api_router.get("/projects/{project_id}")
async def get_project(project_id: str, org: str = Depends(current_org)):
    p = await require_project(project_id, org)
    await enrich_project(p, org)
    return p


@api_router.post("/projects", response_model=Project)
async def create_project(payload: ProjectCreate, org: str = Depends(current_org)):
    obj = Project(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.projects.insert_one(doc)
    await log_activity(obj.id, "project_created", f'Project "{obj.name}" was created')
    return obj


@api_router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, payload: ProjectCreate, org: str = Depends(current_org)):
    res = await db.projects.find_one({"id": project_id, "organizationId": org}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Project not found")
    updated = {**res, **payload.model_dump()}
    await db.projects.update_one({"id": project_id, "organizationId": org}, {"$set": payload.model_dump()})
    return Project(**{k: v for k, v in updated.items() if k in Project.model_fields})


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str, org: str = Depends(current_org)):
    res = await db.projects.delete_one({"id": project_id, "organizationId": org})
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
async def enrich_task(t: dict, org: str):
    t["project_name"] = None
    t["client_name"] = None
    if t.get("project_id"):
        p = await db.projects.find_one({"id": t["project_id"], "organizationId": org}, {"_id": 0, "name": 1, "client_id": 1})
        if p:
            t["project_name"] = p["name"]
            if p.get("client_id"):
                c = await db.clients.find_one({"id": p["client_id"], "organizationId": org}, {"_id": 0, "name": 1})
                t["client_name"] = c["name"] if c else None
    return t


@api_router.get("/tasks")
async def list_tasks(project_id: Optional[str] = None, org: str = Depends(current_org)):
    q = {"organizationId": org}
    if project_id:
        q["project_id"] = project_id
    tasks = await db.tasks.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for t in tasks:
        await enrich_task(t, org)
    return tasks


@api_router.post("/tasks", response_model=Task)
async def create_task(payload: TaskCreate, org: str = Depends(current_org)):
    obj = Task(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.tasks.insert_one(doc)
    await log_activity(obj.project_id, "task_created", f'Task "{obj.title}" was created')
    if obj.done:
        await log_activity(obj.project_id, "task_completed", f'Task "{obj.title}" was completed')
    return obj


@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, payload: TaskCreate, org: str = Depends(current_org)):
    res = await db.tasks.find_one({"id": task_id, "organizationId": org}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = {**res, **payload.model_dump()}
    await db.tasks.update_one({"id": task_id, "organizationId": org}, {"$set": payload.model_dump()})
    if payload.done and not res.get("done"):
        await log_activity(payload.project_id, "task_completed", f'Task "{payload.title}" was completed')
    return Task(**{k: v for k, v in updated.items() if k in Task.model_fields})


@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, org: str = Depends(current_org)):
    res = await db.tasks.delete_one({"id": task_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}


# ------------------- Documents CRUD -------------------
@api_router.get("/documents")
async def list_documents(project_id: Optional[str] = None, org: str = Depends(current_org)):
    q = {"organizationId": org}
    if project_id:
        q["project_id"] = project_id
    return await db.documents.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/documents", response_model=Document)
async def create_document(payload: DocumentCreate, org: str = Depends(current_org)):
    obj = Document(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.documents.insert_one(doc)
    await log_activity(obj.project_id, "document_uploaded", f'Document "{obj.name}" was uploaded')
    return obj


@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, org: str = Depends(current_org)):
    res = await db.documents.delete_one({"id": document_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


class DocumentRename(BaseModel):
    name: str = Field(..., min_length=1)


@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    org: str = Depends(current_org),
):
    if project_id:
        await require_project(project_id, org)
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 25MB limit")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    allowed = {"pdf", "png", "jpg", "jpeg", "gif", "webp", "svg", "doc", "docx", "txt", "rtf",
               "xls", "xlsx", "csv", "ppt", "pptx", "zip", "json", "md"}
    if ext not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")
    path = f"{S.APP_NAME}/uploads/{org}/{uuid.uuid4()}.{ext}"
    ctype = file.content_type or S.guess_content_type(file.filename or "")
    try:
        result = await asyncio.to_thread(S.put_object, path, data, ctype)
    except Exception as e:
        logging.exception("upload failed")
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}")
    doc = {
        "id": str(uuid.uuid4()), "name": file.filename or "Untitled",
        "type": S.category_for(file.filename or ""), "size": S.human_size(result.get("size", len(data))),
        "size_bytes": result.get("size", len(data)), "content_type": ctype,
        "storage_path": result["path"], "project_id": project_id, "organizationId": org,
        "url": f"/api/documents/DOCID/file", "created_at": now_iso(),
    }
    doc["url"] = f"/api/documents/{doc['id']}/file"
    await db.documents.insert_one(dict(doc))
    await log_activity(project_id, "document_uploaded", f'Document "{doc["name"]}" was uploaded')
    doc.pop("_id", None)
    return doc


@api_router.put("/documents/{document_id}")
async def rename_document(document_id: str, payload: DocumentRename, org: str = Depends(current_org)):
    res = await db.documents.find_one({"id": document_id, "organizationId": org}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.documents.update_one({"id": document_id, "organizationId": org}, {"$set": {"name": payload.name.strip()}})
    return {**res, "name": payload.name.strip()}


@api_router.get("/documents/{document_id}/file")
async def download_document(document_id: str, request: Request, auth: Optional[str] = None):
    # Support ?auth= token for direct browser links (img/anchor cannot set headers)
    token = auth
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = A.decode_token(token)
        org = payload.get("org")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    doc = await db.documents.find_one({"id": document_id, "organizationId": org}, {"_id": 0})
    if not doc or not doc.get("storage_path"):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content, ctype = await asyncio.to_thread(S.get_object, doc["storage_path"])
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")
    disposition = "inline" if (doc.get("content_type", "").startswith(("image/", "application/pdf"))) else "attachment"
    return StreamingResponse(io.BytesIO(content), media_type=doc.get("content_type", ctype),
                             headers={"Content-Disposition": f'{disposition}; filename="{_safe_filename(doc.get("name"))}"'})


def _paginate(page: int, page_size: int):
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    return page, page_size, (page - 1) * page_size


@api_router.get("/library/documents")
async def library_documents(org: str = Depends(current_org), q: str = "", type: str = "", page: int = 1, page_size: int = 12):
    page, page_size, skip = _paginate(page, page_size)
    query = {"organizationId": org}
    if q.strip():
        query["name"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    if type and type != "All":
        query["type"] = type
    total = await db.documents.count_documents(query)
    items = await db.documents.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    for it in items:
        if it.get("project_id"):
            p = await db.projects.find_one({"id": it["project_id"]}, {"_id": 0, "name": 1})
            it["project_name"] = p["name"] if p else None
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


async def _enrich_doc_meta(items, org):
    proj_ids = list({i["project_id"] for i in items if i.get("project_id")})
    cli_ids = list({i.get("client_id") for i in items if i.get("client_id")})
    projs = {p["id"]: p for p in await db.projects.find({"id": {"$in": proj_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    clis = {c["id"]: c for c in await db.clients.find({"id": {"$in": cli_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    for i in items:
        i["project_name"] = projs.get(i.get("project_id"), {}).get("name")
        i["client_name"] = clis.get(i.get("client_id"), {}).get("name")
    return items


@api_router.get("/library/proposals")
async def library_proposals(org: str = Depends(current_org), q: str = "", status: str = "", sort: str = "recent", page: int = 1, page_size: int = 12):
    page, page_size, skip = _paginate(page, page_size)
    query = {"organizationId": org}
    if q.strip():
        query["title"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    if status and status != "All":
        query["status"] = status
    sort_field = "title" if sort == "title" else "updated_at"
    direction = 1 if sort == "title" else -1
    total = await db.ai_proposals.count_documents(query)
    proj = {"_id": 0, "id": 1, "title": 1, "status": 1, "project_id": 1, "client_id": 1, "version": 1, "updated_at": 1, "created_at": 1}
    items = await db.ai_proposals.find(query, proj).sort(sort_field, direction).skip(skip).limit(page_size).to_list(page_size)
    await _enrich_doc_meta(items, org)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


@api_router.get("/library/contracts")
async def library_contracts(org: str = Depends(current_org), q: str = "", status: str = "", sort: str = "recent", page: int = 1, page_size: int = 12):
    page, page_size, skip = _paginate(page, page_size)
    query = {"organizationId": org}
    if q.strip():
        query["title"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    if status and status != "All":
        query["status"] = status
    sort_field = "title" if sort == "title" else "updated_at"
    direction = 1 if sort == "title" else -1
    total = await db.ai_contracts.count_documents(query)
    proj = {"_id": 0, "id": 1, "title": 1, "status": 1, "project_id": 1, "client_id": 1, "version": 1, "updated_at": 1, "created_at": 1}
    items = await db.ai_contracts.find(query, proj).sort(sort_field, direction).skip(skip).limit(page_size).to_list(page_size)
    await _enrich_doc_meta(items, org)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


@api_router.get("/library/invoices")
async def library_invoices(org: str = Depends(current_org), q: str = "", status: str = "", sort: str = "recent", page: int = 1, page_size: int = 12):
    page, page_size, skip = _paginate(page, page_size)
    query = {"organizationId": org}
    if q.strip():
        query["$or"] = [{"invoice_number": {"$regex": re.escape(q.strip()), "$options": "i"}},
                        {"title": {"$regex": re.escape(q.strip()), "$options": "i"}}]
    if status and status != "All":
        query["status"] = status
    sort_field = "total" if sort == "amount" else "updated_at"
    direction = -1
    total = await db.ai_invoices.count_documents(query)
    proj = {"_id": 0, "id": 1, "invoice_number": 1, "title": 1, "status": 1, "project_id": 1, "client_id": 1,
            "total": 1, "subtotal": 1, "vat": 1, "content": 1, "version": 1, "updated_at": 1, "created_at": 1}
    items = await db.ai_invoices.find(query, proj).sort(sort_field, direction).skip(skip).limit(page_size).to_list(page_size)
    await _enrich_doc_meta(items, org)
    # org-wide totals (independent of filters)
    totals = {}
    async for row in db.ai_invoices.aggregate([{"$match": {"organizationId": org}}, {"$group": {"_id": "$status", "count": {"$sum": 1}, "sum": {"$sum": "$total"}}}]):
        totals[row["_id"]] = {"count": row["count"], "sum": round(row.get("sum", 0) or 0, 2)}
    revenue = totals.get("Paid", {}).get("sum", 0)
    outstanding = round(totals.get("Sent", {}).get("sum", 0) + totals.get("Overdue", {}).get("sum", 0), 2)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size),
            "totals": {"by_status": totals, "revenue": revenue, "outstanding": outstanding,
                       "count": await db.ai_invoices.count_documents({"organizationId": org})}}


@api_router.get("/analytics")
async def analytics(org: str = Depends(current_org)):
    base = {"organizationId": org}
    # Revenue by month (from Paid + all invoices)
    monthly = {}
    async for row in db.ai_invoices.aggregate([
        {"$match": base},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 7]}, "invoiced": {"$sum": "$total"},
                    "paid": {"$sum": {"$cond": [{"$eq": ["$status", "Paid"]}, "$total", 0]}}}},
        {"$sort": {"_id": 1}}, {"$limit": 12},
    ]):
        monthly[row["_id"]] = {"month": row["_id"], "invoiced": round(row.get("invoiced", 0) or 0, 2), "paid": round(row.get("paid", 0) or 0, 2)}
    revenue_series = list(monthly.values())

    project_status = []
    palette = {"In Progress": "#8b5cf6", "Review": "#22d3ee", "Completed": "#34d399", "Planning": "#f59e0b", "Blocked": "#f87171"}
    async for row in db.projects.aggregate([{"$match": base}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]):
        project_status.append({"name": row["_id"] or "Unknown", "value": row["count"], "color": palette.get(row["_id"], "#a78bfa")})

    invoice_status = []
    async for row in db.ai_invoices.aggregate([{"$match": base}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]):
        invoice_status.append({"status": row["_id"], "count": row["count"]})

    total_invoiced = round(sum(m["invoiced"] for m in revenue_series), 2)
    total_paid = round(sum(m["paid"] for m in revenue_series), 2)
    kpis = {
        "total_clients": await db.clients.count_documents(base),
        "total_projects": await db.projects.count_documents(base),
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "documents": await db.documents.count_documents(base),
        "proposals": await db.ai_proposals.count_documents(base),
        "contracts": await db.ai_contracts.count_documents(base),
        "invoices": await db.ai_invoices.count_documents(base),
        "open_tasks": await db.tasks.count_documents({**base, "done": False}),
        "completed_tasks": await db.tasks.count_documents({**base, "done": True}),
    }
    return {"kpis": kpis, "revenue_series": revenue_series, "project_status": project_status, "invoice_status": invoice_status}


@api_router.get("/notifications")
async def notifications(org: str = Depends(current_org)):
    items = await db.activities.aggregate([
        {"$match": {"organizationId": org}}, {"$sort": {"created_at": -1}}, {"$limit": 10},
        {"$lookup": {"from": "projects", "localField": "project_id", "foreignField": "id", "as": "proj"}},
        {"$project": {"_id": 0, "id": 1, "type": 1, "message": 1, "created_at": 1, "project_id": 1,
                      "project_name": {"$arrayElemAt": ["$proj.name", 0]}}},
    ]).to_list(10)
    return items


# ==================================================================
# SETTINGS & WORKSPACE MANAGEMENT
# ==================================================================
DEFAULT_ORG_SETTINGS = {
    "organization": {
        "website": "", "businessEmail": "", "phone": "", "address": "",
        "vatNumber": "", "kvkNumber": "", "defaultCurrency": "USD", "defaultVat": 0, "logo": "",
    },
    "branding": {
        "primaryColor": "#8b5cf6", "secondaryColor": "#22d3ee", "logo": "", "pdfLogo": "",
        "proposalFooter": "", "contractFooter": "", "invoiceFooter": "",
    },
    "ai": {
        "provider": "openai", "proposalTone": "Professional", "contractTone": "Formal",
        "invoiceNotes": "", "temperature": 0.7,
    },
    "documents": {
        "proposalPrefix": "PROP", "contractPrefix": "CTR", "invoicePrefix": "INV",
        "numberingStart": 1, "pdfPageSize": "A4", "pdfAccentColor": "#8b5cf6",
    },
}
DEFAULT_NOTIF_PREFS = {
    "emailNotifications": True, "productUpdates": True, "securityAlerts": True,
    "billingAlerts": True, "taskReminders": True, "weeklyDigest": False, "aiAlerts": False,
}


def _merged_settings(org_doc: dict) -> dict:
    s = org_doc.get("settings", {}) or {}
    out = {}
    for section, defaults in DEFAULT_ORG_SETTINGS.items():
        out[section] = {**defaults, **(s.get(section, {}) or {})}
    out["organization"]["name"] = org_doc.get("name", "")
    return out


class OrgProfileUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    businessEmail: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    vatNumber: Optional[str] = None
    kvkNumber: Optional[str] = None
    defaultCurrency: Optional[str] = None
    defaultVat: Optional[float] = None
    logo: Optional[str] = None


class SectionUpdate(BaseModel):
    values: dict


class NotifPrefsUpdate(BaseModel):
    values: dict


@api_router.get("/settings")
async def get_settings(user: dict = Depends(current_user)):
    org_doc = await db.organizations.find_one({"id": user["organizationId"]}, {"_id": 0})
    settings = _merged_settings(org_doc or {})
    settings["notifications"] = {**DEFAULT_NOTIF_PREFS, **(user.get("notificationPrefs", {}) or {})}
    return settings


async def _update_section(org: str, section: str, values: dict):
    clean = {f"settings.{section}.{k}": v for k, v in values.items()}
    if clean:
        clean["updatedAt"] = now_iso()
        await db.organizations.update_one({"id": org}, {"$set": clean})
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0})
    return _merged_settings(org_doc)[section]


@api_router.patch("/settings/organization")
async def update_org_profile(payload: OrgProfileUpdate, org: str = Depends(current_org)):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    name = data.pop("name", None)
    if name is not None and name.strip():
        await db.organizations.update_one({"id": org}, {"$set": {"name": name.strip(), "updatedAt": now_iso()}})
    result = await _update_section(org, "organization", data)
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0})
    result["name"] = org_doc.get("name", "")
    return result


@api_router.patch("/settings/branding")
async def update_branding(payload: SectionUpdate, org: str = Depends(current_org)):
    return await _update_section(org, "branding", payload.values)


@api_router.patch("/settings/ai")
async def update_ai_settings(payload: SectionUpdate, org: str = Depends(current_org)):
    return await _update_section(org, "ai", payload.values)


@api_router.patch("/settings/documents")
async def update_doc_settings(payload: SectionUpdate, org: str = Depends(current_org)):
    return await _update_section(org, "documents", payload.values)


@api_router.patch("/settings/notifications")
async def update_notif_prefs(payload: NotifPrefsUpdate, user: dict = Depends(current_user)):
    merged = {**DEFAULT_NOTIF_PREFS, **(user.get("notificationPrefs", {}) or {}), **payload.values}
    await db.users.update_one({"id": user["id"]}, {"$set": {"notificationPrefs": merged, "updatedAt": now_iso()}})
    return merged


@api_router.post("/settings/upload-image")
async def upload_branding_image(file: UploadFile = File(...), org: str = Depends(current_org)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 5MB limit")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        raise HTTPException(status_code=415, detail="Only image files are allowed")
    path = f"{S.APP_NAME}/branding/{org}/{uuid.uuid4()}.{ext}"
    ctype = file.content_type or S.guess_content_type(file.filename or "")
    try:
        result = await asyncio.to_thread(S.put_object, path, data, ctype)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}")
    asset_id = str(uuid.uuid4())
    await db.branding_assets.insert_one({"id": asset_id, "organizationId": org, "storage_path": result["path"],
                                         "content_type": ctype, "created_at": now_iso()})
    return {"id": asset_id, "url": f"/api/settings/image/{asset_id}"}


@api_router.get("/settings/image/{asset_id}")
async def serve_branding_image(asset_id: str, request: Request, auth: Optional[str] = None):
    token = auth
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        org = A.decode_token(token).get("org")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    asset = await db.branding_assets.find_one({"id": asset_id, "organizationId": org}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")
    content, ctype = await asyncio.to_thread(S.get_object, asset["storage_path"])
    return StreamingResponse(io.BytesIO(content), media_type=asset.get("content_type", ctype))


@api_router.post("/auth/logout-all")
async def logout_all(user: dict = Depends(current_user)):
    res = await db.sessions.update_many({"userId": user["id"], "revoked": False}, {"$set": {"revoked": True}})
    return {"ok": True, "revoked": res.modified_count}


@api_router.get("/settings/recent-logins")
async def recent_logins(user: dict = Depends(current_user)):
    sessions = await db.sessions.find({"userId": user["id"]}, {"_id": 0, "jti": 0}).sort("createdAt", -1).limit(10).to_list(10)
    return sessions


@api_router.get("/settings/billing")
async def get_billing(user: dict = Depends(current_user)):
    org = user["organizationId"]
    base = {"organizationId": org}
    seats = await db.users.count_documents({"organizationId": org})
    usage = {
        "clients": await db.clients.count_documents(base),
        "projects": await db.projects.count_documents(base),
        "documents": await db.documents.count_documents(base),
        "proposals": await db.ai_proposals.count_documents(base),
        "contracts": await db.ai_contracts.count_documents(base),
        "invoices": await db.ai_invoices.count_documents(base),
    }
    return {
        "plan": "Pro", "price": 99, "interval": "month", "status": "active",
        "seats": {"used": seats, "included": 5},
        "usage": usage,
        "limits": {"projects": 100, "documents": 1000, "ai_generations": 500},
        "renews_on": "2026-09-01",
    }


@api_router.get("/settings/api-keys")
async def list_api_keys(user: dict = Depends(current_user)):
    return {"keys": [], "note": "API access is coming soon."}


# ------------------- Executive Dashboard -------------------
@api_router.get("/proposals")
async def list_proposals(project_id: Optional[str] = None, org: str = Depends(current_org)):
    q = {"organizationId": org}
    if project_id:
        q["project_id"] = project_id
    return await db.proposals.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/proposals", response_model=Proposal)
async def create_proposal(payload: ProposalCreate, org: str = Depends(current_org)):
    obj = Proposal(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.proposals.insert_one(doc)
    await log_activity(obj.project_id, "proposal_generated", f'Proposal "{obj.title}" was generated')
    return obj


@api_router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, org: str = Depends(current_org)):
    res = await db.proposals.delete_one({"id": proposal_id, "organizationId": org})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"ok": True}


# ------------------- Activities -------------------
@api_router.get("/activities")
async def list_activities(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
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
async def generate_plan(project_id: str, org: str = Depends(current_org)):
    p = await require_project(project_id, org)
    await enrich_project(p, org)
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
async def list_plans(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await db.plans.find({"project_id": project_id}, {"_id": 0}).sort("version", -1).to_list(1000)


@api_router.post("/projects/{project_id}/plans", response_model=Plan)
async def save_plan(project_id: str, payload: PlanSave, org: str = Depends(current_org)):
    await require_project(project_id, org)
    version = await db.plans.count_documents({"project_id": project_id}) + 1
    obj = Plan(project_id=project_id, version=version, sections=payload.sections)
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.plans.insert_one(doc)
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
async def generate_proposal(project_id: str, org: str = Depends(current_org)):
    p = await require_project(project_id, org)
    await enrich_project(p, org)
    context = await build_project_context(p)

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
async def get_proposal(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_proposal(project_id)


@api_router.get("/projects/{project_id}/proposal/versions")
async def proposal_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_proposal(project_id)
    return doc.get("history", []) if doc else []


@api_router.post("/projects/{project_id}/proposal")
async def save_proposal(project_id: str, payload: ProposalContent, org: str = Depends(current_org)):
    p = await require_project(project_id, org)
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
            "organizationId": org, "client_id": p.get("client_id"), "status": payload.status,
            "content": payload.content, "version": version, "history": [version_entry],
            "created_at": now, "updated_at": now,
        }
        await db.ai_proposals.insert_one(doc)
    await log_activity(project_id, "proposal_saved", f"Proposal v{version} was saved")
    return await _get_ai_proposal(project_id)


@api_router.post("/projects/{project_id}/proposal/restore/{version}")
async def restore_proposal(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_proposal(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await save_proposal(project_id, ProposalContent(title=match["title"], status=match["status"], content=match["content"]), org)


def _export_or_404(project_id, proposal):
    if not proposal:
        raise HTTPException(status_code=404, detail="Save the proposal before exporting")


def _safe_filename(name: str) -> str:
    ascii_name = "".join(c if (c.isalnum() or c in " -_") else "_" for c in (name or "proposal"))
    return ascii_name.strip().replace(" ", "_")[:60] or "proposal"


@api_router.get("/projects/{project_id}/proposal/export/pdf")
async def export_proposal_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    proposal = await _get_ai_proposal(project_id)
    _export_or_404(project_id, proposal)
    data = build_pdf(proposal)
    await log_activity(project_id, "proposal_exported", "Proposal exported as PDF")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/proposal/export/docx")
async def export_proposal_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    proposal = await _get_ai_proposal(project_id)
    _export_or_404(project_id, proposal)
    data = build_docx(proposal)
    await log_activity(project_id, "proposal_exported", "Proposal exported as DOCX")
    fname = _safe_filename(proposal.get("title"))
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.docx"'})


@api_router.get("/proposal/sections")
async def proposal_sections(user: dict = Depends(current_user)):
    return {"sections": PROPOSAL_SECTIONS, "statuses": PROPOSAL_STATUSES}


# ------------------- AI Contract Generator -------------------
class ContractContent(BaseModel):
    title: str = "Untitled Contract"
    status: str = "Draft"
    content: dict = Field(default_factory=dict)


async def _get_ai_contract(project_id: str):
    return await db.ai_contracts.find_one({"project_id": project_id}, {"_id": 0})


async def _build_contract_context(project_id: str, org: str):
    p = await require_project(project_id, org)
    await enrich_project(p, org)
    context = await build_project_context(p)

    proposal_id = None
    client = None
    if p.get("client_id"):
        client = await db.clients.find_one({"id": p["client_id"], "organizationId": org}, {"_id": 0})
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
async def generate_contract(project_id: str, org: str = Depends(current_org)):
    p, context, proposal_id = await _build_contract_context(project_id, org)
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
async def get_contract(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_contract(project_id)


@api_router.get("/projects/{project_id}/contract/versions")
async def contract_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_contract(project_id)
    return doc.get("history", []) if doc else []


async def _save_contract(project_id: str, payload: ContractContent, org: str, activity_type: str, activity_msg_fmt: str):
    p = await require_project(project_id, org)
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
            "organizationId": org, "client_id": p.get("client_id"),
            "proposal_id": proposal.get("id") if proposal else None,
            "status": payload.status, "content": payload.content, "version": version,
            "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_contracts.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg_fmt.format(version=version))
    return await _get_ai_contract(project_id)


@api_router.post("/projects/{project_id}/contract")
async def save_contract(project_id: str, payload: ContractContent, org: str = Depends(current_org)):
    return await _save_contract(project_id, payload, org, "contract_saved", "Contract v{version} was saved")


@api_router.post("/projects/{project_id}/contract/restore/{version}")
async def restore_contract(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_contract(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await _save_contract(
        project_id, ContractContent(title=match["title"], status=match["status"], content=match["content"]),
        org, "contract_restored", f"Contract restored from v{version} as v{{version}}",
    )


@api_router.get("/projects/{project_id}/contract/export/pdf")
async def export_contract_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    contract = await _get_ai_contract(project_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Save the contract before exporting")
    data = build_pdf(contract, CONTRACT_SECTIONS, "Service Agreement")
    await log_activity(project_id, "contract_exported", "Contract exported as PDF")
    fname = _safe_filename(contract.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/contract/export/docx")
async def export_contract_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
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
async def contract_sections(user: dict = Depends(current_user)):
    return {"sections": CONTRACT_SECTIONS, "statuses": CONTRACT_STATUSES}


# ------------------- AI Invoice Generator -------------------
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


async def _next_invoice_number(org: str):
    count = await db.ai_invoices.count_documents({"organizationId": org})
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0, "settings": 1})
    prefix = ((org_doc or {}).get("settings", {}).get("documents", {}) or {}).get("invoicePrefix") or "INV"
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m')}-{count + 1:04d}"


@api_router.post("/projects/{project_id}/invoice/generate")
async def generate_invoice(project_id: str, org: str = Depends(current_org)):
    p, context, proposal_id = await _build_contract_context(project_id, org)
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

    cl = await db.clients.find_one({"id": p["client_id"], "organizationId": org}, {"_id": 0}) if p.get("client_id") else None
    issue = datetime.now(timezone.utc)
    due = issue + timedelta(days=14)
    content = {
        "client_name": (cl or {}).get("contact") or (cl or {}).get("name") or "",
        "company": (cl or {}).get("name") or "",
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
        "invoice_number": await _next_invoice_number(org), "title": f"{p.get('name')} — Invoice",
        "content": content, "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
        "proposal_id": proposal_id, "contract_id": contract.get("id") if contract else None,
    }


@api_router.get("/projects/{project_id}/invoice")
async def get_invoice(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_invoice(project_id)


@api_router.get("/projects/{project_id}/invoice/versions")
async def invoice_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_invoice(project_id)
    return doc.get("history", []) if doc else []


async def _save_invoice(project_id: str, payload: InvoiceSave, org: str, activity_type: str, activity_msg: str):
    p = await require_project(project_id, org)
    if payload.status not in INVOICE_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    vat_rate = float(payload.content.get("vat_rate", 0) or 0)
    items, subtotal, vat_amount, total = _compute_invoice(payload.line_items, vat_rate)
    content = {**payload.content, "vat_rate": vat_rate}

    existing = await _get_ai_invoice(project_id)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    inv_number = payload.invoice_number or (existing["invoice_number"] if existing else await _next_invoice_number(org))
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
            "organizationId": org, "client_id": p.get("client_id"), "proposal_id": proposal.get("id") if proposal else None,
            "contract_id": contract.get("id") if contract else None, "status": payload.status, "content": content,
            "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
            "version": version, "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_invoices.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg.format(version=version, number=inv_number))
    return await _get_ai_invoice(project_id)


@api_router.post("/projects/{project_id}/invoice")
async def save_invoice(project_id: str, payload: InvoiceSave, org: str = Depends(current_org)):
    return await _save_invoice(project_id, payload, org, "invoice_saved", "Invoice {number} v{version} was saved")


@api_router.post("/projects/{project_id}/invoice/restore/{version}")
async def restore_invoice(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_invoice(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    payload = InvoiceSave(invoice_number=match["invoice_number"], title=match["title"],
                          status=match["status"], content=match["content"], line_items=match["line_items"])
    return await _save_invoice(project_id, payload, org, "invoice_restored", "Invoice restored from v" + str(version) + " as v{version}")


@api_router.get("/projects/{project_id}/invoice/export/pdf")
async def export_invoice_pdf(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    invoice = await _get_ai_invoice(project_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Save the invoice before exporting")
    data = build_invoice_pdf(invoice)
    await log_activity(project_id, "invoice_exported", "Invoice exported as PDF")
    fname = _safe_filename(invoice.get("invoice_number") or invoice.get("title"))
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@api_router.get("/projects/{project_id}/invoice/export/docx")
async def export_invoice_docx(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
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
async def invoice_config(user: dict = Depends(current_user)):
    return {"fields": INVOICE_FIELDS, "statuses": INVOICE_STATUSES}


# ------------------- Executive Dashboard -------------------
@api_router.get("/dashboard/summary")
async def dashboard_summary(org: str = Depends(current_org)):
    base = {"organizationId": org}
    total_projects = await db.projects.count_documents(base)
    completed_projects = await db.projects.count_documents({**base, "status": "Completed"})

    inv_by_status = {}
    async for row in db.ai_invoices.aggregate([{"$match": base}, {"$group": {"_id": "$status", "count": {"$sum": 1}, "total": {"$sum": "$total"}}}]):
        inv_by_status[row["_id"]] = {"count": row["count"], "total": round(row.get("total", 0) or 0, 2)}
    revenue = inv_by_status.get("Paid", {}).get("total", 0)
    outstanding = round(inv_by_status.get("Sent", {}).get("total", 0) + inv_by_status.get("Overdue", {}).get("total", 0), 2)
    avg_row = await db.ai_invoices.aggregate([{"$match": base}, {"$group": {"_id": None, "avg": {"$avg": "$total"}}}]).to_list(1)
    avg_invoice = round(avg_row[0]["avg"], 2) if avg_row else 0
    total_invoices = await db.ai_invoices.count_documents(base)

    project_status = {}
    async for row in db.projects.aggregate([{"$match": base}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]):
        project_status[row["_id"] or "Unknown"] = row["count"]

    kpis = {
        "total_clients": await db.clients.count_documents(base),
        "active_projects": total_projects - completed_projects,
        "completed_projects": completed_projects,
        "open_tasks": await db.tasks.count_documents({**base, "done": False}),
        "completed_tasks": await db.tasks.count_documents({**base, "done": True}),
        "pending_proposals": await db.ai_proposals.count_documents({**base, "status": {"$in": ["Draft", "Generated", "Sent"]}}),
        "sent_contracts": await db.ai_contracts.count_documents({**base, "status": {"$in": ["Sent", "Signed"]}}),
        "outstanding_invoices": (inv_by_status.get("Sent", {}).get("count", 0) + inv_by_status.get("Overdue", {}).get("count", 0)),
        "paid_invoices": inv_by_status.get("Paid", {}).get("count", 0),
        "revenue": revenue,
    }

    financial = {
        "draft": inv_by_status.get("Draft", {}).get("count", 0),
        "sent": inv_by_status.get("Sent", {}).get("count", 0),
        "paid": inv_by_status.get("Paid", {}).get("count", 0),
        "overdue": inv_by_status.get("Overdue", {}).get("count", 0),
        "cancelled": inv_by_status.get("Cancelled", {}).get("count", 0),
        "revenue": revenue,
        "outstanding_revenue": outstanding,
        "average_invoice_value": avg_invoice,
        "total_invoices": total_invoices,
        "by_status": inv_by_status,
    }

    recent_activity = await db.activities.aggregate([
        {"$match": base}, {"$sort": {"created_at": -1}}, {"$limit": 12},
        {"$lookup": {"from": "projects", "localField": "project_id", "foreignField": "id", "as": "proj"}},
        {"$project": {"_id": 0, "type": 1, "message": 1, "created_at": 1, "project_id": 1,
                      "project_name": {"$arrayElemAt": ["$proj.name", 0]}}},
    ]).to_list(12)

    upcoming_tasks = await db.tasks.aggregate([
        {"$match": {**base, "done": False}},
        {"$lookup": {"from": "projects", "localField": "project_id", "foreignField": "id", "as": "proj"}},
        {"$addFields": {"project_name": {"$arrayElemAt": ["$proj.name", 0]},
                        "nodue": {"$cond": [{"$in": ["$due", ["", None]]}, 1, 0]}}},
        {"$sort": {"nodue": 1, "due": 1}}, {"$limit": 6},
        {"$project": {"_id": 0, "proj": 0, "nodue": 0}},
    ]).to_list(6)

    recent_clients = await db.clients.aggregate([
        {"$match": base}, {"$sort": {"created_at": -1}}, {"$limit": 5},
        {"$lookup": {"from": "projects", "localField": "id", "foreignField": "client_id", "as": "proj"}},
        {"$addFields": {"projects_count": {"$size": "$proj"}}},
        {"$project": {"_id": 0, "proj": 0}},
    ]).to_list(5)

    return {
        "kpis": kpis, "financial": financial, "project_status": project_status,
        "recent_activity": recent_activity, "upcoming_tasks": upcoming_tasks, "recent_clients": recent_clients,
    }


@api_router.get("/dashboard/search")
async def dashboard_search(q: str, org: str = Depends(current_org)):
    if not q or len(q.strip()) < 1:
        return {"clients": [], "projects": [], "invoices": [], "contracts": [], "proposals": []}
    rx = {"$regex": re.escape(q.strip()), "$options": "i"}
    base = {"organizationId": org}
    clients = await db.clients.find({**base, "$or": [{"name": rx}, {"contact": rx}, {"email": rx}]}, {"_id": 0, "id": 1, "name": 1, "contact": 1}).limit(5).to_list(5)
    projects = await db.projects.find({**base, "name": rx}, {"_id": 0, "id": 1, "name": 1, "status": 1}).limit(5).to_list(5)
    invoices = await db.ai_invoices.find({**base, "$or": [{"invoice_number": rx}, {"title": rx}]}, {"_id": 0, "project_id": 1, "invoice_number": 1, "title": 1, "total": 1}).limit(5).to_list(5)
    contracts = await db.ai_contracts.find({**base, "title": rx}, {"_id": 0, "project_id": 1, "title": 1, "status": 1}).limit(5).to_list(5)
    proposals = await db.ai_proposals.find({**base, "title": rx}, {"_id": 0, "project_id": 1, "title": 1, "status": 1}).limit(5).to_list(5)
    documents = await db.documents.find({**base, "name": rx}, {"_id": 0, "id": 1, "name": 1, "type": 1, "project_id": 1}).limit(5).to_list(5)
    return {"clients": clients, "projects": projects, "invoices": invoices, "contracts": contracts, "proposals": proposals, "documents": documents}


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


SCOPED_COLLECTIONS = [
    "clients", "projects", "tasks", "documents", "proposals", "activities",
    "plans", "ai_proposals", "ai_contracts", "ai_invoices", "chat_messages",
]


@app.on_event("startup")
async def startup():
    try:
        await asyncio.to_thread(S.init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    await db.users.create_index("email", unique=True)
    await db.sessions.create_index("jti")
    await db.sessions.create_index("userId")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.email_verification_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")

    # Seed demo account + backfill existing (pre-auth) data to its organization
    demo_email = os.environ.get("DEMO_EMAIL", "jordan@assistify.io").lower()
    demo_password = os.environ.get("DEMO_PASSWORD", "Assistify2026!")
    demo = await db.users.find_one({"email": demo_email})
    now = now_iso()
    if not demo:
        org_id = A.gen_id()
        user_id = A.gen_id()
        await db.organizations.insert_one({
            "id": org_id, "name": "Assistify Inc.", "ownerId": user_id, "createdAt": now, "updatedAt": now})
        await db.users.insert_one({
            "id": user_id, "firstName": "Jordan", "lastName": "Reyes", "email": demo_email,
            "passwordHash": A.hash_password(demo_password), "emailVerified": True,
            "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200",
            "role": "owner", "organizationId": org_id, "timezone": "UTC", "language": "en",
            "createdAt": now, "updatedAt": now, "lastLogin": now, "onboardingCompleted": True})
        logger.info(f"[SEED] Created demo account {demo_email} / org {org_id}")
    else:
        org_id = demo["organizationId"]
        if not A.verify_password(demo_password, demo["passwordHash"]):
            await db.users.update_one({"email": demo_email}, {"$set": {"passwordHash": A.hash_password(demo_password)}})

    # Backfill any legacy documents that lack organizationId
    for coll in SCOPED_COLLECTIONS:
        res = await db[coll].update_many({"organizationId": {"$exists": False}}, {"$set": {"organizationId": org_id}})
        if res.modified_count:
            logger.info(f"[BACKFILL] {coll}: {res.modified_count} docs -> org {org_id}")

    # Existing users (pre-onboarding sprint) should not see the wizard
    await db.users.update_many({"onboardingCompleted": {"$exists": False}}, {"$set": {"onboardingCompleted": True}})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
