# Staging deployment runbook

Exact steps to run Assistify OS on a **real, externally reachable** staging environment.
Provider-agnostic: any host that can run Docker images + terminate HTTPS works (Fly, Render, Railway, AWS/GCP/Azure, a VM + Caddy/nginx, etc.).

## Recommended topology

```
  Users --HTTPS--> staging.example.com          (frontend / nginx SPA)
                         |
                         | REACT_APP_BACKEND_URL
                         v
                   api.staging.example.com      (backend / uvicorn)
                      /                \
                     v                  v
            Managed MongoDB         Managed Redis
                     ^                  ^
                     |                  |
                  worker            scheduler
             (jobs.worker)       (jobs.scheduler)
```

| Component | Role |
|-----------|------|
| **frontend** | Static SPA behind HTTPS |
| **backend** | FastAPI API + cookie sessions |
| **worker** | Drains Redis job queue |
| **scheduler** | Enqueues inbox sync / health / reconcile (+ optional alert delivery) |
| **MongoDB** | Primary data store (managed) |
| **Redis** | Jobs + locks (managed; required when worker/scheduler on) |
| **TLS** | Terminated at load balancer / reverse proxy |

Compose reference: `docker-compose.staging.example.yml`  
Env template: `backend/.env.staging.example`

> `ENVIRONMENT=staging` is treated as **production-like** (fail-fast). That is intentional.

---

## 0. Prerequisites (you must provision)

1. DNS for `staging.example.com` and `api.staging.example.com` (or a single host with path routing)
2. Managed MongoDB database `assistify_staging`
3. Managed Redis instance
4. Container registry access (or build images on the host)
5. Secrets stored outside git (Doppler / Vault / host env / sealed secrets)

---

## 1. Build images

```bash
# Backend
docker build -t ghcr.io/YOUR_ORG/assistify-backend:staging ./backend

# Frontend — bake the PUBLIC API origin at build time
docker build -t ghcr.io/YOUR_ORG/assistify-frontend:staging ./frontend \
  --build-arg REACT_APP_BACKEND_URL=https://api.staging.example.com \
  --build-arg REACT_APP_BILLING_ENABLED=false \
  --build-arg REACT_APP_ENABLE_DEMO_LOGIN=false
```

Push to your registry.

---

## 2. Create secrets file (never commit)

```bash
cp backend/.env.staging.example .env.staging
# edit .env.staging — fill real values
```

Minimum required:

| Variable | Example |
|----------|---------|
| `MONGO_URL` | `mongodb+srv://…` |
| `DB_NAME` | `assistify_staging` |
| `JWT_SECRET` | ≥32 char random |
| `INTEGRATION_ENCRYPTION_KEY` | Fernet / long random |
| `FRONTEND_URL` | `https://staging.example.com` |
| `API_URL` | `https://api.staging.example.com` |
| `CORS_ORIGINS` | `https://staging.example.com` |
| `REDIS_URL` | `rediss://…` |
| `OPENAI_API_KEY` | (or Emergent key) |
| `REQUIRE_REDIS` | `true` |
| `WORKER_ENABLED` | `true` |
| `SCHEDULER_ENABLED` | `true` |
| `ENABLE_DEMO_*` | `false` |

Validate **without printing secrets**:

```bash
python scripts/validate_staging_env.py --env-file .env.staging --strict
```

---

## 3. Deploy containers

### Option A — Docker Compose on a VM

```bash
# Point image names in docker-compose.staging.example.yml at your registry, then:
docker compose -f docker-compose.staging.example.yml --env-file .env.staging up -d
```

Put Caddy/nginx/Traefik in front:

- `staging.example.com` → `frontend:80`
- `api.staging.example.com` → `backend:8000`
- TLS certificates (Let’s Encrypt)

Forward `X-Forwarded-Proto: https` so apps see HTTPS.

### Option B — Platform services

Deploy the same four processes (`backend`, `worker`, `scheduler`, `frontend`) as separate services with the same env. Attach managed Mongo + Redis.

---

## 4. Cookie / CORS (cross-origin SPA)

When SPA and API are on **different hosts**:

| Setting | Value |
|---------|--------|
| `CORS_ORIGINS` | Exact frontend origin |
| Cookies | `Secure=true`, `SameSite=none` (default when `FRONTEND_URL` is https) |
| Frontend fetch | `credentials: "include"` (already in client) |
| CSRF | `csrf_token` cookie + `X-CSRF-Token` header on mutations |

See `docs/AUTH_COOKIES.md`.

---

## 5. Health verification

```bash
curl -fsS https://api.staging.example.com/api/health/live
curl -fsS https://api.staging.example.com/api/health/ready
curl -fsS https://api.staging.example.com/api/health/alerts
curl -fsS https://api.staging.example.com/api/config/public
```

### Expected healthy responses

**Live (always 200 if process up):**
```json
{"status":"ok","check":"live","release":"staging"}
```

**Ready (200 only when required deps OK):**
```json
{
  "status": "ok",
  "check": "ready",
  "checks": {
    "mongodb": {"ok": true},
    "redis": {"ok": true, "configured": true},
    "storage": {"ok": true}
  },
  "failedChecks": []
}
```
If Mongo or required Redis is down → **HTTP 503** with `"status":"degraded"`.

**Alerts:** `200` when no critical alerts; `503` when critical (ready/worker/scheduler failures).

**Public config:** `demoLoginEnabled=false`, `billingEnabled=false`, email/oauth status without secrets.

---

## 6. Smoke auth on HTTPS

1. Open `https://staging.example.com/register`
2. Create account → lands on dashboard/onboarding
3. DevTools → Application → Cookies: `access_token` / `refresh_token` are **httpOnly**; `csrf_token` readable
4. Reload → session persists (refresh)
5. Logout → cookies cleared; `/api/auth/me` → 401
6. Confirm **no** `assistify_token` in localStorage

---

## 7. Playwright against staging

```bash
cd e2e
yarn install
npx playwright install chromium

STAGING_BASE_URL=https://staging.example.com \
E2E_BASE_URL=https://staging.example.com \
E2E_API_URL=https://api.staging.example.com \
yarn test:staging
```

If the staging host is unreachable, tests **skip** (pending) — they do not fake pass.

---

## 8. Optional: email / OAuth / alerts

| Feature | Docs | Default |
|---------|------|---------|
| Resend | `docs/EMAIL_GOLIVE.md` + section below | `EMAIL_SENDING_ENABLED=false` |
| OAuth | `docs/OAUTH_PRODUCTION.md` | not configured |
| Alert webhook | `ALERT_DELIVERY_ENABLED=false` | off |

### Resend staging steps (do not auto-enable)

1. Create Resend API key → `RESEND_API_KEY`
2. Add + verify sending domain in Resend
3. Publish SPF / DKIM (/ DMARC) DNS records
4. Set `FROM_EMAIL` on that domain
5. Keep `EMAIL_SENDING_ENABLED=false` until a controlled test
6. Flip `EMAIL_SENDING_ENABLED=true`
7. Test: verification email, password reset, invite
8. Kill-switch: set `EMAIL_SENDING_ENABLED=false` to stop outbound immediately

Status (no API key exposed): `GET /api/health` → `email`, `GET /api/config/public` → `email`, `GET /api/emails/status` (auth’d).

### OAuth staging redirect URIs

Register **exactly**:

```
https://api.staging.example.com/api/integrations/oauth/callback/google
https://api.staging.example.com/api/integrations/oauth/callback/microsoft
https://api.staging.example.com/api/integrations/oauth/callback/slack
```

Set matching `GOOGLE_REDIRECT_URI` / `MICROSOFT_REDIRECT_URI` / `SLACK_REDIRECT_URI` and `API_URL`.

Readiness (no secrets): `GET /api/integrations/status` → `oauthReadiness`, `GET /api/config/public` → `oauth`.

### Alert delivery

```bash
ALERT_DELIVERY_ENABLED=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...   # or generic HTTPS webhook
# optional: ALERT_DEDUPE_SECONDS=900
```

Scheduler delivers deduplicated alerts. Manual: `POST /api/ops/alerts/dispatch` (admin).

---

## 9. Rollback

1. Point load balancer / compose tags back to previous image digest
2. Keep Mongo/Redis unchanged (forward-only schema)
3. Re-check `/api/health/ready`
4. If bad config: revert `.env.staging` values and restart

---

## 10. Release candidate

Follow `docs/RELEASE_CANDIDATE_CHECKLIST.md` before inviting broader testers.
