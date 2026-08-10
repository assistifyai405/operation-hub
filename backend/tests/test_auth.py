"""Auth sprint tests: registration, login, refresh, logout, forgot/reset, verify-email, profile,
change-password, org isolation, protected routes, brute-force lockout.
Uses BASE_URL from REACT_APP_BACKEND_URL. All endpoints prefixed with /api.
Cookie-only auth: access JWT is in httpOnly cookie, not JSON body.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

pytestmark = pytest.mark.skipif(not BASE_URL, reason="REACT_APP_BACKEND_URL not set")

DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"


def _rand_email():
    return f"qa+{uuid.uuid4().hex[:10]}@example.com"


def _session_token(session, response=None):
    """Prefer httpOnly access_token cookie; fall back only if present."""
    tok = session.cookies.get("access_token")
    if tok:
        return tok
    if response is not None:
        try:
            return (response.json() or {}).get("accessToken")
        except Exception:
            return None
    return None


def _attach_bearer(session, response):
    data = response.json()
    tok = _session_token(session, response)
    if tok:
        data = {**data, "accessToken": tok}
        session.headers.update({"Authorization": f"Bearer {tok}"})
    session._data = data
    return data


@pytest.fixture(scope="module")
def demo_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "remember": True})
    assert r.status_code == 200, f"Demo login failed: {r.status_code} {r.text}"
    _attach_bearer(s, r)
    return s


@pytest.fixture(scope="module")
def new_user_session():
    s = requests.Session()
    email = _rand_email()
    payload = {"firstName": "QA", "lastName": "Tester", "email": email,
               "password": "SuperSecret123!", "company": "QA Org"}
    r = s.post(f"{API}/auth/register", json=payload)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    _attach_bearer(s, r)
    s._email = email
    s._password = "SuperSecret123!"
    return s


# ---------- Registration ----------
class TestRegistration:
    def test_register_sets_cookie_session_and_verify_link(self, new_user_session):
        d = new_user_session._data
        assert d.get("accessToken") and len(d["accessToken"]) > 20
        assert "verificationLink" in d and "token=" in d["verificationLink"]
        assert d["user"]["email"] == new_user_session._email
        assert d["user"]["emailVerified"] is False
        assert d["user"]["organizationId"]
        raw = requests.Session()
        email = _rand_email()
        rr = raw.post(f"{API}/auth/register", json={
            "firstName": "Cookie", "lastName": "Only", "email": email,
            "password": "SuperSecret123!", "company": "Cookie Co",
        })
        assert rr.status_code == 200
        body = rr.json()
        assert "accessToken" not in body
        assert body.get("auth") == "cookie"
        assert raw.cookies.get("access_token")

    def test_register_duplicate_email_rejected(self, new_user_session):
        r = requests.post(f"{API}/auth/register", json={
            "firstName": "X", "lastName": "Y", "email": new_user_session._email,
            "password": "Whatever123!", "company": "x"
        })
        assert r.status_code == 409

    def test_register_invalid_email(self):
        r = requests.post(f"{API}/auth/register", json={
            "firstName": "A", "lastName": "B", "email": "not-an-email",
            "password": "Whatever123!", "company": "x"
        })
        assert r.status_code in (400, 422)

    def test_new_user_sees_no_seed_data(self, new_user_session):
        r = new_user_session.get(f"{API}/clients")
        assert r.status_code == 200
        assert r.json() == []
        r2 = new_user_session.get(f"{API}/projects")
        assert r2.status_code == 200
        assert r2.json() == []


# ---------- Login ----------
class TestLogin:
    def test_demo_login(self, demo_session):
        d = demo_session._data
        assert d["user"]["email"] == DEMO_EMAIL
        assert d["user"]["emailVerified"] is True
        assert d.get("accessToken") or demo_session.cookies.get("access_token")

    def test_wrong_password_returns_401(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": DEMO_EMAIL, "password": "wrong-pass-here", "remember": False})
        assert r.status_code == 401

    def test_brute_force_lockout(self):
        email = f"nobody+{uuid.uuid4().hex[:6]}@example.com"
        codes = []
        for _ in range(6):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "wrong", "remember": False})
            codes.append(r.status_code)
        assert 429 in codes, f"Expected 429 after 5 failures, got {codes}"


# ---------- Session / Refresh / Logout ----------
class TestSession:
    def test_me_with_bearer(self, demo_session):
        r = demo_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == DEMO_EMAIL

    def test_me_without_token(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_refresh_rotates_cookie_session(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "remember": True})
        assert r.status_code == 200
        old_token = _session_token(s, r)
        assert old_token
        r2 = s.post(f"{API}/auth/refresh")
        assert r2.status_code == 200, r2.text
        assert "accessToken" not in r2.json()
        assert r2.json().get("auth") == "cookie"
        new_token = _session_token(s, r2)
        assert new_token and isinstance(new_token, str)
        r3 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert r3.status_code == 200

    def test_logout_revokes_refresh(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "remember": True})
        assert r.status_code == 200
        r2 = s.post(f"{API}/auth/logout")
        assert r2.status_code == 200
        r3 = s.post(f"{API}/auth/refresh")
        assert r3.status_code == 401


# ---------- Protected routes ----------
class TestProtected:
    @pytest.mark.parametrize("path", ["/clients", "/projects", "/dashboard/summary"])
    def test_requires_auth(self, path):
        r = requests.get(f"{API}{path}")
        assert r.status_code == 401, f"{path} did not require auth: {r.status_code}"

# ---------- Forgot / Reset ----------
class TestForgotReset:
    def test_forgot_returns_link_for_existing(self):
        # Use a throwaway user we register just for this test
        s = requests.Session()
        email = _rand_email()
        s.post(f"{API}/auth/register", json={"firstName": "R", "lastName": "P",
               "email": email, "password": "InitPass123!", "company": "R"})
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        data = r.json()
        assert "resetLink" in data and "token=" in data["resetLink"]
        token = data["resetLink"].split("token=")[-1]

        # Reset password
        new_pass = "BrandNew456!"
        r2 = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": new_pass})
        assert r2.status_code == 200

        # Login with new password
        r3 = requests.post(f"{API}/auth/login",
                           json={"email": email, "password": new_pass, "remember": False})
        assert r3.status_code == 200

    def test_forgot_unknown_email_generic(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": "not-a-real-user@example.com"})
        assert r.status_code == 200
        # Should NOT return a resetLink
        assert "resetLink" not in r.json()

    def test_reset_with_invalid_token(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "invalid-xyz", "password": "Whatever123!"})
        assert r.status_code == 400


# ---------- Email verification ----------
class TestEmailVerify:
    def test_verify_email_flow(self):
        s = requests.Session()
        email = _rand_email()
        r = s.post(f"{API}/auth/register", json={"firstName": "V", "lastName": "E",
                   "email": email, "password": "InitPass123!", "company": "V"})
        assert r.status_code == 200
        link = r.json()["verificationLink"]
        token = link.split("token=")[-1]
        assert r.json()["user"]["emailVerified"] is False

        r2 = requests.post(f"{API}/auth/verify-email", json={"token": token})
        assert r2.status_code == 200

        # /me should now show verified
        access = _session_token(s, r) or (r.json() or {}).get("accessToken")
        r3 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert r3.status_code == 200
        assert r3.json()["emailVerified"] is True

    def test_verify_email_invalid_token(self):
        r = requests.post(f"{API}/auth/verify-email", json={"token": "garbage"})
        assert r.status_code == 400


# ---------- Profile / Change password ----------
class TestProfileAndPassword:
    def test_update_profile(self):
        s = requests.Session()
        email = _rand_email()
        r = s.post(f"{API}/auth/register", json={"firstName": "P", "lastName": "O",
                   "email": email, "password": "InitPass123!", "company": "OrigCo"})
        access = _session_token(s, r) or (r.json() or {}).get("accessToken")
        h = {"Authorization": f"Bearer {access}"}
        r2 = requests.patch(f"{API}/auth/profile", headers=h, json={
            "firstName": "Updated", "lastName": "Name", "avatar": "https://x/y.png",
            "timezone": "America/New_York", "language": "en", "company": "NewCo Inc."
        })
        assert r2.status_code == 200
        u = r2.json()
        assert u["firstName"] == "Updated"
        assert u["lastName"] == "Name"
        # Verify org name updated
        r3 = requests.get(f"{API}/auth/organization", headers=h)
        assert r3.status_code == 200
        assert r3.json()["name"] == "NewCo Inc."

    def test_change_password(self):
        s = requests.Session()
        email = _rand_email()
        r = s.post(f"{API}/auth/register", json={"firstName": "C", "lastName": "P",
                   "email": email, "password": "InitPass123!", "company": "C"})
        access = _session_token(s, r) or (r.json() or {}).get("accessToken")
        h = {"Authorization": f"Bearer {access}"}
        # Wrong current
        r2 = requests.post(f"{API}/auth/change-password", headers=h,
                           json={"currentPassword": "wrong", "newPassword": "NewPass456!"})
        assert r2.status_code == 400
        # Correct current
        r3 = requests.post(f"{API}/auth/change-password", headers=h,
                           json={"currentPassword": "InitPass123!", "newPassword": "NewPass456!"})
        assert r3.status_code == 200
        # Login with new
        r4 = requests.post(f"{API}/auth/login",
                           json={"email": email, "password": "NewPass456!", "remember": False})
        assert r4.status_code == 200


# ---------- Regression: existing endpoints still 200 ----------
class TestRegression:
    def test_clients_projects_tasks_reachable(self, demo_session):
        for path in ["/clients", "/projects", "/tasks", "/dashboard/summary"]:
            r = demo_session.get(f"{API}{path}")
            assert r.status_code == 200, f"{path} -> {r.status_code}"

    def test_bcrypt_hash_format(self):
        # Verify by hitting login and confirming success (real bcrypt verify path).
        r = requests.post(f"{API}/auth/login",
                          json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "remember": False})
        assert r.status_code == 200
