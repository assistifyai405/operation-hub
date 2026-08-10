#!/usr/bin/env python3
"""Validate staging/production-like environment configuration WITHOUT printing secrets.

Usage:
  python scripts/validate_staging_env.py
  python scripts/validate_staging_env.py --env-file backend/.env.staging
  python scripts/validate_staging_env.py --strict   # exit 1 if any REQUIRED check is not OK

Statuses: OK | MISSING | INVALID | DISABLED
Never prints secret values.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Known weak JWT secrets (mirrored from backend/config.py — keep in sync)
WEAK_JWT = {
    "",
    "secret",
    "changeme",
    "change-me",
    "change-me-to-a-long-random-string",
    "jwt_secret",
    "jwt-secret",
    "your-secret",
    "your-secret-here",
    "assistify",
    "assistify-secret",
    "dev",
    "development",
    "test",
    "testing",
    "local-dev-secret-change-me-32chars!!",
    "unit-test-secret-key-with-32plus-chars!!",
}


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Env file not found: {path}")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _truthy(name: str) -> bool | None:
    raw = _env(name)
    if raw == "":
        return None
    return raw.lower() in {"1", "true", "yes", "on"}


def _is_https(url: str) -> bool:
    try:
        return urlparse(url).scheme == "https"
    except Exception:
        return False


def _is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def check(name: str, status: str, note: str = "") -> dict:
    assert status in {"OK", "MISSING", "INVALID", "DISABLED"}
    return {"name": name, "status": status, "note": note}


def validate() -> list[dict]:
    rows: list[dict] = []

    # JWT
    jwt = _env("JWT_SECRET")
    if not jwt:
        rows.append(check("JWT_SECRET", "MISSING"))
    elif jwt.strip().lower() in WEAK_JWT or len(jwt) < 32:
        rows.append(check("JWT_SECRET", "INVALID", "weak or shorter than 32 chars"))
    else:
        rows.append(check("JWT_SECRET", "OK"))

    # Encryption key
    enc = _env("INTEGRATION_ENCRYPTION_KEY")
    if not enc:
        rows.append(check("INTEGRATION_ENCRYPTION_KEY", "MISSING"))
    elif len(enc) < 16:
        rows.append(check("INTEGRATION_ENCRYPTION_KEY", "INVALID", "too short"))
    else:
        rows.append(check("INTEGRATION_ENCRYPTION_KEY", "OK"))

    # Mongo
    mongo = _env("MONGO_URL")
    if not mongo:
        rows.append(check("MONGO_URL", "MISSING"))
    elif not (mongo.startswith("mongodb://") or mongo.startswith("mongodb+srv://")):
        rows.append(check("MONGO_URL", "INVALID", "must start with mongodb:// or mongodb+srv://"))
    else:
        rows.append(check("MONGO_URL", "OK"))

    db_name = _env("DB_NAME")
    rows.append(check("DB_NAME", "OK" if db_name else "MISSING"))

    # Redis
    redis = _env("REDIS_URL")
    require_redis = _truthy("REQUIRE_REDIS")
    worker = _truthy("WORKER_ENABLED")
    scheduler = _truthy("SCHEDULER_ENABLED")
    redis_needed = bool(require_redis or worker or scheduler)
    if not redis:
        rows.append(check("REDIS_URL", "MISSING" if redis_needed else "DISABLED", "optional when workers off"))
    elif not (redis.startswith("redis://") or redis.startswith("rediss://")):
        rows.append(check("REDIS_URL", "INVALID", "must start with redis:// or rediss://"))
    else:
        rows.append(check("REDIS_URL", "OK"))

    # Frontend / API / CORS
    frontend = _env("FRONTEND_URL")
    if not frontend:
        rows.append(check("FRONTEND_URL", "MISSING"))
    elif not _is_http_url(frontend):
        rows.append(check("FRONTEND_URL", "INVALID"))
    elif "localhost" in frontend.lower() or "127.0.0.1" in frontend:
        rows.append(check("FRONTEND_URL", "INVALID", "localhost not allowed for staging"))
    elif not _is_https(frontend):
        rows.append(check("FRONTEND_URL", "INVALID", "staging requires https://"))
    else:
        rows.append(check("FRONTEND_URL", "OK"))

    api_url = _env("API_URL") or _env("REACT_APP_BACKEND_URL")
    if not api_url:
        rows.append(check("API_URL", "MISSING", "set API_URL or REACT_APP_BACKEND_URL"))
    elif not _is_http_url(api_url):
        rows.append(check("API_URL", "INVALID"))
    elif "localhost" in api_url.lower() or "127.0.0.1" in api_url:
        rows.append(check("API_URL", "INVALID", "localhost not allowed for staging"))
    elif not _is_https(api_url):
        rows.append(check("API_URL", "INVALID", "staging requires https://"))
    else:
        rows.append(check("API_URL", "OK"))

    cors = _env("CORS_ORIGINS")
    if not cors:
        rows.append(check("CORS_ORIGINS", "MISSING"))
    elif cors.strip() == "*":
        rows.append(check("CORS_ORIGINS", "INVALID", "wildcard not allowed"))
    elif frontend and frontend.rstrip("/") not in [o.strip().rstrip("/") for o in cors.split(",")]:
        rows.append(check("CORS_ORIGINS", "INVALID", "FRONTEND_URL not in allow-list"))
    else:
        rows.append(check("CORS_ORIGINS", "OK"))

    # Cookies
    cookie_secure = _truthy("COOKIE_SECURE")
    cookie_samesite = (_env("COOKIE_SAMESITE") or "").lower()
    if frontend and _is_https(frontend):
        # Defaults are Secure+None when HTTPS frontend; overrides must stay valid
        if cookie_secure is False:
            rows.append(check("COOKIE_SECURE", "INVALID", "must be true for HTTPS staging"))
        else:
            rows.append(check("COOKIE_SECURE", "OK", "true (explicit or default)"))
        if cookie_samesite and cookie_samesite not in {"lax", "none", "strict"}:
            rows.append(check("COOKIE_SAMESITE", "INVALID"))
        elif cookie_samesite == "none" and cookie_secure is False:
            rows.append(check("COOKIE_SAMESITE", "INVALID", "none requires Secure"))
        else:
            # Cross-origin SPA typically needs none
            note = cookie_samesite or "default none for https"
            rows.append(check("COOKIE_SAMESITE", "OK", note))
    else:
        rows.append(check("COOKIE_SECURE", "DISABLED", "set FRONTEND_URL https first"))
        rows.append(check("COOKIE_SAMESITE", "DISABLED", "set FRONTEND_URL https first"))

    # AI
    provider = (_env("AI_PROVIDER") or "openai").lower()
    if provider == "openai":
        key = _env("OPENAI_API_KEY")
        rows.append(check("AI_PROVIDER", "OK", "openai"))
        rows.append(check("OPENAI_API_KEY", "OK" if key else "MISSING"))
    elif provider == "emergent":
        key = _env("EMERGENT_LLM_KEY")
        rows.append(check("AI_PROVIDER", "OK", "emergent"))
        rows.append(check("EMERGENT_LLM_KEY", "OK" if key else "MISSING"))
    else:
        rows.append(check("AI_PROVIDER", "INVALID", provider))

    # Demo flags must be OFF (unset counts as disabled/off — acceptable)
    for flag in ("ENABLE_DEMO_LOGIN", "ENABLE_DEMO_SEED", "ALLOW_DEMO_IN_PRODUCTION"):
        v = _truthy(flag)
        if v is True:
            rows.append(check(flag, "INVALID", "must be off"))
        else:
            rows.append(check(flag, "DISABLED", "off (required)"))

    # Billing
    billing = _truthy("REACT_APP_BILLING_ENABLED")
    if billing is True:
        rows.append(check("REACT_APP_BILLING_ENABLED", "INVALID", "Stripe not implemented — keep false"))
    else:
        rows.append(check("REACT_APP_BILLING_ENABLED", "DISABLED", "off (required)"))

    # Email
    email_provider = (_env("EMAIL_PROVIDER") or "").lower()
    if not email_provider:
        rows.append(check("EMAIL_PROVIDER", "MISSING", "resend|console"))
    elif email_provider not in {"resend", "console"}:
        rows.append(check("EMAIL_PROVIDER", "INVALID"))
    else:
        rows.append(check("EMAIL_PROVIDER", "OK", email_provider))

    sending = _truthy("EMAIL_SENDING_ENABLED")
    if sending is True:
        rows.append(check("EMAIL_SENDING_ENABLED", "OK", "enabled — ensure DNS verified"))
    else:
        rows.append(check("EMAIL_SENDING_ENABLED", "DISABLED", "kill-switch off (safe default)"))

    if email_provider == "resend":
        rows.append(check("RESEND_API_KEY", "OK" if _env("RESEND_API_KEY") else "MISSING"))
        fe = _env("FROM_EMAIL")
        if not fe:
            rows.append(check("FROM_EMAIL", "MISSING"))
        elif "@" not in fe:
            rows.append(check("FROM_EMAIL", "INVALID"))
        else:
            rows.append(check("FROM_EMAIL", "OK"))
    else:
        rows.append(check("RESEND_API_KEY", "DISABLED", "console provider"))
        rows.append(check("FROM_EMAIL", "DISABLED", "console provider"))

    # OAuth (optional)
    for label, id_key, secret_key, redir_key in (
        ("GOOGLE_OAUTH", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"),
        ("MICROSOFT_OAUTH", "MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_REDIRECT_URI"),
        ("SLACK_OAUTH", "SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_REDIRECT_URI"),
    ):
        cid, secret, redir = _env(id_key), _env(secret_key), _env(redir_key)
        if not cid and not secret:
            rows.append(check(label, "DISABLED", "not configured"))
        elif not cid or not secret:
            rows.append(check(label, "INVALID", "id/secret incomplete"))
        elif redir and not _is_https(redir):
            rows.append(check(label, "INVALID", "redirect URI must be https"))
        elif redir and "/api/integrations/oauth/callback/" not in redir:
            rows.append(check(label, "INVALID", "unexpected redirect path"))
        else:
            note = "configured" + (" + redirect" if redir else " (redirect derived at runtime)")
            rows.append(check(label, "OK", note))

    # Worker / scheduler visibility
    rows.append(check("WORKER_ENABLED", "OK" if worker else "DISABLED"))
    rows.append(check("SCHEDULER_ENABLED", "OK" if scheduler else "DISABLED"))
    rows.append(check("REQUIRE_REDIS", "OK" if require_redis else "DISABLED"))

    # Alert delivery (optional)
    alert_url = _env("ALERT_WEBHOOK_URL")
    alert_on = _truthy("ALERT_DELIVERY_ENABLED")
    if not alert_on:
        rows.append(check("ALERT_DELIVERY", "DISABLED", "off by default"))
    elif not alert_url:
        rows.append(check("ALERT_DELIVERY", "INVALID", "enabled but ALERT_WEBHOOK_URL missing"))
    elif not _is_https(alert_url):
        rows.append(check("ALERT_DELIVERY", "INVALID", "webhook must be https"))
    else:
        rows.append(check("ALERT_DELIVERY", "OK"))

    return rows


# Checks that must be OK (not MISSING/INVALID) for a staging go/no-go
REQUIRED_OK = {
    "JWT_SECRET",
    "INTEGRATION_ENCRYPTION_KEY",
    "MONGO_URL",
    "DB_NAME",
    "FRONTEND_URL",
    "API_URL",
    "CORS_ORIGINS",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
}

REQUIRED_NOT_INVALID = {
    "ENABLE_DEMO_LOGIN",
    "ENABLE_DEMO_SEED",
    "ALLOW_DEMO_IN_PRODUCTION",
    "REACT_APP_BILLING_ENABLED",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate staging env (no secrets printed)")
    parser.add_argument("--env-file", type=Path, help="Optional .env file to load (does not override existing env)")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if required checks fail")
    args = parser.parse_args()
    if args.env_file:
        _load_env_file(args.env_file)

    rows = validate()
    width = max((len(r["name"]) for r in rows), default=12)
    print("Assistify OS — staging environment validation")
    print("(statuses only — secret values are never printed)")
    print("-" * 60)
    for r in rows:
        note = f"  # {r['note']}" if r["note"] else ""
        print(f"{r['name']:<{width}}  {r['status']}{note}")
    print("-" * 60)

    by_name = {r["name"]: r for r in rows}
    failures = []
    for name in REQUIRED_OK:
        st = by_name.get(name, {}).get("status")
        if st != "OK":
            failures.append(f"{name}={st}")
    for name in REQUIRED_NOT_INVALID:
        st = by_name.get(name, {}).get("status")
        if st == "INVALID":
            failures.append(f"{name}={st}")

    # AI key presence
    if by_name.get("OPENAI_API_KEY", {}).get("status") == "MISSING" and by_name.get("EMERGENT_LLM_KEY", {}).get("status") == "MISSING":
        failures.append("AI_KEY=MISSING")
    if by_name.get("AI_PROVIDER", {}).get("status") == "INVALID":
        failures.append("AI_PROVIDER=INVALID")

    if failures:
        print(f"RESULT  FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        return 1 if args.strict else 0
    print("RESULT  PASS (required staging checks OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
