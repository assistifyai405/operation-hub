"""Sprint 14: Library/Documents/Analytics/Notifications — TestClient."""

from __future__ import annotations

import io
import sys
import uuid
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, upload_dir = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="LibDemo")
    h = a["headers"]
    # Seed a client/project so analytics + search have data
    cr = client.post("/api/clients", headers=h, json={"name": "Lib Client", "email": "l@l.com"})
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=h, json={"name": "Lib Project", "client_id": cid, "status": "Active"})
    a["project_id"] = pr.json()["id"]
    a["client_id"] = cid
    return a


@pytest.fixture
def fresh_user(client):
    return register_user(client, company="LibFresh")


# ---------- Library endpoints ----------
class TestLibraryDemo:
    def test_library_documents_shape(self, client, auth):
        r = client.get("/api/library/documents?page=1&page_size=12", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ("items", "total", "page", "page_size", "pages"):
            assert k in d
        assert d["page"] == 1 and d["page_size"] == 12
        assert isinstance(d["items"], list)

    def test_library_page_size_capped(self, client, auth):
        r = client.get("/api/library/documents?page=1&page_size=999", headers=auth["headers"])
        assert r.status_code == 200
        assert r.json()["page_size"] == 50

    def test_library_proposals(self, client, auth):
        r = client.get("/api/library/proposals?sort=recent", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        assert set(("items", "total", "page", "page_size", "pages")).issubset(d.keys())

    def test_library_contracts(self, client, auth):
        r = client.get("/api/library/contracts", headers=auth["headers"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_library_invoices_totals(self, client, auth):
        r = client.get("/api/library/invoices", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        assert "totals" in d
        t = d["totals"]
        for k in ("by_status", "revenue", "outstanding", "count"):
            assert k in t
        assert isinstance(t["by_status"], dict)
        assert t["count"] >= 0

    def test_library_invoices_status_filter(self, client, auth):
        r = client.get("/api/library/invoices?status=Generated", headers=auth["headers"])
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["status"] == "Generated"


# ---------- Isolation on fresh org ----------
class TestFreshOrgIsolation:
    def test_fresh_docs_empty(self, client, fresh_user):
        r = client.get("/api/library/documents", headers=fresh_user["headers"])
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_fresh_proposals_empty(self, client, fresh_user):
        r = client.get("/api/library/proposals", headers=fresh_user["headers"])
        assert r.json()["total"] == 0

    def test_fresh_contracts_empty(self, client, fresh_user):
        r = client.get("/api/library/contracts", headers=fresh_user["headers"])
        assert r.json()["total"] == 0

    def test_fresh_invoices_empty(self, client, fresh_user):
        r = client.get("/api/library/invoices", headers=fresh_user["headers"])
        d = r.json()
        assert d["total"] == 0
        assert d["totals"]["count"] == 0
        assert d["totals"]["revenue"] == 0
        assert d["totals"]["outstanding"] == 0

    def test_fresh_analytics_zero(self, client, fresh_user):
        r = client.get("/api/analytics", headers=fresh_user["headers"])
        assert r.status_code == 200
        k = r.json()["kpis"]
        assert k["total_clients"] == 0
        assert k["total_projects"] == 0
        assert k["total_invoiced"] == 0
        assert k["total_paid"] == 0
        assert k["documents"] == 0


# ---------- Document upload / rename / download / delete flow ----------
class TestDocumentUploadFlow:
    def test_upload_rename_download_delete(self, client, fresh_user):
        headers = fresh_user["headers"]
        payload = b"Hello Assistify sprint 14 test file " + uuid.uuid4().hex.encode()
        files = {"file": ("TEST_upload.txt", io.BytesIO(payload), "text/plain")}
        r = client.post("/api/documents/upload", headers=headers, files=files)
        assert r.status_code == 200, f"upload: {r.status_code} {r.text}"
        doc = r.json()
        assert "id" in doc and doc["name"] == "TEST_upload.txt"
        assert doc["url"].endswith(f"/api/documents/{doc['id']}/file")
        doc_id = doc["id"]

        r = client.get("/api/library/documents", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert doc_id in ids

        r = client.put(f"/api/documents/{doc_id}", headers=headers, json={"name": "TEST_renamed.txt"})
        assert r.status_code == 200 and r.json()["name"] == "TEST_renamed.txt"

        r = client.get(f"/api/documents/{doc_id}/file?auth={fresh_user['token']}")
        assert r.status_code == 200
        assert r.content == payload

        r = client.get(f"/api/documents/{doc_id}/file", headers=headers)
        assert r.status_code == 200 and r.content == payload

        client.cookies.clear()
        r = client.get(f"/api/documents/{doc_id}/file")
        assert r.status_code == 401

        r = client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert r.status_code == 200

        r = client.get(f"/api/documents/{doc_id}/file", headers=headers)
        assert r.status_code == 404

    def test_upload_search_and_type_filter(self, client, fresh_user):
        headers = fresh_user["headers"]
        for name, ctype in [("TEST_alpha.pdf", "application/pdf"), ("TEST_beta.png", "image/png")]:
            files = {"file": (name, io.BytesIO(b"x" * 20), ctype)}
            r = client.post("/api/documents/upload", headers=headers, files=files)
            assert r.status_code == 200
        r = client.get("/api/library/documents?q=alpha", headers=headers)
        items = r.json()["items"]
        assert any("alpha" in i["name"].lower() for i in items)
        assert all("beta" not in i["name"].lower() for i in items)


# ---------- Global search ----------
class TestGlobalSearch:
    def test_search_documents_group(self, client, auth):
        r = client.get("/api/dashboard/search?q=a", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for g in ("clients", "projects", "invoices", "contracts", "proposals", "documents"):
            assert g in d, f"missing group {g}"

    def test_search_isolation(self, client, fresh_user):
        r = client.get("/api/dashboard/search?q=Halcyon", headers=fresh_user["headers"])
        d = r.json()
        for g in ("clients", "projects", "invoices", "contracts", "proposals", "documents"):
            assert d[g] == [], f"{g} leaked: {d[g]}"


# ---------- Notifications ----------
class TestNotifications:
    def test_notifications_list(self, client, auth):
        r = client.get("/api/notifications", headers=auth["headers"])
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_fresh_notifications_empty_or_list(self, client, fresh_user):
        r = client.get("/api/notifications", headers=fresh_user["headers"])
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Analytics ----------
class TestAnalyticsDemo:
    def test_analytics_shape(self, client, auth):
        r = client.get("/api/analytics", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ("kpis", "revenue_series", "project_status", "invoice_status"):
            assert k in d
        assert d["kpis"]["total_projects"] >= 1
        assert d["kpis"]["total_clients"] >= 1


# ---------- Auth required ----------
class TestUnauth:
    @pytest.mark.parametrize("path", [
        "/api/library/documents", "/api/library/proposals",
        "/api/library/contracts", "/api/library/invoices",
        "/api/analytics", "/api/notifications", "/api/dashboard/search?q=a",
    ])
    def test_unauth_401(self, client, path):
        client.cookies.clear()
        r = client.get(path)
        assert r.status_code in (401, 403)
