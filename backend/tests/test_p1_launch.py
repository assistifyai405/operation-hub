"""
P1 Launch-Readiness Tests
Covers:
- Security: image/document endpoints ignore ?auth query param
- Email verification send-guard on proposal/contract/invoice
- Verified users can still Send
- Copilot after snapshot optimization
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "jordan@assistify.io"
SEED_PASSWORD = "Assistify2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def seed_token():
    r = requests.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD, "remember": True})
    assert r.status_code == 200, f"seed login failed: {r.status_code} {r.text}"
    return r.json()["accessToken"]


@pytest.fixture(scope="module")
def seed_headers(seed_token):
    return {"Authorization": f"Bearer {seed_token}"}


@pytest.fixture(scope="module")
def unverified_user():
    email = f"TEST_p1_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"firstName": "P1", "lastName": "Tester", "email": email, "password": "TestPass123!", "company": "TestCo"}
    r = requests.post(f"{API}/auth/register", json=payload)
    if r.status_code == 429:
        pytest.skip("Register rate-limited (10/hr/IP)")
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("accessToken")
    assert token
    user = data.get("user", {})
    # confirm unverified
    assert user.get("emailVerified") in (False, None), f"expected unverified user got {user}"
    return {"token": token, "email": email, "user": user}


@pytest.fixture(scope="module")
def unverified_headers(unverified_user):
    return {"Authorization": f"Bearer {unverified_user['token']}"}


@pytest.fixture(scope="module")
def unverified_project(unverified_headers):
    # need a client first
    c = requests.post(f"{API}/clients", json={"name": "TEST_P1_Client", "email": "client@test.com"}, headers=unverified_headers)
    assert c.status_code in (200, 201), f"client create failed: {c.status_code} {c.text}"
    client_id = c.json().get("id") or c.json().get("_id")
    p = requests.post(f"{API}/projects", json={"name": "TEST_P1_Project", "clientId": client_id, "status": "Active"}, headers=unverified_headers)
    assert p.status_code in (200, 201), f"project create failed: {p.status_code} {p.text}"
    return p.json().get("id") or p.json().get("_id")


@pytest.fixture(scope="module")
def seed_project(seed_headers):
    r = requests.get(f"{API}/projects", headers=seed_headers)
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) > 0
    return projects[0].get("id") or projects[0].get("_id")


# ---------- SECURITY: no auth via ?auth= query param ----------
class TestImageDocumentSecurity:
    def test_image_no_auth_query_ignored(self):
        r = requests.get(f"{API}/settings/image/anyid?auth=fake")
        assert r.status_code == 401
        assert "fake" not in r.text  # no token leaked

    def test_document_no_auth_query_ignored(self):
        r = requests.get(f"{API}/documents/anyid/file?auth=fake")
        assert r.status_code == 401
        assert "fake" not in r.text

    def test_image_bearer_returns_404_for_unknown(self, seed_headers):
        r = requests.get(f"{API}/settings/image/nonexistent_asset_xyz", headers=seed_headers)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_document_bearer_returns_404_for_unknown(self, seed_headers):
        r = requests.get(f"{API}/documents/nonexistent_doc_xyz/file", headers=seed_headers)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_image_missing_auth_401(self):
        r = requests.get(f"{API}/settings/image/anything")
        assert r.status_code == 401


# ---------- SEND GUARD for unverified users ----------
class TestSendGuardUnverified:
    def test_proposal_draft_ok(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/proposal",
                          json={"status": "Draft", "content": {"body": "test"}}, headers=unverified_headers)
        assert r.status_code in (200, 201), f"draft should save: {r.status_code} {r.text}"

    def test_proposal_sent_blocked(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/proposal",
                          json={"status": "Sent", "content": {"body": "test"}}, headers=unverified_headers)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"
        assert "verify your email" in r.text.lower()

    def test_contract_draft_ok(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/contract",
                          json={"status": "Draft", "content": {"body": "c"}}, headers=unverified_headers)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_contract_sent_blocked(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/contract",
                          json={"status": "Sent", "content": {"body": "c"}}, headers=unverified_headers)
        assert r.status_code == 403
        assert "verify your email" in r.text.lower()

    def test_invoice_draft_ok(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/invoice",
                          json={"status": "Draft", "content": {"items": []}}, headers=unverified_headers)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_invoice_sent_blocked(self, unverified_headers, unverified_project):
        r = requests.post(f"{API}/projects/{unverified_project}/invoice",
                          json={"status": "Sent", "content": {"items": []}}, headers=unverified_headers)
        assert r.status_code == 403
        assert "verify your email" in r.text.lower()


# ---------- SEND GUARD does NOT block verified users ----------
class TestSendGuardVerified:
    def test_proposal_sent_ok_verified(self, seed_headers, seed_project):
        r = requests.post(f"{API}/projects/{seed_project}/proposal",
                          json={"status": "Sent", "content": {"body": "t"}}, headers=seed_headers)
        assert r.status_code in (200, 201), f"verified user should send: {r.status_code} {r.text}"

    def test_contract_sent_ok_verified(self, seed_headers, seed_project):
        r = requests.post(f"{API}/projects/{seed_project}/contract",
                          json={"status": "Sent", "content": {"body": "t"}}, headers=seed_headers)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_invoice_sent_ok_verified(self, seed_headers, seed_project):
        r = requests.post(f"{API}/projects/{seed_project}/invoice",
                          json={"status": "Sent", "content": {"items": []}}, headers=seed_headers)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"


# ---------- COPILOT still works ----------
class TestCopilot:
    def test_suggestions(self, seed_headers):
        r = requests.get(f"{API}/copilot/suggestions", headers=seed_headers)
        assert r.status_code == 200
        data = r.json()
        # accept list or {suggestions:[]}
        items = data if isinstance(data, list) else data.get("suggestions", [])
        assert isinstance(items, list)
        assert len(items) > 0

    def test_message_read_query(self, seed_headers):
        r = requests.post(f"{API}/copilot/message",
                          json={"message": "How many clients do I have?"}, headers=seed_headers, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert "reply" in data or "message" in data or "response" in data or "content" in data

    def test_message_action_card(self, seed_headers):
        # Ask copilot to create something to trigger action card
        r = requests.post(f"{API}/copilot/message",
                          json={"message": "Create a new task called TEST_P1_CopilotTask due next Friday"},
                          headers=seed_headers, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        # Just verify shape; don't require action_card specifically since LLM may vary
        assert r.json() is not None
