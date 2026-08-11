"""Backend tests for legacy onboarding checklist — TestClient."""

from __future__ import annotations

import sys
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


# ---------- new user onboarding ----------

def test_new_user_onboarding_completed_false_and_zero_percent(client):
    a = register_user(client, company="OnbCo")
    assert a["user"].get("onboardingCompleted") is False
    r = client.get("/api/onboarding", headers=a["headers"])
    assert r.status_code == 200
    j = r.json()
    assert j["completed"] is False
    assert j["percent"] == 0
    assert j["done"] == 0
    assert j["total"] == 6
    for key in ["client", "project", "plan", "proposal", "contract", "invoice"]:
        assert j["checklist"][key] is False


def test_onboarding_checklist_updates_after_client_created(client):
    a = register_user(client, company="OnbClient")
    payload = {"name": "TEST_Acme Co", "contact": "TEST User", "email": "t@t.com", "phone": "+1-555-1111"}
    r = client.post("/api/clients", json=payload, headers=a["headers"])
    assert r.status_code == 200, r.text
    c = r.json()
    assert c.get("phone") == "+1-555-1111"

    r = client.get("/api/onboarding", headers=a["headers"])
    j = r.json()
    assert j["checklist"]["client"] is True
    assert j["percent"] >= 16


def test_onboarding_complete_persists_across_relogin(client):
    a = register_user(client, company="OnbComplete", password="NewPass123!")
    r = client.post("/api/onboarding/complete", headers=a["headers"])
    assert r.status_code == 200
    r = client.get("/api/onboarding", headers=a["headers"])
    assert r.json()["completed"] is True
    client.post("/api/auth/logout", headers=a["headers"])
    client.cookies.clear()
    clear_rate_limits()
    login = client.post("/api/auth/login", json={
        "email": a["email"], "password": "NewPass123!", "remember": True,
    })
    assert login.status_code == 200
    data = auth_json(client, login)
    assert data["user"].get("onboardingCompleted") is True


def test_onboarding_requires_auth(client):
    client.cookies.clear()
    r = client.get("/api/onboarding")
    assert r.status_code == 401
    r = client.post("/api/onboarding/complete")
    assert r.status_code == 401


# ---------- completed user with real data (replaces demo login) ----------

def test_completed_user_partial_checklist(client):
    a = register_user(client, company="OnbDone")
    client.post("/api/onboarding/complete", headers=a["headers"])
    client.post("/api/clients", headers=a["headers"], json={
        "name": "Done Client", "contact": "N", "email": "n@n.com",
    })
    client.post("/api/projects", headers=a["headers"], json={
        "name": "Done Project", "status": "In Progress",
    })
    r = client.get("/api/onboarding", headers=a["headers"])
    j = r.json()
    assert j["completed"] is True
    assert j["checklist"]["client"] is True
    assert j["checklist"]["project"] is True
    assert 30 <= j["percent"] <= 100


# ---------- regression ----------

def test_new_user_can_create_client_and_project_scoped(client):
    a = register_user(client, company="OnbScope")
    rc = client.post("/api/clients", json={
        "name": "TEST_Onb Client", "contact": "N", "email": "n@n.com", "phone": "555",
    }, headers=a["headers"])
    assert rc.status_code == 200
    client_id = rc.json()["id"]
    rp = client.post("/api/projects", json={
        "client_id": client_id, "name": "TEST_Onb Project", "status": "In Progress",
    }, headers=a["headers"])
    assert rp.status_code == 200, rp.text
    proj = rp.json()
    assert proj["client_id"] == client_id
    j = client.get("/api/onboarding", headers=a["headers"]).json()
    assert j["checklist"]["client"] is True
    assert j["checklist"]["project"] is True
    assert j["percent"] >= 33
