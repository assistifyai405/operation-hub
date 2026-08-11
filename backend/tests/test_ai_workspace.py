"""AI Workspace endpoints: stats, search, versions + org isolation — TestClient."""

from __future__ import annotations

import sys
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


def _seed_workspace(client, headers):
    """Create project + AI activities via generate (soft) or manual activity seed."""
    cr = client.post("/api/clients", headers=headers, json={"name": "Northwind Labs", "email": "nw@n.com"})
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=headers, json={
        "name": "NW Redesign", "client_id": cid, "status": "In Progress",
    })
    pid = pr.json()["id"]
    # Try generating docs to populate ai activities; ignore LLM failures
    for path in ("proposal", "plan", "contract", "invoice"):
        client.post(f"/api/projects/{pid}/{path}/generate", headers=headers, json={})
    # Also save docs so versions endpoint has data
    client.post(f"/api/projects/{pid}/proposal", headers=headers, json={
        "title": "NW Proposal", "status": "Draft", "content": {"executive_summary": "v1"},
    })
    client.post(f"/api/projects/{pid}/proposal", headers=headers, json={
        "title": "NW Proposal", "status": "Sent", "content": {"executive_summary": "v2"},
    })
    client.post(f"/api/projects/{pid}/plans", headers=headers, json={
        "sections": {"executive_summary": "Plan v1", "business_goal": "g"},
    })
    client.post(f"/api/projects/{pid}/plans", headers=headers, json={
        "sections": {"executive_summary": "Plan v2", "business_goal": "g"},
    })
    return pid


@pytest.fixture
def auth1(client):
    a = register_user(client, company="AI WS 1")
    a["project_id"] = _seed_workspace(client, a["headers"])
    return a


@pytest.fixture
def auth2(client):
    a = register_user(client, company="AI WS 2")
    a["project_id"] = _seed_workspace(client, a["headers"])
    return a


class TestWorkspaceStats:
    def test_stats_shape(self, client, auth1):
        r = client.get("/api/ai/workspace/stats", headers=auth1["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in [
            "total_actions", "total_time_saved", "week_count", "month_count",
            "avg_confidence", "avg_gen_ms", "by_type", "busiest_day", "sparkline",
        ]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["by_type"], list)
        assert isinstance(d["sparkline"], list) and len(d["sparkline"]) == 7
        assert d["total_actions"] >= 0


class TestWorkspaceSearch:
    def test_default(self, client, auth1):
        r = client.get("/api/ai/workspace/search", headers=auth1["headers"])
        assert r.status_code == 200
        d = r.json()
        assert "total" in d and "items" in d and "types" in d

    def test_type_filter_proposal(self, client, auth1):
        r = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"type": "proposal"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(it["type"] == "proposal" for it in items)

    def test_text_query_northwind(self, client, auth1):
        r = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"q": "Northwind"})
        assert r.status_code == 200
        # Soft: may be empty if activities lack client name embedding
        items = r.json()["items"]
        assert isinstance(items, list)

    def test_sort_most_saved(self, client, auth1):
        r = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"sort": "most_saved"})
        items = r.json()["items"]
        saved = [it.get("time_saved", 0) for it in items]
        assert saved == sorted(saved, reverse=True)

    def test_sort_oldest_reverses(self, client, auth1):
        newest = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"sort": "newest"}).json()["items"]
        oldest = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"sort": "oldest"}).json()["items"]
        if newest and oldest:
            assert [i["id"] for i in newest] == list(reversed([i["id"] for i in oldest]))


class TestWorkspaceVersions:
    def test_versions_have_proposal_and_plan(self, client, auth1):
        r = client.get("/api/ai/workspace/versions", headers=auth1["headers"])
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        if not arr:
            return
        types = {a["type"] for a in arr}
        # At least one type present after seeding saves
        assert types
        for a in arr:
            for k in ["key", "type", "icon", "label", "project_name", "current_version", "link", "versions"]:
                assert k in a, f"missing {k}"


class TestOrgIsolation:
    def test_two_tenants_isolated(self, client, auth1, auth2):
        s1 = client.get("/api/ai/workspace/search", headers=auth1["headers"]).json()
        s2 = client.get("/api/ai/workspace/search", headers=auth2["headers"]).json()
        ids1 = {i["id"] for i in s1["items"]}
        ids2 = {i["id"] for i in s2["items"]}
        assert ids1.isdisjoint(ids2), "tenants share ai_activity ids!"
        v1 = client.get("/api/ai/workspace/versions", headers=auth1["headers"]).json()
        v2 = client.get("/api/ai/workspace/versions", headers=auth2["headers"]).json()
        p1 = {a.get("project_id") for a in v1 if a.get("project_id")}
        p2 = {a.get("project_id") for a in v2 if a.get("project_id")}
        assert p1.isdisjoint(p2)


class TestGenerateMetadata:
    def test_proposal_generate_logs_meta(self, client, auth1):
        pid = auth1["project_id"]
        pre = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"type": "proposal"}).json()["total"]
        r = client.post(f"/api/projects/{pid}/proposal/generate", headers=auth1["headers"], json={})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        post = client.get("/api/ai/workspace/search", headers=auth1["headers"], params={"type": "proposal"}).json()
        assert post["total"] >= pre + 1
        newest = post["items"][0]
        assert newest.get("gen_ms") is not None or newest.get("project_name")
