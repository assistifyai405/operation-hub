# Release candidate checklist (staging → launch gate)

Use against a **real** staging deployment. Check each box only after observed evidence.

## Infrastructure

- [ ] Staging frontend URL reachable over HTTPS
- [ ] Staging API URL reachable over HTTPS
- [ ] TLS certificate valid (no browser warnings)
- [ ] `python scripts/validate_staging_env.py --env-file .env.staging --strict` → PASS
- [ ] Managed MongoDB reachable from backend/worker/scheduler
- [ ] Managed Redis reachable when worker/scheduler enabled

## Health / startup

- [ ] `GET /api/health/live` → 200 `status=ok`
- [ ] `GET /api/health/ready` → **200** (not 503)
- [ ] `GET /api/health/alerts` → 200 and no critical alerts
- [ ] Backend process running
- [ ] Frontend serving SPA
- [ ] Worker process running (if `WORKER_ENABLED=true`)
- [ ] Scheduler process running (if `SCHEDULER_ENABLED=true`)

## Security / flags

- [ ] Demo login disabled (`ENABLE_DEMO_LOGIN=false`, public config confirms)
- [ ] Demo seed disabled
- [ ] Billing gated off (`billingEnabled=false`, no fake Stripe)
- [ ] No secrets in git / build logs / health payloads

## Cookie auth (real HTTPS)

- [ ] Login sets httpOnly Secure cookies
- [ ] CSRF cookie present; mutations succeed from SPA
- [ ] Session persists after full page reload
- [ ] Refresh works without localStorage JWT
- [ ] Logout clears session; subsequent `/api/auth/me` is 401
- [ ] No `assistify_token` in localStorage/sessionStorage

## Product smoke

- [ ] Register new user
- [ ] Login / logout / login again
- [ ] Create client
- [ ] Create project
- [ ] Create task
- [ ] Dashboard loads
- [ ] Opportunities page loads
- [ ] AI Agents page loads agents list
- [ ] Copilot / AI chat page loads
- [ ] Settings page loads

## Email (only if configured)

- [ ] Resend domain verified + DNS OK
- [ ] `EMAIL_SENDING_ENABLED` intentionally set
- [ ] Verification email received
- [ ] Password reset email received
- [ ] Invite email received
- [ ] Kill-switch (`EMAIL_SENDING_ENABLED=false`) stops outbound
- [ ] Health/public email status shows configured without exposing API key

## OAuth (only if configured)

- [ ] Redirect URIs registered for Google / Microsoft / Slack
- [ ] Connect flow completes
- [ ] Reconnect required state surfaces when token revoked
- [ ] Status endpoint shows readiness without client secrets

## Automation / jobs

- [ ] Job enqueued and processed by worker
- [ ] Scheduler tick runs without crash
- [ ] Failed-job depth not climbing unbounded (`/api/health/alerts`)

## Alert delivery (optional)

- [ ] Webhook disabled by default in baseline config
- [ ] When enabled, critical ready failure notifies once (deduped)
- [ ] Payload/logs contain no secrets

## Automated E2E

- [ ] Playwright staging suite ran against the **external** staging URLs
- [ ] Command used documented in the release notes
- [ ] Failures have screenshots/traces retained

```bash
STAGING_BASE_URL=https://staging.example.com \
E2E_BASE_URL=https://staging.example.com \
E2E_API_URL=https://api.staging.example.com \
yarn --cwd e2e test:staging
```

## Rollback

- [ ] Previous image tags identified
- [ ] Rollback steps from `docs/STAGING_DEPLOYMENT_RUNBOOK.md` §9 rehearsed or documented for on-call

## Sign-off

| Role | Name | Date |
|------|------|------|
| Engineer | | |
| Reviewer | | |

**Verdict:** ☐ Ready for wider staging testers ☐ Blocked (list issues below)

Notes:

-
