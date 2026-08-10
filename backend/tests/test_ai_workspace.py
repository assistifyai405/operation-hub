"""AI Workspace endpoints: stats, search, versions + org isolation."""
import os
import pytest
import requests
from pathlib import Path
from conftest import auth_json

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    envf = Path("/app/frontend/.env")
    for line in envf.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE_URL = _load_url()


def _demo_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    assert r.status_code == 200, f"demo provisioning failed: {r.status_code} {r.text[:200]}"
    tok = auth_json(client, r).get("accessToken")
    assert tok, f"missing accessToken in demo response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def demo1():
    return _demo_session()


@pytest.fixture(scope="module")
def demo2():
    return _demo_session()


# ----- stats -----
class TestWorkspaceStats:
    def test_stats_shape_and_seed(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/stats")
        assert r.status_code == 200
        d = r.json()
        for k in ["total_actions", "total_time_saved", "week_count", "month_count",
                  "avg_confidence", "avg_gen_ms", "by_type", "busiest_day", "sparkline"]:
            assert k in d, f"missing key {k}"
        assert d["total_actions"] == 6, f"expected 6 seeded actions, got {d['total_actions']}"
        assert d["total_time_saved"] > 0
        assert isinstance(d["by_type"], list) and len(d["by_type"]) >= 1
        assert isinstance(d["sparkline"], list) and len(d["sparkline"]) == 7
        # avg_gen_ms should be non-zero because seed sets gen_ms
        assert d["avg_gen_ms"] > 0


# ----- search -----
class TestWorkspaceSearch:
    def test_default(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/search")
        assert r.status_code == 200
        d = r.json()
        assert "total" in d and "items" in d and "types" in d
        assert d["total"] >= 6

    def test_type_filter_proposal(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"type": "proposal"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(it["type"] == "proposal" for it in items)

    def test_text_query_northwind(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"q": "Northwind"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        for it in items:
            blob = " ".join([str(it.get(k, "")) for k in ["title", "explanation", "client_name", "project_name"]]).lower()
            assert "northwind" in blob

    def test_sort_most_saved(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"sort": "most_saved"})
        items = r.json()["items"]
        saved = [it.get("time_saved", 0) for it in items]
        assert saved == sorted(saved, reverse=True)

    def test_sort_oldest_reverses(self, demo1):
        newest = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"sort": "newest"}).json()["items"]
        oldest = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"sort": "oldest"}).json()["items"]
        assert [i["id"] for i in newest] == list(reversed([i["id"] for i in oldest]))


# ----- versions -----
class TestWorkspaceVersions:
    def test_versions_have_proposal_and_plan(self, demo1):
        r = demo1.get(f"{BASE_URL}/api/ai/workspace/versions")
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) >= 2
        types = {a["type"] for a in arr}
        assert "proposal" in types
        assert "plan" in types
        for a in arr:
            for k in ["key", "type", "icon", "label", "project_name", "current_version", "link", "versions"]:
                assert k in a, f"missing {k}"
            assert len(a["versions"]) > 1


# ----- org isolation -----
class TestOrgIsolation:
    def test_two_tenants_isolated(self, demo1, demo2):
        s1 = demo1.get(f"{BASE_URL}/api/ai/workspace/search").json()
        s2 = demo2.get(f"{BASE_URL}/api/ai/workspace/search").json()
        ids1 = {i["id"] for i in s1["items"]}
        ids2 = {i["id"] for i in s2["items"]}
        # Same seed structure but different IDs -> no overlap
        assert ids1.isdisjoint(ids2), "tenants share ai_activity ids!"
        v1 = demo1.get(f"{BASE_URL}/api/ai/workspace/versions").json()
        v2 = demo2.get(f"{BASE_URL}/api/ai/workspace/versions").json()
        p1 = {a["project_id"] for a in v1}
        p2 = {a["project_id"] for a in v2}
        assert p1.isdisjoint(p2)


# ----- regression: generate endpoint logs metadata -----
class TestGenerateMetadata:
    def test_proposal_generate_logs_meta(self, demo1):
        # find a project
        projs = demo1.get(f"{BASE_URL}/api/projects").json()
        assert projs, "no seed projects"
        pid = projs[0]["id"]
        pre = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"type": "proposal"}).json()["total"]
        r = demo1.post(f"{BASE_URL}/api/projects/{pid}/proposal/generate", json={}, timeout=90)
        if r.status_code in (502, 503) or (r.status_code >= 400 and "budget" in r.text.lower()):
            pytest.skip(f"LLM budget/unavailable: {r.status_code}")
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        post = demo1.get(f"{BASE_URL}/api/ai/workspace/search", params={"type": "proposal"}).json()
        assert post["total"] >= pre + 1
        # newest item should have gen_ms + project_name
        newest = post["items"][0]
        assert newest.get("gen_ms") is not None
        assert newest.get("project_name")
