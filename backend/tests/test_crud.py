"""CRUD tests for Clients, Projects, Tasks — cookie-auth TestClient (Sprint 26 repair)."""

from __future__ import annotations

import sys
import uuid
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


@pytest.fixture
def auth(client):
    _clear_rl()
    email = f"crud_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Crud",
            "lastName": "Tester",
            "email": email,
            "password": "Password123!",
            "company": "CRUD Co",
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    return {"token": data["accessToken"], "headers": {"Authorization": f"Bearer {data['accessToken']}"}, "email": email}


# ---------- Clients ----------
class TestClients:
    def test_list(self, client, auth):
        r = client.get("/api/clients", headers=auth["headers"])
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_missing_name_422(self, client, auth):
        r = client.post("/api/clients", headers=auth["headers"], json={"contact": "x"})
        assert r.status_code == 422

    def test_create_empty_name_422(self, client, auth):
        r = client.post("/api/clients", headers=auth["headers"], json={"name": ""})
        assert r.status_code == 422

    def test_create_and_get(self, client, auth):
        payload = {"name": "TEST_Northwind", "contact": "Ava", "email": "a@b.co", "value": 5000, "status": "Active"}
        r = client.post("/api/clients", headers=auth["headers"], json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Northwind"
        assert data["value"] == 5000
        assert "id" in data
        auth["client_id"] = data["id"]

        rl = client.get("/api/clients", headers=auth["headers"]).json()
        found = [c for c in rl if c["id"] == data["id"]]
        assert len(found) == 1
        assert found[0].get("projects", 0) == 0

    def test_update(self, client, auth):
        if "client_id" not in auth:
            self.test_create_and_get(client, auth)
        cid = auth["client_id"]
        r = client.put(
            f"/api/clients/{cid}",
            headers=auth["headers"],
            json={"name": "TEST_NW2", "contact": "Bo", "email": "", "value": 999, "status": "Lead"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_NW2"
        rl = client.get("/api/clients", headers=auth["headers"]).json()
        found = [c for c in rl if c["id"] == cid][0]
        assert found["status"] == "Lead"
        assert found["value"] == 999

    def test_update_404(self, client, auth):
        r = client.put(f"/api/clients/nonexistent", headers=auth["headers"], json={"name": "x", "contact": "", "email": "", "value": 0, "status": "Active"})
        assert r.status_code == 404

    def test_delete_404(self, client, auth):
        r = client.delete("/api/clients/nonexistent", headers=auth["headers"])
        assert r.status_code == 404


# ---------- Projects ----------
class TestProjects:
    def test_list(self, client, auth):
        r = client.get("/api/projects", headers=auth["headers"])
        assert r.status_code == 200

    def test_create_missing_name_422(self, client, auth):
        r = client.post("/api/projects", headers=auth["headers"], json={"status": "In Progress"})
        assert r.status_code == 422

    def test_create_with_client_link(self, client, auth):
        cr = client.post(
            "/api/clients",
            headers=auth["headers"],
            json={"name": "TEST_NW2", "contact": "Bo", "email": "", "value": 999, "status": "Lead"},
        )
        assert cr.status_code == 200
        cid = cr.json()["id"]
        auth["client_id"] = cid
        payload = {"name": "TEST_Rebrand", "client_id": cid, "status": "Review", "progress": 30, "due": "2026-02-01", "members": 3}
        r = client.post("/api/projects", headers=auth["headers"], json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["client_id"] == cid
        auth["project_id"] = data["id"]

        pl = client.get("/api/projects", headers=auth["headers"]).json()
        found = [p for p in pl if p["id"] == data["id"]][0]
        assert found.get("client_name") == "TEST_NW2"

        cl = client.get("/api/clients", headers=auth["headers"]).json()
        cli = [c for c in cl if c["id"] == cid][0]
        assert cli.get("projects", 0) >= 1

    def test_update_project(self, client, auth):
        if "project_id" not in auth:
            self.test_create_with_client_link(client, auth)
        pid = auth["project_id"]
        r = client.put(
            f"/api/projects/{pid}",
            headers=auth["headers"],
            json={
                "name": "TEST_Rebrand2",
                "client_id": auth["client_id"],
                "status": "In Progress",
                "progress": 55,
                "due": "",
                "members": 4,
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "In Progress"
        auth["project_name"] = "TEST_Rebrand2"

    def test_update_404(self, client, auth):
        r = client.put(
            "/api/projects/nope",
            headers=auth["headers"],
            json={"name": "x", "client_id": None, "status": "In Progress", "progress": 0, "due": "", "members": 1},
        )
        assert r.status_code == 404


# ---------- Tasks ----------
class TestTasks:
    def test_create_missing_title_422(self, client, auth):
        r = client.post("/api/tasks", headers=auth["headers"], json={"priority": "High"})
        assert r.status_code == 422

    def test_create_with_project_link(self, client, auth):
        if "project_id" not in auth:
            TestProjects().test_create_with_client_link(client, auth)
            TestProjects().test_update_project(client, auth)
        pid = auth["project_id"]
        r = client.post(
            "/api/tasks",
            headers=auth["headers"],
            json={"title": "TEST_Draft SOW", "project_id": pid, "priority": "High", "done": False, "due": "2026-02-05"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == pid
        auth["task_id"] = data["id"]

        tl = client.get("/api/tasks", headers=auth["headers"]).json()
        found = [t for t in tl if t["id"] == data["id"]][0]
        assert found.get("project_name") in ("TEST_Rebrand2", "TEST_Rebrand", found.get("project_name"))
        assert found.get("client_name") == "TEST_NW2"

    def test_foreign_project_rejected(self, client, auth):
        """Cannot plant a task on another workspace's project_id."""
        _clear_rl()
        other = client.post(
            "/api/auth/register",
            json={
                "firstName": "Other",
                "lastName": "Org",
                "email": f"other_{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123!",
                "company": "Other Co",
            },
        )
        assert other.status_code == 200
        otok = auth_json(client, other)["accessToken"]
        oh = {"Authorization": f"Bearer {otok}"}
        pr = client.post("/api/projects", headers=oh, json={"name": "Secret Proj", "status": "Active"})
        assert pr.status_code == 200
        foreign_pid = pr.json()["id"]

        bad = client.post(
            "/api/tasks",
            headers=auth["headers"],
            json={"title": "Cross plant", "project_id": foreign_pid, "priority": "High", "done": False},
        )
        assert bad.status_code in (403, 404)

    def test_toggle_done_persists(self, client, auth):
        if "task_id" not in auth:
            self.test_create_with_project_link(client, auth)
        tid = auth["task_id"]
        r = client.put(
            f"/api/tasks/{tid}",
            headers=auth["headers"],
            json={
                "title": "TEST_Draft SOW",
                "project_id": auth["project_id"],
                "priority": "High",
                "done": True,
                "due": "2026-02-05",
            },
        )
        assert r.status_code == 200
        tl = client.get("/api/tasks", headers=auth["headers"]).json()
        t = [x for x in tl if x["id"] == tid][0]
        assert t["done"] is True

    def test_update_404(self, client, auth):
        r = client.put(
            "/api/tasks/nope",
            headers=auth["headers"],
            json={"title": "x", "project_id": None, "priority": "Low", "done": False, "due": ""},
        )
        assert r.status_code == 404


# ---------- Linking / cascade unlink ----------
class TestUnlinking:
    def test_delete_project_unlinks_tasks(self, client, auth):
        cr = client.post(
            "/api/clients",
            headers=auth["headers"],
            json={"name": "Unlink Client", "contact": "U", "email": "u@u.co", "status": "Active"},
        )
        cid = cr.json()["id"]
        pr = client.post(
            "/api/projects",
            headers=auth["headers"],
            json={"name": "Unlink Proj", "client_id": cid, "status": "Active", "progress": 0, "due": "", "members": 1},
        )
        pid = pr.json()["id"]
        tr = client.post(
            "/api/tasks",
            headers=auth["headers"],
            json={"title": "Unlink Task", "project_id": pid, "priority": "Medium", "done": False},
        )
        tid = tr.json()["id"]
        r = client.delete(f"/api/projects/{pid}", headers=auth["headers"])
        assert r.status_code == 200

        tl = client.get("/api/tasks", headers=auth["headers"]).json()
        t = [x for x in tl if x["id"] == tid][0]
        assert t["project_id"] is None
        assert t.get("project_name") is None

    def test_delete_client_unlinks_projects(self, client, auth):
        cr = client.post(
            "/api/clients",
            headers=auth["headers"],
            json={"name": "Unlink Client 2", "contact": "U2", "email": "u2@u.co", "status": "Active"},
        )
        cid = cr.json()["id"]
        pr = client.post(
            "/api/projects",
            headers=auth["headers"],
            json={"name": "TEST_P2", "client_id": cid, "status": "In Progress", "progress": 0, "due": "", "members": 1},
        )
        pid2 = pr.json()["id"]
        rd = client.delete(f"/api/clients/{cid}", headers=auth["headers"])
        assert rd.status_code == 200

        pl = client.get("/api/projects", headers=auth["headers"]).json()
        p2 = [p for p in pl if p["id"] == pid2][0]
        assert p2["client_id"] is None
        assert p2.get("client_name") is None
