# Assistify OS (Operations Hub)

Premium AI business operating system for agencies and founders — clients, projects, CRM, documents, automations, and Knowledge Brain in one dark-theme workspace.

This repository is the **source of truth**. Do not regenerate the product from scratch.

## Architecture

| Layer | Stack |
|---|---|
| Frontend | React 19 + React Router 7, Craco/CRA, Tailwind, shadcn/ui |
| Backend | FastAPI + Uvicorn |
| Database | MongoDB (Motor/PyMongo) |
| Auth | JWT access (30m) + rotating refresh (httpOnly cookie), bcrypt passwords, org tenancy |
| AI | `AI_PROVIDER=openai` (OpenAI API) or `emergent` (optional Emergent proxy) |
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

## Running tests

```bash
cd backend
source .venv/bin/activate

# Sprint 12–14 suite
pytest tests/test_sprint12_hardening.py tests/test_sprint12_http.py tests/test_sprint13_team.py tests/test_sprint14_email.py -n 0 -q

# Full HTTP suites need a running API + Mongo:
export REACT_APP_BACKEND_URL=http://localhost:8000
pytest tests/test_auth.py -n 0 -q
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

## Product docs

Historical sprint notes and feature inventory live in [`memory/PRD.md`](./memory/PRD.md).
