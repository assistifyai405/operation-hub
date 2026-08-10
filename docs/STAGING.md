# Staging deployment

Staging is the first non-local environment that uses **real MongoDB**, **real Redis**, **HTTPS**, and **cookie-only browser auth**.

**Full step-by-step runbook:** [`docs/STAGING_DEPLOYMENT_RUNBOOK.md`](./STAGING_DEPLOYMENT_RUNBOOK.md)  
**Release candidate checklist:** [`docs/RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md)  
**Env validator (no secrets printed):**

```bash
python scripts/validate_staging_env.py --env-file .env.staging --strict
```

## Prerequisites

1. MongoDB (Atlas or self-hosted) — dedicated `assistify_staging` database
2. Redis — required when workers/scheduler are on
3. HTTPS termination (load balancer / reverse proxy) for frontend + API
4. Secrets from `backend/.env.staging.example` (never commit real values)
5. Frontend image built with:
   - `REACT_APP_BACKEND_URL=https://api.staging.example.com`
   - `REACT_APP_BILLING_ENABLED=false`
   - `REACT_APP_ENABLE_DEMO_LOGIN=false`

## Cookie / CORS model

| Setting | Staging value |
|---------|----------------|
| Browser auth | httpOnly `access_token` + `refresh_token` cookies |
| CSRF | Readable `csrf_token` cookie echoed as `X-CSRF-Token` on mutations |
| `FRONTEND_URL` | `https://staging.example.com` |
| `CORS_ORIGINS` | Exact staging frontend origin |
| Cookies | `Secure=true`, `SameSite=none` when SPA and API are on different hosts |
| Credentials | Frontend always uses `credentials: "include"` |

See also `docs/AUTH_COOKIES.md`.

## Compose

```bash
# Fill env (private)
cp backend/.env.staging.example .env.staging
# edit .env.staging

docker compose -f docker-compose.staging.example.yml --env-file .env.staging up -d
```

Health:

- Live: `GET /api/health/live`
- Ready: `GET /api/health/ready` (503 if Mongo/Redis required deps fail)
- Alerts: `GET /api/health/alerts` (503 on critical)

## Optional services

| Service | Required for staging smoke? | Notes |
|---------|----------------------------|-------|
| AI provider (`OPENAI_API_KEY`) | Yes for AI Agents/Copilot | Fail-fast in production-like env |
| Resend | No | Keep `EMAIL_SENDING_ENABLED=false` until DNS ready |
| Google / Microsoft / Slack OAuth | No | Document redirect URIs before enabling |

## Playwright against staging

```bash
cd e2e
yarn install
npx playwright install chromium

STAGING_BASE_URL=https://staging.example.com \
E2E_BASE_URL=https://staging.example.com \
E2E_API_URL=https://api.staging.example.com \
yarn test
```

If `STAGING_BASE_URL` / API is unreachable, tests **skip** (reported as pending), they do not fake pass.

## Checklist before inviting testers

- [ ] HTTPS on frontend + API
- [ ] CORS allow-list matches frontend
- [ ] Cookie Secure + SameSite correct for cross-origin SPA
- [ ] Demo login/seed off
- [ ] Billing UI gated off
- [ ] Redis + worker + scheduler healthy
- [ ] `/api/health/ready` returns 200
- [ ] Register/login/logout cookie session verified
- [ ] No secrets in git or build logs
