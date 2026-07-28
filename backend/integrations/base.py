"""Integration provider catalog and base protocol."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class ProviderMeta:
    id: str
    name: str
    category: str  # google_workspace | microsoft_365 | communication | automation
    auth_type: str  # oauth | webhook | mixed
    services: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    description: str = ""
    oauth_configurable: bool = False


# Cards on the Integrations page map 1:1 to these provider ids.
PROVIDER_CATALOG: Dict[str, ProviderMeta] = {
    "google": ProviderMeta(
        id="google",
        name="Google Workspace",
        category="google_workspace",
        auth_type="oauth",
        services=["gmail", "calendar", "tasks"],
        permissions=[
            "gmail.readonly",
            "gmail.send",
            "calendar.events",
            "tasks",
        ],
        description="Gmail inbox sync, send, Google Calendar, and Google Tasks.",
        oauth_configurable=True,
    ),
    "microsoft": ProviderMeta(
        id="microsoft",
        name="Microsoft 365",
        category="microsoft_365",
        auth_type="oauth",
        services=["outlook", "calendar"],
        permissions=[
            "Mail.Read",
            "Mail.Send",
            "Calendars.ReadWrite",
            "offline_access",
        ],
        description="Outlook inbox sync, mail send, and Microsoft Calendar.",
        oauth_configurable=True,
    ),
    "slack": ProviderMeta(
        id="slack",
        name="Slack",
        category="communication",
        auth_type="mixed",
        services=["messaging"],
        permissions=["chat:write", "channels:read"],
        description="Send messages to Slack channels via OAuth or Incoming Webhook.",
        oauth_configurable=True,
    ),
    "discord": ProviderMeta(
        id="discord",
        name="Discord",
        category="communication",
        auth_type="webhook",
        services=["messaging"],
        permissions=["webhook.execute"],
        description="Send messages via a Discord Incoming Webhook URL.",
        oauth_configurable=False,
    ),
    "zapier": ProviderMeta(
        id="zapier",
        name="Zapier",
        category="automation",
        auth_type="webhook",
        services=["webhooks"],
        permissions=["webhook.trigger"],
        description="Trigger Zapier Catch Hooks from Assistify automations.",
        oauth_configurable=False,
    ),
    "webhook": ProviderMeta(
        id="webhook",
        name="Webhook",
        category="automation",
        auth_type="webhook",
        services=["rest"],
        permissions=["http.request"],
        description="Generic REST webhook (POST JSON) to any HTTPS endpoint.",
        oauth_configurable=False,
    ),
}


class IntegrationProvider(Protocol):
    provider_id: str

    def is_configured(self) -> bool:
        """True when env credentials allow OAuth (or webhook needs none)."""
        ...

    async def build_auth_url(self, state: str, redirect_uri: str) -> str:
        ...

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Return credentials dict to encrypt + account metadata."""
        ...

    async def refresh(self, credentials: dict) -> dict:
        """Return updated credentials dict."""
        ...

    async def health_check(self, credentials: dict, config: dict) -> dict:
        """Return {ok: bool, message: str}."""
        ...
