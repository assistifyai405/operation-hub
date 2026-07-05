"""CRUD tests for Clients, Projects, Tasks with linking + delete unlink verification."""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://operations-hub-75.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def created_ids():
    return {"clients": [], "projects": [], "tasks": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup(created_ids):
    yield
    for tid in created_ids["tasks"]:
        requests.delete(f"{API}/tasks/{tid}")
    for pid in created_ids["projects"]:
        requests.delete(f"{API}/projects/{pid}")
    for cid in created_ids["clients"]:
        requests.delete(f"{API}/clients/{cid}")


# ---------- Clients ----------
class TestClients:
    def test_list(self):
        r = requests.get(f"{API}/clients")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_missing_name_422(self):
        r = requests.post(f"{API}/clients", json={"contact": "x"})
        assert r.status_code == 422

    def test_create_empty_name_422(self):
        r = requests.post(f"{API}/clients", json={"name": ""})
        assert r.status_code == 422

    def test_create_and_get(self, created_ids):
        payload = {"name": "TEST_Northwind", "contact": "Ava", "email": "a@b.co", "value": 5000, "status": "Active"}
        r = requests.post(f"{API}/clients", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Northwind"
        assert data["value"] == 5000
        assert "id" in data
        created_ids["clients"].append(data["id"])

        # GET verify
        rl = requests.get(f"{API}/clients").json()
        found = [c for c in rl if c["id"] == data["id"]]
        assert len(found) == 1
        assert found[0]["projects"] == 0  # projects count field

    def test_update(self, created_ids):
        cid = created_ids["clients"][0]
        r = requests.put(f"{API}/clients/{cid}", json={"name": "TEST_NW2", "contact": "Bo", "email": "", "value": 999, "status": "Lead"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_NW2"
        # persisted
        rl = requests.get(f"{API}/clients").json()
        found = [c for c in rl if c["id"] == cid][0]
        assert found["status"] == "Lead"
        assert found["value"] == 999

    def test_update_404(self):
        r = requests.put(f"{API}/clients/nonexistent", json={"name": "x"})
        assert r.status_code == 404

    def test_delete_404(self):
        r = requests.delete(f"{API}/clients/nonexistent")
        assert r.status_code == 404


# ---------- Projects ----------
class TestProjects:
    def test_list(self):
        r = requests.get(f"{API}/projects")
        assert r.status_code == 200

    def test_create_missing_name_422(self):
        r = requests.post(f"{API}/projects", json={"status": "In Progress"})
        assert r.status_code == 422

    def test_create_with_client_link(self, created_ids):
        cid = created_ids["clients"][0]
        payload = {"name": "TEST_Rebrand", "client_id": cid, "status": "Review", "progress": 30, "due": "2026-02-01", "members": 3}
        r = requests.post(f"{API}/projects", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["client_id"] == cid
        created_ids["projects"].append(data["id"])

        # list should enrich with client_name
        pl = requests.get(f"{API}/projects").json()
        found = [p for p in pl if p["id"] == data["id"]][0]
        assert "client_name" in found
        assert found["client_name"] == "TEST_NW2"

        # client projects count should now be 1
        cl = requests.get(f"{API}/clients").json()
        cli = [c for c in cl if c["id"] == cid][0]
        assert cli["projects"] == 1

    def test_update_project(self, created_ids):
        pid = created_ids["projects"][0]
        r = requests.put(f"{API}/projects/{pid}", json={"name": "TEST_Rebrand2", "client_id": created_ids["clients"][0], "status": "In Progress", "progress": 55, "due": "", "members": 4})
        assert r.status_code == 200
        assert r.json()["status"] == "In Progress"

    def test_update_404(self):
        r = requests.put(f"{API}/projects/nope", json={"name": "x"})
        assert r.status_code == 404


# ---------- Tasks ----------
class TestTasks:
    def test_create_missing_title_422(self):
        r = requests.post(f"{API}/tasks", json={"priority": "High"})
        assert r.status_code == 422

    def test_create_with_project_link(self, created_ids):
        pid = created_ids["projects"][0]
        r = requests.post(f"{API}/tasks", json={"title": "TEST_Draft SOW", "project_id": pid, "priority": "High", "done": False, "due": "2026-02-05"})
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == pid
        created_ids["tasks"].append(data["id"])

        # list enriches project_name + client_name
        tl = requests.get(f"{API}/tasks").json()
        found = [t for t in tl if t["id"] == data["id"]][0]
        assert found["project_name"] == "TEST_Rebrand2"
        assert found["client_name"] == "TEST_NW2"

    def test_toggle_done_persists(self, created_ids):
        tid = created_ids["tasks"][0]
        r = requests.put(f"{API}/tasks/{tid}", json={"title": "TEST_Draft SOW", "project_id": created_ids["projects"][0], "priority": "High", "done": True, "due": "2026-02-05"})
        assert r.status_code == 200
        # verify persistence
        tl = requests.get(f"{API}/tasks").json()
        t = [x for x in tl if x["id"] == tid][0]
        assert t["done"] is True

    def test_update_404(self):
        r = requests.put(f"{API}/tasks/nope", json={"title": "x"})
        assert r.status_code == 404


# ---------- Linking / cascade unlink ----------
class TestUnlinking:
    def test_delete_project_unlinks_tasks(self, created_ids):
        pid = created_ids["projects"][0]
        tid = created_ids["tasks"][0]
        r = requests.delete(f"{API}/projects/{pid}")
        assert r.status_code == 200
        created_ids["projects"].remove(pid)

        tl = requests.get(f"{API}/tasks").json()
        t = [x for x in tl if x["id"] == tid][0]
        assert t["project_id"] is None
        assert t["project_name"] is None
        assert t["client_name"] is None

    def test_delete_client_unlinks_projects(self, created_ids):
        cid = created_ids["clients"][0]
        # create another project linked to client
        r = requests.post(f"{API}/projects", json={"name": "TEST_P2", "client_id": cid, "status": "In Progress", "progress": 0, "due": "", "members": 1})
        assert r.status_code == 200
        pid2 = r.json()["id"]
        created_ids["projects"].append(pid2)

        # delete client
        rd = requests.delete(f"{API}/clients/{cid}")
        assert rd.status_code == 200
        created_ids["clients"].remove(cid)

        # project should be unlinked
        pl = requests.get(f"{API}/projects").json()
        p2 = [p for p in pl if p["id"] == pid2][0]
        assert p2["client_id"] is None
        assert p2["client_name"] is None
