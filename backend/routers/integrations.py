"""Universal Integrations Hub API.

Routes (organization-scoped; admin for connect/disconnect/refresh):
  GET  /api/integrations
  GET  /api/integrations/status
  POST /api/integrations/connect
  POST /api/integrations/disconnect
  POST /api/integrations/refresh
  POST /api/integrations/health
  GET  /api/integrations/oauth/callback/{provider}
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from audit import write_audit
from config import get_settings
from core import db, now_iso
from dependencies import current_user, current_org
from integrations.base import PROVIDER_CATALOG
from integrations import store
from integrations.crypto import public_safe
from integrations.providers import get_provider, new_oauth_state
from permissions import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations")

HTTPS_RE = re.compile(r"^https://", re.I)


def _redirect_uri(provider: str, request: Request = None) -> str:
    s = get_settings()
    explicit = {
        "google": s.google_redirect_uri,
        "microsoft": s.microsoft_redirect_uri,
        "slack": s.slack_redirect_uri,
    }.get(provider)
    if explicit:
        return explicit.rstrip("/")
    # Prefer API_URL (canonical API origin), then request base, never the SPA origin.
    api_base = (getattr(s, "api_url", None) or "").rstrip("/")
    if api_base:
        return f"{api_base}/api/integrations/oauth/callback/{provider}"
    if request is not None:
        return str(request.base_url).rstrip("/") + f"/api/integrations/oauth/callback/{provider}"
    # Last resort — still API-shaped path (operators should set API_URL / *_REDIRECT_URI)
    return f"/api/integrations/oauth/callback/{provider}"


class ConnectBody(BaseModel):
    provider: str
    # Webhook-style
    webhookUrl: Optional[str] = None
    signingSecret: Optional[str] = None
    channel: Optional[str] = None
    displayName: Optional[str] = None
    services: Optional[List[str]] = None
    # Prefer OAuth when available
    useOauth: bool = True


class ProviderRef(BaseModel):
    provider: str
    integrationId: Optional[str] = None


@router.get("")
async def list_integrations(org: str = Depends(current_org), user: dict = Depends(current_user)):
    items = await store.list_integrations(org)
    catalog = [
        {
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "authType": m.auth_type,
            "services": m.services,
            "permissions": m.permissions,
            "description": m.description,
            "oauthConfigurable": m.oauth_configurable,
            "oauthReady": _oauth_ready(m.id),
        }
        for m in PROVIDER_CATALOG.values()
    ]
    return {"items": items, "catalog": catalog}


def _oauth_ready(provider: str) -> bool:
    try:
        p = get_provider(provider)
        if provider == "slack":
            return bool(getattr(p, "oauth_ready", lambda: False)())
        if provider in ("google", "microsoft"):
            return p.is_configured()
    except Exception:
        return False
    return False


@router.get("/status")
async def integrations_status(org: str = Depends(current_org), user: dict = Depends(current_user)):
    items = await store.list_integrations(org)
    connected = [i for i in items if i.get("status") == "connected"]
    errors = [i for i in items if i.get("status") == "error"]
    by_provider = {i["provider"]: i for i in items}

    def _readiness(provider: str) -> str:
        """configured | not_configured | reconnect_required | connected"""
        oauth = _oauth_ready(provider)
        doc = by_provider.get(provider)
        if doc and doc.get("status") == "error":
            return "reconnect_required"
        if doc and doc.get("status") == "connected":
            if (doc.get("healthStatus") or "") in ("error", "unhealthy", "expired"):
                return "reconnect_required"
            return "connected"
        if provider in ("google", "microsoft", "slack"):
            return "configured" if oauth else "not_configured"
        return "configured" if doc else "not_configured"

    return {
        "connectedCount": len(connected),
        "errorCount": len(errors),
        "providers": {
            i["provider"]: {
                "status": i.get("status"),
                "healthStatus": i.get("healthStatus"),
                "lastSyncAt": i.get("lastSyncAt"),
                "accountEmail": i.get("accountEmail"),
                "permissions": i.get("permissions") or [],
                "readiness": _readiness(i["provider"]),
            }
            for i in items
        },
        "oauthReadiness": {
            "google": _readiness("google"),
            "microsoft": _readiness("microsoft"),
            "slack": _readiness("slack"),
        },
        "redirectUriTemplates": {
            "google": _redirect_uri("google"),
            "microsoft": _redirect_uri("microsoft"),
            "slack": _redirect_uri("slack"),
        },
    }


@router.post("/connect")
async def connect_integration(
    payload: ConnectBody,
    request: Request,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    provider = (payload.provider or "").strip().lower()
    if provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    meta = PROVIDER_CATALOG[provider]
    impl = get_provider(provider)

    # --- Webhook / Discord / Zapier / Slack-via-webhook ---
    if payload.webhookUrl:
        url = payload.webhookUrl.strip()
        if not HTTPS_RE.match(url):
            raise HTTPException(status_code=400, detail="webhookUrl must be an HTTPS URL")
        if provider in ("google", "microsoft") and payload.useOauth:
            raise HTTPException(status_code=400, detail=f"{meta.name} requires OAuth, not a webhook URL")
        creds = {"webhook_url": url}
        if payload.signingSecret:
            creds["signing_secret"] = payload.signingSecret
        config = {}
        if payload.channel:
            config["channel"] = payload.channel
        if payload.displayName:
            config["displayName"] = payload.displayName
        doc = await store.upsert_connection(
            org_id=org, provider=provider, user=user,
            credentials=creds,
            account_name=payload.displayName or meta.name,
            permissions=list(meta.permissions),
            services=payload.services or meta.services,
            config=config,
        )
        # Health check
        health = await impl.health_check(creds, config)
        await store.update_health(org, doc["id"], health["ok"], health["message"])
        doc = public_safe(await store.get_by_id(org, doc["id"]))
        await write_audit(
            org, "integration_connected",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"provider": provider, "via": "webhook"},
        )
        return {"ok": True, "mode": "webhook", "integration": doc}

    # --- OAuth ---
    if meta.auth_type in ("oauth", "mixed") and payload.useOauth:
        if provider == "slack" and not getattr(impl, "oauth_ready", lambda: False)():
            raise HTTPException(
                status_code=503,
                detail="Slack OAuth is not configured. Provide an Incoming Webhook URL, or set SLACK_CLIENT_ID/SECRET.",
            )
        if provider in ("google", "microsoft") and not impl.is_configured():
            raise HTTPException(
                status_code=503,
                detail=f"{meta.name} OAuth is not configured on the server. Set client id/secret env vars.",
            )
        if provider in ("discord", "zapier", "webhook"):
            raise HTTPException(status_code=400, detail=f"Connect {meta.name} with a webhookUrl")

        state = new_oauth_state()
        redirect_uri = _redirect_uri(provider, request)
        await db.integration_oauth_states.insert_one({
            "state": state,
            "organizationId": org,
            "provider": provider,
            "userId": user["id"],
            "redirectUri": redirect_uri,
            "services": payload.services or meta.services,
            "createdAt": now_iso(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        })
        auth_url = await impl.build_auth_url(state, redirect_uri)
        await write_audit(
            org, "integration_connect_started",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"provider": provider},
        )
        return {"ok": True, "mode": "oauth", "authUrl": auth_url, "state": state, "provider": provider}

    raise HTTPException(status_code=400, detail="Provide webhookUrl or enable OAuth for this provider")


@router.get("/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    settings = get_settings()
    front = settings.frontend_url.rstrip("/")
    provider = provider.lower()
    if error:
        return RedirectResponse(f"{front}/integrations?error={error}&provider={provider}")
    if not code or not state:
        return RedirectResponse(f"{front}/integrations?error=missing_code&provider={provider}")

    st = await db.integration_oauth_states.find_one({"state": state, "provider": provider})
    if not st:
        return RedirectResponse(f"{front}/integrations?error=invalid_state&provider={provider}")
    # Single-use state
    await db.integration_oauth_states.delete_one({"state": state})
    try:
        exp = datetime.fromisoformat(st["expiresAt"].replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return RedirectResponse(f"{front}/integrations?error=state_expired&provider={provider}")
    except Exception:
        pass

    org = st["organizationId"]
    user = await db.users.find_one({"id": st["userId"]}, {"_id": 0}) or {"id": st["userId"]}
    impl = get_provider(provider)
    redirect_uri = st.get("redirectUri") or _redirect_uri(provider, request)
    try:
        result = await impl.exchange_code(code, redirect_uri)
        doc = await store.upsert_connection(
            org_id=org,
            provider=provider,
            user=user,
            credentials=result["credentials"],
            account_email=result.get("accountEmail") or "",
            account_name=result.get("accountName") or "",
            permissions=result.get("permissions"),
            services=st.get("services"),
            config=result.get("config") or {},
        )
        await write_audit(
            org, "integration_connected",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"provider": provider, "via": "oauth"},
        )
        return RedirectResponse(f"{front}/integrations?connected={provider}&id={doc.get('id') or ''}")
    except Exception as e:
        logger.exception("OAuth callback failed for %s", provider)
        await write_audit(
            org, "integration_connect_failed",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"provider": provider, "error": str(e)[:200]},
        )
        return RedirectResponse(f"{front}/integrations?error=oauth_failed&provider={provider}")


@router.post("/disconnect")
async def disconnect_integration(
    payload: ProviderRef,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    provider = (payload.provider or "").strip().lower()
    if provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail="Unknown provider")
    doc = await store.mark_disconnected(org, provider)
    if not doc:
        raise HTTPException(status_code=404, detail="Integration not found")
    await write_audit(
        org, "integration_disconnected",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"provider": provider},
    )
    return {"ok": True, "integration": doc}


@router.post("/refresh")
async def refresh_integration(
    payload: ProviderRef,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    provider = (payload.provider or "").strip().lower()
    doc = await store.get_by_provider(org, provider)
    if not doc or not doc.get("encryptedCredentials"):
        raise HTTPException(status_code=404, detail="Integration not connected")
    if doc.get("status") == "disconnected":
        raise HTTPException(status_code=400, detail="Integration is disconnected")
    impl = get_provider(provider)
    try:
        creds = await store.load_credentials(doc)
        updated = await impl.refresh(creds)
        await store.save_credentials(
            org, doc["id"], updated,
            status="connected", healthStatus="healthy", healthMessage="Token refreshed",
            lastSyncAt=now_iso(), error=None,
        )
        await write_audit(
            org, "integration_refreshed",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"provider": provider},
        )
        return {"ok": True, "integration": public_safe(await store.get_by_id(org, doc["id"]))}
    except Exception as e:
        await store.update_health(org, doc["id"], False, str(e)[:500])
        raise HTTPException(status_code=400, detail=f"Refresh failed: {e}") from e


@router.post("/health")
async def health_check(
    payload: ProviderRef,
    org: str = Depends(current_org),
    user: dict = Depends(current_user),
):
    provider = (payload.provider or "").strip().lower()
    doc = await store.get_by_provider(org, provider)
    if not doc or doc.get("status") == "disconnected" or not doc.get("encryptedCredentials"):
        raise HTTPException(status_code=404, detail="Integration not connected")
    impl = get_provider(provider)
    try:
        creds = await store.load_credentials(doc)
        # Attempt refresh on OAuth providers if health fails
        result = await impl.health_check(creds, doc.get("config") or {})
        if not result["ok"] and provider in ("google", "microsoft") and creds.get("refresh_token"):
            try:
                creds = await impl.refresh(creds)
                await store.save_credentials(org, doc["id"], creds)
                result = await impl.health_check(creds, doc.get("config") or {})
            except Exception as e:
                result = {"ok": False, "message": str(e)[:500]}
        await store.update_health(org, doc["id"], result["ok"], result["message"])
        return {
            "ok": result["ok"],
            "message": result["message"],
            "integration": public_safe(await store.get_by_id(org, doc["id"])),
        }
    except Exception as e:
        await store.update_health(org, doc["id"], False, str(e)[:500])
        raise HTTPException(status_code=400, detail=str(e)) from e
