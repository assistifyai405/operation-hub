"""Provider implementations (Google, Microsoft, Slack, Discord, Zapier, Webhook)."""
from __future__ import annotations

import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import get_settings
from integrations.base import PROVIDER_CATALOG

logger = logging.getLogger(__name__)


# ---------------- Google ----------------
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]


class GoogleProvider:
    provider_id = "google"

    def is_configured(self) -> bool:
        import os
        s = get_settings()
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        if cid is None:
            cid = s.google_client_id
        csec = os.environ.get("GOOGLE_CLIENT_SECRET")
        if csec is None:
            csec = s.google_client_secret
        return bool((cid or "").strip() and (csec or "").strip())

    async def build_auth_url(self, state: str, redirect_uri: str) -> str:
        s = get_settings()
        params = {
            "client_id": s.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(GOOGLE_TOKEN, data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            r.raise_for_status()
            tokens = r.json()
            access = tokens.get("access_token")
            info = {}
            if access:
                ui = await client.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access}"})
                if ui.status_code == 200:
                    info = ui.json()
        return {
            "credentials": {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "token_type": tokens.get("token_type", "Bearer"),
                "scope": tokens.get("scope"),
            },
            "accountEmail": info.get("email") or "",
            "accountName": info.get("name") or "",
            "permissions": list(PROVIDER_CATALOG["google"].permissions),
        }

    async def refresh(self, credentials: dict) -> dict:
        s = get_settings()
        refresh = credentials.get("refresh_token")
        if not refresh:
            raise ValueError("No refresh token available — reconnect Google")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(GOOGLE_TOKEN, data={
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            })
            r.raise_for_status()
            data = r.json()
        credentials = dict(credentials)
        credentials["access_token"] = data.get("access_token")
        credentials["expires_in"] = data.get("expires_in")
        if data.get("refresh_token"):
            credentials["refresh_token"] = data["refresh_token"]
        return credentials

    async def health_check(self, credentials: dict, config: dict) -> dict:
        token = credentials.get("access_token")
        if not token:
            return {"ok": False, "message": "Missing access token"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 401:
                return {"ok": False, "message": "Token expired — refresh required"}
            if r.status_code >= 400:
                return {"ok": False, "message": f"Google API error ({r.status_code})"}
        return {"ok": True, "message": "Google Workspace healthy"}


# ---------------- Microsoft ----------------
class MicrosoftProvider:
    provider_id = "microsoft"

    def _tenant(self) -> str:
        return get_settings().microsoft_tenant or "common"

    def is_configured(self) -> bool:
        import os
        s = get_settings()
        cid = os.environ.get("MICROSOFT_CLIENT_ID")
        if cid is None:
            cid = s.microsoft_client_id
        csec = os.environ.get("MICROSOFT_CLIENT_SECRET")
        if csec is None:
            csec = s.microsoft_client_secret
        return bool((cid or "").strip() and (csec or "").strip())

    async def build_auth_url(self, state: str, redirect_uri: str) -> str:
        s = get_settings()
        scopes = " ".join([
            "openid", "email", "profile", "offline_access",
            "Mail.Read", "Mail.Send", "Calendars.ReadWrite", "User.Read",
        ])
        params = {
            "client_id": s.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": scopes,
            "state": state,
        }
        return f"https://login.microsoftonline.com/{self._tenant()}/oauth2/v2.0/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"https://login.microsoftonline.com/{self._tenant()}/oauth2/v2.0/token",
                data={
                    "client_id": s.microsoft_client_id,
                    "client_secret": s.microsoft_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            r.raise_for_status()
            tokens = r.json()
            access = tokens.get("access_token")
            info = {}
            if access:
                ui = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access}"},
                )
                if ui.status_code == 200:
                    info = ui.json()
        return {
            "credentials": {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "token_type": tokens.get("token_type", "Bearer"),
                "scope": tokens.get("scope"),
            },
            "accountEmail": info.get("mail") or info.get("userPrincipalName") or "",
            "accountName": info.get("displayName") or "",
            "permissions": list(PROVIDER_CATALOG["microsoft"].permissions),
        }

    async def refresh(self, credentials: dict) -> dict:
        s = get_settings()
        refresh = credentials.get("refresh_token")
        if not refresh:
            raise ValueError("No refresh token — reconnect Microsoft 365")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"https://login.microsoftonline.com/{self._tenant()}/oauth2/v2.0/token",
                data={
                    "client_id": s.microsoft_client_id,
                    "client_secret": s.microsoft_client_secret,
                    "refresh_token": refresh,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            data = r.json()
        credentials = dict(credentials)
        credentials["access_token"] = data.get("access_token")
        credentials["expires_in"] = data.get("expires_in")
        if data.get("refresh_token"):
            credentials["refresh_token"] = data["refresh_token"]
        return credentials

    async def health_check(self, credentials: dict, config: dict) -> dict:
        token = credentials.get("access_token")
        if not token:
            return {"ok": False, "message": "Missing access token"}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 401:
                return {"ok": False, "message": "Token expired — refresh required"}
            if r.status_code >= 400:
                return {"ok": False, "message": f"Microsoft Graph error ({r.status_code})"}
        return {"ok": True, "message": "Microsoft 365 healthy"}


# ---------------- Slack ----------------
class SlackProvider:
    provider_id = "slack"

    def is_configured(self) -> bool:
        s = get_settings()
        # OAuth optional — webhook URL connect always available
        return True

    def oauth_ready(self) -> bool:
        s = get_settings()
        return bool(s.slack_client_id and s.slack_client_secret)

    async def build_auth_url(self, state: str, redirect_uri: str) -> str:
        s = get_settings()
        if not self.oauth_ready():
            raise ValueError("Slack OAuth is not configured (SLACK_CLIENT_ID/SECRET)")
        params = {
            "client_id": s.slack_client_id,
            "scope": "chat:write,channels:read,incoming-webhook",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        s = get_settings()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://slack.com/api/oauth.v2.access", data={
                "client_id": s.slack_client_id,
                "client_secret": s.slack_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            })
            r.raise_for_status()
            data = r.json()
        if not data.get("ok"):
            raise ValueError(data.get("error") or "Slack OAuth failed")
        incoming = (data.get("incoming_webhook") or {})
        return {
            "credentials": {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "token_type": data.get("token_type"),
                "webhook_url": incoming.get("url"),
            },
            "accountEmail": "",
            "accountName": (data.get("team") or {}).get("name") or "",
            "permissions": list(PROVIDER_CATALOG["slack"].permissions),
            "config": {"channel": incoming.get("channel") or "", "teamId": (data.get("team") or {}).get("id")},
        }

    async def refresh(self, credentials: dict) -> dict:
        # Slack user tokens often don't rotate; return as-is if no refresh token
        if not credentials.get("refresh_token"):
            return credentials
        return credentials

    async def health_check(self, credentials: dict, config: dict) -> dict:
        token = credentials.get("access_token")
        webhook = credentials.get("webhook_url") or config.get("webhookUrl")
        if token:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = r.json() if r.status_code == 200 else {}
                if data.get("ok"):
                    return {"ok": True, "message": f"Slack OK ({data.get('team', 'workspace')})"}
                return {"ok": False, "message": data.get("error") or "Slack auth.test failed"}
        if webhook:
            return {"ok": True, "message": "Slack Incoming Webhook configured"}
        return {"ok": False, "message": "No Slack credentials"}


# ---------------- Discord / Zapier / Webhook ----------------
class WebhookStyleProvider:
    def __init__(self, provider_id: str):
        self.provider_id = provider_id

    def is_configured(self) -> bool:
        return True

    async def build_auth_url(self, state: str, redirect_uri: str) -> str:
        raise ValueError(f"{self.provider_id} uses webhook URL connection, not OAuth")

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        raise ValueError("Not an OAuth provider")

    async def refresh(self, credentials: dict) -> dict:
        return credentials

    async def health_check(self, credentials: dict, config: dict) -> dict:
        url = credentials.get("webhook_url") or config.get("webhookUrl")
        if not url:
            return {"ok": False, "message": "Webhook URL missing"}
        if not str(url).lower().startswith("https://"):
            return {"ok": False, "message": "Webhook URL must use HTTPS"}
        # Lightweight HEAD/GET — some webhooks reject; treat reachable TLS as healthy
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.request("HEAD", url)
                # Many webhook endpoints reject HEAD — still OK if connection works
                if r.status_code < 500:
                    return {"ok": True, "message": "Webhook endpoint reachable"}
                return {"ok": False, "message": f"Endpoint returned {r.status_code}"}
        except httpx.HTTPError as e:
            return {"ok": False, "message": f"Unreachable: {type(e).__name__}"}


PROVIDERS = {
    "google": GoogleProvider(),
    "microsoft": MicrosoftProvider(),
    "slack": SlackProvider(),
    "discord": WebhookStyleProvider("discord"),
    "zapier": WebhookStyleProvider("zapier"),
    "webhook": WebhookStyleProvider("webhook"),
}


def get_provider(provider_id: str):
    p = PROVIDERS.get(provider_id)
    if not p:
        raise KeyError(provider_id)
    return p


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
