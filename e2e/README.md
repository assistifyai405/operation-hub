# End-to-end smoke (Playwright)

Targets a **running** frontend + backend (local compose or real staging). Does not mock the app.
Auth is **cookie-only** — tests assert no JWT in `localStorage` / `sessionStorage`.

## Local

```bash
# Terminal A — API
cd backend && uvicorn server:app --host 127.0.0.1 --port 8000

# Terminal B — SPA (must bake API URL at build time)
cd frontend
REACT_APP_BACKEND_URL=http://127.0.0.1:8000 yarn build
npx serve -s build -l 3000

# Terminal C — tests
cd e2e
yarn install
npx playwright install chromium
yarn test:local
# or:
E2E_BASE_URL=http://127.0.0.1:3000 E2E_API_URL=http://127.0.0.1:8000 yarn test
```

If the API is unreachable, tests are **skipped** (pending) — not failed, not faked as pass.

## Staging (external HTTPS)

Requires real URLs — `yarn test:staging` exits with code `2` (PENDING) if `STAGING_BASE_URL` is missing or localhost.

```bash
cd e2e
yarn install
npx playwright install chromium

STAGING_BASE_URL=https://staging.example.com \
E2E_BASE_URL=https://staging.example.com \
E2E_API_URL=https://api.staging.example.com \
yarn test:staging
```

Artifacts on failure: `e2e/test-results/` (screenshots, traces, video).

See `docs/STAGING_DEPLOYMENT_RUNBOOK.md` and `docs/RELEASE_CANDIDATE_CHECKLIST.md`.
