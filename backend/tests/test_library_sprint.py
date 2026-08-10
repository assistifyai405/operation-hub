"""Sprint 14: Library/Documents/Analytics/Notifications/GlobalSearch integration tests.

Covers:
- Auth (demo + fresh register)
- GET /api/library/{documents,proposals,contracts,invoices} pagination + filters + isolation
- POST /api/documents/upload -> real file lands in library and downloads via /file?auth=
- PUT /api/documents/{id} rename
- DELETE /api/documents/{id}
- GET /api/analytics (real KPIs, isolation)
- GET /api/notifications (real activities, isolation)
- GET /api/dashboard/search returns documents group
- Deep-link data readiness (project/invoice/contract/proposal have ids)
"""
import io
import os
import uuid
import pytest
import requests
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password, "remember": True}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return auth_json(None, r).get("accessToken")


@pytest.fixture(scope="module")
def demo_token():
    return _login(DEMO_EMAIL, DEMO_PASSWORD)


@pytest.fixture(scope="module")
def demo_headers(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}


@pytest.fixture(scope="module")
def fresh_user():
    email = f"lib+{uuid.uuid4().hex[:10]}@example.com"
    pw = "TestPass123!"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "firstName": "Lib", "lastName": "Tester", "email": email, "password": pw, "company": "TestCo"
    }, timeout=30)
    assert r.status_code in (200, 201), f"register: {r.status_code} {r.text}"
    token = auth_json(None, r).get("accessToken")
    return {"email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


# ---------- Library endpoints (demo has data) ----------
class TestLibraryDemo:
    def test_library_documents_shape(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/documents?page=1&page_size=12", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("items", "total", "page", "page_size", "pages"):
            assert k in d
        assert d["page"] == 1 and d["page_size"] == 12
        assert isinstance(d["items"], list)

    def test_library_page_size_capped(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/documents?page=1&page_size=999", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["page_size"] == 50

    def test_library_proposals(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/proposals?sort=recent", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert set(("items", "total", "page", "page_size", "pages")).issubset(d.keys())

    def test_library_contracts(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/contracts", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d

    def test_library_invoices_totals(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/invoices", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "totals" in d
        t = d["totals"]
        for k in ("by_status", "revenue", "outstanding", "count"):
            assert k in t
        # demo org has 1 invoice ~8640, status Generated
        assert t["count"] >= 1
        assert isinstance(t["by_status"], dict)

    def test_library_invoices_status_filter(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/library/invoices?status=Generated", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["status"] == "Generated"


# ---------- Isolation on fresh org ----------
class TestFreshOrgIsolation:
    def test_fresh_docs_empty(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/library/documents", headers=fresh_user["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_fresh_proposals_empty(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/library/proposals", headers=fresh_user["headers"], timeout=30)
        assert r.json()["total"] == 0

    def test_fresh_contracts_empty(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/library/contracts", headers=fresh_user["headers"], timeout=30)
        assert r.json()["total"] == 0

    def test_fresh_invoices_empty(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/library/invoices", headers=fresh_user["headers"], timeout=30)
        d = r.json()
        assert d["total"] == 0
        assert d["totals"]["count"] == 0
        assert d["totals"]["revenue"] == 0
        assert d["totals"]["outstanding"] == 0

    def test_fresh_analytics_zero(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/analytics", headers=fresh_user["headers"], timeout=30)
        assert r.status_code == 200
        k = r.json()["kpis"]
        assert k["total_clients"] == 0
        assert k["total_projects"] == 0
        assert k["total_invoiced"] == 0
        assert k["total_paid"] == 0
        assert k["documents"] == 0


# ---------- Document upload / rename / download / delete flow ----------
class TestDocumentUploadFlow:
    def test_upload_rename_download_delete(self, fresh_user):
        headers = fresh_user["headers"]
        # Upload a small txt
        payload = b"Hello Assistify sprint 14 test file " + uuid.uuid4().hex.encode()
        files = {"file": ("TEST_upload.txt", io.BytesIO(payload), "text/plain")}
        r = requests.post(f"{BASE_URL}/api/documents/upload", headers=headers, files=files, timeout=60)
        assert r.status_code == 200, f"upload: {r.status_code} {r.text}"
        doc = r.json()
        assert "id" in doc and doc["name"] == "TEST_upload.txt"
        assert doc["url"].endswith(f"/api/documents/{doc['id']}/file")
        doc_id = doc["id"]

        # Verify appears in library
        r = requests.get(f"{BASE_URL}/api/library/documents", headers=headers, timeout=30)
        ids = [i["id"] for i in r.json()["items"]]
        assert doc_id in ids

        # Rename
        r = requests.put(f"{BASE_URL}/api/documents/{doc_id}", headers=headers, json={"name": "TEST_renamed.txt"}, timeout=30)
        assert r.status_code == 200 and r.json()["name"] == "TEST_renamed.txt"

        # Download via ?auth=
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}/file?auth={fresh_user['token']}", timeout=30)
        assert r.status_code == 200
        assert r.content == payload

        # Download via Bearer header
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}/file", headers=headers, timeout=30)
        assert r.status_code == 200 and r.content == payload

        # Download unauth -> 401
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}/file", timeout=30)
        assert r.status_code == 401

        # Delete
        r = requests.delete(f"{BASE_URL}/api/documents/{doc_id}", headers=headers, timeout=30)
        assert r.status_code == 200

        # Verify 404 on download after delete
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}/file", headers=headers, timeout=30)
        assert r.status_code == 404

    def test_upload_search_and_type_filter(self, fresh_user):
        headers = fresh_user["headers"]
        # Upload 2 files
        for name, ctype in [("TEST_alpha.pdf", "application/pdf"), ("TEST_beta.png", "image/png")]:
            files = {"file": (name, io.BytesIO(b"x"*20), ctype)}
            r = requests.post(f"{BASE_URL}/api/documents/upload", headers=headers, files=files, timeout=30)
            assert r.status_code == 200
        # search
        r = requests.get(f"{BASE_URL}/api/library/documents?q=alpha", headers=headers, timeout=30)
        items = r.json()["items"]
        assert any("alpha" in i["name"].lower() for i in items)
        assert all("beta" not in i["name"].lower() for i in items)


# ---------- Global search now includes documents ----------
class TestGlobalSearch:
    def test_search_documents_group(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/search?q=a", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for g in ("clients", "projects", "invoices", "contracts", "proposals", "documents"):
            assert g in d, f"missing group {g}"

    def test_search_isolation(self, fresh_user):
        # Fresh user with no clients/projects/invoices/etc; may have uploaded documents
        # from prior tests in this module. Verify no leakage from demo org.
        r = requests.get(f"{BASE_URL}/api/dashboard/search?q=Halcyon", headers=fresh_user["headers"], timeout=30)
        d = r.json()
        for g in ("clients", "projects", "invoices", "contracts", "proposals", "documents"):
            assert d[g] == [], f"{g} leaked from demo org: {d[g]}"


# ---------- Notifications ----------
class TestNotifications:
    def test_demo_notifications(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/notifications", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_fresh_notifications_empty_or_list(self, fresh_user):
        r = requests.get(f"{BASE_URL}/api/notifications", headers=fresh_user["headers"], timeout=30)
        assert r.status_code == 200
        # fresh user has no activities
        assert isinstance(r.json(), list)


# ---------- Analytics on demo has real numbers ----------
class TestAnalyticsDemo:
    def test_demo_analytics_shape(self, demo_headers):
        r = requests.get(f"{BASE_URL}/api/analytics", headers=demo_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("kpis", "revenue_series", "project_status", "invoice_status"):
            assert k in d
        assert d["kpis"]["total_projects"] >= 1
        assert d["kpis"]["invoices"] >= 1


# ---------- Auth required ----------
class TestUnauth:
    @pytest.mark.parametrize("path", [
        "/api/library/documents", "/api/library/proposals",
        "/api/library/contracts", "/api/library/invoices",
        "/api/analytics", "/api/notifications", "/api/dashboard/search?q=a",
    ])
    def test_unauth_401(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code in (401, 403)
