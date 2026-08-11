# Closed beta runbook (Sprint 28)

Concise steps to run Assistify as a **local closed-beta release candidate** for 1–5 real users.

No production deploy. Billing/Stripe is off. Custom agents stay hidden. Demo login stays off.

## 1. Start the full stack

```bash
# From repo root (Windows: Docker Desktop + PowerShell/WSL)
$env:OPENAI_API_KEY="sk-..."   # PowerShell; optional but required for real AI
docker compose build
docker compose up --force-recreate
```

Services: `frontend` (:3000), `backend` (:8000), `mongo`, `redis`, `worker`, `scheduler`.

## 2. Run the release gate

```bash
python scripts/check_local_release.py
# or:
FRONTEND_URL=http://localhost:3000 API_URL=http://localhost:8000 python scripts/check_local_release.py --json
```

Expect: frontend reachable; `/api/health/live` + `/api/health/ready` = 200; alerts non-critical;
Mongo/Redis healthy; `worker` + `scheduler` heartbeats `running`; `syncMode=false`.

## 3. Enable beta mode

Set in backend / compose:

```bash
BETA_MODE=true
```

Optional frontend build fallback: `REACT_APP_BETA_MODE=true` (runtime public config wins).

When enabled:

- Subtle **Assistify Beta** indicator in the authenticated product
- **Send feedback** entry in the header
- Owner/admin **Beta feedback** settings tab

## 4. Set AI daily limit

```bash
AI_DAILY_REQUEST_LIMIT=200
```

- Per-workspace, server-side enforcement (not frontend-only)
- `0` = unlimited (not recommended for shared owner keys)
- Exceeded requests return **HTTP 429** with a clear message
- Owner/admin: Settings → Operations (AI requests today / daily limit)
- Also mirrored on Settings → Billing as informational usage (no payment)

## 5. Create / invite first beta users

1. Register the owner account at `/register` (or use an existing owner).
2. Complete onboarding (no sample/demo data is seeded).
3. Settings → Team → invite by email.
4. **If `EMAIL_SENDING_ENABLED=false`:** the API creates the invite but does **not** pretend an email was sent. In development, copy the returned invite link and share it manually.
5. Invitee opens `/invite/:token`, accepts, and joins the same workspace.

Do not create a second user system — use Team invites only.

## 6. Inspect feedback

- In-app: Settings → **Beta feedback** (owner/admin)
- API: `GET /api/feedback` (admin), `POST /api/feedback` (any authenticated user)

Categories: Bug · Idea · Confusing · Other. Stored in MongoDB, org-scoped.

## 7. Inspect AI usage

- Settings → Operations → **AI requests today** / **AI daily limit**
- `GET /api/ops/ai-usage` (admin)
- `GET /api/ops/status` includes `aiUsage`, `betaFeedbackCount`, workspace counts, worker/scheduler

## 8. Shut down safely

```bash
docker compose stop
# or fully tear down:
docker compose down
# volumes (destroys local Mongo data — only if intentional):
docker compose down -v
```

## Required / important env

| Var | Notes |
|-----|--------|
| `BETA_MODE` | `true` for closed beta UI |
| `AI_DAILY_REQUEST_LIMIT` | Default `200` |
| `OPENAI_API_KEY` | Host env for compose; never commit |
| `JWT_SECRET` | Strong outside local |
| `EMAIL_SENDING_ENABLED` | Keep `false` unless Resend is ready |
| `ENABLE_DEMO_LOGIN` / `ENABLE_DEMO_SEED` | Keep `false` |
| `REACT_APP_BILLING_ENABLED` | `false` |
| `LEGAL_*` | Optional placeholders — see [`KVK_LAUNCH_INFO.md`](./KVK_LAUNCH_INFO.md) |

## Live AI smoke (opt-in)

```bash
export RUN_LIVE_AI_TESTS=true
export OPENAI_API_KEY=sk-...   # real key; never sk-test*
cd backend && .venv/bin/pytest tests/test_sprint27_beta_runtime.py -k live -q
```

Do **not** fake a PASS if the provider is unavailable.

## Windows verification commands (operator)

```powershell
docker compose build
docker compose up --force-recreate
python scripts/check_local_release.py
```

## Related

- [`CLOSED_BETA_CHECKLIST.md`](./CLOSED_BETA_CHECKLIST.md)
- [`KVK_READINESS_CHECKLIST.md`](./KVK_READINESS_CHECKLIST.md)
- [`KVK_LAUNCH_INFO.md`](./KVK_LAUNCH_INFO.md)
- [`ASYNC_WORKERS.md`](./ASYNC_WORKERS.md)
- [`AUTH_COOKIES.md`](./AUTH_COOKIES.md)
