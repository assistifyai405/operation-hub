"""Admin operations API — jobs, reconciliation, sync triggers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import write_audit
from core import db, now_iso
from dependencies import current_user, current_org, rate_limit
from jobs import enqueue, failed_job_count, retry_job
from jobs.reconciliation import reconcile_stuck_emails, stuck_email_count
from permissions import require_admin, role_at_least

router = APIRouter(prefix="/api/ops")


class ResolveEmailBody(BaseModel):
    action: str = Field(..., description="mark_failed | mark_sent | retry")
    note: str = ""


@router.get("/status")
async def ops_status(org: str = Depends(current_org), user: dict = Depends(require_admin)):
    from config import get_settings
    from redis_client import ping_redis
    from routers.health import health

    s = get_settings()
    base = await health()
    last_sync = await db.mailboxes.find(
        {"organizationId": org},
        {"_id": 0, "id": 1, "emailAddress": 1, "syncStatus": 1, "lastSuccessfulSyncAt": 1, "lastError": 1, "provider": 1},
    ).to_list(20)
    return {
        **base,
        "redis": ping_redis(),
        "failedJobs": await failed_job_count(),
        "stuckEmails": await stuck_email_count(org),
        "unhealthyIntegrations": await db.integrations.count_documents(
            {"organizationId": org, "status": "error"}
        ),
        "mailboxes": last_sync,
        "workerEnabled": s.worker_enabled,
        "schedulerEnabled": s.scheduler_enabled,
        "release": s.release_version,
    }


@router.post("/jobs/{job_id}/retry")
async def ops_retry_job(job_id: str, org: str = Depends(current_org), user: dict = Depends(require_admin)):
    rate_limit(f"ops-retry:{user['id']}", 30, 3600)
    try:
        doc = await retry_job(job_id, org_id=org)
    except ValueError as e:
        # Allow system jobs with null org for platform admins — still scope when org set
        try:
            doc = await retry_job(job_id, org_id=None)
            if doc.get("organizationId") and doc.get("organizationId") != org:
                raise HTTPException(status_code=404, detail="Job not found")
        except ValueError:
            raise HTTPException(status_code=404, detail=str(e)) from e
    await write_audit(org, "ops_job_retried", actor_id=user.get("id"), actor_email=user.get("email"), meta={"jobId": job_id})
    return doc


@router.post("/mailboxes/{mailbox_id}/sync")
async def ops_sync_mailbox(mailbox_id: str, org: str = Depends(current_org), user: dict = Depends(require_admin)):
    rate_limit(f"ops-sync:{org}:{user['id']}", 20, 3600)
    mb = await db.mailboxes.find_one({"id": mailbox_id, "organizationId": org}, {"_id": 0})
    if not mb:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    job = await enqueue(
        "inbox_sync",
        organization_id=org,
        payload={"mailboxId": mailbox_id},
        request_id=None,
    )
    await write_audit(org, "ops_mailbox_sync_enqueued", actor_id=user.get("id"), actor_email=user.get("email"), meta={"mailboxId": mailbox_id, "jobId": job.get("id")})
    return {"job": job}


@router.post("/emails/reconcile")
async def ops_reconcile(org: str = Depends(current_org), user: dict = Depends(require_admin)):
    rate_limit(f"ops-reconcile:{org}", 10, 3600)
    result = await reconcile_stuck_emails(organization_id=org)
    await write_audit(org, "ops_email_reconcile", actor_id=user.get("id"), actor_email=user.get("email"), meta=result)
    return result


@router.post("/emails/{email_id}/resolve")
async def ops_resolve_email(
    email_id: str,
    body: ResolveEmailBody,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    rate_limit(f"ops-resolve:{org}", 30, 3600)
    doc = await db.outbound_emails.find_one({"id": email_id, "organizationId": org}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    if doc.get("status") not in ("needs_review", "delivery_unknown", "failed", "sending"):
        raise HTTPException(status_code=400, detail="Email is not in a resolvable state")

    action = (body.action or "").lower()
    if action == "mark_failed":
        await db.outbound_emails.update_one(
            {"id": email_id, "organizationId": org},
            {"$set": {
                "status": "failed",
                "failureReason": (body.note or "Marked failed by admin")[:500],
                "failedAt": now_iso(),
                "updatedAt": now_iso(),
            }},
        )
    elif action == "mark_sent":
        # Only when human confirmed delivery in provider mailbox
        await db.outbound_emails.update_one(
            {"id": email_id, "organizationId": org},
            {"$set": {
                "status": "sent",
                "failureReason": None,
                "sentAt": doc.get("sentAt") or now_iso(),
                "updatedAt": now_iso(),
            }},
        )
    elif action == "retry":
        if doc.get("providerMessageId") and doc.get("status") in ("needs_review", "delivery_unknown"):
            raise HTTPException(status_code=400, detail="Confirm delivery before retrying — provider message id already present")
        await db.outbound_emails.update_one(
            {"id": email_id, "organizationId": org},
            {"$set": {"status": "approved", "updatedAt": now_iso(), "failureReason": None}},
        )
        from routers.emails import perform_send
        return await perform_send(await db.outbound_emails.find_one({"id": email_id}, {"_id": 0}), user, force_retry=True)
    else:
        raise HTTPException(status_code=400, detail="action must be mark_failed|mark_sent|retry")

    await write_audit(
        org, "ops_email_resolved",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"emailId": email_id, "action": action},
    )
    return await db.outbound_emails.find_one({"id": email_id, "organizationId": org}, {"_id": 0, "versions": 0})


@router.post("/integrations/{provider}/health")
async def ops_integration_health(provider: str, org: str = Depends(current_org), user: dict = Depends(require_admin)):
    rate_limit(f"ops-health:{org}", 30, 3600)
    job = await enqueue(
        "integration_health",
        organization_id=org,
        payload={"provider": provider},
    )
    return {"job": job}


@router.post("/alerts/dispatch")
async def ops_dispatch_alerts(org: str = Depends(current_org), user: dict = Depends(require_admin)):
    """Manually evaluate + deliver health alerts to the optional webhook (admin).

    Safe response — never includes webhook URL or secrets.
    """
    rate_limit(f"ops-alerts:{user['id']}", 10, 3600)
    from alerts_delivery import deliver_alerts, delivery_enabled
    result = await deliver_alerts(force=True)
    await write_audit(
        org, "ops_alerts_dispatched",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"delivered": result.get("delivered"), "reason": result.get("reason"), "alertCount": result.get("alertCount")},
    )
    return {"ok": True, "deliveryEnabled": delivery_enabled(), **{k: v for k, v in result.items() if k != "webhook"}}
