"""Settings sprint backend tests - covers all /api/settings* endpoints and related auth."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password, "remember": False})
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


def _register():
    email = f"set{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "firstName": "Set", "lastName": "Test", "email": email,
        "password": "TestPass123!", "company": f"SetOrg-{uuid.uuid4().hex[:6]}"
    })
    assert r.status_code in (200, 201), r.text
    return email, r.json()["accessToken"]


@pytest.fixture(scope="module")
def demo_token():
    return _login(DEMO_EMAIL, DEMO_PASSWORD)


@pytest.fixture(scope="module")
def demo_h(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}


# ---- Auth guards ----
def test_settings_requires_auth():
    for ep in ["/api/settings", "/api/settings/billing", "/api/settings/recent-logins", "/api/settings/api-keys"]:
        r = requests.get(f"{BASE_URL}{ep}")
        assert r.status_code == 401, f"{ep} expected 401 got {r.status_code}"


def test_patch_settings_requires_auth():
    r = requests.patch(f"{BASE_URL}/api/settings/organization", json={"name": "x"})
    assert r.status_code == 401


# ---- GET /api/settings shape ----
def test_get_settings_shape(demo_h):
    r = requests.get(f"{BASE_URL}/api/settings", headers=demo_h)
    assert r.status_code == 200
    data = r.json()
    for key in ("organization", "branding", "ai", "documents", "notifications"):
        assert key in data, f"missing section {key}"
    assert "name" in data["organization"]
    assert "primaryColor" in data["branding"]
    assert "provider" in data["ai"]
    assert "invoicePrefix" in data["documents"]
    assert "emailNotifications" in data["notifications"]


# ---- PATCH organization ----
def test_patch_organization_persists(demo_h):
    payload = {"website": "https://assistify.io", "vatNumber": "NL123", "defaultCurrency": "EUR",
               "defaultVat": 21, "phone": "+31 20 0000000", "kvkNumber": "KVK9999",
               "address": "TEST ADDRESS", "businessEmail": "biz@assistify.io"}
    r = requests.patch(f"{BASE_URL}/api/settings/organization", headers=demo_h, json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["website"] == "https://assistify.io"
    assert body["defaultCurrency"] == "EUR"
    # Verify persistence
    r2 = requests.get(f"{BASE_URL}/api/settings", headers=demo_h)
    assert r2.json()["organization"]["vatNumber"] == "NL123"
    assert r2.json()["organization"]["defaultVat"] == 21


# ---- PATCH branding ----
def test_patch_branding_persists(demo_h):
    payload = {"values": {"primaryColor": "#ff0000", "secondaryColor": "#00ff00",
                          "proposalFooter": "TEST PROP FOOTER", "contractFooter": "TEST CTR FOOTER",
                          "invoiceFooter": "TEST INV FOOTER"}}
    r = requests.patch(f"{BASE_URL}/api/settings/branding", headers=demo_h, json=payload)
    assert r.status_code == 200
    assert r.json()["primaryColor"] == "#ff0000"
    r2 = requests.get(f"{BASE_URL}/api/settings", headers=demo_h)
    assert r2.json()["branding"]["proposalFooter"] == "TEST PROP FOOTER"


# ---- PATCH ai ----
def test_patch_ai_persists(demo_h):
    payload = {"values": {"provider": "openai", "proposalTone": "Casual", "contractTone": "Formal",
                          "temperature": 0.5, "invoiceNotes": "TEST AI NOTES"}}
    r = requests.patch(f"{BASE_URL}/api/settings/ai", headers=demo_h, json=payload)
    assert r.status_code == 200
    assert r.json()["proposalTone"] == "Casual"
    r2 = requests.get(f"{BASE_URL}/api/settings", headers=demo_h)
    assert r2.json()["ai"]["temperature"] == 0.5


# ---- PATCH documents ----
def test_patch_documents_persists(demo_h):
    payload = {"values": {"proposalPrefix": "PROP", "contractPrefix": "CTR", "invoicePrefix": "TSTINV",
                          "numberingStart": 100, "pdfPageSize": "A4", "pdfAccentColor": "#123456"}}
    r = requests.patch(f"{BASE_URL}/api/settings/documents", headers=demo_h, json=payload)
    assert r.status_code == 200
    assert r.json()["invoicePrefix"] == "TSTINV"
    r2 = requests.get(f"{BASE_URL}/api/settings", headers=demo_h)
    assert r2.json()["documents"]["pdfAccentColor"] == "#123456"


# ---- PATCH notifications ----
def test_patch_notifications_persists(demo_h):
    payload = {"values": {"weeklyDigest": True, "aiAlerts": True, "emailNotifications": False}}
    r = requests.patch(f"{BASE_URL}/api/settings/notifications", headers=demo_h, json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["weeklyDigest"] is True
    assert body["aiAlerts"] is True
    assert body["emailNotifications"] is False
    # Restore
    requests.patch(f"{BASE_URL}/api/settings/notifications", headers=demo_h,
                   json={"values": {"emailNotifications": True, "weeklyDigest": False, "aiAlerts": False}})


# ---- Auth profile update ----
def test_patch_auth_profile(demo_h):
    r = requests.patch(f"{BASE_URL}/api/auth/profile", headers=demo_h,
                       json={"firstName": "Jordan", "lastName": "Demo", "timezone": "Europe/Amsterdam", "language": "en"})
    assert r.status_code == 200, r.text
    me = requests.get(f"{BASE_URL}/api/auth/me", headers=demo_h).json()
    assert me["firstName"] == "Jordan"
    assert me["timezone"] == "Europe/Amsterdam"


# ---- Billing ----
def test_billing_endpoint(demo_h):
    r = requests.get(f"{BASE_URL}/api/settings/billing", headers=demo_h)
    assert r.status_code == 200
    data = r.json()
    assert data["plan"] == "Pro"
    assert "seats" in data and "used" in data["seats"] and "included" in data["seats"]
    assert "usage" in data
    for k in ("clients", "projects", "documents", "proposals", "contracts", "invoices"):
        assert k in data["usage"]
    assert data["usage"]["clients"] >= 0


# ---- API keys placeholder ----
def test_api_keys_placeholder(demo_h):
    r = requests.get(f"{BASE_URL}/api/settings/api-keys", headers=demo_h)
    assert r.status_code == 200
    data = r.json()
    assert data["keys"] == []


# ---- Recent logins ----
def test_recent_logins(demo_h):
    r = requests.get(f"{BASE_URL}/api/settings/recent-logins", headers=demo_h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Sessions list ----
def test_sessions_list(demo_h):
    r = requests.get(f"{BASE_URL}/api/auth/sessions", headers=demo_h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Organization isolation for fresh user ----
def test_fresh_user_isolation():
    email, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/settings", headers=h)
    assert r.status_code == 200
    s = r.json()
    # Fresh org: independent defaults
    assert s["organization"]["defaultCurrency"] == "USD"
    assert s["organization"]["vatNumber"] == ""
    assert s["branding"]["proposalFooter"] == ""
    assert s["organization"]["name"] != "Assistify Inc."
    # Notifications defaults
    assert s["notifications"]["emailNotifications"] is True
    assert s["notifications"]["weeklyDigest"] is False


# ---- Invoice prefix applied to new invoice numbering ----
def test_invoice_prefix_affects_numbering():
    # Fresh user to avoid disturbing demo counters
    email, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    # Set custom prefix
    r = requests.patch(f"{BASE_URL}/api/settings/documents", headers=h,
                       json={"values": {"invoicePrefix": "ZZZ"}})
    assert r.status_code == 200
    # Create a client + project + invoice
    c = requests.post(f"{BASE_URL}/api/clients", headers=h, json={"name": "TEST_C", "email": "c@c.com"})
    assert c.status_code in (200, 201), c.text
    client_id = c.json()["id"]
    p = requests.post(f"{BASE_URL}/api/projects", headers=h, json={"name": "TEST_P", "clientId": client_id})
    assert p.status_code in (200, 201), p.text
    project_id = p.json()["id"]
    inv = requests.post(f"{BASE_URL}/api/ai/generate-invoice", headers=h,
                        json={"projectId": project_id, "clientId": client_id,
                              "lineItems": [{"description": "x", "qty": 1, "unitPrice": 100}]})
    if inv.status_code in (200, 201):
        num = inv.json().get("invoiceNumber") or inv.json().get("number") or ""
        assert "ZZZ" in num, f"expected ZZZ prefix in invoice number, got {num}"
    else:
        pytest.skip(f"invoice generation not available: {inv.status_code}")


# ---- Change password ----
def test_change_password_flow():
    email, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/api/auth/change-password", headers=h,
                      json={"currentPassword": "TestPass123!", "newPassword": "NewPass456!"})
    assert r.status_code == 200, r.text
    # Old password fails
    r2 = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "TestPass123!"})
    assert r2.status_code == 401
    # New password works
    r3 = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "NewPass456!"})
    assert r3.status_code == 200


# ---- Logout all ----
def test_logout_all():
    email, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/api/auth/logout-all", headers=h)
    assert r.status_code == 200
    assert r.json().get("ok") is True


# ---- Upload image ----
def test_upload_branding_image(demo_h):
    files = {"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")}
    r = requests.post(f"{BASE_URL}/api/settings/upload-image", headers=demo_h, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body and "url" in body
    assert body["url"].startswith("/api/settings/image/")


# ---- Regression smoke ----
def test_regression_endpoints(demo_h):
    for ep in ["/api/dashboard/summary", "/api/clients", "/api/projects", "/api/tasks",
               "/api/notifications", "/api/analytics", "/api/library/invoices"]:
        r = requests.get(f"{BASE_URL}{ep}", headers=demo_h)
        assert r.status_code == 200, f"{ep} failed {r.status_code}"
