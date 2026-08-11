"""Workspace feature tests — TestClient + registered user."""

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


@pytest.fixture
def auth(client):
    return register_user(client, company="Workspace Co")


@pytest.fixture
def ids(client, auth):
    store = {"projects": [], "tasks": [], "documents": [], "proposals": [], "headers": auth["headers"]}
    payload = {
        "name": "TEST_WS_Project", "status": "In Progress", "progress": 10,
        "due": "2026-03-01", "members": 2,
        "description": "TEST desc", "notes": "TEST notes",
    }
    r = client.post("/api/projects", headers=auth["headers"], json=payload)
    assert r.status_code == 200
    store["projects"].append(r.json()["id"])
    yield store
    h = store["headers"]
    for d in list(store["documents"]):
        client.delete(f"/api/documents/{d}", headers=h)
    for p in list(store["proposals"]):
        client.delete(f"/api/proposals/{p}", headers=h)
    for t in list(store["tasks"]):
        client.delete(f"/api/tasks/{t}", headers=h)
    for p in list(store["projects"]):
        client.delete(f"/api/projects/{p}", headers=h)


class TestProjectGet:
    def test_get_project_404(self, client, auth):
        r = client.get("/api/projects/nonexistent-id-xyz", headers=auth["headers"])
        assert r.status_code == 404

    def test_create_project_with_description_notes(self, client, ids):
        pid = ids["projects"][0]
        rg = client.get(f"/api/projects/{pid}", headers=ids["headers"])
        assert rg.status_code == 200
        pj = rg.json()
        assert pj["id"] == pid
        assert pj["description"] == "TEST desc"
        assert "client_name" in pj


class TestActivityAutoLog:
    def test_project_created_activity(self, client, ids):
        pid = ids["projects"][0]
        r = client.get(f"/api/activities?project_id={pid}", headers=ids["headers"])
        assert r.status_code == 200
        types = [a["type"] for a in r.json()]
        assert "project_created" in types

    def test_task_created_and_completed_activity(self, client, ids):
        pid = ids["projects"][0]
        h = ids["headers"]
        rc = client.post("/api/tasks", headers=h, json={
            "title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": False, "due": "",
        })
        assert rc.status_code == 200
        tid = rc.json()["id"]
        ids["tasks"].append(tid)

        acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert any(a["type"] == "task_created" for a in acts)
        assert not any(a["type"] == "task_completed" for a in acts)
        assert acts[0]["type"] == "task_created"

        ru = client.put(f"/api/tasks/{tid}", headers=h, json={
            "title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": True, "due": "",
        })
        assert ru.status_code == 200
        acts2 = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert any(a["type"] == "task_completed" for a in acts2)
        assert acts2[0]["type"] == "task_completed"

        completed_count = sum(1 for a in acts2 if a["type"] == "task_completed")
        client.put(f"/api/tasks/{tid}", headers=h, json={
            "title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": True, "due": "",
        })
        acts3 = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert sum(1 for a in acts3 if a["type"] == "task_completed") == completed_count

    def test_task_created_done_true_logs_both(self, client, ids):
        pid = ids["projects"][0]
        h = ids["headers"]
        r = client.post("/api/tasks", headers=h, json={
            "title": "TEST_WS_DoneTask", "project_id": pid, "priority": "Low", "done": True, "due": "",
        })
        assert r.status_code == 200
        ids["tasks"].append(r.json()["id"])
        acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        msgs = [a["message"] for a in acts if "TEST_WS_DoneTask" in a["message"]]
        assert any("was created" in m for m in msgs)
        assert any("was completed" in m for m in msgs)


class TestDocuments:
    def test_create_list_filter_and_activity(self, client, ids):
        pid = ids["projects"][0]
        h = ids["headers"]
        r = client.post("/api/documents", headers=h, json={"name": "TEST_SOW.pdf", "type": "PDF", "project_id": pid})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_SOW.pdf"
        assert data["type"] == "PDF"
        assert data["project_id"] == pid
        ids["documents"].append(data["id"])

        rl = client.get(f"/api/documents?project_id={pid}", headers=h)
        assert rl.status_code == 200
        docs = rl.json()
        assert any(d["id"] == data["id"] for d in docs)
        assert all(d["project_id"] == pid for d in docs)

        acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert any(a["type"] == "document_uploaded" and "TEST_SOW.pdf" in a["message"] for a in acts)

    def test_delete_document(self, client, ids):
        if not ids["documents"]:
            self.test_create_list_filter_and_activity(client, ids)
        did = ids["documents"][0]
        h = ids["headers"]
        r = client.delete(f"/api/documents/{did}", headers=h)
        assert r.status_code == 200
        ids["documents"].remove(did)
        rl = client.get(f"/api/documents?project_id={ids['projects'][0]}", headers=h).json()
        assert not any(d["id"] == did for d in rl)

    def test_delete_404(self, client, auth):
        r = client.delete("/api/documents/nonexistent", headers=auth["headers"])
        assert r.status_code == 404


class TestProposals:
    def test_create_list_filter_and_activity(self, client, ids):
        pid = ids["projects"][0]
        h = ids["headers"]
        r = client.post("/api/proposals", headers=h, json={
            "title": "TEST_Proposal_A", "amount": "$5,000", "status": "Draft",
            "content": "scope", "project_id": pid,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "TEST_Proposal_A"
        ids["proposals"].append(data["id"])

        rl = client.get(f"/api/proposals?project_id={pid}", headers=h)
        assert rl.status_code == 200
        props = rl.json()
        assert any(p["id"] == data["id"] for p in props)

        acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert any(a["type"] == "proposal_generated" and "TEST_Proposal_A" in a["message"] for a in acts)

    def test_delete_proposal(self, client, ids):
        if not ids["proposals"]:
            self.test_create_list_filter_and_activity(client, ids)
        pid = ids["proposals"][0]
        r = client.delete(f"/api/proposals/{pid}", headers=ids["headers"])
        assert r.status_code == 200
        ids["proposals"].remove(pid)


class TestTasksProjectFilter:
    def test_tasks_project_filter(self, client, ids):
        pid = ids["projects"][0]
        h = ids["headers"]
        client.post("/api/tasks", headers=h, json={
            "title": "Filter Task", "project_id": pid, "priority": "Medium",
        })
        rl = client.get(f"/api/tasks?project_id={pid}", headers=h)
        assert rl.status_code == 200
        tasks = rl.json()
        assert len(tasks) >= 1
        assert all(t["project_id"] == pid for t in tasks)


class TestActivityOrdering:
    def test_newest_first(self, client, ids):
        pid = ids["projects"][0]
        acts = client.get(f"/api/activities?project_id={pid}", headers=ids["headers"]).json()
        assert len(acts) >= 1
        for i in range(len(acts) - 1):
            assert acts[i]["created_at"] >= acts[i + 1]["created_at"]


class TestCascade:
    def test_delete_project_cascades_activities(self, client, auth):
        h = auth["headers"]
        rp = client.post("/api/projects", headers=h, json={"name": "TEST_WS_Cascade", "status": "In Progress"})
        pid = rp.json()["id"]
        client.post("/api/documents", headers=h, json={"name": "TEST_c.doc", "type": "Doc", "project_id": pid})
        acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert len(acts) >= 2
        rd = client.delete(f"/api/projects/{pid}", headers=h)
        assert rd.status_code == 200
        acts2 = client.get(f"/api/activities?project_id={pid}", headers=h).json()
        assert acts2 == []
        docs = client.get("/api/documents", headers=h).json()
        for d in docs:
            if d["name"] == "TEST_c.doc":
                client.delete(f"/api/documents/{d['id']}", headers=h)
