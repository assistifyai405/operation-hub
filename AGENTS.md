# AGENTS.md

## Cursor Cloud specific instructions

Assistify OS is a single full-stack product with three services. Standard install/run/test
commands live in [`README.md`](./README.md); only the non-obvious caveats are captured here.

### Services

| Service | Port | Start command (run from repo root) |
|---|---|---|
| MongoDB (required) | 27017 | `mongod --dbpath /data/db --logpath /var/log/mongodb/mongod.log --bind_ip 127.0.0.1 --fork` |
| Backend (FastAPI) | 8000 | `cd backend && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000` |
| Frontend (CRA/Craco) | 3000 | `cd frontend && BROWSER=none yarn start` |

- MongoDB is a system package baked into the VM snapshot; it is **not** started by the update
  script. Start it manually (command above) if `mongosh --eval 'db.runCommand({ping:1})'` fails.
- Python deps install to `~/.local` (user site), so `uvicorn`/`pytest` are not on `PATH` — invoke
  them via `python3 -m uvicorn` / `python3 -m pytest`.

### Environment files (gitignored — must exist locally)

- `backend/.env` and `frontend/.env` are gitignored and are **not** committed. Copy from the
  `.env.example` files.
- The backend **fails to boot** with `AI_PROVIDER=openai` unless `OPENAI_API_KEY` is set, even
  though AI is nominally optional. Use a placeholder key (e.g. `sk-local-dev-placeholder-key`) to
  boot; core CRM/projects/docs work fully, but AI features (Copilot, generators, Knowledge Brain)
  return auth errors until a real key is supplied. Provide a real `OPENAI_API_KEY` secret to
  exercise AI features.
- Set `ENABLE_DEMO_SEED=true` and `DEMO_PASSWORD=Assistify2026!` in `backend/.env`. The whole
  Python test suite hardcodes the demo login as `jordan@assistify.io` / `Assistify2026!`; the
  startup seed auto-syncs the demo user's password to match `DEMO_PASSWORD` on every boot.

### Testing caveats

- `backend/pytest.ini` forces `-n 2 --dist loadscope` (do not edit). Run serially with `-n 0`
  (never `-p no:xdist`).
- The reliable local subset (no gotchas) is the README's:
  `python3 -m pytest tests/test_sprint12_hardening.py tests/test_sprint12_http.py tests/test_sprint13_team.py -n 0 -q`.
- Most other test modules are HTTP integration tests that hit a live server via `requests` and
  default `REACT_APP_BACKEND_URL` to the hosted preview. Export
  `REACT_APP_BACKEND_URL=http://localhost:8000` to point them at the local backend.
- These HTTP suites were built for the hosted multi-IP preview and are **flaky when the whole
  suite is run at once against a single local backend**:
  - `/api/auth/demo` is rate-limited to 10 calls/hour per IP (in-memory; reset by restarting the
    backend).
  - Login has a brute-force lockout after 5 failed attempts / 15 min, stored in MongoDB
    `login_attempts` keyed by `ip:email`. Since all local requests share `127.0.0.1`, the
    `test_brute_force_lockout`/wrong-password tests can lock the shared demo account. Reset with
    `mongosh --quiet assistify --eval 'db.login_attempts.deleteMany({})'`.
  - `test_demo_sees_seed_clients` expects a demo workspace pre-seeded with 3 clients. The startup
    seed only provisions the demo **user**; sample workspace data (clients/projects) is only
    created by the isolated `/api/auth/demo` tenant path, so this test fails locally by design.
  - Prefer running individual modules on a freshly restarted backend rather than the full suite.

### Frontend notes

- No dedicated `lint` script; ESLint runs through `craco start`/`craco build` and currently emits
  only `react-hooks/exhaustive-deps` warnings (non-blocking).
- `frontend/yarn.lock` is not committed; `yarn install` resolves fresh (versions are largely pinned
  via the `resolutions` field in `package.json`).
