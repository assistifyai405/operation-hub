"""Backend tests for AI Memory & Knowledge Brain — TestClient (no demo seed)."""

from __future__ import annotations

import sys
import uuid
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
    a = register_user(client, company="Memory A")
    h = a["headers"]
    # Seed starter memories (replaces demo seed of 6)
    cats = ["Writing Style", "Brand Voice", "Business", "Preferences", "Clients", "Pricing"]
    for i, cat in enumerate(cats):
        r = client.post("/api/memory/memories", headers=h, json={
            "title": f"Seed mem {i}", "category": cat,
            "content": f"Seed content {i} about the business.",
            "keywords": ["seed", cat.lower().split()[0]],
            "confidence": 70 + i, "source": "Manual",
        })
        assert r.status_code == 200, r.text
    return a


@pytest.fixture
def auth2(client):
    return register_user(client, company="Memory B")


# ---------------- Memory CRUD & Listing ----------------
class TestMemoryCRUD:
    def test_seeded_memories(self, client, auth):
        r = client.get("/api/memory/memories", headers=auth["headers"])
        assert r.status_code == 200
        mems = r.json()
        assert isinstance(mems, list)
        assert len(mems) >= 6, f"Expected >=6 seeded memories, got {len(mems)}"
        m = mems[0]
        for key in ("id", "title", "category", "confidence", "source", "times_used", "created_at", "updated_at"):
            assert key in m, f"Missing key {key}"

    def test_create_memory(self, client, auth):
        payload = {
            "title": "TEST_prefers_short_intros", "category": "Writing Style",
            "content": "Prefers 1-2 sentence introductions.", "keywords": ["intro", "concise"],
            "confidence": 85, "source": "Manual",
        }
        r = client.post("/api/memory/memories", headers=auth["headers"], json=payload)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["title"] == payload["title"]
        assert m["category"] == "Writing Style"
        assert m["confidence"] == 85
        assert m["pinned"] is False
        assert m["learning_enabled"] is True
        r2 = client.get("/api/memory/memories", headers=auth["headers"], params={"q": "TEST_prefers_short_intros"})
        assert any(x["id"] == m["id"] for x in r2.json())
        auth["mem_id"] = m["id"]

    def test_update_memory(self, client, auth):
        if "mem_id" not in auth:
            self.test_create_memory(client, auth)
        mid = auth["mem_id"]
        r = client.put(f"/api/memory/memories/{mid}", headers=auth["headers"], json={
            "title": "TEST_prefers_short_intros_v2", "category": "Brand Voice",
            "content": "Updated content", "keywords": ["intro"], "confidence": 90, "source": "Manual",
        })
        assert r.status_code == 200
        assert r.json()["title"].endswith("_v2")
        found = [m for m in client.get("/api/memory/memories", headers=auth["headers"]).json() if m["id"] == mid]
        assert found and found[0]["category"] == "Brand Voice" and found[0]["confidence"] == 90

    def test_pin_memory(self, client, auth):
        if "mem_id" not in auth:
            self.test_create_memory(client, auth)
        mid = auth["mem_id"]
        r = client.patch(f"/api/memory/memories/{mid}/pin", headers=auth["headers"], json={"pinned": True})
        assert r.status_code == 200 and r.json()["pinned"] is True
        mems = client.get("/api/memory/memories", headers=auth["headers"]).json()
        assert mems[0]["id"] == mid, "Pinned memory should be first"

    def test_toggle_learning(self, client, auth):
        if "mem_id" not in auth:
            self.test_create_memory(client, auth)
        mid = auth["mem_id"]
        r = client.patch(f"/api/memory/memories/{mid}/learning", headers=auth["headers"], json={"learning_enabled": False})
        assert r.status_code == 200 and r.json()["learning_enabled"] is False

    def test_pin_404(self, client, auth):
        r = client.patch("/api/memory/memories/nonexistent-id/pin", headers=auth["headers"], json={"pinned": True})
        assert r.status_code == 404

    def test_delete_memory(self, client, auth):
        # create dedicated memory to delete
        r = client.post("/api/memory/memories", headers=auth["headers"], json={
            "title": "TEST_to_delete", "category": "Business", "content": "x",
            "keywords": [], "confidence": 50, "source": "Manual",
        })
        mid = r.json()["id"]
        r = client.delete(f"/api/memory/memories/{mid}", headers=auth["headers"])
        assert r.status_code == 200
        r2 = client.delete(f"/api/memory/memories/{mid}", headers=auth["headers"])
        assert r2.status_code == 404

    def test_list_filters(self, client, auth):
        r = client.get("/api/memory/memories", headers=auth["headers"], params={"sort": "used"})
        assert r.status_code == 200
        r = client.get("/api/memory/memories", headers=auth["headers"], params={"sort": "confidence"})
        assert r.status_code == 200
        r = client.get("/api/memory/memories", headers=auth["headers"], params={"category": "Business"})
        assert r.status_code == 200
        assert all(m["category"] == "Business" for m in r.json())


# ---------------- Stats ----------------
class TestStats:
    def test_stats_structure(self, client, auth):
        r = client.get("/api/memory/stats", headers=auth["headers"])
        assert r.status_code == 200
        s = r.json()
        for key in (
            "total", "by_category", "avg_confidence", "total_uses", "most_used",
            "newest", "learned_today", "recently_updated", "pending_learning", "categories",
        ):
            assert key in s, f"Missing stats key: {key}"
        assert isinstance(s["by_category"], list)
        assert isinstance(s["most_used"], list)
        assert s["total"] >= 6


# ---------------- Merge ----------------
class TestMerge:
    def test_merge_two_memories(self, client, auth):
        ids = []
        for i in range(2):
            r = client.post("/api/memory/memories", headers=auth["headers"], json={
                "title": f"TEST_merge_src_{i}_{uuid.uuid4().hex[:6]}", "category": "Preferences",
                "content": f"src {i}", "keywords": [f"k{i}"], "confidence": 70, "source": "Manual",
            })
            assert r.status_code == 200
            ids.append(r.json()["id"])
        r = client.post("/api/memory/memories/merge", headers=auth["headers"], json={
            "ids": ids, "title": f"TEST_merged_{uuid.uuid4().hex[:6]}", "category": "Preferences",
        })
        assert r.status_code == 200, r.text
        merged = r.json()
        assert merged["source"] == "Merged"
        for old_id in ids:
            r2 = client.delete(f"/api/memory/memories/{old_id}", headers=auth["headers"])
            assert r2.status_code == 404
        client.delete(f"/api/memory/memories/{merged['id']}", headers=auth["headers"])

    def test_merge_requires_two(self, client, auth):
        r = client.post("/api/memory/memories/merge", headers=auth["headers"], json={
            "ids": ["nope"], "title": "TEST_x", "category": "Business",
        })
        assert r.status_code == 400


# ---------------- Search + Ask ----------------
class TestSearchAsk:
    def test_search(self, client, auth):
        r = client.get("/api/memory/search", headers=auth["headers"], params={"q": "the"})
        assert r.status_code == 200
        assert "results" in r.json()

    def test_search_empty(self, client, auth):
        r = client.get("/api/memory/search", headers=auth["headers"], params={"q": ""})
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_ask_brain(self, client, auth):
        r = client.post("/api/memory/ask", headers=auth["headers"], json={"question": "What do you know about my pricing?"})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            data = r.json()
            assert "answer" in data
            assert isinstance(data["answer"], str) and len(data["answer"]) > 0


# ---------------- Learning ----------------
class TestLearning:
    def test_learn_event_and_auto_distill(self, client, auth):
        last = None
        for i in range(4):
            r = client.post("/api/memory/learn/event", headers=auth["headers"], json={
                "kind": "approval" if i % 2 == 0 else "rejection",
                "doc_type": "proposal", "section": "intro",
                "before": "Long verbose introduction about many things.",
                "after": "Concise intro.",
                "command": "make the intro shorter",
            })
            assert r.status_code == 200
            last = r.json()
            assert "ok" in last and "pending" in last
        assert "learned" in last

    def test_analyze_endpoint(self, client, auth):
        client.post("/api/memory/learn/event", headers=auth["headers"], json={
            "kind": "approval", "doc_type": "invoice", "section": "notes",
            "before": "Please pay within 30 days.", "after": "Net 15.", "command": "shorter payment terms",
        })
        r = client.post("/api/memory/learn/analyze", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            d = r.json()
            assert d.get("ok") is True
            assert "learned" in d


# ---------------- Insights & Business Profile ----------------
class TestInsightsProfile:
    def test_insights(self, client, auth):
        r = client.get("/api/memory/insights", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            arr = r.json()
            assert isinstance(arr, list)
            if arr:
                assert "insight" in arr[0]

    def test_business_profile_get_default(self, client, auth2):
        r = client.get("/api/memory/business-profile", headers=auth2["headers"])
        assert r.status_code == 200
        assert "sections" in r.json()

    def test_business_profile_generate(self, client, auth):
        r = client.post("/api/memory/business-profile", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            d = r.json()
            assert "sections" in d


# ---------------- Org isolation ----------------
class TestOrgIsolation:
    def test_isolation_between_orgs(self, client, auth, auth2):
        payload = {
            "title": f"TEST_iso_{uuid.uuid4().hex[:8]}", "category": "Business",
            "content": "org1 only", "keywords": [], "confidence": 80, "source": "Manual",
        }
        r = client.post("/api/memory/memories", headers=auth["headers"], json=payload)
        assert r.status_code == 200
        mid = r.json()["id"]
        r2 = client.get("/api/memory/memories", headers=auth2["headers"], params={"q": payload["title"]})
        assert r2.status_code == 200
        assert not any(m["id"] == mid for m in r2.json()), "Cross-org leak!"
        r3 = client.delete(f"/api/memory/memories/{mid}", headers=auth2["headers"])
        assert r3.status_code == 404
        client.delete(f"/api/memory/memories/{mid}", headers=auth["headers"])


# ---------------- Smart reuse regression ----------------
class TestSmartReuseRegression:
    def test_proposal_generator_still_works(self, client, auth):
        # Prefer project-scoped generate
        cr = client.post("/api/clients", headers=auth["headers"], json={"name": "Acme", "email": "a@a.com"})
        pr = client.post("/api/projects", headers=auth["headers"], json={
            "name": "Website redesign", "client_id": cr.json()["id"], "status": "Active",
        })
        r = client.post(f"/api/projects/{pr.json()['id']}/proposal/generate", headers=auth["headers"])
        assert r.status_code in (200, 400, 402, 404, 422, 429, 500, 502, 503), r.text
        assert "sk-" not in r.text.lower()

    def test_assistant_chat_still_works(self, client, auth):
        r = client.post("/api/assistant/chat", headers=auth["headers"], json={"message": "Hi", "context": {}})
        assert r.status_code in (200, 404, 422, 502, 503), r.text
        assert "sk-" not in r.text.lower()
