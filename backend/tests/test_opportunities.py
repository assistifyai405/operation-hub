"""Backend tests for the AI Opportunities & Recommendations sprint (iteration_23).
Covers: list, brief, health, dismiss (7d snooze), archive-project, org-isolation.
"""
import os
import pytest
import requests
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _demo_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/demo", json={})
    assert r.status_code == 200, f"demo login failed: {r.status_code} {r.text[:200]}"
    tok = auth_json(None, r).get("accessToken")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, r.json()


@pytest.fixture(scope="module")
def client():
    s, _ = _demo_client()
    return s


@pytest.fixture(scope="module")
def client2():
    """A second, independent demo org for isolation tests."""
    s, _ = _demo_client()
    return s


# ---------------- GET /api/opportunities ----------------
class TestOpportunitiesList:
    def test_shape_and_sort(self, client):
        r = client.get(f"{API}/opportunities")
        assert r.status_code == 200
        data = r.json()
        for k in ("items", "total", "total_time_saved", "counts", "generated_at"):
            assert k in data, f"missing {k}"
        assert isinstance(data["items"], list)
        assert set(data["counts"].keys()) >= {"critical", "high", "medium", "low"}
        # sorted by score desc
        scores = [i["score"] for i in data["items"]]
        assert scores == sorted(scores, reverse=True)
        # demo seeds ~6 opps
        assert data["total"] >= 3, f"expected demo to seed opportunities, got {data['total']}"

    def test_item_fields(self, client):
        r = client.get(f"{API}/opportunities")
        items = r.json()["items"]
        assert items, "expected at least one opportunity"
        it = items[0]
        for k in ("id", "key", "type", "title", "explanation", "why", "time_saved",
                  "confidence", "score", "priority", "color", "icon", "action", "entity"):
            assert k in it, f"missing field {k} on item"
        assert it["priority"] in ("Critical", "High", "Medium", "Low")
        assert it["color"] in ("red", "orange", "yellow", "green")
        assert 0 <= it["score"] <= 100
        a = it["action"]
        for k in ("label", "kind", "link", "command", "project_id", "client_id"):
            assert k in a
        assert "project_name" in it["entity"] and "client_name" in it["entity"]


# ---------------- GET /api/opportunities/brief ----------------
class TestBrief:
    def test_brief(self, client):
        r = client.get(f"{API}/opportunities/brief")
        assert r.status_code == 200
        b = r.json()
        for k in ("greeting", "lines", "total_time_saved", "total", "top"):
            assert k in b
        assert b["greeting"].startswith("Good ")
        assert isinstance(b["lines"], list) and len(b["lines"]) >= 1
        assert len(b["top"]) <= 3


# ---------------- GET /api/opportunities/health ----------------
class TestHealth:
    def test_health(self, client):
        r = client.get(f"{API}/opportunities/health")
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


# ---------------- POST /api/opportunities/dismiss ----------------
class TestDismiss:
    def test_dismiss_hides_key(self, client):
        r = client.get(f"{API}/opportunities")
        items = r.json()["items"]
        if not items:
            pytest.skip("no opportunities to dismiss")
        key = items[0]["key"]
        d = client.post(f"{API}/opportunities/dismiss", json={"key": key})
        assert d.status_code == 200 and d.json().get("ok") is True
        # reload
        r2 = client.get(f"{API}/opportunities")
        keys = {i["key"] for i in r2.json()["items"]}
        assert key not in keys, f"dismissed key {key} still present"


# ---------------- POST /api/opportunities/archive-project ----------------
class TestArchive:
    def test_404_unknown(self, client):
        r = client.post(f"{API}/opportunities/archive-project/does-not-exist-xyz")
        assert r.status_code == 404

    def test_archive_project(self, client):
        # Find any non-archived project on this org
        pr = client.get(f"{API}/projects")
        assert pr.status_code == 200
        projs = pr.json() if isinstance(pr.json(), list) else pr.json().get("items", [])
        target = next((p for p in projs if p.get("status") != "Archived"), None)
        if not target:
            pytest.skip("no non-archived project")
        pid = target["id"]
        r = client.post(f"{API}/opportunities/archive-project/{pid}")
        assert r.status_code == 200
        assert r.json().get("status") == "Archived"
        # verify via GET
        g = client.get(f"{API}/projects/{pid}")
        assert g.status_code == 200
        assert g.json().get("status") == "Archived"


# ---------------- Org isolation ----------------
class TestOrgIsolation:
    def test_isolation(self, client, client2):
        r1 = client.get(f"{API}/opportunities").json()
        r2 = client2.get(f"{API}/opportunities").json()
        keys1 = {i["key"] for i in r1["items"]}
        keys2 = {i["key"] for i in r2["items"]}
        # Distinct demo orgs should not share opportunity keys (which include entity IDs)
        overlap = keys1 & keys2
        assert not overlap, f"unexpected cross-org overlap: {overlap}"
