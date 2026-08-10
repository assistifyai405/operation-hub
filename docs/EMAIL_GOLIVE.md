# Email go-live readiness (Resend)

Transactional email (verify, password reset, invites) uses `email_service` → Resend or console.

Product outbound mail (Email Center) is separately gated.

## Providers

| `EMAIL_PROVIDER` | Behavior |
|------------------|----------|
| `console` | Logs / preview only — **not** real delivery |
| `resend` | Sends when `RESEND_API_KEY` + `FROM_EMAIL` configured |

## Kill-switches

| Flag | Scope |
|------|--------|
| `EMAIL_SENDING_ENABLED=false` | Blocks **product/outbound** sends (`outbound_sending_allowed`) |
| Missing Resend key | Transactional send returns `{sent: false, mode: "unconfigured"}` — **does not pretend success** |

Auth flows in development may still expose `verificationLink` / invite links in API JSON when Resend is not enabled (`email_service.is_enabled() == false`). Staging/production with Resend configured must **not** rely on those links in API responses.

## Flows to verify before go-live

1. **Verification email** — register → inbox → `/verify-email`
2. **Password reset** — forgot → reset link → new password
3. **Invite email** — team invite → `/invite/:token`
4. **Outbound** — only after `EMAIL_SENDING_ENABLED=true` + Resend configured

## Failure handling

- Provider errors → `sent: false` + logged error (no secrets)
- Outbound drafts → `failed` / `needs_review` with `failureReason`
- Webhooks (`RESEND_WEBHOOK_SECRET`) update delivery state when configured

## DNS / domain (Resend)

Before enabling real send in staging/production:

1. Add and verify the sending domain in Resend
2. Publish SPF / DKIM (and DMARC recommended) DNS records Resend provides
3. Set `FROM_EMAIL` to an address on that domain
4. Optional: `REPLY_TO_EMAIL`, `RESEND_WEBHOOK_SECRET`
5. Flip `EMAIL_SENDING_ENABLED=true` only after a successful test send

## Automated tests

Tests use `EMAIL_PROVIDER=console` and `EMAIL_SENDING_ENABLED=false`.  
**Do not** require live Resend credentials in CI.
