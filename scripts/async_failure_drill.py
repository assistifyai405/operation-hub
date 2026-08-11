#!/usr/bin/env python3
"""Documented async failure/recovery drill helper (local or compose-mapped ports).

Does NOT stop Docker services itself — only observes READY while you stop/start
worker/scheduler in another terminal.

Usage:
  # Terminal A:
  python scripts/async_failure_drill.py --watch 120

  # Terminal B:
  docker compose stop worker
  # wait until script reports READY != 200
  docker compose start worker
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error


def ready_code(api: str) -> tuple[int, dict]:
    url = api.rstrip("/") + "/api/health/ready"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            return resp.status, data
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8", errors="replace") or "{}")
        except Exception:
            data = {}
        return e.code, data
    except Exception as e:
        return 0, {"error": str(e)[:120]}


def main() -> int:
    p = argparse.ArgumentParser(description="Watch READY during worker stop/start drill")
    p.add_argument("--api", default=os.environ.get("API_URL") or "http://127.0.0.1:8000")
    p.add_argument("--watch", type=float, default=120.0, help="Seconds to watch")
    p.add_argument("--interval", type=float, default=3.0)
    args = p.parse_args()

    print(f"Watching READY at {args.api} for {args.watch}s")
    print("In another terminal: docker compose stop worker  (then start worker)")
    end = time.time() + args.watch
    seen_degraded = False
    seen_ok = False
    while time.time() < end:
        code, data = ready_code(args.api)
        jobs = ((data.get("checks") or {}).get("jobs") or {}) if isinstance(data, dict) else {}
        worker = (jobs.get("worker") or {}).get("status")
        sched = (jobs.get("scheduler") or {}).get("status")
        print(f"  READY={code} worker={worker} scheduler={sched} syncMode={jobs.get('syncMode')}")
        if code == 200:
            seen_ok = True
        if code in (503, 0) or worker in ("stale", "unavailable"):
            seen_degraded = True
        time.sleep(args.interval)

    print(f"observed_ok={seen_ok} observed_degraded={seen_degraded}")
    if not seen_ok:
        print("FAIL: never saw READY 200")
        return 1
    print("OK (manual stop/start must produce degraded then recover — check flags above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
