"""Demo login disabled + billing pending + auth regression (TestClient).

ENABLE_DEMO_LOGIN=false intentionally — demo endpoint must reject.
Isolation/billing covered via real registered users (no demo seed).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json, clear_rate_limits, register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Demo endpoint intentionally disabled ----------
class TestDemoEndpoint:
    def test_demo_returns_disabled(self, client):
        clear_rate_limits()
        r = client.post("/api/auth/demo")
        assert r.status_code in (401, 403, 404), r.text
        assert "sk-" not in r.text.lower()

    def test_demo_does_not_set_session_cookies(self, client):
        clear_rate_limits()
        client.cookies.clear()
        r = client.post("/api/auth/demo")
        assert r.status_code in (401, 403, 404)
        # Must not mint a usable session when demo is disabled
        assert not client.cookies.get("access_token")


# ---------- Tenant isolation via real users ----------
class TestDemoIsolation:
    def test_two_users_have_different_orgs(self, client):
        a = register_user(client, company="IsoA")
        b = register_user(client, company="IsoB")
        org1 = a["user"].get("organizationId")
        org2 = b["user"].get("organizationId")
        assert org1 and org2 and org1 != org2

    def test_user_sees_own_clients(self, client):
        a = register_user(client, company="ClientsA")
        for name in ("Halcyon Group", "Vertex Studio", "Northwind Labs"):
            r = client.post(
                "/api/clients",
                headers=a["headers"],
                json={"name": name, "email": f"{name.split()[0].lower()}@test.com"},
            )
            assert r.status_code in (200, 201), r.text
        r = client.get("/api/clients", headers=a["headers"])
        assert r.status_code == 200
        clients = r.json()
        if isinstance(clients, dict) and "clients" in clients:
            clients = clients["clients"]
        assert len(clients) == 3
        names = {c.get("name") for c in clients}
        assert {"Halcyon Group", "Vertex Studio", "Northwind Labs"}.issubset(names)

    def test_user_b_cannot_see_user_a_client(self, client):
        a = register_user(client, company="IsoCreateA")
        b = register_user(client, company="IsoCreateB")
        # Seed B with 3 clients so count stays stable
        for i in range(3):
            client.post(
                "/api/clients",
                headers=b["headers"],
                json={"name": f"B Client {i}", "email": f"b{i}@test.com"},
            )
        payload = {"name": "TEST_Isolation_Client", "email": "iso@test.com"}
        c = client.post("/api/clients", json=payload, headers=a["headers"])
        assert c.status_code in (200, 201), c.text
        r = client.get("/api/clients", headers=b["headers"])
        assert r.status_code == 200
        clients = r.json()
        if isinstance(clients, dict) and "clients" in clients:
            clients = clients["clients"]
        names = [c.get("name") for c in clients]
        assert "TEST_Isolation_Client" not in names
        assert len(clients) == 3, f"org B contaminated: {names}"


# ---------- Seeded workspace via real CRUD ----------
class TestDemoSeededWorkspace:
    def test_projects_created(self, client):
        a = register_user(client, company="ProjSeed")
        cr = client.post("/api/clients", headers=a["headers"], json={"name": "Seed Co", "email": "s@s.com"})
        assert cr.status_code == 200
        cid = cr.json()["id"]
        for name in ("Brand Redesign", "Q3 Marketing Site"):
            r = client.post(
                "/api/projects",
                headers=a["headers"],
                json={"name": name, "client_id": cid, "status": "In Progress"},
            )
            assert r.status_code == 200, r.text
        r = client.get("/api/projects", headers=a["headers"])
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, dict) and "projects" in data:
            data = data["projects"]
        assert len(data) == 2
        names = {p.get("name") for p in data}
        assert "Brand Redesign" in names and "Q3 Marketing Site" in names

    def test_tasks_created(self, client):
        a = register_user(client, company="TaskSeed")
        pr = client.post("/api/projects", headers=a["headers"], json={"name": "T Proj", "status": "Active"})
        assert pr.status_code == 200
        pid = pr.json()["id"]
        for i in range(3):
            r = client.post(
                "/api/tasks",
                headers=a["headers"],
                json={"title": f"Task {i}", "project_id": pid, "priority": "Medium"},
            )
            assert r.status_code == 200, r.text
        r = client.get("/api/tasks", headers=a["headers"])
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, dict) and "tasks" in data:
            data = data["tasks"]
        assert len(data) == 3

    def test_dashboard_summary(self, client):
        a = register_user(client, company="DashSeed")
        client.post("/api/clients", headers=a["headers"], json={"name": "D Client", "email": "d@d.com"})
        r = client.get("/api/dashboard/summary", headers=a["headers"])
        assert r.status_code == 200
        body = r.json()
        assert "kpis" in body
        assert body["kpis"], "kpis empty"


# ---------- Billing pending ----------
class TestBillingPending:
    def test_billing_not_fake_pro(self, client):
        a = register_user(client, company="BillCo")
        r = client.get("/api/settings/billing", headers=a["headers"])
        assert r.status_code == 200
        b = r.json()
        assert b.get("plan") is None or b.get("status") == "pending" or b.get("billingConfigured") is False
        assert b.get("plan") != "Pro"


# ---------- Regression: normal auth still works ----------
class TestAuthRegression:
    def test_login_after_register(self, client):
        clear_rate_limits()
        email = f"login_{uuid.uuid4().hex[:10]}@example.com"
        pw = "Assistify2026!"
        r = client.post(
            "/api/auth/register",
            json={
                "firstName": "Jordan", "lastName": "User",
                "email": email, "password": pw, "company": "LoginCo",
            },
        )
        assert r.status_code == 200, r.text
        client.post("/api/auth/logout", headers=_auth(auth_json(client, r)["accessToken"]))
        client.cookies.clear()
        clear_rate_limits()
        r = client.post("/api/auth/login", json={"email": email, "password": pw, "remember": True})
        assert r.status_code == 200, r.text
        data = auth_json(client, r)
        assert "accessToken" in data
        me = client.get("/api/auth/me", headers=_auth(data["accessToken"]))
        assert me.status_code == 200
        assert me.json().get("email") == email

    def test_register_fresh(self, client):
        clear_rate_limits()
        email = f"TEST_{uuid.uuid4().hex[:10]}@assistify.test"
        r = client.post(
            "/api/auth/register",
            json={
                "firstName": "Test", "lastName": "User",
                "email": email, "password": "TestPassword123!",
            },
        )
        assert r.status_code == 200, r.text
        data = auth_json(client, r)
        assert "accessToken" in data
