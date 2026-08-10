# End-to-end smoke (Playwright)

Targets a **running** frontend + backend. Does not mock the app.

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
E2E_BASE_URL=http://127.0.0.1:3000 E2E_API_URL=http://127.0.0.1:8000 yarn test
```

If the API is unreachable, tests are skipped (not failed).
