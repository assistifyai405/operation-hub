# AGENTS.md

## Cursor Cloud specific instructions

Assistify OS is a two-part app: a FastAPI backend (`backend/`, `/api/*`, port 8000) and a
React 19 SPA (`frontend/`, port 3000) backed by MongoDB. Standard setup/run/test commands live in
[`README.md`](./README.md); only the non-obvious, environment-specific notes are captured here.

### Services and how to run them

The update script installs dependencies (MongoDB + backend venv + frontend `node_modules`) but does
**not** start anything. Start services yourself:

- MongoDB (required): `mongod --dbpath /data/db --bind_ip 127.0.0.1 --port 27017`. Docker is not
  available in this environment, so MongoDB is installed natively (mongodb-org 8.0).
- Backend (required): from `backend/`, `. .venv/bin/activate && uvicorn server:app --reload --host 0.0.0.0 --port 8000`.
  Reads `backend/.env`. Health: `GET /api/health/ready`.
- Frontend (required for UI): from `frontend/`, `BROWSER=none yarn start` (reads `frontend/.env`).
- Redis / worker / scheduler are optional. With `WORKER_ENABLED=false` (the dev default), background
  jobs run inline in the API process — no Redis needed.

`backend/.env` and `frontend/.env` are gitignored; recreate them from the `.env.example` files if missing.
For local dev use `AI_PROVIDER=openai` with a dummy `OPENAI_API_KEY` (the app boots fine; only live AI
calls fail), `EMAIL_PROVIDER=console`, and `STORAGE_PROVIDER=local`.

### Running the backend test suite (important gotcha)

Run pytest with the CI env vars exported, and in particular **`DB_NAME=assistify_test`**:

```bash
cd backend && . .venv/bin/activate
env MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=assistify_test \
    JWT_SECRET='unit-test-secret-key-with-32plus-chars!!' ENVIRONMENT=development \
    EMAIL_PROVIDER=console AI_PROVIDER=openai OPENAI_API_KEY=sk-test-key \
    STORAGE_PROVIDER=local CORS_ORIGINS=http://localhost:3000 ENABLE_DEMO_SEED=false \
  pytest tests/test_sprint12_hardening.py tests/test_sprint12_http.py tests/test_sprint13_team.py \
         tests/test_sprint14_email.py tests/test_sprint15_integrations.py tests/test_sprint16_inbox.py \
         tests/test_sprint17_native_send.py tests/test_sprint18_ops.py -n 0 -q
```

Why this matters: `tests/conftest.py` loads `backend/.env` into the environment, and the test `mongo`
fixture reads `os.environ["DB_NAME"]` while the app under test is forced to `assistify_test`. If your
dev `backend/.env` uses a different `DB_NAME` (e.g. `assistify`) and you do **not** export
`DB_NAME=assistify_test`, direct DB writes in tests land in one database while the app reads another,
causing ~25 spurious failures (e.g. `403 "Draft must be approved before sending"`). Exporting
`DB_NAME=assistify_test` keeps both on the same test DB and the full suite passes (98 passed).
Do not modify `pytest.ini` `addopts`; use `-n 0` to run serially.

### Dependencies

- `backend/requirements.txt` pins `emergentintegrations==0.2.0`, which is not on PyPI and is only used
  when `AI_PROVIDER=emergent`. Local/OpenAI dev does not need it; the update script installs
  requirements with that one optional package filtered out so all other pins stay intact.
- `litellm` is pinned to a direct wheel URL; installing `emergentintegrations` from its extra index
  alongside the pinned requirements causes an unresolvable `litellm` conflict — another reason it is
  skipped locally.

### Lint / build

Backend has no enforced lint config; the authoritative static check (matching CI) is
`python -m compileall -q . && python -c "import indexes, redis_client, rate_limit, distributed_locks, jobs, observability, errors"`.
The frontend runs ESLint automatically via `react-scripts` during `yarn start` / `yarn build`
(hook-dependency warnings are non-blocking).
