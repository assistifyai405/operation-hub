"""Opportunities tests — repaired for cookie-auth TestClient (Sprint 26).

No longer depends on demo-login seeds. Creates real workspace conditions.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()
    try:
        from redis_client import get_redis
        r = get_redis()
        if r:
            for k in list(r.scan_iter("assistify:rl:*")):
                r.delete(k)
    except Exception:
        pass


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register_workspace(client, company="Opp Co"):
    _clear_rl()
    email = f"opp_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Opp",
            "lastName": "User",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    h = {"Authorization": f"Bearer {data['accessToken']}"}
    # Seed conditions that should generate opportunities
    cr = client.post("/api/clients", headers=h, json={"name": "Stale Client", "contact": "S", "email": "s@o.test", "status": "Active"})
    assert cr.status_code == 200
    cid = cr.json()["id"]
    pr = client.post(
        "/api/projects",
        headers=h,
        json={"name": "No Deadline Proj", "client_id": cid, "status": "Active"},
    )
    assert pr.status_code == 200
    pid = pr.json()["id"]
    due = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    tr = client.post(
        "/api/tasks",
        headers=h,
        json={"title": "Overdue Opp Task", "project_id": pid, "priority": "High", "due": due, "done": False},
    )
    assert tr.status_code == 200
    return {"headers": h, "email": email, "client_id": cid, "project_id": pid, "task_id": tr.json()["id"]}


@pytest.fixture(scope="module")
def workspace(api_client):
    c, _ = api_client
    return _register_workspace(c, company="Opp Main")


@pytest.fixture(scope="module")
def workspace2(api_client):
    c, _ = api_client
    return _register_workspace(c, company="Opp Other")


class TestOpportunitiesList:
    def test_shape_and_sort(self, client, workspace):
        r = client.get("/api/opportunities", headers=workspace["headers"])
        assert r.status_code == 200
        data = r.json()
        for k in ("items", "total", "total_time_saved", "counts", "generated_at"):
            assert k in data, f"missing {k}"
        assert isinstance(data["items"], list)
        assert set(data["counts"].keys()) >= {"critical", "high", "medium", "low"}
        scores = [i["score"] for i in data["items"]]
        assert scores == sorted(scores, reverse=True)
        # Real overdue/stale conditions should yield at least one opportunity
        assert data["total"] >= 1, f"expected opportunities from seeded conditions, got {data['total']}"

    def test_item_fields(self, client, workspace):
        r = client.get("/api/opportunities", headers=workspace["headers"])
        items = r.json()["items"]
        assert items, "expected at least one opportunity"
        it = items[0]
        for k in (
            "id", "key", "type", "title", "explanation", "why", "time_saved",
            "confidence", "score", "priority", "color", "icon", "action", "entity",
        ):
            assert k in it, f"missing field {k} on item"
        assert it["priority"] in ("Critical", "High", "Medium", "Low")
        assert it["color"] in ("red", "orange", "yellow", "green")
        assert 0 <= it["score"] <= 100
        a = it["action"]
        for k in ("label", "kind", "link", "command", "project_id", "client_id"):
            assert k in a
        assert "project_name" in it["entity"] and "client_name" in it["entity"]


class TestBrief:
    def test_brief(self, client, workspace):
        r = client.get("/api/opportunities/brief", headers=workspace["headers"])
        assert r.status_code == 200
        b = r.json()
        for k in ("greeting", "lines", "total_time_saved", "total", "top"):
            assert k in b
        assert b["greeting"].startswith("Good ")
        assert isinstance(b["lines"], list) and len(b["lines"]) >= 1
        assert len(b["top"]) <= 3


class TestHealth:
    def test_health(self, client, workspace):
        r = client.get("/api/opportunities/health", headers=workspace["headers"])
        assert r.status_code == 200
        h = r.json()
        assert 0 <= h["score"] <= 100
        assert h["grade"] in ("Excellent", "Good", "Fair", "Needs attention")
        cat_names = {c["name"] for c in h["categories"]}
        expected = {"Invoices", "Contracts", "Projects", "Clients", "Activity", "Outstanding work"}
        assert expected.issubset(cat_names), f"missing categories: {expected - cat_names}"
        for c in h["categories"]:
            assert 0 <= c["score"] <= 100
            assert isinstance(c["reasons"], list) and len(c["reasons"]) >= 1
        assert isinstance(h["top_reasons"], list)


class TestDismiss:
    def test_dismiss_hides_key(self, client, workspace):
        r = client.get("/api/opportunities", headers=workspace["headers"])
        items = r.json()["items"]
        if not items:
            pytest.skip("no opportunities to dismiss")
        key = items[0]["key"]
        d = client.post("/api/opportunities/dismiss", headers=workspace["headers"], json={"key": key})
        assert d.status_code == 200 and d.json().get("ok") is True
        r2 = client.get("/api/opportunities", headers=workspace["headers"])
        keys = {i["key"] for i in r2.json()["items"]}
        assert key not in keys, f"dismissed key {key} still present"


class TestArchive:
    def test_404_unknown(self, client, workspace):
        r = client.post("/api/opportunities/archive-project/does-not-exist-xyz", headers=workspace["headers"])
        assert r.status_code == 404

    def test_archive_project(self, client, workspace):
        pr = client.get("/api/projects", headers=workspace["headers"])
        assert pr.status_code == 200
        projs = pr.json() if isinstance(pr.json(), list) else pr.json().get("items", [])
        target = next((p for p in projs if p.get("status") != "Archived"), None)
        if not target:
            pytest.skip("no non-archived project")
        pid = target["id"]
        r = client.post(f"/api/opportunities/archive-project/{pid}", headers=workspace["headers"])
        assert r.status_code == 200
        assert r.json().get("status") == "Archived"
        g = client.get(f"/api/projects/{pid}", headers=workspace["headers"])
        assert g.status_code == 200
        assert g.json().get("status") == "Archived"


class TestOrgIsolation:
    def test_isolation(self, client, workspace, workspace2):
        r1 = client.get("/api/opportunities", headers=workspace["headers"]).json()
        r2 = client.get("/api/opportunities", headers=workspace2["headers"]).json()
        keys1 = {i["key"] for i in r1["items"]}
        keys2 = {i["key"] for i in r2["items"]}
        overlap = keys1 & keys2
        assert not overlap, f"unexpected cross-org overlap: {overlap}"
