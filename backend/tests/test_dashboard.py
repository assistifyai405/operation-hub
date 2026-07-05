"""Tests for Executive Dashboard endpoints: /api/dashboard/summary and /api/dashboard/search."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestDashboardSummary:
    def test_summary_status_and_shape(self, client):
        r = client.get(f"{API}/dashboard/summary", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["kpis", "financial", "project_status", "recent_activity", "upcoming_tasks", "recent_clients"]:
            assert k in data, f"missing {k}"

    def test_kpi_keys(self, client):
        d = client.get(f"{API}/dashboard/summary", timeout=30).json()
        kpis = d["kpis"]
        expected = ["total_clients", "active_projects", "completed_projects", "open_tasks",
                    "completed_tasks", "pending_proposals", "sent_contracts",
                    "outstanding_invoices", "paid_invoices", "revenue"]
        for k in expected:
            assert k in kpis, f"missing kpi {k}"
            assert isinstance(kpis[k], (int, float)), f"kpi {k} not numeric: {kpis[k]}"

    def test_financial_fields(self, client):
        d = client.get(f"{API}/dashboard/summary", timeout=30).json()
        fin = d["financial"]
        for k in ["revenue", "outstanding_revenue", "average_invoice_value", "total_invoices", "by_status"]:
            assert k in fin
        assert isinstance(fin["by_status"], dict)

    def test_lists_are_arrays(self, client):
        d = client.get(f"{API}/dashboard/summary", timeout=30).json()
        assert isinstance(d["recent_activity"], list)
        assert isinstance(d["upcoming_tasks"], list)
        assert isinstance(d["recent_clients"], list)
        # No mongo _id leaks
        for coll in [d["recent_activity"], d["upcoming_tasks"], d["recent_clients"]]:
            for item in coll:
                assert "_id" not in item

    def test_kpi_math_consistency(self, client):
        d = client.get(f"{API}/dashboard/summary", timeout=30).json()
        kpis = d["kpis"]
        # active + completed projects = sum of project_status values
        total_status = sum(d["project_status"].values())
        assert kpis["active_projects"] + kpis["completed_projects"] == total_status


class TestDashboardSearch:
    def test_search_empty_query(self, client):
        r = client.get(f"{API}/dashboard/search?q=", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["clients", "projects", "invoices", "contracts", "proposals"]:
            assert d[k] == []

    def test_search_returns_groups(self, client):
        r = client.get(f"{API}/dashboard/search?q=a", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["clients", "projects", "invoices", "contracts", "proposals"]:
            assert k in d
            assert isinstance(d[k], list)

    def test_search_no_object_ids(self, client):
        d = client.get(f"{API}/dashboard/search?q=a", timeout=15).json()
        for group in d.values():
            for item in group:
                assert "_id" not in item

    def test_search_nonexistent(self, client):
        d = client.get(f"{API}/dashboard/search?q=zzzzzunlikely12345", timeout=15).json()
        assert d["clients"] == []
        assert d["projects"] == []


class TestRegression:
    """Ensure existing project workspace endpoints still work."""

    def test_projects_list(self, client):
        r = client.get(f"{API}/projects", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_clients_list(self, client):
        r = client.get(f"{API}/clients", timeout=15)
        assert r.status_code == 200

    def test_invoice_config(self, client):
        r = client.get(f"{API}/invoice/config", timeout=15)
        assert r.status_code == 200
        assert "statuses" in r.json()

    def test_proposal_sections(self, client):
        r = client.get(f"{API}/proposal/sections", timeout=15)
        assert r.status_code == 200

    def test_contract_sections(self, client):
        r = client.get(f"{API}/contract/sections", timeout=15)
        assert r.status_code == 200
