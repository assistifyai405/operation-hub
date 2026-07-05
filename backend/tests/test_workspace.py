"""Workspace feature tests: projects.get, documents, proposals, activities, activity auto-logging."""
import os
import time
import requests
import pytest

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def ids():
    return {"projects": [], "tasks": [], "documents": [], "proposals": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup(ids):
    yield
    for d in ids["documents"]:
        requests.delete(f"{API}/documents/{d}")
    for p in ids["proposals"]:
        requests.delete(f"{API}/proposals/{p}")
    for t in ids["tasks"]:
        requests.delete(f"{API}/tasks/{t}")
    for p in ids["projects"]:
        requests.delete(f"{API}/projects/{p}")


class TestProjectGet:
    def test_get_project_404(self):
        r = requests.get(f"{API}/projects/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_create_project_with_description_notes(self, ids):
        payload = {
            "name": "TEST_WS_Project", "status": "In Progress", "progress": 10,
            "due": "2026-03-01", "members": 2,
            "description": "TEST desc", "notes": "TEST notes",
        }
        r = requests.post(f"{API}/projects", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["description"] == "TEST desc"
        assert data["notes"] == "TEST notes"
        ids["projects"].append(data["id"])

        # GET single
        rg = requests.get(f"{API}/projects/{data['id']}")
        assert rg.status_code == 200
        pj = rg.json()
        assert pj["id"] == data["id"]
        assert pj["description"] == "TEST desc"
        assert "client_name" in pj


class TestActivityAutoLog:
    def test_project_created_activity(self, ids):
        pid = ids["projects"][0]
        r = requests.get(f"{API}/activities?project_id={pid}")
        assert r.status_code == 200
        acts = r.json()
        types = [a["type"] for a in acts]
        assert "project_created" in types

    def test_task_created_and_completed_activity(self, ids):
        pid = ids["projects"][0]
        # create task not done
        rc = requests.post(f"{API}/tasks", json={"title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": False, "due": ""})
        assert rc.status_code == 200
        tid = rc.json()["id"]
        ids["tasks"].append(tid)

        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        assert any(a["type"] == "task_created" for a in acts)
        assert not any(a["type"] == "task_completed" for a in acts)

        # newest-first assertion
        assert acts[0]["type"] == "task_created"

        # Update to done=True
        ru = requests.put(f"{API}/tasks/{tid}", json={"title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": True, "due": ""})
        assert ru.status_code == 200
        acts2 = requests.get(f"{API}/activities?project_id={pid}").json()
        assert any(a["type"] == "task_completed" for a in acts2)
        assert acts2[0]["type"] == "task_completed"  # newest

        # Update again with done=True (already done) should NOT log a duplicate task_completed
        completed_count = sum(1 for a in acts2 if a["type"] == "task_completed")
        ru2 = requests.put(f"{API}/tasks/{tid}", json={"title": "TEST_WS_Task", "project_id": pid, "priority": "High", "done": True, "due": ""})
        assert ru2.status_code == 200
        acts3 = requests.get(f"{API}/activities?project_id={pid}").json()
        completed_count2 = sum(1 for a in acts3 if a["type"] == "task_completed")
        assert completed_count2 == completed_count

    def test_task_created_done_true_logs_both(self, ids):
        pid = ids["projects"][0]
        r = requests.post(f"{API}/tasks", json={"title": "TEST_WS_DoneTask", "project_id": pid, "priority": "Low", "done": True, "due": ""})
        assert r.status_code == 200
        ids["tasks"].append(r.json()["id"])
        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        # both events for this task
        msgs = [a["message"] for a in acts if "TEST_WS_DoneTask" in a["message"]]
        assert any("was created" in m for m in msgs)
        assert any("was completed" in m for m in msgs)


class TestDocuments:
    def test_create_list_filter_and_activity(self, ids):
        pid = ids["projects"][0]
        r = requests.post(f"{API}/documents", json={"name": "TEST_SOW.pdf", "type": "PDF", "project_id": pid})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_SOW.pdf"
        assert data["type"] == "PDF"
        assert data["project_id"] == pid
        ids["documents"].append(data["id"])

        # filter by project_id
        rl = requests.get(f"{API}/documents?project_id={pid}")
        assert rl.status_code == 200
        docs = rl.json()
        assert any(d["id"] == data["id"] for d in docs)
        assert all(d["project_id"] == pid for d in docs)

        # activity logged
        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        assert any(a["type"] == "document_uploaded" and "TEST_SOW.pdf" in a["message"] for a in acts)

    def test_delete_document(self, ids):
        did = ids["documents"][0]
        r = requests.delete(f"{API}/documents/{did}")
        assert r.status_code == 200
        ids["documents"].remove(did)
        rl = requests.get(f"{API}/documents?project_id={ids['projects'][0]}").json()
        assert not any(d["id"] == did for d in rl)

    def test_delete_404(self):
        r = requests.delete(f"{API}/documents/nonexistent")
        assert r.status_code == 404


class TestProposals:
    def test_create_list_filter_and_activity(self, ids):
        pid = ids["projects"][0]
        r = requests.post(f"{API}/proposals", json={"title": "TEST_Proposal_A", "amount": "$5,000", "status": "Draft", "content": "scope", "project_id": pid})
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "TEST_Proposal_A"
        ids["proposals"].append(data["id"])

        rl = requests.get(f"{API}/proposals?project_id={pid}")
        assert rl.status_code == 200
        props = rl.json()
        assert any(p["id"] == data["id"] for p in props)

        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        assert any(a["type"] == "proposal_generated" and "TEST_Proposal_A" in a["message"] for a in acts)

    def test_delete_proposal(self, ids):
        pid = ids["proposals"][0]
        r = requests.delete(f"{API}/proposals/{pid}")
        assert r.status_code == 200
        ids["proposals"].remove(pid)


class TestTasksProjectFilter:
    def test_tasks_project_filter(self, ids):
        pid = ids["projects"][0]
        rl = requests.get(f"{API}/tasks?project_id={pid}")
        assert rl.status_code == 200
        tasks = rl.json()
        assert len(tasks) >= 1
        assert all(t["project_id"] == pid for t in tasks)


class TestActivityOrdering:
    def test_newest_first(self, ids):
        pid = ids["projects"][0]
        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        assert len(acts) >= 2
        # ISO strings sort correctly lexicographically
        for i in range(len(acts) - 1):
            assert acts[i]["created_at"] >= acts[i + 1]["created_at"]


class TestCascade:
    def test_delete_project_cascades_activities(self):
        # Create fresh project, add doc, then delete project -> activities gone
        rp = requests.post(f"{API}/projects", json={"name": "TEST_WS_Cascade", "status": "In Progress"})
        pid = rp.json()["id"]
        requests.post(f"{API}/documents", json={"name": "TEST_c.doc", "type": "Doc", "project_id": pid})
        acts = requests.get(f"{API}/activities?project_id={pid}").json()
        assert len(acts) >= 2
        rd = requests.delete(f"{API}/projects/{pid}")
        assert rd.status_code == 200
        acts2 = requests.get(f"{API}/activities?project_id={pid}").json()
        assert acts2 == []
        # cleanup doc manually
        docs = requests.get(f"{API}/documents").json()
        for d in docs:
            if d["name"] == "TEST_c.doc":
                requests.delete(f"{API}/documents/{d['id']}")
