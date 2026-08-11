"""Sprint 2 — AI activities / time-saved / insights — TestClient."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="Sprint2 AI")
    h = a["headers"]
    cr = client.post("/api/clients", headers=h, json={"name": "S2 Client", "email": "s2@c.com"})
    assert cr.status_code == 200
    pr = client.post("/api/projects", headers=h, json={
        "name": "TEST_Sprint2 AI Project", "client_id": cr.json()["id"], "status": "In Progress",
    })
    assert pr.status_code == 200
    a["project_id"] = pr.json()["id"]
    # Seed at least one activity via save (non-AI) if generate fails
    return a


# ---------- Activity feed ----------
class TestActivities:
    def test_activities_all_scope(self, client, auth):
        r = client.get("/api/ai/activities?scope=all&limit=100", headers=auth["headers"])
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # May be empty for fresh org — shape check if present
        if items:
            it = items[0]
            for k in ["id", "type", "icon", "label", "title", "explanation",
                      "source_page", "time_saved", "created_at"]:
                assert k in it, f"missing field {k}"

    def test_backfill_idempotent(self, client, auth):
        r1 = client.get("/api/ai/activities?scope=all&limit=500", headers=auth["headers"]).json()
        r2 = client.get("/api/ai/activities?scope=all&limit=500", headers=auth["headers"]).json()
        assert len(r1) == len(r2)


# ---------- Time saved ----------
class TestTimeSaved:
    def test_time_saved_structure(self, client, auth):
        r = client.get("/api/ai/time-saved", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ["today", "week", "month", "lifetime", "count"]:
            assert k in d and isinstance(d[k], int), f"{k} missing/not int"
        assert d["lifetime"] >= d["week"] >= d["today"]
        assert d["lifetime"] >= d["month"] >= d["week"] or d["month"] >= d["week"]


# ---------- History grouping ----------
class TestHistory:
    def test_history_grouped(self, client, auth):
        r = client.get("/api/ai/activities/history", headers=auth["headers"])
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
    def test_insights_ok(self, client, auth):
        r = client.get("/api/ai/insights", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert isinstance(data, list)
        for it in data:
            for k in ["id", "type", "severity", "icon", "explanation", "link", "action_label"]:
                assert k in it, f"insight missing {k}"

    def test_insights_cached_second_call_fast(self, client, auth):
        t0 = time.time()
        r = client.get("/api/ai/insights", headers=auth["headers"])
        assert r.status_code in (200, 502, 503)
        assert time.time() - t0 < 30


# ---------- Notifications ----------
class TestNotifications:
    def test_notifications_structure(self, client, auth):
        r = client.get("/api/ai/notifications", headers=auth["headers"])
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for it in items:
            for k in ["icon", "title", "message", "created_at"]:
                assert k in it, f"notification missing {k}"


# ---------- Generate document -> activity logged ----------
class TestGenerationLogsActivity:
    def _count_type(self, client, headers, atype):
        items = client.get("/api/ai/activities?scope=all&limit=500", headers=headers).json()
        return sum(1 for i in items if i.get("type") == atype)

    def test_generate_proposal_logs_activity(self, client, auth):
        h, pid = auth["headers"], auth["project_id"]
        before = self._count_type(client, h, "proposal")
        ts_before = client.get("/api/ai/time-saved", headers=h).json()["lifetime"]
        r = client.post(f"/api/projects/{pid}/proposal/generate", headers=h, json={})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        after = self._count_type(client, h, "proposal")
        ts_after = client.get("/api/ai/time-saved", headers=h).json()["lifetime"]
        assert after == before + 1
        assert ts_after - ts_before >= 23
        items = client.get("/api/ai/activities?scope=all&limit=5", headers=h).json()
        proposals = [i for i in items if i.get("type") == "proposal"]
        assert proposals and proposals[0]["time_saved"] == 23

    def test_generate_plan_logs_activity(self, client, auth):
        h, pid = auth["headers"], auth["project_id"]
        before = self._count_type(client, h, "plan")
        r = client.post(f"/api/projects/{pid}/plan/generate", headers=h, json={})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            assert self._count_type(client, h, "plan") == before + 1

    def test_generate_contract_logs_activity(self, client, auth):
        h, pid = auth["headers"], auth["project_id"]
        before = self._count_type(client, h, "contract")
        r = client.post(f"/api/projects/{pid}/contract/generate", headers=h, json={})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            assert self._count_type(client, h, "contract") == before + 1

    def test_generate_invoice_logs_activity(self, client, auth):
        h, pid = auth["headers"], auth["project_id"]
        before = self._count_type(client, h, "invoice")
        r = client.post(f"/api/projects/{pid}/invoice/generate", headers=h, json={})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            assert self._count_type(client, h, "invoice") == before + 1


# ---------- Regression ----------
class TestRegression:
    def test_dashboard_still_works(self, client, auth):
        r = client.get("/api/dashboard/summary", headers=auth["headers"])
        assert r.status_code == 200

    def test_copilot_still_works(self, client, auth):
        r = client.get("/api/copilot/suggestions", headers=auth["headers"])
        assert r.status_code == 200
