"""Health / live / ready endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from dependencies import current_user
from permissions import role_at_least

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health")


def _release() -> str:
    try:
        from config import get_settings
        return getattr(get_settings(), "release_version", None) or "dev"
    except Exception:
        return "dev"


@router.get("/live")
async def live():
    """Liveness — process is up. Never checks dependencies."""
    return {"status": "ok", "check": "live", "release": _release()}


@router.get("/ready")
async def ready():
    """Readiness — required dependencies available.

    Returns 503 when a production-required dependency is unavailable.
    Never silently reports healthy Redis when REQUIRE_REDIS / workers need it.
    """
    from fastapi.responses import JSONResponse
    from config import get_settings
    from redis_client import ping_redis, redis_required_for_production

    s = get_settings()
    checks = {}
    overall = True
    reasons = []

    try:
        from core import db
        await db.command("ping")
        checks["mongodb"] = {"ok": True}
    except Exception as e:
        checks["mongodb"] = {"ok": False, "error": str(e)[:120]}
        overall = False
        reasons.append("mongodb")

    rp = ping_redis()
    checks["redis"] = rp
    redis_required = redis_required_for_production() or bool(getattr(s, "require_redis", False))
    if redis_required and not rp.get("ok"):
        overall = False
        reasons.append("redis")

    try:
        from storage import _provider
        checks["storage"] = {"ok": True, "provider": _provider()}
    except Exception as e:
        checks["storage"] = {"ok": False, "error": str(e)[:80]}
        if s.is_production:
            overall = False
            reasons.append("storage")

    checks["jobs"] = {
        "workerEnabled": bool(getattr(s, "worker_enabled", False)),
        "schedulerEnabled": bool(getattr(s, "scheduler_enabled", False)),
        "requireRedis": redis_required,
        "syncMode": not bool(getattr(s, "worker_enabled", False)) or not rp.get("ok"),
    }

    # Queue depth is informational only (never secrets)
    try:
        from redis_client import get_redis
        from jobs import QUEUE_KEY, FAILED_KEY
        r = get_redis()
        if r:
            checks["jobs"]["queueDepth"] = int(r.llen(QUEUE_KEY) or 0)
            checks["jobs"]["failedDepth"] = int(r.llen(FAILED_KEY) or 0)
    except Exception:
        pass

    body = {
        "status": "ok" if overall else "degraded",
        "check": "ready",
        "release": _release(),
        "environment": s.environment,
        "checks": checks,
        "failedChecks": reasons,
    }
    if not overall:
        return JSONResponse(status_code=503, content=body)
    return body


@router.get("")
async def health():
    """General health (safe, no secrets). Always 200; status may be degraded."""
    from config import get_settings
    from redis_client import ping_redis, redis_required_for_production
    from email_providers import get_email_provider, outbound_sending_allowed

    s = get_settings()
    mongo_ok = False
    try:
        from core import db
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False

    redis = ping_redis()
    email_ok, email_reason = outbound_sending_allowed(s)
    ai_configured = bool(
        (s.ai_provider == "openai" and s.openai_api_key)
        or (s.ai_provider == "emergent" and s.emergent_llm_key)
    )
    redis_required = redis_required_for_production() or bool(getattr(s, "require_redis", False))
    degraded = (not mongo_ok) or (redis_required and not redis.get("ok"))
    return {
        "status": "degraded" if degraded else "ok",
        "release": _release(),
        "environment": s.environment,
        "mongodb": {"ok": mongo_ok},
        "redis": redis,
        "worker": {"enabled": bool(getattr(s, "worker_enabled", False))},
        "scheduler": {"enabled": bool(getattr(s, "scheduler_enabled", False))},
        "requireRedis": redis_required,
        "storage": {"provider": s.storage_provider},
        "ai": {"provider": s.ai_provider, "configured": ai_configured},
        "billing": {"configured": False, "status": "pending"},
        "demo": {
            "loginEnabled": bool(s.enable_demo_login),
            "seedEnabled": bool(s.enable_demo_seed),
        },
        "email": {
            "provider": s.email_provider,
            "sendingEnabled": s.email_sending_enabled,
            "configured": get_email_provider(s).is_configured() if s.email_provider == "resend" else True,
            "canSend": email_ok,
        },
    }


@router.get("/details")
async def health_details(user: dict = Depends(current_user)):
    """Admin-only detailed health + ops counters."""
    if not role_at_least(user.get("role"), "admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    base = await health()
    from jobs import failed_job_count
    from jobs.reconciliation import stuck_email_count
    from core import db

    base["failedJobs"] = await failed_job_count()
    base["stuckEmails"] = await stuck_email_count()
    base["unhealthyIntegrations"] = await db.integrations.count_documents(
        {"status": "error"}
    )
    return base


@router.get("/alerts")
async def health_alerts():
    """Lightweight alert hooks for staging/production monitors (no secrets).

    Scrape this endpoint (or `/api/health/ready`) from uptime tooling.
    Returns HTTP 503 when any critical alert is active (ready failure).
    """
    from fastapi.responses import JSONResponse
    from config import get_settings
    from redis_client import ping_redis, redis_required_for_production
    from jobs import failed_job_count
    from core import db

    s = get_settings()
    alerts = []
    critical = False
    failed_checks = []

    # Mongo
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
        failed_checks.append("mongodb")

    rp = ping_redis()
    redis_required = redis_required_for_production() or bool(getattr(s, "require_redis", False))
    if redis_required and not rp.get("ok"):
        failed_checks.append("redis")

    if failed_checks:
        critical = True
        alerts.append({
            "severity": "critical",
            "code": "ready_failed",
            "message": "Readiness dependencies unavailable",
            "failedChecks": failed_checks,
        })

    if getattr(s, "worker_enabled", False) and not rp.get("ok"):
        critical = True
        alerts.append({
            "severity": "critical",
            "code": "worker_unavailable",
            "message": "Worker enabled but Redis unreachable (jobs cannot drain)",
        })

    if getattr(s, "scheduler_enabled", False) and not rp.get("ok"):
        critical = True
        alerts.append({
            "severity": "critical",
            "code": "scheduler_unavailable",
            "message": "Scheduler enabled but Redis unreachable",
        })

    failed_depth = 0
    try:
        failed_depth = int(await failed_job_count() or 0)
    except Exception:
        failed_depth = 0
    if failed_depth >= 5:
        alerts.append({
            "severity": "warning",
            "code": "failed_job_depth",
            "message": f"Failed job queue depth is {failed_depth}",
            "count": failed_depth,
        })

    email_failures = 0
    try:
        from datetime import datetime, timezone, timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        email_failures = await db.outbound_emails.count_documents(
            {"status": "failed", "failedAt": {"$gte": since}}
        )
    except Exception:
        email_failures = 0
    if email_failures >= 3:
        alerts.append({
            "severity": "warning",
            "code": "email_send_failures",
            "message": f"{email_failures} outbound email failures in the last hour",
            "count": email_failures,
        })

    unhealthy = 0
    try:
        unhealthy = await db.integrations.count_documents({"status": "error"})
    except Exception:
        unhealthy = 0
    if unhealthy >= 1:
        alerts.append({
            "severity": "warning",
            "code": "integration_refresh_failures",
            "message": f"{unhealthy} integration(s) in error / needs reauth",
            "count": unhealthy,
        })

    body = {
        "ok": not critical,
        "critical": critical,
        "alertCount": len(alerts),
        "alerts": alerts,
        "release": _release(),
        "environment": s.environment,
    }
    if critical:
        return JSONResponse(status_code=503, content=body)
    return body
