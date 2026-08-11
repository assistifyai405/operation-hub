# Assistify

AI-powered business operating system for small businesses and freelancers — manage
clients, projects, tasks, AI-assisted work, proposals/contracts/invoices, and workflow
in one workspace.

This repository is the **source of truth**. Do not regenerate the product from scratch.

## Closed beta (Sprint 28)

See:

- [`docs/CLOSED_BETA_RUNBOOK.md`](./docs/CLOSED_BETA_RUNBOOK.md) — start stack, beta mode, AI limit, invites, feedback, shutdown
- [`docs/CLOSED_BETA_CHECKLIST.md`](./docs/CLOSED_BETA_CHECKLIST.md)
- [`docs/KVK_READINESS_CHECKLIST.md`](./docs/KVK_READINESS_CHECKLIST.md)
- [`docs/KVK_LAUNCH_INFO.md`](./docs/KVK_LAUNCH_INFO.md)

Quick Docker path (Windows operator):

```powershell
$env:OPENAI_API_KEY="sk-..."
docker compose build
docker compose up --force-recreate
python scripts/check_local_release.py
```

Key closed-beta env: `BETA_MODE=true`, `AI_DAILY_REQUEST_LIMIT=200`, demo/billing flags off.

## Architecture

| Layer | Stack |
|---|---|
| Frontend | React 19 + React Router 7, Craco/CRA, Tailwind, shadcn/ui |
| Backend | FastAPI + Uvicorn |
| Database | MongoDB (Motor/PyMongo) |
| Auth | Cookie-only JWT access (30m) + rotating refresh (httpOnly), CSRF, bcrypt, org tenancy |
| AI | `AI_PROVIDER=openai` (OpenAI API) or `emergent` (optional proxy) |
| Storage | `STORAGE_PROVIDER=local` (filesystem) or `emergent` (optional object store) |

```
frontend/   → SPA (port 3000)
backend/    → FastAPI /api/* (port 8000)
memory/     → PRD / product history
```

## Prerequisites

- Python 3.11+ (3.12 tested)
- Node.js 18+ and Yarn (or npm)
- MongoDB 6+ running locally or a MongoDB Atlas URI
- Optional: OpenAI API key for AI features; Resend API key for real email

## Quick start (local)

### 1. MongoDB

```bash
# Local example
mongod --dbpath /data/db
# Or use Atlas and put the URI in MONGO_URL
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set MONGO_URL, DB_NAME, JWT_SECRET
# For local AI: AI_PROVIDER=openai + OPENAI_API_KEY
# For local files: STORAGE_PROVIDER=local

uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API root: http://localhost:8000/api/

### 3. Frontend

```bash
cd frontend
cp .env.example .env
# REACT_APP_BACKEND_URL=http://localhost:8000

yarn install    # or: npm install
yarn start      # or: npm start → http://localhost:3000
```

Register a new account at `/register`, or set `ENABLE_DEMO_SEED=true` in `backend/.env` and restart to create the optional demo user.

## Environment variables

See also:

- [`.env.example`](./.env.example) (root overview)
- [`backend/.env.example`](./backend/.env.example)
- [`frontend/.env.example`](./frontend/.env.example)

### Backend — required

| Variable | Description |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `JWT_SECRET` | Signing secret (≥32 chars in production; weak defaults rejected) |

### Backend — production requirements

| Variable | Description |
|---|---|
| `ENVIRONMENT` | `production` or `development` (default `development`) |
| `CORS_ORIGINS` | Explicit comma-separated origins (**required** in production; `*` forbidden) |
| `FRONTEND_URL` | Used for verify/reset email links |

### Backend — AI

| Variable | Description |
|---|---|
| `AI_PROVIDER` | `openai` (default) or `emergent` |
| `AI_MODEL` | e.g. `gpt-4o-mini` (OpenAI) or `gpt-5.4` (Emergent) |
| `OPENAI_API_KEY` | Required when `AI_PROVIDER=openai` |
| `EMERGENT_LLM_KEY` | Required when `AI_PROVIDER=emergent` |

### Backend — storage

| Variable | Description |
|---|---|
| `STORAGE_PROVIDER` | `local` (default in development) or `emergent` |
| `UPLOAD_DIR` | Local upload root (default `backend/uploads`) |
| `EMERGENT_LLM_KEY` | Also required when `STORAGE_PROVIDER=emergent` |

### Backend — optional

| Variable | Description |
|---|---|
| `ENABLE_DEMO_SEED` | `true` to create/sync the demo account on startup (**off by default**) |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | Demo credentials when seeding is enabled |
| `RESEND_API_KEY` / `FROM_EMAIL` | Real transactional email; omit for dev-mode link fallback |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | Override auto cookie policy |

### Frontend

| Variable | Description |
|---|---|
| `REACT_APP_BACKEND_URL` | Backend origin, e.g. `http://localhost:8000` |
| `REACT_APP_BILLING_ENABLED` | `true` only when Stripe is integrated (keep `false`) |

**Never commit real `.env` files or secrets.**

## Using OpenAI instead of Emergent

```bash
# backend/.env
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
# Leave EMERGENT_LLM_KEY unset
```

All product features (generators, Copilot, Assistant, Knowledge Brain, CRM briefs) go through `ai_service.AIService` and pick up this provider automatically. Clear errors are returned if the selected provider has no API key.

To keep Emergent as a fallback:

```bash
AI_PROVIDER=emergent
AI_MODEL=gpt-5.4
EMERGENT_LLM_KEY=...
```

## Local file storage

```bash
STORAGE_PROVIDER=local
UPLOAD_DIR=./uploads
```

Uploads are written under `UPLOAD_DIR` with org-scoped paths. Download still uses the existing authenticated routes:

- `GET /api/documents/{id}/file`
- `GET /api/settings/image/{id}`

These require a Bearer token or the httpOnly `access_token` cookie, enforce organization isolation, and reject path traversal. No frontend changes are required.

## Local authentication (HTTP)

When `ENVIRONMENT=development` and `FRONTEND_URL` is `http://…`, cookies use `Secure=False` and `SameSite=Lax` so login/refresh works on localhost HTTP.

In production (or HTTPS frontend URLs), cookies stay `Secure=True` and `SameSite=None` for cross-origin SPAs.

## Team members & invitations

Roles on `users.role` (org-scoped via `organizationId`):

| Role | Capabilities |
|---|---|
| **owner** | Full access; invite; change roles; remove members; transfer ownership |
| **admin** | Product access; invite; remove regular members; cannot touch owner/ownership |
| **member** | Product access only; cannot manage team or org settings (branding/org/docs/AI settings) |

### Invite flow

1. Owner/Admin opens **Settings → Team** and invites by email + role (`admin` or `member`).
2. Email is sent via Resend when `RESEND_API_KEY` is set. In development without Resend, the API returns `invitationLink` (never in production).
3. Invitee opens `/invite/:token`, then registers or signs in with the invited email.
4. Accept connects them to the organization. Tokens are single-use, hashed at rest (`tokenHash`), and expire after `INVITATION_EXPIRY_DAYS` (default 7).

Ownership transfer: **Settings → Team → Transfer** (owner only). Owners cannot leave/remove themselves without transferring first.

Seat helper `GET /api/team/seats` reports `active_members` + `pending_invitations` for future Stripe limits (not enforced yet).

## Outbound email (Email Center)

Providers (`EMAIL_PROVIDER`):

| Provider | Behavior |
|---|---|
| **console** | Default in development. Validates and records sends; never calls external APIs. Safe metadata may appear in API responses in development only. |
| **resend** | Production provider. Requires `RESEND_API_KEY` + `FROM_EMAIL`. |

**Important:** `EMAIL_SENDING_ENABLED` defaults to **false**. Outbound product mail also requires **Settings → Email → Enable organization sending**. Transactional mail (verify / reset / invite) uses the provider without that outbound gate so auth still works.

### Approval workflow

1. Compose a draft in **Emails** (or let an automation create one).
2. If org `approvalRequired` is on, submit for approval; owners/admins approve (admins cannot self-approve).
3. Send only when approved (and gates above pass). Atomic status transition prevents duplicate provider calls.
4. Daily org limit: `min(org.dailySendingLimit, EMAIL_DAILY_LIMIT)`. Max 20 recipients per message.

Automations (`prepare_email` / `prepare_followup`) create real `outbound_emails` drafts linked by `automationApprovalId` (deduped). They never silent-send unless org `autoSendFromAutomation` is on, approval is off, and global/org sending is enabled.

### Resend webhooks

`POST /api/webhooks/resend` verifies Svix signatures with `RESEND_WEBHOOK_SECRET` and updates `deliveryStatus` (`delivered` / `bounced` / `complained`). No JWT. Idempotent via `svix-id`.

## Integrations Hub

Organization-scoped connections for Google Workspace, Microsoft 365, Slack, Discord, Zapier, and generic REST webhooks.

| Provider | Auth | Capabilities |
|---|---|---|
| Google Workspace | OAuth | Gmail inbox sync (`gmail.readonly`), Gmail send, Calendar events, Google Tasks |
| Microsoft 365 | OAuth | Outlook inbox sync (`Mail.Read`), Outlook send (`Mail.Send`), Calendar events |
| Slack | OAuth or Incoming Webhook | `chat.postMessage` / webhook |
| Discord | Incoming Webhook | Channel messages |
| Zapier | Catch Hook URL | Automation triggers |
| Webhook | HTTPS URL | Generic JSON POST |

API: `GET /api/integrations`, `GET /api/integrations/status`, `POST /api/integrations/connect|disconnect|refresh|health`, OAuth callback at `/api/integrations/oauth/callback/{provider}`. Refresh tokens and webhook secrets are Fernet-encrypted; never returned to the frontend.

Automations can run: `create_calendar_event`, `create_google_task`, `send_slack_message`, `send_discord_message`, `trigger_webhook` (external / approval-gated by default).

## Shared Inbox (Sprint 16)

Turns connected Google Workspace / Microsoft 365 accounts into an organization-scoped business inbox.

### Required OAuth scopes

**Google** (see `GOOGLE_SCOPES` in `backend/integrations/providers.py`):

- `openid`, `email`, `profile`
- `https://www.googleapis.com/auth/gmail.readonly` — inbox sync
- `https://www.googleapis.com/auth/gmail.send` — existing outbound send
- `https://www.googleapis.com/auth/calendar.events`, `https://www.googleapis.com/auth/tasks`

**Microsoft Graph**:

- `openid`, `email`, `profile`, `offline_access`, `User.Read`
- `Mail.Read` — inbox sync
- `Mail.Send` — existing outbound send
- `Calendars.ReadWrite`

After deploying scope changes, users must **reconnect** Google/Microsoft under **Integrations** so consent includes mail read.

### Sync behavior

- Manual: Inbox UI sync buttons, or `POST /api/inbox/mailboxes/{id}/sync` (owner/admin; rate-limited).
- Scheduled-ready: `python -m inbox.sync_all` (optional `--org`, `--mailbox`, `--force-full`).
- Gmail: history API when `syncCursor` (historyId) is valid; falls back to INBOX list + cursor reset when history is stale (404).
- Outlook: Graph Inbox delta queries; 410/404 resets the delta link and re-bootstraps.
- Per-mailbox in-process lock prevents overlapping sync jobs. Bounded page/message limits. Spam/trash (Gmail) and Junk/Deleted (Outlook) are not ingested by default.
- Provider rate limits surface as clear mailbox `lastError` / HTTP 400 — retry later.
- Dedup: unique `(organizationId, mailboxId, providerMessageId)`; also skip by `internetMessageId` and outbound-sent IDs.

### AI reply workflow

1. Open a thread → **Summarize** or **Draft reply**.
2. Draft reply creates a Sprint 14 `outbound_emails` document (`source=ai`, usually `pending_approval`) with threading metadata (`inboxThreadId`, `providerThreadId`, `inReplyTo`, `references`, `replyProvider`).
3. Edit/approve/send only via Email Center — **never auto-sent** from inbox endpoints.
4. Email Center shows linked conversation + “View conversation”.

### Privacy & retention

- Strict org isolation on all inbox collections and attachment downloads.
- HTML sanitized server-side (scripts/images stripped; safe `https`/`mailto` links only). External images are not auto-loaded.
- Attachment metadata synced only; bytes fetched on demand via authenticated API (15 MB cap, safe filenames, `Content-Disposition: attachment`).
- OAuth tokens stay encrypted; never logged or returned to the frontend.

### Known limitations

- **Graph send confirmation:** Microsoft Graph often returns `202 Accepted` with an empty body. Assistify creates a draft then sends and re-reads the message; if confirmation fails, status becomes `delivery_unknown` / `needs_review` rather than blindly retrying.
- Read/unread is local DB state (`gmail.readonly` / no modify scopes for labels).
- Live Gmail/Outlook success requires real OAuth credentials and reconnect after scope updates — mocked provider tests do not prove live connectivity.
- Inbox automation events are recorded and listed in trigger metadata; broad auto-execution of user workflows on those events is not enabled yet.
- Large-file Graph upload sessions are not implemented; attachment total soft-cap is ~20 MB.

## Native provider sending (Sprint 17)

### Transport routing

| Message type | Transport |
|---|---|
| Inbox-linked reply (`inboxThreadId` / `mailboxId` / `replyProvider`) | **Gmail** or **Microsoft Graph only** — never silent Resend fallback |
| Standalone outbound email | Configured `EMAIL_PROVIDER` (`console` or `resend`) |

Stored fields: `transportProvider`, `mailboxId`, `integrationId`, `providerThreadId`, `providerConversationId`, `internetMessageId`, `sentVia`, `providerRawStatus`, safe `transportMetadata`.

### Gmail native send

- MIME multipart (text + HTML), `In-Reply-To` / `References`, Gmail `threadId`
- From = connected mailbox address (no spoofing)
- Token refresh via Sprint 15 integration layer
- Persists `providerMessageId` + `internetMessageId` for sync dedupe

### Microsoft native send

- Prefer `createReply` → patch → send when replying to an inbound Graph message
- New mail: create draft → send → confirm by GET
- Conversation ID / internetMessageId retained when Graph returns them

### Idempotency & ambiguous delivery

- Atomic `approved|failed|… → sending` claim with `lastSendAttemptId`
- Confirmed success never re-calls the provider
- Ambiguous Graph acceptance → `delivery_unknown` / `needs_review` (check mailbox before retry)
- Clear failed sends may be retried; never retry when a provider message id already exists on an unconfirmed record

### Attachment limits

- Org-scoped document refs only; path-traversal rejected
- ~10 MB per file / ~20 MB total soft limits for native send
- Metadata preserved; no executable rendering

Inbox API: `/api/inbox/mailboxes`, `/api/inbox/threads`, summarize, draft-reply, link/unlink, attachment download, events catalog.

## Deployment (Sprint 18)

Assistify is deployable outside Emergent. There is **no one-click cloud deploy** in this repo — use Docker Compose locally and your preferred hosts in production.

### Local Docker Compose

```bash
export OPENAI_API_KEY=sk-...   # optional; needed for live AI
docker compose build
docker compose up --force-recreate
# API http://localhost:8000  ·  UI http://localhost:3000
# Services: mongo, redis, backend, worker, scheduler, frontend
python scripts/check_local_release.py
```

Health: `GET /api/health/live`, `/api/health/ready`, `/api/health/alerts`.
Async ops: [`docs/ASYNC_WORKERS.md`](docs/ASYNC_WORKERS.md).  
Closed beta: [`docs/CLOSED_BETA_RUNBOOK.md`](docs/CLOSED_BETA_RUNBOOK.md) · [`docs/CLOSED_BETA_CHECKLIST.md`](docs/CLOSED_BETA_CHECKLIST.md).

### Recommended production layout

| Component | Suggestion |
|---|---|
| API | Render / Railway / any container host running `backend` image |
| Worker | Same image, `python -m jobs.worker` |
| Scheduler | Same image, `python -m jobs.scheduler` (one replica) |
| Frontend | Vercel / Netlify / static nginx (`frontend` image) |
| MongoDB | **MongoDB Atlas** (do not require self-hosted Mongo in cloud) |
| Redis | Upstash / Redis Cloud / managed Redis (`REDIS_URL`) |

See `docker-compose.production.example.yml`. Set strong `JWT_SECRET`, explicit `CORS_ORIGINS`, HTTPS `FRONTEND_URL`, OAuth redirect URIs to the production API host, verify Resend domain, reconnect Google/Microsoft after URL/scope changes.

### Workers & jobs

- Without Redis / with `WORKER_ENABLED=false`, jobs run **inline** (dev-friendly).
- Production multi-worker mode requires `REDIS_URL` (+ `REQUIRE_REDIS` / `WORKER_ENABLED`).
- Job payloads store **IDs only** (never OAuth tokens).
- Intervals: `INBOX_SYNC_INTERVAL_MINUTES`, `INTEGRATION_HEALTH_INTERVAL_MINUTES`, `EMAIL_RECONCILIATION_INTERVAL_MINUTES`.

### Observability

- Structured JSON logs when `JSON_LOGS=true` (default in production).
- Optional `SENTRY_DSN` (disabled when unset).
- Settings → **Operations** (owner/admin): readiness, failed jobs, stuck emails, mailbox sync, reconcile.

### Backups

```bash
export MONGO_URL='mongodb+srv://…'
export DB_NAME=assistify
./scripts/backup-mongo.sh ./backups
```

Also back up env secrets and object-storage uploads. Roll back by redeploying the previous image tag and restoring Atlas point-in-time / dump if needed.

### CI

GitHub Actions (`.github/workflows/ci.yml`): backend pytest Sprint 12–18, frontend build, Docker image builds, basic secret scan.

## Running tests

```bash
cd backend
source .venv/bin/activate

# Sprint 12–18 suite
pytest tests/test_sprint12_hardening.py tests/test_sprint12_http.py \
       tests/test_sprint13_team.py tests/test_sprint14_email.py \
       tests/test_sprint15_integrations.py tests/test_sprint16_inbox.py \
       tests/test_sprint17_native_send.py tests/test_sprint18_ops.py -n 0 -q

# Optional Redis integration (when REDIS_URL is set):
# REDIS_URL=redis://localhost:6379/0 pytest tests/test_sprint18_ops.py -n 0 -q
```

## Deployment checklist

1. `ENVIRONMENT=production`
2. Strong unique `JWT_SECRET` (≥32 random chars)
3. Explicit `CORS_ORIGINS` (no `*`)
4. `FRONTEND_URL` set to the real SPA origin (HTTPS)
5. `ENABLE_DEMO_SEED=false` (or unset)
6. Choose AI: `OPENAI_API_KEY` + `AI_PROVIDER=openai` **or** Emergent key
7. Choose storage: durable `STORAGE_PROVIDER` (local disk only if the volume is persistent)
8. Email: `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, `FROM_EMAIL` / `FROM_NAME`; keep `EMAIL_SENDING_ENABLED=false` until org settings and approval rules are reviewed, then enable deliberately
9. Optional: `RESEND_WEBHOOK_SECRET` + Resend dashboard webhook → `/api/webhooks/resend`
10. Confirm cookies are Secure on HTTPS
11. Do not ship default demo passwords
12. Integrations: set `INTEGRATION_ENCRYPTION_KEY`, Google/Microsoft/Slack OAuth client credentials, and redirect URIs pointing at `/api/integrations/oauth/callback/{provider}`

## Product docs

Historical sprint notes and feature inventory live in [`memory/PRD.md`](./memory/PRD.md).
