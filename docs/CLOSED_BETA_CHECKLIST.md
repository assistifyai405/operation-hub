# Closed beta release checklist (Sprint 27)

Use with [`CLOSED_BETA_RUNBOOK.md`](./CLOSED_BETA_RUNBOOK.md) and `python scripts/check_local_release.py`.

Mark each item only after you verify it on your machine (Docker Desktop on Windows is the intended runtime proof).

## Infrastructure

- [ ] `docker compose build` green
- [ ] `docker compose up --force-recreate` — all services running
- [ ] `frontend` reachable (`http://localhost:3000`)
- [ ] `backend` `/api/health/live` = **200**
- [ ] `backend` `/api/health/ready` = **200**
- [ ] `/api/health/alerts` — **non-critical**
- [ ] Mongo healthy
- [ ] Redis healthy
- [ ] Worker heartbeat = **running**
- [ ] Scheduler heartbeat = **running**
- [ ] `syncMode` = **false**
- [ ] `workerEnabled` = **true** / `schedulerEnabled` = **true**
- [ ] Release gate script exits **0**: `python scripts/check_local_release.py`

## Async jobs

- [ ] `enqueue_safe_test_job.py --mode noop` → succeeded; queue drains
- [ ] `enqueue_safe_test_job.py --mode fail` → failed / dead-letter path
- [ ] Stop worker → READY degrades; start worker → READY recovers (heartbeat-based)

## AI

- [ ] Real OpenAI smoke passed **or** explicitly marked **PENDING** (no fake pass)
- [ ] Proposal generation works with live key (client → project → proposal persists after refresh)
- [ ] Copilot / AI Agents reachable in UI (no provider secret leakage on errors)

## Product smoke

- [ ] Register / login
- [ ] Onboarding completes
- [ ] Client / project / task CRUD
- [ ] Proposal generation (mock or live)
- [ ] Copilot chat
- [ ] AI Agents list
- [ ] Logout / login again
- [ ] **No** demo login path enabled

## Readiness honesty

- [ ] Billing pending / disabled (no Stripe)
- [ ] OAuth status honest (`configured` / `not_configured` / …) — no fake connected
- [ ] Email sending disabled by default; no false “sent”
- [ ] **No secrets** in UI, public config, health, or logs (`sk-`, JWT, Resend keys)

## Tests (CI / local)

- [ ] Full backend pytest
- [ ] Frontend unit tests
- [ ] `CI=true yarn build`
- [ ] Playwright smoke
- [ ] Playwright RC journey

## Sign-off

| Field | Value |
|-------|--------|
| Date | |
| Operator | |
| Compose OK | YES / NO |
| Live AI | PASS / PENDING / FAIL |
| Ready for 1–5 closed beta users | YES / NO |
| Notes | |
