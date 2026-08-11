# Closed beta runbook (Sprint 27)

Concise steps to run Assistify as a **local closed-beta release candidate**.  
No production deploy. Billing/Stripe is off. Custom agents stay hidden.

## Start the stack

```bash
# From repo root (Windows: use Docker Desktop + PowerShell/WSL)
export OPENAI_API_KEY=sk-...   # optional but required for real AI
docker compose build
docker compose up --force-recreate
```

Services: `frontend` (:3000), `backend` (:8000), `mongo`, `redis`, `worker`, `scheduler`.

## Required / important env

| Var | Notes |
|-----|--------|
| `OPENAI_API_KEY` | Host env interpolated into compose (`${OPENAI_API_KEY:-}`). No hardcoded test key. |
| `JWT_SECRET` | Set in compose for local only; use a strong secret outside local. |
| `REDIS_URL` / `MONGO_URL` | Provided by compose service DNS. |
| `WORKER_ENABLED` / `SCHEDULER_ENABLED` / `REQUIRE_REDIS` | `true` on API + workers in compose. |
| `EMAIL_SENDING_ENABLED` | Keep `false` (console provider). |
| `ENABLE_DEMO_LOGIN` / `ENABLE_DEMO_SEED` | Keep `false`. |
| `REACT_APP_BILLING_ENABLED` | `false` (Stripe not implemented). |

Never commit real secrets. Use `.env.example` as a template only.

## Verify health (release gate)

```bash
python scripts/check_local_release.py
# or:
FRONTEND_URL=http://localhost:3000 API_URL=http://localhost:8000 python scripts/check_local_release.py --json
```

Expect: frontend reachable; `/api/health/live` + `/api/health/ready` = 200; alerts non-critical; Mongo/Redis healthy; `worker` + `scheduler` heartbeats `running`; `syncMode=false`; `workerEnabled`/`schedulerEnabled` true.

## Verify worker / scheduler + Redis jobs

```bash
# Heartbeats via ready payload
curl -s http://localhost:8000/api/health/ready | python -m json.tool

# Safe job drain (noop) + dead-letter path (fail)
REDIS_URL=redis://127.0.0.1:6379/0 MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=assistify \
  python scripts/enqueue_safe_test_job.py --mode noop
REDIS_URL=redis://127.0.0.1:6379/0 MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=assistify \
  python scripts/enqueue_safe_test_job.py --mode fail
```

`DB_NAME` must match the running API/worker database (compose default: `assistify`).

## Async failure / recovery drill

```bash
docker compose stop worker
# Wait ~90s for heartbeat TTL → READY should degrade (503) when REQUIRE_REDIS=true
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/health/ready

docker compose start worker
# Heartbeat resumes → READY returns 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/health/ready

# Optional: same pattern for scheduler
docker compose stop scheduler
# ...observe degrade...
docker compose start scheduler
```

This validates **stale heartbeat detection**, not merely config flags.

## Live AI smoke (opt-in)

```bash
export RUN_LIVE_AI_TESTS=true
export OPENAI_API_KEY=sk-...   # real key; never sk-test*
cd backend && .venv/bin/pytest tests/test_sprint27_beta_runtime.py -k live -q
# or Sprint 26 provider smoke:
.venv/bin/pytest tests/test_sprint26_async_security.py::test_live_ai_smoke_optional -q
```

If the key is missing: tests **skip (PENDING)** — do not treat as pass.

## Inspect logs (sanity)

```bash
docker compose logs backend --tail=200
docker compose logs worker --tail=200
docker compose logs scheduler --tail=200
docker compose logs redis --tail=100
```

Flag: restart loops, repeated exceptions, Redis connection errors, stale heartbeats, auth storms, any `sk-` / API key material in output.

## Reset local beta test data

```bash
docker compose down
docker volume rm $(docker volume ls -q | grep mongo_data) 2>/dev/null || true
# Or wipe DB only while stack is up:
# docker compose exec mongo mongosh assistify --eval 'db.dropDatabase()'
docker compose up --force-recreate
```

## Stop the stack

```bash
docker compose down
# Add -v to also delete the mongo volume
```

## OAuth / email readiness

- OAuth: optional. `GET /api/config/public` → `oauth.{google,microsoft,slack}` = `configured` | `not_configured`.
- Authenticated: `GET /api/integrations/status` → `oauthReadiness` + `redirectUriTemplates` (uses `API_URL`).
- Never fake a successful OAuth connection without real credentials.
- Email: console + `EMAIL_SENDING_ENABLED=false` → status `configured_disabled`, `canSend=false`.

## Known limitations

- **Billing / Stripe:** off / pending
- **OAuth:** optional; providers may be `not_configured`
- **Custom agents:** hidden / not part of closed beta surface
- **Production deploy:** not automated by this sprint
- **Demo login:** disabled
