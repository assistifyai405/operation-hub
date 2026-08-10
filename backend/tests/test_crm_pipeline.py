"""Backend tests for AI CRM & Sales Pipeline sprint (iteration_24)."""
import os
import time
import pytest
import requests
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

STAGES = ["New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating", "Won", "Lost"]


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/demo", timeout=30)
    assert r.status_code == 200, f"demo login failed: {r.status_code} {r.text[:200]}"
    tok = auth_json(client, r).get("accessToken")
    assert tok
    return tok


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# --- Pipeline ---
class TestPipeline:
    def test_pipeline_shape(self, client):
        r = client.get(f"{API}/crm/pipeline")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["stages"] == STAGES
        assert len(data["columns"]) == 7
        for col in data["columns"]:
            assert set(col.keys()) >= {"stage", "count", "value", "items"}
        # Each item decorated
        items = [i for c in data["columns"] for i in c["items"]]
        assert len(items) >= 6, "demo should seed >=6 leads"
        for it in items:
            for k in ("score", "probability", "ai_confidence", "color"):
                assert k in it, f"missing {k}"
            assert "client_name" in it

    def test_pipeline_search(self, client):
        r = client.get(f"{API}/crm/pipeline", params={"q": "zzzzzznope"})
        assert r.status_code == 200
        assert sum(c["count"] for c in r.json()["columns"]) == 0

    def test_pipeline_sort_value(self, client):
        r = client.get(f"{API}/crm/pipeline", params={"sort": "value"})
        assert r.status_code == 200
        for col in r.json()["columns"]:
            vals = [i.get("value") or 0 for i in col["items"]]
            assert vals == sorted(vals, reverse=True)


# --- Leads CRUD ---
class TestLeadsCRUD:
    def test_lead_full_flow(self, client):
        # Create
        payload = {"title": "TEST_lead_crm", "stage": "New", "value": 15000, "notes": "test"}
        r = client.post(f"{API}/crm/leads", json=payload)
        assert r.status_code == 200, r.text
        lead = r.json()
        lid = lead["id"]
        assert lead["stage"] == "New"
        assert "score" in lead and "probability" in lead

        # Get
        r = client.get(f"{API}/crm/leads/{lid}")
        assert r.status_code == 200
        got = r.json()
        assert "timeline" in got and "followups" in got

        # Invalid stage on create
        r = client.post(f"{API}/crm/leads", json={"title": "x", "stage": "Bogus"})
        assert r.status_code == 400

        # Update
        r = client.put(f"{API}/crm/leads/{lid}", json={**payload, "value": 25000, "title": "TEST_lead_crm_upd"})
        assert r.status_code == 200
        assert r.json()["value"] == 25000

        # Stage move
        r = client.patch(f"{API}/crm/leads/{lid}/stage", json={"stage": "Qualified"})
        assert r.status_code == 200
        assert r.json()["stage"] == "Qualified"

        # Verify persistence
        r = client.get(f"{API}/crm/leads/{lid}")
        assert r.json()["stage"] == "Qualified"
        history = r.json().get("stage_history", [])
        assert any(h["stage"] == "Qualified" for h in history)

        # Invalid stage patch
        r = client.patch(f"{API}/crm/leads/{lid}/stage", json={"stage": "Nope"})
        assert r.status_code == 400

        # Convert (creates project)
        r = client.post(f"{API}/crm/leads/{lid}/convert")
        assert r.status_code == 200
        pid1 = r.json()["project_id"]
        assert pid1
        # Idempotent
        r2 = client.post(f"{API}/crm/leads/{lid}/convert")
        assert r2.json()["project_id"] == pid1

        # Delete
        r = client.delete(f"{API}/crm/leads/{lid}")
        assert r.status_code == 200
        r = client.get(f"{API}/crm/leads/{lid}")
        assert r.status_code == 404

    def test_unknown_id(self, client):
        assert client.get(f"{API}/crm/leads/does-not-exist").status_code == 404
        assert client.patch(f"{API}/crm/leads/does-not-exist/stage", json={"stage": "New"}).status_code == 404
        assert client.delete(f"{API}/crm/leads/does-not-exist").status_code == 404


# --- AI brief ---
class TestAIBrief:
    def test_ai_brief_generation(self, client):
        # pick an existing seed lead
        pl = client.get(f"{API}/crm/pipeline").json()
        lid = None
        for c in pl["columns"]:
            if c["items"]:
                lid = c["items"][0]["id"]
                break
        assert lid
        r = client.post(f"{API}/crm/leads/{lid}/ai-brief")
        if r.status_code == 502:
            pytest.skip(f"LLM env-limited: {r.text[:150]}")
        assert r.status_code == 200, r.text
        b = r.json()
        for k in ("relationship_summary", "conversation_summary", "missing_info", "suggested_followup",
                  "objections", "deal_health", "win_probability", "urgency", "risk_level", "next_best_action"):
            assert k in b, f"missing {k}"


# --- Contacts ---
class TestContacts:
    def test_contacts_list(self, client):
        r = client.get(f"{API}/crm/contacts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 3
        for c in data:
            for k in ("projects_count", "open_leads", "pipeline_value", "last_activity"):
                assert k in c

    def test_contact_detail(self, client):
        contacts = client.get(f"{API}/crm/contacts").json()
        cid = contacts[0]["id"]
        r = client.get(f"{API}/crm/contacts/{cid}")
        assert r.status_code == 200
        d = r.json()
        for k in ("projects", "leads", "proposals", "contracts", "invoices", "timeline", "pipeline_value"):
            assert k in d


# --- Search ---
class TestSearch:
    def test_search_basic(self, client):
        r = client.get(f"{API}/crm/search", params={"q": "a"})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        types = {x["type"] for x in data["results"]}
        # at least contact or project should appear
        assert types


# --- Sales metrics ---
class TestSalesMetrics:
    def test_sales_metrics_shape(self, client):
        r = client.get(f"{API}/crm/sales-metrics")
        assert r.status_code == 200
        m = r.json()
        for k in ("pipeline_value", "weighted_pipeline", "closing_this_week", "leads_needing_attention",
                  "win_rate", "avg_deal_size", "conversion_rate", "ai_insights", "stage_breakdown"):
            assert k in m
        assert len(m["stage_breakdown"]) == 7
        assert isinstance(m["ai_insights"], list) and len(m["ai_insights"]) >= 1
        assert m["pipeline_value"] > 0, "demo should have open pipeline"


# --- Org isolation ---
class TestOrgIsolation:
    def test_org_isolation(self):
        # Register a fresh user
        import uuid
        email = f"iso_{uuid.uuid4().hex[:8]}@test.local"
        r = requests.post(f"{API}/auth/register", json={
            "firstName": "Iso", "lastName": "Test", "email": email,
            "password": "IsoTest2026!"
        }, timeout=30)
        assert r.status_code in (200, 201), r.text
        tok = auth_json(client, r).get("accessToken")
        assert tok
        h = {"Authorization": f"Bearer {tok}"}
        # Fresh org should see 0 leads
        r = requests.get(f"{API}/crm/pipeline", headers=h)
        assert r.status_code == 200
        assert sum(c["count"] for c in r.json()["columns"]) == 0
        # Contacts empty or org-scoped
        r = requests.get(f"{API}/crm/contacts", headers=h)
        assert r.status_code == 200
        assert r.json() == []


# --- Regression on /clients with enriched fields ---
class TestClientsRegression:
    def test_client_create_with_new_fields(self, client):
        payload = {
            "name": "TEST_ClientReg", "contact": "Jane", "email": "j@t.co",
            "phone": "111", "value": 1000, "status": "Prospect",
            "industry": "SaaS", "tags": ["vip"], "website": "https://t.co",
            "company_size": "10-50"
        }
        r = client.post(f"{API}/clients", json=payload)
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        r = client.get(f"{API}/clients")
        assert r.status_code == 200
        found = next((c for c in r.json() if c["id"] == cid), None)
        assert found is not None
        # cleanup
        client.delete(f"{API}/clients/{cid}")
