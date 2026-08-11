# Async workers, Redis & health (Sprint 26)

## Local full-stack (Docker)

```bash
export OPENAI_API_KEY=sk-...   # optional; AI features need a real key
docker compose up --build --force-recreate
```

Services: `frontend`, `backend`, `mongo`, `redis`, `worker`, `scheduler`.

Local compose sets on the **API**:

- `WORKER_ENABLED=true` — enqueue goes to Redis (not silent sync)
- `SCHEDULER_ENABLED=true` — health expects a live scheduler heartbeat
- `REQUIRE_REDIS=true` — READY degrades without Redis / live workers

Worker/scheduler containers run `python -m jobs.worker` and `python -m jobs.scheduler`.

## Plain local (no Docker)

Without Redis / workers, the API stays in **sync mode** (`syncMode=true`): jobs run inline in the request process. This is intentional for lightweight unit tests and solo API development.

```bash
# API only
cd backend && uvicorn server:app --host 127.0.0.1 --port 8000

# Optional async stack
export REDIS_URL=redis://127.0.0.1:6379/0
export WORKER_ENABLED=true
export SCHEDULER_ENABLED=true
export REQUIRE_REDIS=true
python -m jobs.worker
python -m jobs.scheduler
```

## Health interpretation

| Endpoint | Meaning |
|----------|---------|
| `/api/health/live` | Process up (always 200 if serving) |
| `/api/health/ready` | Required deps OK; **503** when degraded |
| `/api/health/alerts` | Critical/warning hooks for monitors |

`checks.jobs` fields:

- `workerEnabled` / `schedulerEnabled` — config flags on the API process
- `requireRedis` — Redis is mandatory for readiness
- `syncMode` — true when the API runs jobs inline
- `worker` / `scheduler` — heartbeat status: `running` \| `stale` \| `unavailable` \| `disabled`
- `queueDepth` / `failedDepth` — Redis list lengths

A worker is **not** healthy just because `WORKER_ENABLED=true`. READY requires a fresh Redis heartbeat when Redis is required.

## Inspect queues

```bash
redis-cli LLEN assistify:jobs:queue
redis-cli LLEN assistify:jobs:failed
redis-cli HGETALL assistify:heartbeat:worker
redis-cli HGETALL assistify:heartbeat:scheduler
```

## Optional live AI smoke

```bash
export RUN_LIVE_AI_TESTS=true
export OPENAI_API_KEY=sk-...
cd backend && .venv/bin/pytest tests/test_sprint26_async_security.py::test_live_ai_smoke_optional -q
```

Never commit API keys. Docker compose uses `${OPENAI_API_KEY:-}` (no `sk-test` runtime fallback).
