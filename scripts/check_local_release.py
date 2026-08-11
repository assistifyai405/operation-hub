#!/usr/bin/env python3
"""Local / Docker closed-beta release gate.

Verifies frontend + backend health + async worker/scheduler heartbeats.
Never prints secrets. Exit 0 on success, 1 on failure.

Usage:
  python scripts/check_local_release.py
  FRONTEND_URL=http://localhost:3000 API_URL=http://localhost:8000 python scripts/check_local_release.py
  python scripts/check_local_release.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def _get(url: str, timeout: float = 8.0) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else None
            except json.JSONDecodeError:
                data = body[:200]
            return resp.status, data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body) if body else {"detail": str(e)}
        except json.JSONDecodeError:
            data = {"detail": body[:200] or str(e)}
        return e.code, data
    except Exception as e:
        return 0, {"error": str(e)[:200]}


def _ok(label: str, cond: bool, detail: str = "") -> dict:
    return {"check": label, "ok": bool(cond), "detail": detail}


def _scrub(text: str) -> str:
    low = (text or "").lower()
    if "sk-" in low or "api_key" in low or "bearer " in low:
        return "<redacted>"
    return text[:240]


def run(frontend: str, api: str) -> tuple[bool, list[dict]]:
    results: list[dict] = []

    # Frontend
    code, _ = _get(frontend.rstrip("/") + "/", timeout=10)
    results.append(_ok("frontend_reachable", code in (200, 301, 302, 304), f"HTTP {code}"))

    # Live
    code, live = _get(api.rstrip("/") + "/api/health/live")
    results.append(_ok("health_live", code == 200 and isinstance(live, dict) and live.get("check") == "live", f"HTTP {code}"))

    # Ready
    code, ready = _get(api.rstrip("/") + "/api/health/ready")
    ready_ok = code == 200 and isinstance(ready, dict) and ready.get("status") == "ok"
    results.append(_ok("health_ready", ready_ok, f"HTTP {code} status={isinstance(ready, dict) and ready.get('status')}"))

    jobs = {}
    checks = {}
    if isinstance(ready, dict):
        checks = ready.get("checks") or {}
        jobs = checks.get("jobs") or {}

    mongo = (checks.get("mongodb") or {})
    redis = (checks.get("redis") or {})
    results.append(_ok("mongodb", bool(mongo.get("ok")), _scrub(str(mongo.get("error") or "ok"))))
    results.append(_ok("redis", bool(redis.get("ok")), _scrub(str(redis.get("error") or ("configured" if redis.get("configured") else "missing")))))

    results.append(_ok("workerEnabled", jobs.get("workerEnabled") is True, str(jobs.get("workerEnabled"))))
    results.append(_ok("schedulerEnabled", jobs.get("schedulerEnabled") is True, str(jobs.get("schedulerEnabled"))))
    results.append(_ok("syncMode_false", jobs.get("syncMode") is False, str(jobs.get("syncMode"))))

    worker = jobs.get("worker") or {}
    scheduler = jobs.get("scheduler") or {}
    results.append(_ok("worker_heartbeat_running", worker.get("status") == "running", str(worker.get("status"))))
    results.append(_ok("scheduler_heartbeat_running", scheduler.get("status") == "running", str(scheduler.get("status"))))

    # Alerts
    code, alerts = _get(api.rstrip("/") + "/api/health/alerts")
    alerts_ok = code == 200 and isinstance(alerts, dict) and alerts.get("critical") is False
    results.append(_ok("alerts_non_critical", alerts_ok, f"HTTP {code} critical={isinstance(alerts, dict) and alerts.get('critical')}"))

    # Public config — no secrets, billing/demo off
    code, pub = _get(api.rstrip("/") + "/api/config/public")
    pub_ok = code == 200 and isinstance(pub, dict)
    blob = json.dumps(pub).lower() if pub_ok else ""
    results.append(_ok("public_config", pub_ok and "sk-" not in blob and "jwt_secret" not in blob, f"HTTP {code}"))
    if pub_ok:
        results.append(_ok("billing_pending", pub.get("billingEnabled") in (False, None, 0), str(pub.get("billingEnabled"))))
        results.append(_ok("demo_login_disabled", not pub.get("demoLoginEnabled"), str(pub.get("demoLoginEnabled"))))
        email = pub.get("email") or {}
        results.append(_ok(
            "email_not_falsely_sending",
            email.get("canSend") is False or email.get("sendingEnabled") is False or email.get("status") in ("configured_disabled", "disabled", "not_configured"),
            str(email.get("status")),
        ))
        oauth = pub.get("oauth") or {}
        for p in ("google", "microsoft", "slack"):
            st = oauth.get(p)
            results.append(_ok(f"oauth_{p}_status", st in ("configured", "not_configured", "reconnect_required", "connected"), str(st)))

    # Secret scrub on ready/alerts payloads
    for label, payload in (("ready_payload", ready), ("alerts_payload", alerts)):
        raw = json.dumps(payload).lower() if isinstance(payload, dict) else str(payload).lower()
        results.append(_ok(f"{label}_no_secrets", "sk-" not in raw and "jwt_secret" not in raw and "openai_api_key" not in raw, ""))

    return all(r["ok"] for r in results), results


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistify local/Docker release gate")
    parser.add_argument("--frontend", default=os.environ.get("FRONTEND_URL") or os.environ.get("E2E_BASE_URL") or "http://127.0.0.1:3000")
    parser.add_argument("--api", default=os.environ.get("API_URL") or os.environ.get("E2E_API_URL") or "http://127.0.0.1:8000")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    ok, results = run(args.frontend.rstrip("/"), args.api.rstrip("/"))
    if args.json:
        print(json.dumps({"ok": ok, "frontend": args.frontend, "api": args.api, "checks": results}, indent=2))
    else:
        print(f"Assistify release gate — frontend={args.frontend} api={args.api}")
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            detail = f" — {r['detail']}" if r.get("detail") else ""
            print(f"  [{mark}] {r['check']}{detail}")
        print("RESULT:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
