"""Backend tests for onboarding sprint (GET/POST /api/onboarding, checklist auto-derivation, phone on client, non-regression)."""
import os
import uuid
import requests
import pytest
from conftest import auth_json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"


def _register_new():
    email = f"onb+{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "firstName": "Onb", "lastName": "Tester",
        "email": email, "password": "NewPass123!", "company": "OnbCo"
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = auth_json(None, r)
    return email, data["accessToken"], data.get("user", {})


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email, "password": password, "remember": True
    }, timeout=30)
    assert r.status_code == 200, r.text
    return auth_json(None, r).get("accessToken"), r.json().get("user", {})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- new user onboarding ----------

def test_new_user_onboarding_completed_false_and_zero_percent():
    email, token, user = _register_new()
    assert user.get("onboardingCompleted") is False
    r = requests.get(f"{BASE_URL}/api/onboarding", headers=_auth(token))
    assert r.status_code == 200
    j = r.json()
    assert j["completed"] is False
    assert j["percent"] == 0
    assert j["done"] == 0
    assert j["total"] == 6
    for key in ["client", "project", "plan", "proposal", "contract", "invoice"]:
        assert j["checklist"][key] is False


def test_onboarding_checklist_updates_after_client_created():
    email, token, _ = _register_new()
    # Create a client with phone (new field)
    payload = {"name": "TEST_Acme Co", "contact": "TEST User",
               "email": "t@t.com", "phone": "+1-555-1111"}
    r = requests.post(f"{BASE_URL}/api/clients", json=payload, headers=_auth(token))
    assert r.status_code == 200, r.text
    c = r.json()
    assert c.get("phone") == "+1-555-1111"

    r = requests.get(f"{BASE_URL}/api/onboarding", headers=_auth(token))
    j = r.json()
    assert j["checklist"]["client"] is True
    assert j["percent"] >= 16  # 1/6 ~ 17


def test_onboarding_complete_persists_across_relogin():
    email, token, _ = _register_new()
    r = requests.post(f"{BASE_URL}/api/onboarding/complete", headers=_auth(token))
    assert r.status_code == 200
    # GET onboarding shows completed=true
    r = requests.get(f"{BASE_URL}/api/onboarding", headers=_auth(token))
    assert r.json()["completed"] is True
    # Re-login and confirm user.onboardingCompleted persists
    token2, user2 = _login(email, "NewPass123!")
    assert user2.get("onboardingCompleted") is True


def test_onboarding_requires_auth():
    r = requests.get(f"{BASE_URL}/api/onboarding")
    assert r.status_code == 401
    r = requests.post(f"{BASE_URL}/api/onboarding/complete")
    assert r.status_code == 401


# ---------- demo (existing) user unaffected ----------

def test_demo_user_onboarding_completed_true_and_partial_checklist():
    token, user = _login(DEMO_EMAIL, DEMO_PASSWORD)
    assert user.get("onboardingCompleted") is True
    r = requests.get(f"{BASE_URL}/api/onboarding", headers=_auth(token))
    j = r.json()
    assert j["completed"] is True
    # demo has clients + projects at minimum (~50-67%)
    assert j["checklist"]["client"] is True
    assert j["checklist"]["project"] is True
    assert 30 <= j["percent"] <= 100


# ---------- regression: create project links to client for new user ----------

def test_new_user_can_create_client_and_project_scoped():
    email, token, _ = _register_new()
    # Create client
    rc = requests.post(f"{BASE_URL}/api/clients", json={
        "name": "TEST_Onb Client", "contact": "N",
        "email": "n@n.com", "phone": "555"
    }, headers=_auth(token))
    assert rc.status_code == 200
    client_id = rc.json()["id"]
    # Create project
    rp = requests.post(f"{BASE_URL}/api/projects", json={
        "client_id": client_id, "name": "TEST_Onb Project",
        "status": "In Progress"
    }, headers=_auth(token))
    assert rp.status_code == 200, rp.text
    proj = rp.json()
    assert proj["client_id"] == client_id
    # Onboarding should now show client + project true
    j = requests.get(f"{BASE_URL}/api/onboarding", headers=_auth(token)).json()
    assert j["checklist"]["client"] is True
    assert j["checklist"]["project"] is True
    assert j["percent"] >= 33
