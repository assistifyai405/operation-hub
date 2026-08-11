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

from ai_service import AIService, extract_json, AIConfigError, public_ai_error
from proposal_config import PROPOSAL_SECTIONS, PROPOSAL_STATUSES, PROPOSAL_SYSTEM, build_proposal_prompt
from contract_config import CONTRACT_SECTIONS, CONTRACT_STATUSES, CONTRACT_SYSTEM, build_contract_prompt
from invoice_config import INVOICE_STATUSES, INVOICE_FIELDS, INVOICE_SYSTEM, build_invoice_prompt
from proposal_export import build_pdf, build_docx
from invoice_export import build_invoice_pdf, build_invoice_docx
import auth as A
import storage as S
import email_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from core import client, db, now_iso, log_activity, ai_service
from config import get_settings as get_app_settings
from dependencies import (public_user, current_user, current_org, require_project,
                          rate_limit, _client_ip)
from routers.copilot import router as copilot_router
from routers.exports import router as exports_router
from routers.ai import router as ai_router
from routers.assistant import router as assistant_router
from routers.opportunities import router as opportunities_router
from routers.crm import router as crm_router
from routers.memory import router as memory_router
from routers.memory import build_memory_prompt
from routers.automation import router as automation_router
from routers.automation import seed_demo_automations
from routers.onboarding import router as onboarding_router
from routers.dashboard_exec import router as dashboard_exec_router
from routers.team import router as team_router
from routers.emails import router as emails_router
from routers.webhooks import router as webhooks_router
from routers.integrations import router as integrations_router
from routers.inbox import router as inbox_router
from routers.health import router as health_router
from routers.ops import router as ops_router
from routers.feedback import router as feedback_router
from routers import team as team_mod
from permissions import require_admin, normalize_role
import ai_activity as aia
from observability import RequestContextMiddleware, configure_logging
from errors import install_error_handlers

app = FastAPI()
install_error_handlers(app)
app.add_middleware(RequestContextMiddleware)
api_router = APIRouter(prefix="/api")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/api/auth"


# ==================================================================
# AUTHENTICATION
# ==================================================================


# --- auth models ---
class RegisterRequest(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=60)
    lastName: str = Field(default="", max_length=60)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    company: str = ""
    invitationToken: Optional[str] = None
    language: Optional[str] = None


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


def _cookie_flags() -> dict:
    """httpOnly cookies: secure+SameSite=None in production/HTTPS; lax+insecure on local HTTP."""
    s = get_app_settings()
    return {"httponly": True, "secure": s.cookie_secure, "samesite": s.cookie_samesite}


def _set_refresh_cookie(response: Response, token: str, remember: bool):
    max_age = A.REFRESH_TOKEN_DAYS * 86400 if remember else 86400
    response.set_cookie(key=REFRESH_COOKIE, value=token, max_age=max_age, path=COOKIE_PATH, **_cookie_flags())


def _set_access_cookie(response: Response, access: str):
    # Enables direct-link authenticated downloads (PDF/DOCX exports via window.open)
    response.set_cookie(
        key="access_token", value=access, max_age=A.ACCESS_TOKEN_MINUTES * 60, path="/api", **_cookie_flags()
    )


def _set_csrf_cookie(response: Response, token: str | None = None):
    from csrf import CSRF_COOKIE, csrf_cookie_flags, new_csrf_token
    value = token or new_csrf_token()
    # Readable by SPA (not httpOnly); path=/ so JS can always read it
    response.set_cookie(key=CSRF_COOKIE, value=value, max_age=A.REFRESH_TOKEN_DAYS * 86400, path="/", **csrf_cookie_flags())
    return value


def _clear_auth_cookies(response: Response):
    flags = _cookie_flags()
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, secure=flags["secure"], samesite=flags["samesite"])
    response.delete_cookie("access_token", path="/api", secure=flags["secure"], samesite=flags["samesite"])
    from csrf import CSRF_COOKIE, csrf_cookie_flags
    cf = csrf_cookie_flags()
    response.delete_cookie(CSRF_COOKIE, path="/", secure=cf["secure"], samesite=cf["samesite"])


def _issue_session_cookies(response: Response, access: str, refresh: str, remember: bool):
    """Set access + refresh + CSRF cookies. Never expose JWTs to JS."""
    _set_refresh_cookie(response, refresh, remember)
    _set_access_cookie(response, access)
    _set_csrf_cookie(response)



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
    base = get_app_settings().frontend_url.rstrip("/")
    return f"{base}{path}?token={token}"


def _guard_send(user, status: str):
    # Block client-facing "send" actions until the acting user verifies their email.
    # When called internally (e.g. Copilot), `user` is the unresolved Depends sentinel, not a dict -> skip.
    if isinstance(user, dict) and status == "Sent" and not user.get("emailVerified", False):
        raise HTTPException(status_code=403, detail="Please verify your email before sending documents to clients.")


async def _email_brand(org_id: str) -> dict:
    org_doc = await db.organizations.find_one({"id": org_id}, {"_id": 0}) or {}
    s = _merged_settings(org_doc)
    b, o = s["branding"], s["organization"]
    return {
        "company_name": o.get("name") or "Assistify",
        "primary": b.get("primaryColor") or "#16A34A",
        "logo_url": b.get("logo") or o.get("logo") or "",
    }


@api_router.post("/auth/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    rate_limit(f"register:{_client_ip(request)}", 10, 3600)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    from locale_util import is_allowed_locale, normalize_locale
    # Prefer explicit client locale; else Accept-Language; else English.
    lang = None
    if payload.language:
        if not is_allowed_locale(payload.language):
            raise HTTPException(status_code=400, detail="language must be 'nl' or 'en'")
        lang = normalize_locale(payload.language)
    else:
        accept = request.headers.get("accept-language") or ""
        for part in accept.split(","):
            tag = part.split(";")[0].strip()
            if tag and is_allowed_locale(tag):
                lang = normalize_locale(tag)
                break
    lang = lang or "en"

    now = now_iso()
    user_id = A.gen_id()
    invite = None
    if payload.invitationToken:
        invite = await team_mod.consume_invitation_for_new_user(payload.invitationToken.strip(), email)
        org_id = invite["organizationId"]
        role = normalize_role(invite.get("role"))
        onboarding_done = True
    else:
        org_id = A.gen_id()
        org_name = payload.company.strip() or f"{payload.firstName}'s Organization"
        await db.organizations.insert_one({
            "id": org_id, "name": org_name, "ownerId": user_id, "createdAt": now, "updatedAt": now,
        })
        role = "owner"
        onboarding_done = False

    user = {
        "id": user_id, "firstName": payload.firstName.strip(), "lastName": payload.lastName.strip(),
        "email": email, "passwordHash": A.hash_password(payload.password), "emailVerified": False,
        "avatar": "", "role": role, "organizationId": org_id, "timezone": "UTC", "language": lang,
        "createdAt": now, "updatedAt": now, "lastLogin": now, "joinedAt": now,
        "onboardingCompleted": onboarding_done,
    }
    await db.users.insert_one(user)

    if invite:
        ok = await team_mod.mark_invitation_accepted(invite["id"], user_id, invite["tokenHash"])
        if not ok:
            # Extremely rare race — roll back user to avoid orphan invite acceptance
            await db.users.delete_one({"id": user_id})
            raise HTTPException(status_code=409, detail="This invitation has already been used")
        from audit import write_audit
        await write_audit(
            org_id, "invitation_accepted",
            actor_id=user_id, actor_email=email,
            target_user_id=user_id, target_email=email,
            meta={"role": role, "invitationId": invite["id"], "via": "register"},
        )

    # Email verification — send via Resend when configured, else dev-mode fallback
    vtoken = A.gen_token()
    await db.email_verification_tokens.insert_one({
        "token": vtoken, "userId": user_id, "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=2), "created_at": now,
    })
    verify_link = _dev_link("/verify-email", vtoken)
    brand = await _email_brand(org_id)
    await email_service.send_verification_email(email, verify_link, brand)

    access, refresh = await _create_session(user, request, True)
    _issue_session_cookies(response, access, refresh, True)
    out = {"user": public_user(user), "joinedViaInvitation": bool(invite), "auth": "cookie"}
    if not email_service.is_enabled():
        # Dev-mode only: expose the link so the flow is testable without a mail provider.
        logger.info(f"[EMAIL:VERIFY:DEV] {email} -> {verify_link}")
        out["verificationLink"] = verify_link
    return out


async def _seed_demo_data(org_id: str):
    """Seed a small, isolated set of sample data so a demo workspace isn't empty."""
    now = now_iso()
    clients = [
        {"name": "Northwind Labs", "contact": "Dana Whitfield", "email": "dana@northwind.test", "phone": "+1 415 555 0132", "value": 48200, "status": "Active", "industry": "SaaS", "company_size": "50-200", "website": "northwind.test", "owner": "You", "tags": ["priority", "retainer"], "notes": "Recurring web work. Responsive, values speed."},
        {"name": "Vertex Studio", "contact": "Marco Ruiz", "email": "marco@vertex.test", "phone": "+1 646 555 0177", "value": 31900, "status": "Active", "industry": "Creative Agency", "company_size": "10-50", "website": "vertex.test", "owner": "You", "tags": ["design"], "notes": "Referral. Slow to reply lately."},
        {"name": "Halcyon Group", "contact": "Priya Nair", "email": "priya@halcyon.test", "phone": "+44 20 7946 0958", "value": 62400, "status": "Active", "industry": "Finance", "company_size": "200-500", "website": "halcyon.test", "owner": "You", "tags": ["enterprise", "priority"], "notes": "High-value account. Brand redesign in progress."},
    ]
    client_ids = {}
    for c in clients:
        obj = Client(**c)
        doc = obj.model_dump(); doc["organizationId"] = org_id; doc["is_demo"] = True
        await db.clients.insert_one(doc)
        client_ids[c["name"]] = obj.id
    projects = [
        {"name": "Brand Redesign", "client": "Halcyon Group", "status": "In Progress", "description": "Full visual identity refresh and website redesign."},
        {"name": "Q3 Marketing Site", "client": "Northwind Labs", "status": "Planning", "description": "New marketing website with CMS."},
    ]
    proj_ids = []
    for p in projects:
        obj = Project(name=p["name"], client_id=client_ids.get(p["client"]), status=p["status"], description=p["description"])
        doc = obj.model_dump(); doc["organizationId"] = org_id; doc["is_demo"] = True
        await db.projects.insert_one(doc)
        proj_ids.append(obj.id)
        await db.activities.insert_one({"id": str(uuid.uuid4()), "project_id": obj.id, "organizationId": org_id,
                                        "type": "project_created", "message": f'Project "{obj.name}" was created', "created_at": now, "is_demo": True})
    tasks = [
        {"title": "Kickoff call with client", "priority": "High", "project_id": proj_ids[0]},
        {"title": "Draft moodboard", "priority": "Medium", "project_id": proj_ids[0]},
        {"title": "Collect brand assets", "priority": "Low", "project_id": proj_ids[1]},
    ]
    for t in tasks:
        obj = Task(**t)
        doc = obj.model_dump(); doc["organizationId"] = org_id; doc["is_demo"] = True
        await db.tasks.insert_one(doc)

    # Sample sales leads so the CRM pipeline demonstrates value immediately.
    def _iso_days(d):
        return (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
    def _close_in(d):
        return (datetime.now(timezone.utc) + timedelta(days=d)).strftime("%Y-%m-%d")
    lead_samples = [
        {"title": "Brand Redesign — Phase 2", "client": "Halcyon Group", "project": proj_ids[0], "stage": "Negotiating", "value": 42000, "expected_close": _close_in(5), "owner": "You", "source": "Existing client", "tags": ["enterprise"], "notes": "Wants a phase 2 covering the app UI. Budget approved, finalizing scope.", "age": 2},
        {"title": "Q3 Marketing Site", "client": "Northwind Labs", "project": proj_ids[1], "stage": "Proposal Sent", "value": 28500, "expected_close": _close_in(12), "owner": "You", "source": "Inbound", "tags": ["web"], "notes": "Proposal sent, awaiting feedback from their marketing lead.", "age": 6},
        {"title": "Rebrand + Website", "client": "Vertex Studio", "stage": "Qualified", "value": 19000, "expected_close": _close_in(25), "owner": "You", "source": "Referral", "tags": ["design"], "notes": "Interested but comparing options.", "age": 11},
        {"title": "Marketing Retainer", "client": "Northwind Labs", "stage": "Meeting Scheduled", "value": 36000, "expected_close": _close_in(18), "owner": "You", "source": "Existing client", "tags": ["retainer"], "notes": "Monthly retainer discussion. Meeting booked.", "age": 1},
        {"title": "Landing Page Sprint", "stage": "New", "value": 6500, "contact_name": "Alex Kim", "email": "alex@brightfold.test", "expected_close": _close_in(30), "owner": "You", "source": "Cold outreach", "tags": [], "notes": "New inbound from website form.", "age": 0},
        {"title": "Annual Report Design", "client": "Halcyon Group", "stage": "Won", "value": 15400, "expected_close": _close_in(-3), "owner": "You", "source": "Existing client", "tags": ["enterprise"], "notes": "Closed and delivered.", "age": 20},
    ]
    for ls in lead_samples:
        created = _iso_days(ls.pop("age", 0))
        client_key = ls.pop("client", None)
        pid = ls.pop("project", None)
        doc = {"id": str(uuid.uuid4()), "organizationId": org_id, "title": ls["title"],
               "client_id": client_ids.get(client_key) if client_key else None, "project_id": pid,
               "stage": ls["stage"], "value": ls["value"], "probability": None,
               "expected_close": ls.get("expected_close", ""), "owner": ls.get("owner", ""),
               "contact_name": ls.get("contact_name", ""), "email": ls.get("email", ""), "phone": "",
               "source": ls.get("source", ""), "notes": ls.get("notes", ""), "tags": ls.get("tags", []),
               "created_at": created, "updated_at": created, "stage_changed_at": created,
               "stage_history": [{"stage": "New", "at": created}, {"stage": ls["stage"], "at": created}], "is_demo": True}
        await db.leads.insert_one(doc)

    # Seed starter memories so the Knowledge Brain shows value immediately.
    mem_seed = [
        ("Prefers concise, confident introductions", "Writing Style", "Opening sections should be short and get to the value fast — avoid long preambles.", 88, "Learned from your edits"),
        ("Signs documents with the company name", "Brand Voice", "Client documents close with the studio name and a warm line.", 82, "Learned from your edits"),
        ("Prefers bullet lists over dense paragraphs", "Writing Style", "Deliverables, scope and next steps are formatted as scannable bullets.", 85, "Learned from your edits"),
        ("Typical project pricing $20k–$60k", "Pricing", "Most engagements land between $20,000 and $60,000 depending on scope.", 78, "Business data"),
        ("Core services: brand & web design", "Services", "The business focuses on brand identity, web design and marketing sites.", 90, "Business data"),
        ("Communicates formally with enterprise clients", "Preferences", "Enterprise accounts (e.g. Halcyon) get a more formal, thorough tone.", 72, "Learned from your edits"),
    ]
    for title, cat, content, conf, src in mem_seed:
        await db.memories.insert_one({
            "id": str(uuid.uuid4()), "organizationId": org_id, "title": title, "category": cat,
            "content": content, "keywords": [], "confidence": conf, "source": src,
            "times_used": (conf % 7), "pinned": cat == "Brand Voice", "learning_enabled": True, "is_demo": True,
            "created_at": _iso_days(conf % 5), "updated_at": _iso_days(conf % 3)})

    # Sample AI activity so the AI Workspace demonstrates value from the first visit.
    hal, nw = client_ids.get("Halcyon Group"), client_ids.get("Northwind Labs")
    samples = [
        ("proposal", f'Proposal generated for {projects[0]["name"]}',
         "Assistify drafted a full client proposal covering scope, timeline and pricing.", 0, 4200, "Halcyon Group", projects[0]["name"], proj_ids[0]),
        ("plan", f'Project plan created for {projects[0]["name"]}',
         "Assistify analyzed the project and produced a structured delivery plan with phases and milestones.", 0, 3100, "Halcyon Group", projects[0]["name"], proj_ids[0]),
        ("contract", f'Contract drafted for {projects[0]["name"]}',
         "Assistify prepared a service agreement with standard protective clauses ready for review.", 1, 5200, "Halcyon Group", projects[0]["name"], proj_ids[0]),
        ("plan", f'Project plan created for {projects[1]["name"]}',
         "Assistify mapped out phases and next actions for the marketing site build.", 2, 2800, "Northwind Labs", projects[1]["name"], proj_ids[1]),
        ("invoice", f'Invoice prepared for {projects[0]["name"]}',
         "Assistify built an invoice with line items, VAT and totals calculated automatically.", 3, 2100, "Halcyon Group", projects[0]["name"], proj_ids[0]),
        ("proposal", f'Proposal generated for {projects[1]["name"]}',
         "Assistify drafted a client-ready proposal tailored to the project brief.", 5, 3900, "Northwind Labs", projects[1]["name"], proj_ids[1]),
    ]
    for atype, title, expl, days_ago, gms, cname, pname, pid in samples:
        when = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=days_ago)).isoformat()
        e = aia._entry(org_id, atype, title, expl, "Project Workspace", {"project_id": pid}, when,
                       meta={"gen_ms": gms, "client_name": cname, "project_name": pname})
        e["is_demo"] = True
        await db.ai_activities.insert_one(dict(e))

    # A versioned proposal + plan so Version Compare has content on day one.
    v_now = now_iso()
    await db.ai_proposals.insert_one({
        "id": str(uuid.uuid4()), "title": f"{projects[0]['name']} — Proposal", "project_id": proj_ids[0],
        "organizationId": org_id, "client_id": hal, "status": "Sent", "content": {}, "version": 2,
        "history": [
            {"version": 1, "title": f"{projects[0]['name']} — Proposal", "status": "Draft", "content": {}, "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
            {"version": 2, "title": f"{projects[0]['name']} — Proposal", "status": "Sent", "content": {}, "created_at": v_now},
        ], "created_at": v_now, "updated_at": v_now, "is_demo": True,
    })
    for ver in (1, 2):
        await db.plans.insert_one({"id": str(uuid.uuid4()), "project_id": proj_ids[0], "organizationId": org_id,
                                   "version": ver, "sections": {}, "is_demo": True, "created_at": (datetime.now(timezone.utc) - timedelta(days=2 - ver)).isoformat()})
    await db.organizations.update_one({"id": org_id}, {"$set": {"ai_backfilled": True}})

    # Provision the AI Automation Engine (defaults + templates) and run one pass so
    # the Approval Center & History demonstrate value from the first visit.
    await seed_demo_automations(org_id)


@api_router.post("/auth/demo")
async def create_demo(request: Request, response: Response):
    """Provision a brand-new ISOLATED demo tenant (own org + anonymous user) and sign in.
    Each call creates a fresh workspace — demo users never share data.

    Disabled unless ENABLE_DEMO_LOGIN=true (never on by default in any environment).
    """
    from config import get_settings
    if not get_settings().enable_demo_login:
        raise HTTPException(status_code=404, detail="Demo login is disabled")
    rate_limit(f"demo:{_client_ip(request)}", 10, 3600)
    now = now_iso()
    org_id = A.gen_id()
    user_id = A.gen_id()
    email = f"demo+{uuid.uuid4().hex[:10]}@assistify.demo"
    await db.organizations.insert_one({
        "id": org_id, "name": "Demo Workspace", "ownerId": user_id,
        "isDemo": True, "createdAt": now, "updatedAt": now,
    })
    user = {
        "id": user_id, "firstName": "Demo", "lastName": "User", "email": email,
        "passwordHash": A.hash_password(A.gen_token()),  # random, unusable — no password login for demo
        "emailVerified": True, "avatar": "", "role": "owner", "organizationId": org_id,
        "timezone": "UTC", "language": "en", "isDemo": True,
        "createdAt": now, "updatedAt": now, "lastLogin": now, "onboardingCompleted": True,
    }
    await db.users.insert_one(user)
    await _seed_demo_data(org_id)
    access, refresh = await _create_session(user, request, False)
    _issue_session_cookies(response, access, refresh, False)
    return {"user": public_user(user), "isDemo": True, "auth": "cookie"}


@api_router.get("/config/public")
async def public_config():
    """Non-secret feature flags + staging readiness (never exposes secrets)."""
    from config import get_settings
    from email_providers import get_email_provider, outbound_sending_allowed
    cfg = get_settings()
    email_ok, email_reason = outbound_sending_allowed(cfg)
    provider = get_email_provider(cfg)
    email_configured = provider.is_configured() if cfg.email_provider == "resend" else cfg.email_provider == "console"

    def _oauth_status(pid: str) -> str:
        try:
            from routers.integrations import _oauth_ready
            return "configured" if _oauth_ready(pid) else "not_configured"
        except Exception:
            return "not_configured"

    return {
        "demoLoginEnabled": bool(cfg.enable_demo_login),
        "demoSeedEnabled": bool(cfg.enable_demo_seed),
        "billingEnabled": False,  # Stripe not integrated; frontend also gates via REACT_APP_BILLING_ENABLED
        "betaMode": bool(cfg.beta_mode),
        "environment": cfg.environment,
        "email": {
            "provider": cfg.email_provider,
            "sendingEnabled": bool(cfg.email_sending_enabled),
            "configured": bool(email_configured),
            "canSend": bool(email_ok and cfg.email_sending_enabled),
            "status": (
                "ready" if (email_ok and cfg.email_sending_enabled and email_configured)
                else ("configured_disabled" if email_configured and not cfg.email_sending_enabled
                      else ("not_configured" if not email_configured else "blocked"))
            ),
            # reason is safe/non-secret (e.g. kill-switch message)
            "blockedReason": None if email_ok else email_reason,
        },
        "oauth": {
            "google": _oauth_status("google"),
            "microsoft": _oauth_status("microsoft"),
            "slack": _oauth_status("slack"),
        },
        "cookies": {
            "secure": bool(cfg.cookie_secure),
            "sameSite": cfg.cookie_samesite,
        },
        "legal": {
            "companyName": cfg.legal_company_name or None,
            "tradeName": cfg.legal_trade_name or None,
            "contactEmail": cfg.legal_contact_email or None,
            "privacyEmail": cfg.legal_privacy_email or None,
            "address": cfg.legal_address or None,
            "kvkNumber": cfg.legal_kvk_number or None,
            "vatNumber": cfg.legal_vat_number or None,
            "placeholders": not bool(cfg.legal_company_name and cfg.legal_contact_email),
        },
    }



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
    _issue_session_cookies(response, access, refresh, payload.remember)
    return {"user": public_user(user), "auth": "cookie"}


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
    _issue_session_cookies(response, access, new_refresh, remember)
    return {"user": public_user(user), "auth": "cookie"}


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            payload = A.decode_token(token)
            await db.sessions.update_one({"jti": payload.get("jti")}, {"$set": {"revoked": True}})
        except Exception:
            pass
    _clear_auth_cookies(response)
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
    brand = await _email_brand(user["organizationId"])
    await email_service.send_password_reset_email(email, reset_link, brand)
    if email_service.is_enabled():
        return generic
    # Dev-mode only: expose the link so the flow is testable without a mail provider.
    logger.info(f"[EMAIL:RESET:DEV] {email} -> {reset_link}")
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
    brand = await _email_brand(user["organizationId"])
    await email_service.send_verification_email(user["email"], link, brand)
    if email_service.is_enabled():
        return {"ok": True, "message": "Verification email sent"}
    logger.info(f"[EMAIL:VERIFY:DEV] {user['email']} -> {link}")
    return {"ok": True, "verificationLink": link}


@api_router.patch("/auth/profile")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(current_user)):
    from locale_util import is_allowed_locale, normalize_locale
    updates = {}
    for f in ["firstName", "lastName", "avatar", "timezone", "language"]:
        v = getattr(payload, f)
        if v is not None:
            if f == "language":
                if not is_allowed_locale(v):
                    raise HTTPException(status_code=400, detail="language must be 'nl' or 'en'")
                v = normalize_locale(v)
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


# ---------------------------------------------------------------------------
# Legacy onboarding endpoints (Sprint 1 first-run checklist)
# Kept for backward compatibility with older clients and tests.
# The Sprint 9 full-screen wizard uses routers/onboarding.py under the same
# /api/onboarding prefix (state/profile/seed-demo/checklist/…). Do NOT remove
# these legacy routes in this sprint — they remain intentional dual APIs.
# ---------------------------------------------------------------------------
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
        "accent": "brand",
        "system_message": "You are Assistify Copilot, a sharp, concise business operating assistant for entrepreneurs. Help with planning, tasks, clients and general operations. Keep answers practical and action-oriented.",
    },
    "sales": {
        "id": "sales", "name": "Sales Strategist", "role": "Revenue & Deals",
        "description": "Crafts outreach, pricing strategy and closes deals.",
        "avatar": "https://images.unsplash.com/photo-1689443111130-6e9c7dfd8f9e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "emerald",
        "system_message": "You are the Sales Strategist for Assistify. You specialize in outbound outreach, cold email copy, pricing strategy, objection handling and deal closing. Be persuasive, concise and results-driven.",
    },
    "writer": {
        "id": "writer", "name": "Proposal Writer", "role": "Docs & Proposals",
        "description": "Writes crisp proposals, SOWs and client documents.",
        "avatar": "https://images.unsplash.com/photo-1689443111384-1cf214df988a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "blue",
        "system_message": "You are the Proposal Writer for Assistify. You write polished, well-structured business proposals, scopes of work and client-facing documents. Use clear headings and professional tone.",
    },
    "analyst": {
        "id": "analyst", "name": "Data Analyst", "role": "Insights & Metrics",
        "description": "Turns numbers into clear business insights.",
        "avatar": "https://images.unsplash.com/photo-1689443111070-2c1a1110fe82?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwyfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMHRlY2glMjBzdGFydHVwJTIwbG9nb3xlbnwwfHx8fDE3ODMyMzk4NzF8MA&ixlib=rb-4.1.0&q=85",
        "accent": "amber",
        "system_message": "You are the Data Analyst for Assistify. You interpret business metrics, revenue trends and KPIs, and give clear, quantified insights and recommendations.",
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
    industry: str = ""
    company_size: str = ""
    website: str = ""
    address: str = ""
    notes: str = ""
    owner: str = ""
    next_follow_up: str = ""
    source: str = ""
    tags: List[str] = Field(default_factory=list)


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
    return {"message": "Assistify API"}


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

    async def event_generator():
        full = ""
        try:
            async for delta in ai_service.stream(agent["system_message"], req.message, session_id=req.session_id):
                full += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except AIConfigError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
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
    await log_activity(obj.id, "project_created", f'Project "{obj.name}" was created', org=org)
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
    scoped = {"project_id": project_id, "organizationId": org}
    await db.tasks.update_many(scoped, {"$set": {"project_id": None}})
    await db.documents.delete_many(scoped)
    await db.proposals.delete_many(scoped)
    await db.plans.delete_many(scoped)
    await db.ai_proposals.delete_many(scoped)
    await db.ai_contracts.delete_many(scoped)
    await db.ai_invoices.delete_many(scoped)
    await db.activities.delete_many(scoped)
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
    if payload.project_id:
        await require_project(payload.project_id, org)
    obj = Task(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.tasks.insert_one(doc)
    await log_activity(obj.project_id, "task_created", f'Task "{obj.title}" was created', org=org)
    if obj.done:
        await log_activity(obj.project_id, "task_completed", f'Task "{obj.title}" was completed', org=org)
    return obj


@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, payload: TaskCreate, org: str = Depends(current_org)):
    res = await db.tasks.find_one({"id": task_id, "organizationId": org}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.project_id:
        await require_project(payload.project_id, org)
    updated = {**res, **payload.model_dump()}
    await db.tasks.update_one({"id": task_id, "organizationId": org}, {"$set": payload.model_dump()})
    if payload.done and not res.get("done"):
        await log_activity(payload.project_id, "task_completed", f'Task "{payload.title}" was completed', org=org)
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
    if payload.project_id:
        await require_project(payload.project_id, org)
    obj = Document(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.documents.insert_one(doc)
    await log_activity(obj.project_id, "document_uploaded", f'Document "{obj.name}" was uploaded', org=org)
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


def _safe_filename(name: str) -> str:
    ascii_name = "".join(c if (c.isalnum() or c in " -_") else "_" for c in (name or "file"))
    return ascii_name.strip().replace(" ", "_")[:60] or "file"


@api_router.get("/documents/{document_id}/file")
async def download_document(document_id: str, request: Request):
    # Authenticated via Bearer header or the httpOnly access_token cookie (no token in URL).
    token = None
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
            p = await db.projects.find_one({"id": it["project_id"], "organizationId": org}, {"_id": 0, "name": 1})
            it["project_name"] = p["name"] if p else None
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


async def _enrich_doc_meta(items, org):
    proj_ids = list({i["project_id"] for i in items if i.get("project_id")})
    cli_ids = list({i.get("client_id") for i in items if i.get("client_id")})
    projs = {p["id"]: p for p in await db.projects.find({"id": {"$in": proj_ids}, "organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    clis = {c["id"]: c for c in await db.clients.find({"id": {"$in": cli_ids}, "organizationId": org}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
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
        "primaryColor": "#16a34a", "secondaryColor": "#22d3ee", "logo": "", "pdfLogo": "",
        "proposalFooter": "", "contractFooter": "", "invoiceFooter": "",
    },
    "ai": {
        "provider": "openai", "proposalTone": "Professional", "contractTone": "Formal",
        "invoiceNotes": "", "temperature": 0.7,
    },
    "documents": {
        "proposalPrefix": "PROP", "contractPrefix": "CTR", "invoicePrefix": "INV",
        "numberingStart": 1, "pdfPageSize": "A4", "pdfAccentColor": "#16a34a",
    },
    "email": {
        "senderName": "", "senderEmail": "", "replyToEmail": "", "companySignature": "",
        "sendingEnabled": False, "dailySendingLimit": 50,
        "approvalRequired": True, "autoSendFromAutomation": False,
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
    allowed = set(DEFAULT_ORG_SETTINGS.get(section, {}).keys())
    clean = {f"settings.{section}.{k}": v for k, v in values.items() if k in allowed}
    if clean:
        clean["updatedAt"] = now_iso()
        await db.organizations.update_one({"id": org}, {"$set": clean})
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0})
    return _merged_settings(org_doc)[section]


@api_router.patch("/settings/organization")
async def update_org_profile(payload: OrgProfileUpdate, org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    name = data.pop("name", None)
    if name is not None and name.strip():
        await db.organizations.update_one({"id": org}, {"$set": {"name": name.strip(), "updatedAt": now_iso()}})
    result = await _update_section(org, "organization", data)
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0})
    result["name"] = org_doc.get("name", "")
    return result


@api_router.patch("/settings/branding")
async def update_branding(payload: SectionUpdate, org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    return await _update_section(org, "branding", payload.values)


@api_router.patch("/settings/ai")
async def update_ai_settings(payload: SectionUpdate, org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    return await _update_section(org, "ai", payload.values)


@api_router.patch("/settings/documents")
async def update_doc_settings(payload: SectionUpdate, org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    return await _update_section(org, "documents", payload.values)


class EmailSettingsUpdate(BaseModel):
    values: dict


@api_router.patch("/settings/email")
async def update_email_settings(payload: EmailSettingsUpdate, org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    """Organization outbound email settings (no provider API keys)."""
    import re as _re
    values = dict(payload.values or {})
    email_re = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    for key in ("senderEmail", "replyToEmail"):
        if key in values and values[key]:
            v = str(values[key]).strip().lower()
            if not email_re.match(v):
                raise HTTPException(status_code=400, detail=f"Invalid {key}")
            values[key] = v
        elif key in values and values[key] == "":
            values[key] = ""
    if "dailySendingLimit" in values:
        try:
            lim = int(values["dailySendingLimit"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="dailySendingLimit must be an integer")
        if lim < 1 or lim > 10000:
            raise HTTPException(status_code=400, detail="dailySendingLimit must be between 1 and 10000")
        values["dailySendingLimit"] = lim
    for bkey in ("sendingEnabled", "approvalRequired", "autoSendFromAutomation"):
        if bkey in values:
            values[bkey] = bool(values[bkey])
    if "senderName" in values:
        values["senderName"] = str(values["senderName"] or "")[:120]
    if "companySignature" in values:
        values["companySignature"] = str(values["companySignature"] or "")[:2000]
    return await _update_section(org, "email", values)


@api_router.patch("/settings/notifications")
async def update_notif_prefs(payload: NotifPrefsUpdate, user: dict = Depends(current_user)):
    filtered = {k: bool(v) for k, v in payload.values.items() if k in DEFAULT_NOTIF_PREFS}
    merged = {**DEFAULT_NOTIF_PREFS, **(user.get("notificationPrefs", {}) or {}), **filtered}
    await db.users.update_one({"id": user["id"]}, {"$set": {"notificationPrefs": merged, "updatedAt": now_iso()}})
    return merged


@api_router.post("/settings/upload-image")
async def upload_branding_image(file: UploadFile = File(...), org: str = Depends(current_org), _admin: dict = Depends(require_admin)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 5MB limit")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    if ext not in {"png", "jpg", "jpeg", "gif", "webp"}:
        raise HTTPException(status_code=415, detail="Only PNG, JPG, GIF or WEBP images are allowed")
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
async def serve_branding_image(asset_id: str, request: Request):
    # Authenticated via Bearer header or the httpOnly access_token cookie (no token in URL).
    token = None
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
async def logout_all(response: Response, user: dict = Depends(current_user)):
    res = await db.sessions.update_many({"userId": user["id"], "revoked": False}, {"$set": {"revoked": True}})
    _clear_auth_cookies(response)
    return {"ok": True, "revoked": res.modified_count}


@api_router.get("/settings/recent-logins")
async def recent_logins(user: dict = Depends(current_user)):
    sessions = await db.sessions.find({"userId": user["id"]}, {"_id": 0, "jti": 0}).sort("createdAt", -1).limit(10).to_list(10)
    return sessions


@api_router.get("/settings/billing")
async def get_billing(user: dict = Depends(current_user)):
    """Usage + seat info. Plan/payment fields stay pending until Stripe is integrated."""
    org = user["organizationId"]
    base = {"organizationId": org}
    from seats import seat_usage
    seats_info = await seat_usage(org)
    usage = {
        "clients": await db.clients.count_documents(base),
        "projects": await db.projects.count_documents(base),
        "documents": await db.documents.count_documents(base),
        "proposals": await db.ai_proposals.count_documents(base),
        "contracts": await db.ai_contracts.count_documents(base),
        "invoices": await db.ai_invoices.count_documents(base),
    }
    ai_usage = None
    try:
        from ai_usage import get_ai_usage
        ai_usage = await get_ai_usage(org)
    except Exception:
        pass
    return {
        "plan": None,
        "price": None,
        "interval": None,
        "status": "pending",
        "billingConfigured": False,
        "message": "Billing is not available during beta.",
        "seats": {
            "used": seats_info["active_members"],
            "pending": seats_info["pending_invitations"],
            "included": None,
        },
        "seatUsage": seats_info,
        "usage": usage,
        "limits": {"projects": None, "documents": None, "ai_generations": None},
        "renews_on": None,
        "aiUsage": ai_usage,
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
    if payload.project_id:
        await require_project(payload.project_id, org)
    obj = Proposal(**payload.model_dump())
    doc = obj.model_dump()
    doc["organizationId"] = org
    await db.proposals.insert_one(doc)
    await log_activity(obj.project_id, "proposal_generated", f'Proposal "{obj.title}" was generated', org=org)
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
    return await db.activities.find({"project_id": project_id, "organizationId": org}, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ------------------- AI Project Planner -------------------
PLAN_SECTIONS = [
    "executive_summary", "business_goal", "technical_requirements", "recommended_plan",
    "milestones", "suggested_tasks", "estimated_timeline", "risks", "next_actions",
]

PLANNER_SYSTEM = (
    "You are an elite AI project planner for Assistify. Given full project context, you produce "
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
    org = project.get("organizationId")
    if not org:
        raise ValueError("project missing organizationId")
    scoped = {"project_id": pid, "organizationId": org}
    tasks = await db.tasks.find(scoped, {"_id": 0}).to_list(1000)
    docs = await db.documents.find(scoped, {"_id": 0}).to_list(1000)
    acts = await db.activities.find(scoped, {"_id": 0}).sort("created_at", 1).to_list(1000)
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
    _t0 = time.perf_counter()

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
    prompt += await build_memory_prompt(org, ["Processes", "Business", "Preferences", "Services"])
    try:
        text = await ai_service.complete(PLANNER_SYSTEM, prompt, session_id=f"planner-{project_id}-{uuid.uuid4()}")
        sections = parse_plan_json(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable plan. Please regenerate.")
    except AIConfigError as e:
        logging.warning("plan generation config: %s", e)
        raise HTTPException(status_code=503, detail=public_ai_error(e, "AI is not configured. Please try again later."))
    except Exception as e:
        logging.exception("plan generation failed")
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Plan generation failed. Please try again."))
    await aia.log_ai_activity(org, "plan", f'Project plan created for {p.get("name")}',
                              f'Assistify analyzed {p.get("name")} and produced a structured delivery plan with phases, milestones and tasks.',
                              "Project Workspace", {"project_id": project_id},
                              gen_ms=int((time.perf_counter() - _t0) * 1000),
                              client_name=p.get("client_name"), project_name=p.get("name"))
    return {"sections": sections, "report": aia.build_ai_report("plan", p, sections)}


@api_router.get("/projects/{project_id}/plans")
async def list_plans(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await db.plans.find({"project_id": project_id, "organizationId": org}, {"_id": 0}).sort("version", -1).to_list(1000)


@api_router.post("/projects/{project_id}/plans", response_model=Plan)
async def save_plan(project_id: str, payload: PlanSave, org: str = Depends(current_org)):
    await require_project(project_id, org)
    version = await db.plans.count_documents({"project_id": project_id, "organizationId": org}) + 1
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


async def _get_ai_proposal(project_id: str, org: str):
    return await db.ai_proposals.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


@api_router.post("/projects/{project_id}/proposal/generate")
async def generate_proposal(project_id: str, org: str = Depends(current_org)):
    p = await require_project(project_id, org)
    await enrich_project(p, org)
    context = await build_project_context(p)

    latest_plan = await db.plans.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0}, sort=[("version", -1)])
    if latest_plan:
        secs = latest_plan.get("sections", {})
        context += "\n\nLATEST AI PROJECT PLAN:\n" + json.dumps(secs)[:4000]

    prompt = build_proposal_prompt(context)
    _t0 = time.perf_counter()
    try:
        content = await ai_service.complete_json(PROPOSAL_SYSTEM, prompt, PROPOSAL_SECTIONS, session_id=f"proposal-{project_id}-{uuid.uuid4()}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable proposal. Please regenerate.")
    except AIConfigError as e:
        logging.warning("proposal generation config: %s", e)
        raise HTTPException(status_code=503, detail=public_ai_error(e, "AI is not configured. Please try again later."))
    except Exception as e:
        logging.exception("proposal generation failed")
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Proposal generation failed. Please try again."))

    await log_activity(project_id, "proposal_generated", f'Proposal for "{p.get("name")}" was generated')
    _cn = f' for {p.get("client_name")}' if p.get("client_name") else ""
    await aia.log_ai_activity(org, "proposal", f'Proposal generated for {p.get("name")}',
                              f'Assistify drafted a full client proposal for {p.get("name")}{_cn}, so you didn\'t have to write it from scratch.',
                              "Project Workspace", {"project_id": project_id},
                              gen_ms=int((time.perf_counter() - _t0) * 1000),
                              client_name=p.get("client_name"), project_name=p.get("name"))
    default_title = f"{p.get('name')} — Proposal"
    return {"title": default_title, "content": content, "report": aia.build_ai_report("proposal", p, content)}


@api_router.get("/projects/{project_id}/proposal")
async def get_proposal(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_proposal(project_id, org)


@api_router.get("/projects/{project_id}/proposal/versions")
async def proposal_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_proposal(project_id, org)
    return doc.get("history", []) if doc else []


@api_router.post("/projects/{project_id}/proposal")
async def save_proposal(project_id: str, payload: ProposalContent, org: str = Depends(current_org), user: dict = Depends(current_user)):
    p = await require_project(project_id, org)
    if payload.status not in PROPOSAL_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    _guard_send(user, payload.status)

    existing = await _get_ai_proposal(project_id, org)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    version_entry = {
        "version": version, "title": payload.title, "status": payload.status,
        "content": payload.content, "created_at": now,
    }
    if existing:
        history = existing.get("history", []) + [version_entry]
        await db.ai_proposals.update_one({"project_id": project_id, "organizationId": org}, {"$set": {
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
    return await _get_ai_proposal(project_id, org)


@api_router.post("/projects/{project_id}/proposal/restore/{version}")
async def restore_proposal(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_proposal(project_id, org)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await save_proposal(project_id, ProposalContent(title=match["title"], status=match["status"], content=match["content"]), org)



@api_router.get("/proposal/sections")
async def proposal_sections(user: dict = Depends(current_user)):
    return {"sections": PROPOSAL_SECTIONS, "statuses": PROPOSAL_STATUSES}


# ------------------- AI Contract Generator -------------------
class ContractContent(BaseModel):
    title: str = "Untitled Contract"
    status: str = "Draft"
    content: dict = Field(default_factory=dict)


async def _get_ai_contract(project_id: str, org: str):
    return await db.ai_contracts.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


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

    proposal = await _get_ai_proposal(project_id, org)
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

    latest_plan = await db.plans.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0}, sort=[("version", -1)])
    if latest_plan:
        context += "\n\nLATEST AI PROJECT PLAN:\n" + json.dumps(latest_plan.get("sections", {}))[:3000]

    return p, context, proposal_id


@api_router.post("/projects/{project_id}/contract/generate")
async def generate_contract(project_id: str, org: str = Depends(current_org)):
    p, context, proposal_id = await _build_contract_context(project_id, org)
    prompt = build_contract_prompt(context)
    prompt += await build_memory_prompt(org, ["Policies", "Contract Style", "Business", "Preferences", "Brand Voice"])
    _t0 = time.perf_counter()
    try:
        content = await ai_service.complete_json(CONTRACT_SYSTEM, prompt, CONTRACT_SECTIONS, session_id=f"contract-{project_id}-{uuid.uuid4()}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable contract. Please regenerate.")
    except AIConfigError as e:
        logging.warning("contract generation config: %s", e)
        raise HTTPException(status_code=503, detail=public_ai_error(e, "AI is not configured. Please try again later."))
    except Exception as e:
        logging.exception("contract generation failed")
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Contract generation failed. Please try again."))

    await log_activity(project_id, "contract_generated", f'Service agreement for "{p.get("name")}" was generated')
    _cn = f' with {p.get("client_name")}' if p.get("client_name") else ""
    await aia.log_ai_activity(org, "contract", f'Contract drafted for {p.get("name")}',
                              f'Assistify prepared a service agreement{_cn} with standard protective clauses ready for review.',
                              "Project Workspace", {"project_id": project_id},
                              gen_ms=int((time.perf_counter() - _t0) * 1000),
                              client_name=p.get("client_name"), project_name=p.get("name"))
    return {"title": f"{p.get('name')} — Service Agreement", "content": content, "proposal_id": proposal_id, "report": aia.build_ai_report("contract", p, content)}


@api_router.get("/projects/{project_id}/contract")
async def get_contract(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_contract(project_id, org)


@api_router.get("/projects/{project_id}/contract/versions")
async def contract_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_contract(project_id, org)
    return doc.get("history", []) if doc else []


async def _save_contract(project_id: str, payload: ContractContent, org: str, activity_type: str, activity_msg_fmt: str):
    p = await require_project(project_id, org)
    if payload.status not in CONTRACT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    existing = await _get_ai_contract(project_id, org)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    entry = {"version": version, "title": payload.title, "status": payload.status, "content": payload.content, "created_at": now}
    if existing:
        history = existing.get("history", []) + [entry]
        await db.ai_contracts.update_one({"project_id": project_id, "organizationId": org}, {"$set": {
            "title": payload.title, "status": payload.status, "content": payload.content,
            "version": version, "history": history, "updated_at": now,
        }})
    else:
        proposal = await _get_ai_proposal(project_id, org)
        doc = {
            "id": str(uuid.uuid4()), "title": payload.title, "project_id": project_id,
            "organizationId": org, "client_id": p.get("client_id"),
            "proposal_id": proposal.get("id") if proposal else None,
            "status": payload.status, "content": payload.content, "version": version,
            "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_contracts.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg_fmt.format(version=version))
    return await _get_ai_contract(project_id, org)


@api_router.post("/projects/{project_id}/contract")
async def save_contract(project_id: str, payload: ContractContent, org: str = Depends(current_org), user: dict = Depends(current_user)):
    _guard_send(user, payload.status)
    return await _save_contract(project_id, payload, org, "contract_saved", "Contract v{version} was saved")


@api_router.post("/projects/{project_id}/contract/restore/{version}")
async def restore_contract(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_contract(project_id, org)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    return await _save_contract(
        project_id, ContractContent(title=match["title"], status=match["status"], content=match["content"]),
        org, "contract_restored", f"Contract restored from v{version} as v{{version}}",
    )



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


async def _get_ai_invoice(project_id: str, org: str):
    return await db.ai_invoices.find_one({"project_id": project_id, "organizationId": org}, {"_id": 0})


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
    contract = await _get_ai_contract(project_id, org)
    if contract:
        context += "\n\nSIGNED/DRAFT CONTRACT PAYMENT TERMS:\n" + json.dumps(contract.get("content", {}).get("payment_terms", []))

    prompt = build_invoice_prompt(context)
    prompt += await build_memory_prompt(org, ["Pricing", "Business", "Preferences", "Policies"])
    _t0 = time.perf_counter()
    try:
        raw = await ai_service.complete(INVOICE_SYSTEM, prompt, session_id=f"invoice-{project_id}-{uuid.uuid4()}")
        data = extract_json(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned an unparseable invoice. Please regenerate.")
    except AIConfigError as e:
        logging.warning("invoice generation config: %s", e)
        raise HTTPException(status_code=503, detail=public_ai_error(e, "AI is not configured. Please try again later."))
    except Exception as e:
        logging.exception("invoice generation failed")
        raise HTTPException(status_code=502, detail=public_ai_error(e, "Invoice generation failed. Please try again."))

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
    await aia.log_ai_activity(org, "invoice", f'Invoice prepared for {p.get("name")}',
                              f'Assistify built an invoice for {p.get("name")} with line items, VAT and totals calculated automatically.',
                              "Project Workspace", {"project_id": project_id},
                              gen_ms=int((time.perf_counter() - _t0) * 1000),
                              client_name=p.get("client_name"), project_name=p.get("name"))
    return {
        "invoice_number": await _next_invoice_number(org), "title": f"{p.get('name')} — Invoice",
        "content": content, "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
        "proposal_id": proposal_id, "contract_id": contract.get("id") if contract else None,
        "report": aia.build_ai_report("invoice", p, content),
    }


@api_router.get("/projects/{project_id}/invoice")
async def get_invoice(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    return await _get_ai_invoice(project_id, org)


@api_router.get("/projects/{project_id}/invoice/versions")
async def invoice_versions(project_id: str, org: str = Depends(current_org)):
    await require_project(project_id, org)
    doc = await _get_ai_invoice(project_id, org)
    return doc.get("history", []) if doc else []


async def _save_invoice(project_id: str, payload: InvoiceSave, org: str, activity_type: str, activity_msg: str):
    p = await require_project(project_id, org)
    if payload.status not in INVOICE_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")

    vat_rate = float(payload.content.get("vat_rate", 0) or 0)
    items, subtotal, vat_amount, total = _compute_invoice(payload.line_items, vat_rate)
    content = {**payload.content, "vat_rate": vat_rate}

    existing = await _get_ai_invoice(project_id, org)
    version = (existing["version"] + 1) if existing else 1
    now = now_iso()
    inv_number = payload.invoice_number or (existing["invoice_number"] if existing else await _next_invoice_number(org))
    entry = {
        "version": version, "invoice_number": inv_number, "title": payload.title, "status": payload.status,
        "content": content, "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total, "created_at": now,
    }
    if existing:
        history = existing.get("history", []) + [entry]
        await db.ai_invoices.update_one({"project_id": project_id, "organizationId": org}, {"$set": {
            "invoice_number": inv_number, "title": payload.title, "status": payload.status, "content": content,
            "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
            "version": version, "history": history, "updated_at": now,
        }})
    else:
        proposal = await _get_ai_proposal(project_id, org)
        contract = await _get_ai_contract(project_id, org)
        doc = {
            "id": str(uuid.uuid4()), "invoice_number": inv_number, "title": payload.title, "project_id": project_id,
            "organizationId": org, "client_id": p.get("client_id"), "proposal_id": proposal.get("id") if proposal else None,
            "contract_id": contract.get("id") if contract else None, "status": payload.status, "content": content,
            "line_items": items, "subtotal": subtotal, "vat": vat_amount, "total": total,
            "version": version, "history": [entry], "created_at": now, "updated_at": now,
        }
        await db.ai_invoices.insert_one(doc)
    await log_activity(project_id, activity_type, activity_msg.format(version=version, number=inv_number))
    return await _get_ai_invoice(project_id, org)


@api_router.post("/projects/{project_id}/invoice")
async def save_invoice(project_id: str, payload: InvoiceSave, org: str = Depends(current_org), user: dict = Depends(current_user)):
    _guard_send(user, payload.status)
    return await _save_invoice(project_id, payload, org, "invoice_saved", "Invoice {number} v{version} was saved")


@api_router.post("/projects/{project_id}/invoice/restore/{version}")
async def restore_invoice(project_id: str, version: int, org: str = Depends(current_org)):
    await require_project(project_id, org)
    existing = await _get_ai_invoice(project_id, org)
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    match = next((v for v in existing.get("history", []) if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail="Version not found")
    payload = InvoiceSave(invoice_number=match["invoice_number"], title=match["title"],
                          status=match["status"], content=match["content"], line_items=match["line_items"])
    return await _save_invoice(project_id, payload, org, "invoice_restored", "Invoice restored from v" + str(version) + " as v{version}")



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
app.include_router(copilot_router)
app.include_router(exports_router)
app.include_router(ai_router)
app.include_router(assistant_router)
app.include_router(opportunities_router)
app.include_router(crm_router)
app.include_router(memory_router)
app.include_router(automation_router)
app.include_router(onboarding_router)
app.include_router(dashboard_exec_router)
app.include_router(team_router)
app.include_router(emails_router)
app.include_router(webhooks_router)
app.include_router(integrations_router)
app.include_router(inbox_router)
app.include_router(health_router)
app.include_router(ops_router)
app.include_router(feedback_router)

def _cors_origins() -> List[str]:
    try:
        return get_app_settings().cors_origins
    except Exception:
        raw = os.environ.get("CORS_ORIGINS", "*")
        return ["*"] if raw.strip() == "*" else [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

from csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# Optional host allow-list (set TRUSTED_HOSTS in production behind a known domain)
try:
    _th = get_app_settings().trusted_hosts
    if _th:
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=_th)
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
try:
    cfg0 = get_app_settings()
    configure_logging(cfg0.log_level, json_logs=cfg0.json_logs)
    if cfg0.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(
                dsn=cfg0.sentry_dsn,
                environment=cfg0.environment,
                release=cfg0.release_version,
                integrations=[FastApiIntegration()],
                send_default_pii=False,
            )
        except Exception as e:
            logging.getLogger(__name__).warning("Sentry init skipped: %s", e)
except Exception:
    pass
logger = logging.getLogger(__name__)


SCOPED_COLLECTIONS = [
    "clients", "projects", "tasks", "documents", "proposals", "activities",
    "plans", "ai_proposals", "ai_contracts", "ai_invoices", "chat_messages",
]


@app.on_event("startup")
async def startup():
    cfg = get_app_settings()
    logger.info(
        "Starting Assistify (%s) storage=%s ai=%s cookie_secure=%s samesite=%s",
        cfg.environment, cfg.storage_provider, cfg.ai_provider, cfg.cookie_secure, cfg.cookie_samesite,
    )
    try:
        await asyncio.to_thread(S.init_storage)
        logger.info("Object storage initialized (%s)", cfg.storage_provider)
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    from indexes import ensure_indexes
    idx = await ensure_indexes(db)
    if not idx.get("ok"):
        logger.error("Index initialization reported errors: %s", idx.get("errors"))

    # Import job handlers for registration
    try:
        import jobs.handlers  # noqa: F401
    except Exception as e:
        logger.warning("Job handlers import failed: %s", e)

    logger.info(
        "Email provider=%s sending_enabled=%s",
        cfg.email_provider, cfg.email_sending_enabled,
    )
    # Demo account seeding is OPT-IN via ENABLE_DEMO_SEED=true (never automatic in production).
    org_id = None
    if cfg.enable_demo_seed:
        demo_email = cfg.demo_email
        demo_password = cfg.demo_password
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
            # Only sync demo password when seeding is explicitly enabled
            if not A.verify_password(demo_password, demo["passwordHash"]):
                await db.users.update_one({"email": demo_email}, {"$set": {"passwordHash": A.hash_password(demo_password)}})
                logger.info("[SEED] Synced demo account password from DEMO_PASSWORD")

        # Backfill any legacy documents that lack organizationId (only when demo seed is on)
        for coll in SCOPED_COLLECTIONS:
            res = await db[coll].update_many({"organizationId": {"$exists": False}}, {"$set": {"organizationId": org_id}})
            if res.modified_count:
                logger.info(f"[BACKFILL] {coll}: {res.modified_count} docs -> org {org_id}")
    else:
        logger.info("[SEED] Demo seed disabled (set ENABLE_DEMO_SEED=true to enable)")

    # Existing users (pre-onboarding sprint) should not see the wizard
    await db.users.update_many({"onboardingCompleted": {"$exists": False}}, {"$set": {"onboardingCompleted": True}})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
