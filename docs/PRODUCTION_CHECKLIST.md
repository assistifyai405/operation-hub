# Production release checklist

Operational steps before the first live Assistify OS deployment. Keep billing pending (no Stripe). Demo stays off.

## 1. Secrets & environment

- [ ] Copy `docs/PRODUCTION_ENV.md` into your secret store
- [ ] Set `ENVIRONMENT=production`
- [ ] Strong unique `JWT_SECRET` (≥32 chars, not a known weak value)
- [ ] Set `INTEGRATION_ENCRYPTION_KEY` (Fernet or long random secret)
- [ ] Set AI provider key (`OPENAI_API_KEY` or `EMERGENT_LLM_KEY`)
- [ ] `ENABLE_DEMO_LOGIN=false`, `ENABLE_DEMO_SEED=false`, `ALLOW_DEMO_IN_PRODUCTION=false`
- [ ] `REACT_APP_BILLING_ENABLED=false`, `REACT_APP_ENABLE_DEMO_LOGIN=false`
- [ ] No secrets committed to git / images

## 2. Domain & HTTPS

- [ ] Public HTTPS app domain (`FRONTEND_URL=https://…`)
- [ ] Public HTTPS API domain (`API_URL` / load balancer)
- [ ] TLS termination configured
- [ ] `CORS_ORIGINS` = exact https app origin(s)
- [ ] Optional `TRUSTED_HOSTS` for Host header allow-list

## 3. Data stores

- [ ] Managed MongoDB reachable from API/worker/scheduler
- [ ] `DB_NAME` set; indexes created on API startup
- [ ] Managed Redis reachable; `REDIS_URL` set
- [ ] `REQUIRE_REDIS=true` (or implied by workers)
- [ ] Backups enabled for Mongo (and Redis if durable state matters)

## 4. Processes

- [ ] API (`uvicorn`) running
- [ ] Worker (`python -m jobs.worker`) with `WORKER_ENABLED=true`
- [ ] Scheduler (`python -m jobs.scheduler`) with `SCHEDULER_ENABLED=true`
- [ ] Restart policies (`unless-stopped` or orchestrator equivalent)

## 5. Email & OAuth (optional for day-1 UI, required for those features)

- [ ] Resend (or keep sending disabled): `EMAIL_SENDING_ENABLED` deliberate
- [ ] Google / Microsoft / Slack OAuth redirect URIs match production API
- [ ] Reconnect integrations after scope changes

## 6. Build & deploy

- [ ] Build backend image (no `.env` copied into image)
- [ ] Build frontend with production `REACT_APP_BACKEND_URL`
- [ ] Use `docker-compose.production.example.yml` as a starting point (or k8s equivalent)
- [ ] Rolling deploy or blue/green available

## 7. Health checks

- [ ] `GET /api/health/live` → 200
- [ ] `GET /api/health/ready` → 200 (Mongo + Redis when required)
- [ ] Ready returns **503** if Redis is down while required
- [ ] Load balancer uses live for liveness, ready for traffic

## 8. Smoke tests

- [ ] Register / login
- [ ] Dashboard loads (empty-state OK)
- [ ] Create client → project → task
- [ ] Opportunities + AI Agents + Copilot + Settings load
- [ ] Logout / login again
- [ ] Run Playwright: `cd e2e && npx playwright test` (against live URLs)
- [ ] Backend: `pytest` subset for sprint 19–20

## 9. Rollback

- [ ] Previous container image tag retained
- [ ] Redis/Mongo not migrated destructively in this release
- [ ] Rollback steps: redeploy previous image → confirm `/api/health/ready` → re-run smoke login
- [ ] Feature flags: keep demo/billing off during rollback

## 10. Post-deploy watch

- [ ] Error rate / Sentry (if configured)
- [ ] Failed job depth (`/api/health/ready` jobs section or ops admin)
- [ ] Email send failures stay non-blocking when sending disabled
