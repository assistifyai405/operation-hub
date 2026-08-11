"""Job handlers — import this module to register handlers."""
from __future__ import annotations

import logging

from jobs import register

logger = logging.getLogger(__name__)


@register("inbox_sync")
async def handle_inbox_sync(job: dict):
    from inbox.sync_service import sync_mailbox
    payload = job.get("payload") or {}
    org_id = job.get("organizationId") or payload.get("organizationId")
    mailbox_id = payload.get("mailboxId")
    if not org_id or not mailbox_id:
        raise ValueError("organizationId and mailboxId required")
    # Verify org ownership
    from core import db
    mb = await db.mailboxes.find_one({"id": mailbox_id, "organizationId": org_id}, {"_id": 0, "id": 1})
    if not mb:
        raise ValueError("Mailbox not found for organization")
    return await sync_mailbox(org_id, mailbox_id, force_full=bool(payload.get("forceFull")))


@register("send_scheduled_email")
async def handle_send_scheduled(job: dict):
    from core import db
    from routers.emails import perform_send
    payload = job.get("payload") or {}
    org_id = job.get("organizationId")
    email_id = payload.get("emailId")
    doc = await db.outbound_emails.find_one(
        {"id": email_id, "organizationId": org_id, "status": "scheduled"}, {"_id": 0},
    )
    if not doc:
        return {"skipped": True, "reason": "not_scheduled"}
    # System actor
    user = {"id": doc.get("createdBy"), "email": doc.get("createdByEmail"), "role": "owner"}
    return await perform_send(doc, user)


@register("integration_health")
async def handle_integration_health(job: dict):
    from core import db
    from integrations import store
    from integrations.providers import get_provider
    org_id = job.get("organizationId")
    payload = job.get("payload") or {}
    provider = payload.get("provider")
    if not org_id or not provider:
        raise ValueError("organizationId and provider required")
    integ = await store.get_by_provider(org_id, provider)
    if not integ or integ.get("status") == "disconnected":
        return {"ok": False, "reason": "disconnected"}
    try:
        p = get_provider(provider)
        if hasattr(p, "health_check"):
            ok = await p.health_check(await store.load_credentials(integ))
        else:
            ok = bool(integ.get("encryptedCredentials"))
        await store.update_health(org_id, integ["id"], bool(ok), "ok" if ok else "unhealthy")
        return {"ok": bool(ok)}
    except Exception as e:
        await store.update_health(org_id, integ["id"], False, str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@register("reconcile_sending")
async def handle_reconcile_sending(job: dict):
    from jobs.reconciliation import reconcile_stuck_emails
    org_id = job.get("organizationId")
    return await reconcile_stuck_emails(organization_id=org_id)


@register("cleanup_expired")
async def handle_cleanup(job: dict):
    from core import db, now_iso
    # OAuth states with string expires — best-effort delete expired ISO strings older than now
    now = now_iso()
    res1 = await db.integration_oauth_states.delete_many({"expiresAt": {"$lt": now}})
    # Expired invitations
    res2 = await db.organization_invitations.update_many(
        {"status": "pending", "expiresAt": {"$lt": now}},
        {"$set": {"status": "expired", "updatedAt": now}},
    )
    return {
        "oauthStatesDeleted": getattr(res1, "deleted_count", 0),
        "invitationsExpired": getattr(res2, "modified_count", 0),
    }


@register("process_webhook")
async def handle_webhook(job: dict):
    from jobs.webhooks import apply_resend_event
    payload = job.get("payload") or {}
    return await apply_resend_event(payload)


@register("inbox_ai_summary")
async def handle_ai_summary(job: dict):
    # Optional deferred summary — invoke existing router logic pieces
    from core import db, now_iso, ai_service
    payload = job.get("payload") or {}
    org_id = job.get("organizationId")
    thread_id = payload.get("threadId")
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org_id}, {"_id": 0})
    if not t:
        raise ValueError("Thread not found")
    msgs = await db.inbound_messages.find(
        {"threadId": thread_id, "organizationId": org_id},
        {"_id": 0, "from": 1, "textBody": 1, "receivedAt": 1},
    ).sort("receivedAt", 1).to_list(40)
    transcript = "\n\n".join(
        f"From: {m.get('from')}\n{(m.get('textBody') or '')[:2000]}" for m in msgs
    )[:15000]
    data = await ai_service.complete_json(
        "Summarize business email threads. Return only JSON.",
        f"Subject: {t.get('subject')}\n\n{transcript}\n\nReturn keys: summary, intent, urgency, sentiment, requestedActions, openQuestions, suggestedNextStep.",
        [
            {"key": "summary", "type": "text"},
            {"key": "intent", "type": "text"},
            {"key": "urgency", "type": "text"},
            {"key": "sentiment", "type": "text"},
            {"key": "requestedActions", "type": "list"},
            {"key": "openQuestions", "type": "list"},
            {"key": "suggestedNextStep", "type": "text"},
        ],
    )
    await db.email_threads.update_one(
        {"id": thread_id, "organizationId": org_id},
        {"$set": {"aiSummary": data, "aiSummaryUpdatedAt": now_iso(), "updatedAt": now_iso()}},
    )
    return {"threadId": thread_id, "ok": True}


@register("test_noop")
async def handle_test_noop(job: dict):
    """Safe internal test job — no external I/O."""
    payload = job.get("payload") or {}
    return {"ok": True, "echo": str(payload.get("echo") or "")[:80]}


@register("test_fail")
async def handle_test_fail(job: dict):
    """Safe internal test job that always fails (for retry/dead-letter QA)."""
    raise RuntimeError("intentional test failure")
