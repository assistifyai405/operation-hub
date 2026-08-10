# OAuth production readiness (Google / Microsoft / Slack)

Integrations use server-side OAuth with **encrypted credential storage** (`INTEGRATION_ENCRYPTION_KEY`).

## Redirect URIs

Register these **exact** callback URLs in each provider console (staging + production separately):

| Provider | Redirect URI |
|----------|----------------|
| Google | `{API_URL}/api/integrations/oauth/callback/google` |
| Microsoft | `{API_URL}/api/integrations/oauth/callback/microsoft` |
| Slack | `{API_URL}/api/integrations/oauth/callback/slack` |

Example staging:

```
https://api.staging.example.com/api/integrations/oauth/callback/google
https://api.staging.example.com/api/integrations/oauth/callback/microsoft
https://api.staging.example.com/api/integrations/oauth/callback/slack
```

Override via env: `GOOGLE_REDIRECT_URI`, `MICROSOFT_REDIRECT_URI`, `SLACK_REDIRECT_URI`.

## Security checks (implemented)

| Control | Behavior |
|---------|----------|
| State | Random state stored in Mongo; single-use; expiry checked |
| Code exchange | Uses stored `redirectUri` from connect step |
| Token storage | Fernet-encrypted credentials at rest |
| Reconnect | Disconnect + connect again; refresh endpoint for OAuth tokens |
| Revoked/expired | Health/refresh marks error / needs reauth; user reconnects from Integrations |

## Required env (when enabling a provider)

```
INTEGRATION_ENCRYPTION_KEY=...   # required in production-like envs
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://api.example.com/api/integrations/oauth/callback/google
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT=common
MICROSOFT_REDIRECT_URI=...
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_REDIRECT_URI=...
```

## Staging readiness (no secrets)

| Endpoint | Fields |
|----------|--------|
| `GET /api/config/public` → `oauth` | `configured` / `not_configured` per provider |
| `GET /api/integrations/status` → `oauthReadiness` | `configured` / `not_configured` / `connected` / `reconnect_required` |
| `redirectUriTemplates` | Exact callback URLs derived from `API_URL` / explicit `*_REDIRECT_URI` |

Callback URL construction prefers (in order): explicit `*_REDIRECT_URI` → `API_URL` → request base URL.

## Automated tests

Integration tests mock providers / use fixtures.  
**Do not** require live OAuth client secrets in CI.
