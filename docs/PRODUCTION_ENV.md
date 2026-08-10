# Production environment variables

Never commit real secrets. Copy templates into private secret stores / `.env` files that stay gitignored.

## REQUIRED (production)

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT=production` | Enables production fail-fast rules |
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `JWT_SECRET` | ≥32 chars; must not match known weak defaults |
| `CORS_ORIGINS` | Comma-separated **https** origins (no `*`, no localhost) |
| `FRONTEND_URL` | Public **https** app origin |
| `REDIS_URL` | Required when `WORKER_ENABLED`, `SCHEDULER_ENABLED`, or `REQUIRE_REDIS` |
| `INTEGRATION_ENCRYPTION_KEY` | Encrypts OAuth tokens at rest |
| `OPENAI_API_KEY` or `EMERGENT_LLM_KEY` | Matches `AI_PROVIDER` |

## REQUIRED WHEN WORKERS/SCHEDULER ON

| Variable | Purpose |
|----------|---------|
| `WORKER_ENABLED=true` | API may enqueue; worker process must also run |
| `SCHEDULER_ENABLED=true` | Periodic inbox sync / scheduled send / health jobs |
| `REQUIRE_REDIS=true` | Ready probe fails if Redis is down (default when workers/scheduler on) |

## OPTIONAL (production)

| Variable | Purpose |
|----------|---------|
| `APP_URL` / `API_URL` | Canonical URLs for links & ops |
| `EMAIL_PROVIDER=resend` | Transactional email |
| `EMAIL_SENDING_ENABLED` | Product outbound mail kill-switch (default false) |
| `RESEND_API_KEY` / `FROM_EMAIL` / `FROM_NAME` | Resend config |
| `RESEND_WEBHOOK_SECRET` | Delivery webhooks |
| `GOOGLE_*` / `MICROSOFT_*` / `SLACK_*` | Integrations OAuth |
| `TRUSTED_HOSTS` | Optional Host header allow-list |
| `SENTRY_DSN` / `RELEASE_VERSION` / `LOG_LEVEL` / `JSON_LOGS` | Ops |
| `STORAGE_PROVIDER` / `UPLOAD_DIR` | File storage (`local` or `emergent`) |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | Override cookie policy (defaults from URLs) |
| (see `docs/AUTH_COOKIES.md`) | Browser sessions are cookie-only + CSRF double-submit |

## DISABLED BY DEFAULT (keep off for first launch)

| Variable | Default | Notes |
|----------|---------|-------|
| `ENABLE_DEMO_LOGIN` | `false` | Forced **off** in production unless `ALLOW_DEMO_IN_PRODUCTION=true` |
| `ENABLE_DEMO_SEED` | `false` | Same hard-disable rule |
| `ALLOW_DEMO_IN_PRODUCTION` | `false` | Escape hatch only |
| `REACT_APP_BILLING_ENABLED` | `false` | Stripe not implemented — keep false |
| `REACT_APP_ENABLE_DEMO_LOGIN` | `false` | Hide demo CTA in the SPA build |

## DEVELOPMENT ONLY

| Variable | Notes |
|----------|-------|
| `ENVIRONMENT=development` | Allows localhost CORS/cookies |
| Weak `JWT_SECRET` for local compose | Rejected in production |
| `EMAIL_PROVIDER=console` | Logs mail instead of sending |
| `OPENAI_API_KEY=sk-test-not-used` | Local compose placeholder |
| Docker Compose hardcoded JWT | Never reuse in production |

## Frontend build args

| Variable | Purpose |
|----------|---------|
| `REACT_APP_BACKEND_URL` | API origin baked into the SPA |
| `REACT_APP_BILLING_ENABLED` | Must stay `false` until Stripe |
| `REACT_APP_ENABLE_DEMO_LOGIN` | Must stay `false` in production builds |
