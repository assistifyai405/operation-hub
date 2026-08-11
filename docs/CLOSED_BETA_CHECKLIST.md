# Closed beta release checklist (Sprint 28)

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

## Beta configuration

- [ ] `BETA_MODE=true`
- [ ] Subtle **Assistify Beta** indicator visible when authenticated
- [ ] **Send feedback** works; owner can view submissions
- [ ] `AI_DAILY_REQUEST_LIMIT` set (sensible default 200)
- [ ] Ops view shows AI usage, feedback count, worker/scheduler, failed jobs

## Async jobs

- [ ] `enqueue_safe_test_job.py --mode noop` → succeeded; queue drains
- [ ] `enqueue_safe_test_job.py --mode fail` → failed / dead-letter path
- [ ] Stop worker → READY degrades; start worker → READY recovers (heartbeat-based)

## AI

- [ ] Real OpenAI smoke passed **or** explicitly marked **PENDING** (no fake pass)
- [ ] Proposal generation works with live key (client → project → proposal persists after refresh)
- [ ] Copilot / AI Agents reachable in UI (no provider secret leakage on errors)
- [ ] Daily limit returns clear **429** when exceeded (server-side)

## Product smoke

- [ ] Register / login
- [ ] Onboarding completes (**no** demo/fake data seeded)
- [ ] Client / project / task CRUD
- [ ] Empty Morning Brief when workspace empty (no invented metrics)
- [ ] Proposal generation (mock or live)
- [ ] Copilot chat
- [ ] AI Agents list (custom agents hidden)
- [ ] Team invite: if email disabled, manual-link messaging is honest
- [ ] Logout / login again — data persists
- [ ] **No** demo login path enabled

## Billing / legal / brand

- [ ] Billing shows **“Billing is not available during beta.”** (no fake Active plan / trial)
- [ ] Privacy / Terms / Beta notice pages load with placeholders (no invented KVK/VAT)
- [ ] Positioning: AI-powered business operating system
- [ ] No Emergent / Operation Hub / fake free trial copy in product UI

## Readiness honesty

- [ ] OAuth status honest (`configured` / `not_configured`) — no fake connected
- [ ] Email sending disabled by default; no false “sent”
- [ ] **No secrets** in UI, public config, health, or logs (`sk-`, JWT, Resend keys)
- [ ] Cookie-only auth; no JWT in localStorage

## Tests (CI / local)

- [ ] Full backend pytest
- [ ] Frontend unit tests
- [ ] `CI=true yarn build`
- [ ] Playwright smoke
- [ ] Playwright RC journey
- [ ] Playwright beta journey (`e2e/tests/beta-journey.spec.js`)

## KVK / business prep

- [ ] [`KVK_READINESS_CHECKLIST.md`](./KVK_READINESS_CHECKLIST.md) reviewed by owner
- [ ] [`KVK_LAUNCH_INFO.md`](./KVK_LAUNCH_INFO.md) env keys identified for post-registration fill

## Explicitly not required for closed beta

- [ ] Stripe / production deploy / custom agents / OAuth providers / real email sending
