"""AI Invoice Generator — TestClient (soften LLM generate; keep CRUD math)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

EXPECTED_STATUSES = ["Draft", "Generated", "Sent", "Paid", "Overdue", "Cancelled", "Archived"]
INV_RE = re.compile(r"^INV-\d{6}-\d{4}$")


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    return register_user(client, company="Invoice Co")


@pytest.fixture
def project(client, auth):
    h = auth["headers"]
    cr = client.post("/api/clients", headers=h, json={
        "name": "TEST_INVOICE_ClientCo", "contact": "Jane Doe", "email": "jane@testinv.com",
    })
    assert cr.status_code in (200, 201), cr.text
    client_id = cr.json()["id"]
    pr = client.post("/api/projects", headers=h, json={
        "name": "TEST_INVOICE_MODULE", "description": "Testing invoice",
        "status": "In Progress", "client_id": client_id,
    })
    assert pr.status_code in (200, 201), pr.text
    pid = pr.json()["id"]
    client.post("/api/notes", headers=h, json={"project_id": pid, "content": "Budget $10k, Net 14."})
    yield {"project_id": pid, "client_id": client_id, "headers": h}
    client.delete(f"/api/projects/{pid}", headers=h)
    client.delete(f"/api/clients/{client_id}", headers=h)


def test_invoice_config(client, auth):
    r = client.get("/api/invoice/config", headers=auth["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["statuses"] == EXPECTED_STATUSES
    assert isinstance(data["fields"], list) and len(data["fields"]) > 0
    keys = [f["key"] for f in data["fields"]]
    assert "billing_address" in keys and "payment_terms" in keys


def test_generate_bad_project(client, auth):
    r = client.post("/api/projects/does-not-exist-xyz/invoice/generate", headers=auth["headers"])
    assert r.status_code == 404


def test_generate_shape(client, project):
    h, pid = project["headers"], project["project_id"]
    r = client.post(f"/api/projects/{pid}/invoice/generate", headers=h)
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    if r.status_code != 200:
        return
    generated = r.json()
    for k in ("invoice_number", "title", "content", "line_items", "subtotal", "vat", "total"):
        assert k in generated, f"missing {k}"
    if generated.get("invoice_number"):
        assert INV_RE.match(generated["invoice_number"]) or generated["invoice_number"].startswith("INV")
    assert isinstance(generated["line_items"], list)


def test_vat_totals_recomputed(client, project):
    h, pid = project["headers"], project["project_id"]
    payload = {
        "title": "TEST_INVOICE_TOTALS", "status": "Draft",
        "content": {"vat_rate": 20, "description": "test totals"},
        "line_items": [
            {"description": "A", "quantity": 10, "unit_price": 100},
            {"description": "B", "quantity": 2, "unit_price": 250},
        ],
    }
    r = client.post(f"/api/projects/{pid}/invoice", headers=h, json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["subtotal"] == 1500
    assert doc["vat"] == 300
    assert doc["total"] == 1800
    for li in doc["line_items"]:
        assert li["amount"] == li["quantity"] * li["unit_price"]
    assert doc["version"] == 1
    for f in (
        "invoice_number", "title", "project_id", "client_id",
        "status", "content", "line_items", "subtotal", "vat", "total", "version",
        "history", "created_at", "updated_at",
    ):
        assert f in doc, f"missing {f}"
    assert len(doc["history"]) == 1


def test_get_invoice_persisted(client, project):
    h, pid = project["headers"], project["project_id"]
    # ensure saved
    client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "TEST_INVOICE_TOTALS", "status": "Draft",
        "content": {"vat_rate": 20},
        "line_items": [
            {"description": "A", "quantity": 10, "unit_price": 100},
            {"description": "B", "quantity": 2, "unit_price": 250},
        ],
    })
    r = client.get(f"/api/projects/{pid}/invoice", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["version"] >= 1
    assert d["total"] == 1800


def test_invalid_status(client, project):
    h, pid = project["headers"], project["project_id"]
    r = client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "x", "status": "NotAStatus", "content": {"vat_rate": 0}, "line_items": [],
    })
    assert r.status_code == 422


def test_save_v2_increments(client, project):
    h, pid = project["headers"], project["project_id"]
    client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "v1", "status": "Draft", "content": {"vat_rate": 20},
        "line_items": [{"description": "A", "quantity": 1, "unit_price": 100}],
    })
    payload = {
        "title": "TEST_INVOICE_TOTALS v2", "status": "Generated",
        "content": {"vat_rate": 10, "description": "v2"},
        "line_items": [{"description": "Solo", "quantity": 3, "unit_price": 200}],
    }
    r = client.post(f"/api/projects/{pid}/invoice", headers=h, json=payload)
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] >= 2
    assert doc["subtotal"] == 600
    assert doc["vat"] == 60
    assert doc["total"] == 660


def test_versions_endpoint(client, project):
    h, pid = project["headers"], project["project_id"]
    client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "v1", "status": "Draft", "content": {"vat_rate": 0},
        "line_items": [{"description": "A", "quantity": 1, "unit_price": 10}],
    })
    client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "v2", "status": "Generated", "content": {"vat_rate": 0},
        "line_items": [{"description": "B", "quantity": 2, "unit_price": 10}],
    })
    r = client.get(f"/api/projects/{pid}/invoice/versions", headers=h)
    assert r.status_code == 200
    hist = r.json()
    assert len(hist) >= 2
