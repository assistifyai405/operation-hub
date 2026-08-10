# Cookie-only browser authentication

## Model

Authenticated browser sessions use **httpOnly cookies**. The SPA does **not** store access JWTs in `localStorage` or `sessionStorage`.

| Cookie | httpOnly | Purpose |
|--------|----------|---------|
| `access_token` | yes | Short-lived JWT (`path=/api`) |
| `refresh_token` | yes | Rotating refresh session (`path=/api/auth`) |
| `csrf_token` | **no** | Double-submit CSRF for cookie sessions |

Login / register / refresh / invite-accept set cookies and return JSON shaped like:

```json
{ "user": { "...": "..." }, "auth": "cookie" }
```

**No `accessToken` field** is returned to the browser.

## CSRF

Mutating requests (`POST`/`PUT`/`PATCH`/`DELETE`) that authenticate via cookies must send:

```
X-CSRF-Token: <value of csrf_token cookie>
```

Exempt paths: login, register, refresh, forgot/reset/verify, demo, webhooks, OAuth callback, health, public config.

`Authorization: Bearer …` skips CSRF (machine clients / automated tests). Prefer cookies for browsers.

## Production / staging cookie flags

When `FRONTEND_URL` is `https://` (or `ENVIRONMENT` is production-like):

- `Secure=true`
- `SameSite=none` (cross-origin SPA ↔ API)

Local HTTP development:

- `Secure=false`
- `SameSite=lax`

Overrides: `COOKIE_SECURE`, `COOKIE_SAMESITE`.

## Session lifecycle

1. **Login/register** → set access + refresh + CSRF cookies  
2. **Page reload** → `POST /api/auth/refresh` (credentials include) restores user  
3. **Logout** → revoke refresh session + clear cookies  
4. **Expired/invalid** → API returns 401; SPA clears legacy storage and routes to `/login`

## Security notes

- Never log access/refresh JWT values
- Clear legacy `assistify_token` keys on bootstrap
- CORS must list exact frontend origins with credentialed requests
