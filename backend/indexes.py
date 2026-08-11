"""Central MongoDB index initialization (idempotent, never drops indexes)."""
from __future__ import annotations

import logging
from typing import Any, Callable, List, Tuple

logger = logging.getLogger(__name__)


async def ensure_indexes(db) -> dict:
    """Create required indexes. Returns summary; raises on hard failures."""
    created = 0
    errors: List[str] = []

    async def _one(label: str, coro):
        nonlocal created
        try:
            await coro
            created += 1
        except Exception as e:
            msg = f"{label}: {e}"
            errors.append(msg)
            logger.error("Index init failed — %s", msg)

    specs: List[Tuple[str, Any]] = [
        ("users.email", db.users.create_index("email", unique=True)),
        ("users.org_role", db.users.create_index([("organizationId", 1), ("role", 1)])),
        ("users.org_id", db.users.create_index([("organizationId", 1), ("id", 1)])),
        ("sessions.jti", db.sessions.create_index("jti")),
        ("sessions.userId", db.sessions.create_index("userId")),
        ("password_reset.ttl", db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)),
        ("email_verify.ttl", db.email_verification_tokens.create_index("expires_at", expireAfterSeconds=0)),
        ("login_attempts", db.login_attempts.create_index("identifier")),
        ("ai_activities", db.ai_activities.create_index([("organizationId", 1), ("created_at", -1)])),
        ("invitations.tokenHash", db.organization_invitations.create_index("tokenHash", unique=True)),
        ("invitations.org_email", db.organization_invitations.create_index([("organizationId", 1), ("email", 1), ("status", 1)])),
        ("audit_logs", db.audit_logs.create_index([("organizationId", 1), ("createdAt", -1)])),
        ("outbound.org_status", db.outbound_emails.create_index([("organizationId", 1), ("status", 1), ("updatedAt", -1)])),
        ("outbound.org_createdBy", db.outbound_emails.create_index([("organizationId", 1), ("createdBy", 1)])),
        ("outbound.providerMessageId", db.outbound_emails.create_index("providerMessageId")),
        ("outbound.org_internetMessageId", db.outbound_emails.create_index([("organizationId", 1), ("internetMessageId", 1)])),
        ("outbound.automationApprovalId", db.outbound_emails.create_index([("organizationId", 1), ("automationApprovalId", 1)])),
        ("outbound.org_id", db.outbound_emails.create_index([("organizationId", 1), ("id", 1)])),
        ("outbound.status_attempt", db.outbound_emails.create_index([("status", 1), ("lastSendAttemptAt", 1)])),
        ("outbound.scheduled", db.outbound_emails.create_index([("status", 1), ("scheduledFor", 1)])),
        ("outbound.inbox_thread", db.outbound_emails.create_index([("organizationId", 1), ("inboxThreadId", 1), ("status", 1)])),
        ("webhook.svix", db.email_webhook_events.create_index("svixId", unique=True, sparse=True)),
        ("integrations.org_provider", db.integrations.create_index([("organizationId", 1), ("provider", 1)], unique=True)),
        ("oauth_states.state", db.integration_oauth_states.create_index("state", unique=True)),
        ("oauth_states.expires", db.integration_oauth_states.create_index("expiresAt")),
        ("mailboxes.unique", db.mailboxes.create_index([("organizationId", 1), ("provider", 1), ("providerAccountId", 1)], unique=True)),
        ("mailboxes.org_id", db.mailboxes.create_index([("organizationId", 1), ("id", 1)])),
        ("mailboxes.sync", db.mailboxes.create_index([("syncEnabled", 1), ("lastSuccessfulSyncAt", 1)])),
        ("threads.unique", db.email_threads.create_index([("organizationId", 1), ("mailboxId", 1), ("providerThreadId", 1)], unique=True)),
        ("threads.latest", db.email_threads.create_index([("organizationId", 1), ("latestMessageAt", -1)])),
        ("threads.org_id", db.email_threads.create_index([("organizationId", 1), ("id", 1)])),
        ("inbound.unique", db.inbound_messages.create_index([("organizationId", 1), ("mailboxId", 1), ("providerMessageId", 1)], unique=True)),
        ("inbound.internetMessageId", db.inbound_messages.create_index([("organizationId", 1), ("internetMessageId", 1)])),
        ("inbound.thread", db.inbound_messages.create_index([("organizationId", 1), ("threadId", 1), ("receivedAt", 1)])),
        ("inbox_events", db.inbox_events.create_index([("organizationId", 1), ("createdAt", -1)])),
        ("job_runs.org", db.job_runs.create_index([("organizationId", 1), ("createdAt", -1)])),
        ("job_runs.status", db.job_runs.create_index([("status", 1), ("createdAt", -1)])),
        ("job_runs.idempotency", db.job_runs.create_index([("idempotencyKey", 1)], unique=True, sparse=True)),
        ("organizations.id", db.organizations.create_index("id", unique=True)),
        ("automation_logs", db.automation_logs.create_index([("organizationId", 1), ("created_at", -1)])),
        ("beta_feedback.org", db.beta_feedback.create_index([("organizationId", 1), ("createdAt", -1)])),
        ("ai_usage_daily", db.ai_usage_daily.create_index([("organizationId", 1), ("day", 1)], unique=True)),
    ]

    for label, coro in specs:
        await _one(label, coro)

    summary = {"createdOrEnsured": created, "errors": errors, "ok": len(errors) == 0}
    if errors:
        logger.error("Index initialization completed with %d error(s)", len(errors))
    else:
        logger.info("Index initialization ok (%d indexes)", created)
    return summary
