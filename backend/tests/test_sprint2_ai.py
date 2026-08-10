"""Sprint 2 — 'Make Assistify Feel Alive' backend tests.
Covers: /api/ai/activities, /activities/history, /time-saved, /insights,
/notifications, backfill idempotency, and doc-generate -> ai_activity logging."""
import os
import time
import pytest
import requests
from conftest import auth_json

def _load_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_env()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"

CREDS = {"email": "jordan@assistify.io", "password": "Assistify2026!", "remember": True}


@pytest.fixture(scope="module")
def auth():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=CREDS, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = auth_json(None, r).get("accessToken")
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def project_id(auth):
    # Create a fresh project (also grab an existing client)
    clients = auth.get(f"{API}/clients").json()
    assert clients, "seed clients missing"
    cid = clients[0]["id"]
    r = auth.post(f"{API}/projects", json={
        "name": "TEST_Sprint2 AI Project",
        "clientId": cid,
        "status": "In Progress",
        "budget": 5000,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# ---------- Activity feed ----------
class TestActivities:
    def test_activities_all_scope_nonempty_backfilled(self, auth):
        r = auth.get(f"{API}/ai/activities?scope=all&limit=100")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) > 0, "seed org should be backfilled with existing docs"
        it = items[0]
        for k in ["id", "type", "icon", "label", "title", "explanation",
                  "source_page", "time_saved", "created_at"]:
            assert k in it, f"missing field {k}"

    def test_backfill_idempotent(self, auth):
        r1 = auth.get(f"{API}/ai/activities?scope=all&limit=500").json()
        r2 = auth.get(f"{API}/ai/activities?scope=all&limit=500").json()
        assert len(r1) == len(r2), "backfill duplicated on second call"


# ---------- Time saved ----------
class TestTimeSaved:
    def test_time_saved_structure(self, auth):
        r = auth.get(f"{API}/ai/time-saved")
        assert r.status_code == 200
        d = r.json()
        for k in ["today", "week", "month", "lifetime", "count"]:
            assert k in d and isinstance(d[k], int), f"{k} missing/not int"
        assert d["lifetime"] >= d["week"] >= d["today"]
        assert d["lifetime"] >= d["month"] >= d["week"] or d["month"] >= d["week"]


# ---------- History grouping ----------
class TestHistory:
    def test_history_grouped(self, auth):
        r = auth.get(f"{API}/ai/activities/history")
        assert r.status_code == 200
        d = r.json()
        assert "groups" in d and "total" in d and "total_time_saved" in d
        valid_labels = {"Today", "Yesterday", "This Week", "Earlier"}
        total_sum = 0
        for g in d["groups"]:
            assert g["label"] in valid_labels
            for it in g["items"]:
                total_sum += it.get("time_saved", 0)
        assert d["total_time_saved"] == total_sum


# ---------- Insights ----------
class TestInsights:
    def test_insights_ok(self, auth):
        r = auth.get(f"{API}/ai/insights", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        for it in data:
            for k in ["id", "type", "severity", "icon", "explanation", "link", "action_label"]:
                assert k in it, f"insight missing {k}"

    def test_insights_cached_second_call_fast(self, auth):
        # first call may have polished; second should hit cache and be quick
        t0 = time.time()
        r = auth.get(f"{API}/ai/insights", timeout=30)
        assert r.status_code == 200
        assert time.time() - t0 < 10


# ---------- Notifications ----------
class TestNotifications:
    def test_notifications_structure(self, auth):
        r = auth.get(f"{API}/ai/notifications", timeout=60)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        kinds = {i.get("kind") for i in items}
        # completion should exist (backfill)
        assert "completion" in kinds or "insight" in kinds
        for it in items:
            for k in ["icon", "title", "message", "created_at"]:
                assert k in it, f"notification missing {k}"


# ---------- Generate document -> activity logged ----------
class TestGenerationLogsActivity:
    def _count_type(self, auth, atype):
        items = auth.get(f"{API}/ai/activities?scope=all&limit=500").json()
        return sum(1 for i in items if i.get("type") == atype)

    def test_generate_proposal_logs_activity(self, auth, project_id):
        before = self._count_type(auth, "proposal")
        ts_before = auth.get(f"{API}/ai/time-saved").json()["lifetime"]
        r = auth.post(f"{API}/projects/{project_id}/proposal/generate", json={}, timeout=120)
        assert r.status_code == 200, r.text
        after = self._count_type(auth, "proposal")
        ts_after = auth.get(f"{API}/ai/time-saved").json()["lifetime"]
        assert after == before + 1, f"proposal activity not logged: {before}->{after}"
        assert ts_after - ts_before >= 23, f"time_saved didn't grow by ≥23 (proposal): {ts_before}->{ts_after}"
        # Confirm the new entry has time_saved=23
        items = auth.get(f"{API}/ai/activities?scope=all&limit=5").json()
        proposals = [i for i in items if i.get("type") == "proposal"]
        assert proposals and proposals[0]["time_saved"] == 23

    def test_generate_plan_logs_activity(self, auth, project_id):
        before = self._count_type(auth, "plan")
        r = auth.post(f"{API}/projects/{project_id}/plan/generate", json={}, timeout=120)
        assert r.status_code == 200, r.text
        after = self._count_type(auth, "plan")
        assert after == before + 1

    def test_generate_contract_logs_activity(self, auth, project_id):
        before = self._count_type(auth, "contract")
        r = auth.post(f"{API}/projects/{project_id}/contract/generate", json={}, timeout=120)
        assert r.status_code == 200, r.text
        after = self._count_type(auth, "contract")
        assert after == before + 1

    def test_generate_invoice_logs_activity(self, auth, project_id):
        before = self._count_type(auth, "invoice")
        r = auth.post(f"{API}/projects/{project_id}/invoice/generate", json={}, timeout=120)
        assert r.status_code == 200, r.text
        after = self._count_type(auth, "invoice")
        assert after == before + 1


# ---------- Regression: existing endpoints still work ----------
class TestRegression:
    def test_dashboard_still_works(self, auth):
        r = auth.get(f"{API}/dashboard/summary")
        assert r.status_code == 200

    def test_copilot_still_works(self, auth):
        r = auth.get(f"{API}/copilot/suggestions", timeout=60)
        assert r.status_code == 200
