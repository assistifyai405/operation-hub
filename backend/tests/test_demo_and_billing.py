"""Tests for POST /api/auth/demo endpoint, tenant isolation, seeded data, and regression on normal auth."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def demo1():
    r = requests.post(f"{API}/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip("Rate limited — expected in-memory 10/hr limit")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def demo2():
    r = requests.post(f"{API}/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip("Rate limited")
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Demo endpoint shape ----------
class TestDemoEndpoint:
    def test_demo_returns_user_and_token(self, demo1):
        assert "accessToken" in demo1 and isinstance(demo1["accessToken"], str) and len(demo1["accessToken"]) > 10
        assert demo1.get("isDemo") is True
        user = demo1["user"]
        assert user["role"] == "owner"
        assert user.get("emailVerified") is True
        assert user.get("onboardingCompleted") is True
        assert re.match(r"^demo\+.+@assistify\.demo$", user["email"]), f"unexpected email {user['email']}"

    def test_demo_sets_cookies(self):
        r = requests.post(f"{API}/auth/demo", timeout=30)
        if r.status_code == 429:
            pytest.skip("rate limited")
        assert r.status_code == 200
        cookies = r.cookies.get_dict()
        # Expect at least access_token cookie
        assert any(k in cookies for k in ("access_token", "refresh_token")), f"cookies={cookies}"


# ---------- Tenant isolation ----------
class TestDemoIsolation:
    def test_two_demos_have_different_orgs(self, demo1, demo2):
        org1 = demo1["user"].get("organizationId")
        org2 = demo2["user"].get("organizationId")
        assert org1 and org2 and org1 != org2

    def test_demo1_sees_only_own_seeded_clients(self, demo1):
        r = requests.get(f"{API}/clients", headers=_auth(demo1["accessToken"]), timeout=30)
        assert r.status_code == 200
        clients = r.json()
        # response may be list or wrapped
        if isinstance(clients, dict) and "clients" in clients:
            clients = clients["clients"]
        assert isinstance(clients, list)
        assert len(clients) == 3, f"expected 3 seeded clients, got {len(clients)}: {[c.get('name') for c in clients]}"
        names = {c.get("name") for c in clients}
        assert {"Halcyon Group", "Vertex Studio", "Northwind Labs"}.issubset(names), names

    def test_demo2_cannot_see_demo1_created_client(self, demo1, demo2):
        # demo1 creates a new client
        payload = {"name": "TEST_Isolation_Client", "email": "iso@test.com"}
        c = requests.post(f"{API}/clients", json=payload, headers=_auth(demo1["accessToken"]), timeout=30)
        assert c.status_code in (200, 201), c.text
        # demo2 lists clients — must not include TEST_Isolation_Client and count must remain 3
        r = requests.get(f"{API}/clients", headers=_auth(demo2["accessToken"]), timeout=30)
        assert r.status_code == 200
        clients = r.json()
        if isinstance(clients, dict) and "clients" in clients:
            clients = clients["clients"]
        names = [c.get("name") for c in clients]
        assert "TEST_Isolation_Client" not in names
        assert len(clients) == 3, f"demo2 org contaminated: {names}"


# ---------- Seeded workspace ----------
class TestDemoSeededWorkspace:
    def test_projects_seeded(self, demo1):
        r = requests.get(f"{API}/projects", headers=_auth(demo1["accessToken"]), timeout=30)
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, dict) and "projects" in data:
            data = data["projects"]
        assert len(data) == 2, f"expected 2 projects got {len(data)}"
        names = {p.get("name") for p in data}
        assert "Brand Redesign" in names and "Q3 Marketing Site" in names, names

    def test_tasks_seeded(self, demo1):
        r = requests.get(f"{API}/tasks", headers=_auth(demo1["accessToken"]), timeout=30)
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, dict) and "tasks" in data:
            data = data["tasks"]
        assert len(data) == 3, f"expected 3 tasks got {len(data)}"

    def test_dashboard_summary(self, demo1):
        r = requests.get(f"{API}/dashboard/summary", headers=_auth(demo1["accessToken"]), timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "kpis" in body
        assert body["kpis"], "kpis empty"


# ---------- Regression: normal auth still works ----------
class TestAuthRegression:
    def test_login_seed_account(self):
        r = requests.post(f"{API}/auth/login", json={
            "email": os.environ.get("DEMO_EMAIL", "jordan@assistify.io"),
            "password": os.environ.get("DEMO_PASSWORD", "Assistify2026!"),
            "remember": True,
        }, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "accessToken" in data
        token = data["accessToken"]

        me = requests.get(f"{API}/auth/me", headers=_auth(token), timeout=30)
        assert me.status_code == 200
        assert me.json().get("email") == "jordan@assistify.io"

    def test_register_fresh(self):
        import uuid
        email = f"TEST_{uuid.uuid4().hex[:10]}@assistify.test"
        r = requests.post(f"{API}/auth/register", json={
            "firstName": "Test", "lastName": "User",
            "email": email, "password": "TestPassword123!",
        }, timeout=30)
        if r.status_code == 429:
            pytest.skip("rate limited")
        assert r.status_code == 200, r.text
        assert "accessToken" in r.json()
