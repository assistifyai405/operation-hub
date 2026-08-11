"""Tests for Executive Dashboard endpoints — TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="DashSum")
    client.post("/api/clients", headers=a["headers"], json={"name": "DS Client", "email": "ds@c.com"})
    client.post("/api/projects", headers=a["headers"], json={"name": "DS Project", "status": "In Progress"})
    return a


class TestDashboardSummary:
    def test_summary_status_and_shape(self, client, auth):
        r = client.get("/api/dashboard/summary", headers=auth["headers"])
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["kpis", "financial", "project_status", "recent_activity", "upcoming_tasks", "recent_clients"]:
            assert k in data, f"missing {k}"

    def test_kpi_keys(self, client, auth):
        d = client.get("/api/dashboard/summary", headers=auth["headers"]).json()
        kpis = d["kpis"]
        expected = [
            "total_clients", "active_projects", "completed_projects", "open_tasks",
            "completed_tasks", "pending_proposals", "sent_contracts",
            "outstanding_invoices", "paid_invoices", "revenue",
        ]
        for k in expected:
            assert k in kpis, f"missing kpi {k}"
            assert isinstance(kpis[k], (int, float)), f"kpi {k} not numeric: {kpis[k]}"

    def test_financial_fields(self, client, auth):
        d = client.get("/api/dashboard/summary", headers=auth["headers"]).json()
        fin = d["financial"]
        for k in ["revenue", "outstanding_revenue", "average_invoice_value", "total_invoices", "by_status"]:
            assert k in fin
        assert isinstance(fin["by_status"], dict)

    def test_lists_are_arrays(self, client, auth):
        d = client.get("/api/dashboard/summary", headers=auth["headers"]).json()
        assert isinstance(d["recent_activity"], list)
        assert isinstance(d["upcoming_tasks"], list)
        assert isinstance(d["recent_clients"], list)
        for coll in [d["recent_activity"], d["upcoming_tasks"], d["recent_clients"]]:
            for item in coll:
                assert "_id" not in item

    def test_kpi_math_consistency(self, client, auth):
        d = client.get("/api/dashboard/summary", headers=auth["headers"]).json()
        kpis = d["kpis"]
        total_status = sum(d["project_status"].values())
        assert kpis["active_projects"] + kpis["completed_projects"] == total_status


class TestDashboardSearch:
    def test_search_empty_query(self, client, auth):
        r = client.get("/api/dashboard/search?q=", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ["clients", "projects", "invoices", "contracts", "proposals"]:
            assert d[k] == []

    def test_search_returns_groups(self, client, auth):
        r = client.get("/api/dashboard/search?q=a", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ["clients", "projects", "invoices", "contracts", "proposals"]:
            assert k in d
            assert isinstance(d[k], list)

    def test_search_no_object_ids(self, client, auth):
        d = client.get("/api/dashboard/search?q=a", headers=auth["headers"]).json()
        for group in d.values():
            for item in group:
                assert "_id" not in item

    def test_search_nonexistent(self, client, auth):
        d = client.get("/api/dashboard/search?q=zzzzzunlikely12345", headers=auth["headers"]).json()
        assert d["clients"] == []
        assert d["projects"] == []


class TestRegression:
    def test_projects_list(self, client, auth):
        r = client.get("/api/projects", headers=auth["headers"])
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_clients_list(self, client, auth):
        r = client.get("/api/clients", headers=auth["headers"])
        assert r.status_code == 200

    def test_invoice_config(self, client, auth):
        r = client.get("/api/invoice/config", headers=auth["headers"])
        assert r.status_code == 200
        assert "statuses" in r.json()

    def test_proposal_sections(self, client, auth):
        r = client.get("/api/proposal/sections", headers=auth["headers"])
        assert r.status_code == 200

    def test_contract_sections(self, client, auth):
        r = client.get("/api/contract/sections", headers=auth["headers"])
        assert r.status_code == 200
