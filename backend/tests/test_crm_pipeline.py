"""Backend tests for AI CRM & Sales Pipeline — TestClient (no demo seed)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

STAGES = ["New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating", "Won", "Lost"]


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="CRM Co")
    h = a["headers"]
    # Seed clients + leads so pipeline/metrics have data
    contacts = []
    for i, name in enumerate(["Acme CRM", "Beta CRM", "Gamma CRM"]):
        r = client.post("/api/clients", headers=h, json={
            "name": name, "contact": f"C{i}", "email": f"c{i}@crm.test", "status": "Prospect", "value": 1000 * (i + 1),
        })
        assert r.status_code == 200, r.text
        contacts.append(r.json()["id"])
    stages = ["New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating", "New"]
    for i, st in enumerate(stages):
        r = client.post("/api/crm/leads", headers=h, json={
            "title": f"Lead {i}", "stage": st, "value": 5000 * (i + 1),
            "client_id": contacts[i % len(contacts)], "notes": "seed",
        })
        assert r.status_code == 200, r.text
    a["contacts"] = contacts
    return a


# --- Pipeline ---
class TestPipeline:
    def test_pipeline_shape(self, client, auth):
        r = client.get("/api/crm/pipeline", headers=auth["headers"])
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["stages"] == STAGES
        assert len(data["columns"]) == 7
        for col in data["columns"]:
            assert set(col.keys()) >= {"stage", "count", "value", "items"}
        items = [i for c in data["columns"] for i in c["items"]]
        assert len(items) >= 6
        for it in items:
            for k in ("score", "probability", "ai_confidence", "color"):
                assert k in it, f"missing {k}"
            assert "client_name" in it

    def test_pipeline_search(self, client, auth):
        r = client.get("/api/crm/pipeline", headers=auth["headers"], params={"q": "zzzzzznope"})
        assert r.status_code == 200
        assert sum(c["count"] for c in r.json()["columns"]) == 0

    def test_pipeline_sort_value(self, client, auth):
        r = client.get("/api/crm/pipeline", headers=auth["headers"], params={"sort": "value"})
        assert r.status_code == 200
        for col in r.json()["columns"]:
            vals = [i.get("value") or 0 for i in col["items"]]
            assert vals == sorted(vals, reverse=True)


# --- Leads CRUD ---
class TestLeadsCRUD:
    def test_lead_full_flow(self, client, auth):
        h = auth["headers"]
        payload = {"title": "TEST_lead_crm", "stage": "New", "value": 15000, "notes": "test"}
        r = client.post("/api/crm/leads", headers=h, json=payload)
        assert r.status_code == 200, r.text
        lead = r.json()
        lid = lead["id"]
        assert lead["stage"] == "New"
        assert "score" in lead and "probability" in lead

        r = client.get(f"/api/crm/leads/{lid}", headers=h)
        assert r.status_code == 200
        got = r.json()
        assert "timeline" in got and "followups" in got

        r = client.post("/api/crm/leads", headers=h, json={"title": "x", "stage": "Bogus"})
        assert r.status_code == 400

        r = client.put(f"/api/crm/leads/{lid}", headers=h, json={**payload, "value": 25000, "title": "TEST_lead_crm_upd"})
        assert r.status_code == 200
        assert r.json()["value"] == 25000

        r = client.patch(f"/api/crm/leads/{lid}/stage", headers=h, json={"stage": "Qualified"})
        assert r.status_code == 200
        assert r.json()["stage"] == "Qualified"

        r = client.get(f"/api/crm/leads/{lid}", headers=h)
        assert r.json()["stage"] == "Qualified"
        history = r.json().get("stage_history", [])
        assert any(h_["stage"] == "Qualified" for h_ in history)

        r = client.patch(f"/api/crm/leads/{lid}/stage", headers=h, json={"stage": "Nope"})
        assert r.status_code == 400

        r = client.post(f"/api/crm/leads/{lid}/convert", headers=h)
        assert r.status_code == 200
        pid1 = r.json()["project_id"]
        assert pid1
        r2 = client.post(f"/api/crm/leads/{lid}/convert", headers=h)
        assert r2.json()["project_id"] == pid1

        r = client.delete(f"/api/crm/leads/{lid}", headers=h)
        assert r.status_code == 200
        r = client.get(f"/api/crm/leads/{lid}", headers=h)
        assert r.status_code == 404

    def test_unknown_id(self, client, auth):
        h = auth["headers"]
        assert client.get("/api/crm/leads/does-not-exist", headers=h).status_code == 404
        assert client.patch("/api/crm/leads/does-not-exist/stage", headers=h, json={"stage": "New"}).status_code == 404
        assert client.delete("/api/crm/leads/does-not-exist", headers=h).status_code == 404


# --- AI brief ---
class TestAIBrief:
    def test_ai_brief_generation(self, client, auth):
        h = auth["headers"]
        pl = client.get("/api/crm/pipeline", headers=h).json()
        lid = None
        for c in pl["columns"]:
            if c["items"]:
                lid = c["items"][0]["id"]
                break
        assert lid
        r = client.post(f"/api/crm/leads/{lid}/ai-brief", headers=h)
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            b = r.json()
            for k in (
                "relationship_summary", "conversation_summary", "missing_info", "suggested_followup",
                "objections", "deal_health", "win_probability", "urgency", "risk_level", "next_best_action",
            ):
                assert k in b, f"missing {k}"


# --- Contacts ---
class TestContacts:
    def test_contacts_list(self, client, auth):
        r = client.get("/api/crm/contacts", headers=auth["headers"])
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 3
        for c in data:
            for k in ("projects_count", "open_leads", "pipeline_value", "last_activity"):
                assert k in c

    def test_contact_detail(self, client, auth):
        contacts = client.get("/api/crm/contacts", headers=auth["headers"]).json()
        cid = contacts[0]["id"]
        r = client.get(f"/api/crm/contacts/{cid}", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        for k in ("projects", "leads", "proposals", "contracts", "invoices", "timeline", "pipeline_value"):
            assert k in d


# --- Search ---
class TestSearch:
    def test_search_basic(self, client, auth):
        r = client.get("/api/crm/search", headers=auth["headers"], params={"q": "a"})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        types = {x["type"] for x in data["results"]}
        assert types


# --- Sales metrics ---
class TestSalesMetrics:
    def test_sales_metrics_shape(self, client, auth):
        r = client.get("/api/crm/sales-metrics", headers=auth["headers"])
        assert r.status_code == 200
        m = r.json()
        for k in (
            "pipeline_value", "weighted_pipeline", "closing_this_week", "leads_needing_attention",
            "win_rate", "avg_deal_size", "conversion_rate", "ai_insights", "stage_breakdown",
        ):
            assert k in m
        assert len(m["stage_breakdown"]) == 7
        assert isinstance(m["ai_insights"], list) and len(m["ai_insights"]) >= 1
        assert m["pipeline_value"] > 0


# --- Org isolation ---
class TestOrgIsolation:
    def test_org_isolation(self, client):
        a = register_user(client, company="IsoCRM")
        h = a["headers"]
        r = client.get("/api/crm/pipeline", headers=h)
        assert r.status_code == 200
        assert sum(c["count"] for c in r.json()["columns"]) == 0
        r = client.get("/api/crm/contacts", headers=h)
        assert r.status_code == 200
        assert r.json() == []


# --- Regression on /clients with enriched fields ---
class TestClientsRegression:
    def test_client_create_with_new_fields(self, client, auth):
        h = auth["headers"]
        payload = {
            "name": "TEST_ClientReg", "contact": "Jane", "email": "j@t.co",
            "phone": "111", "value": 1000, "status": "Prospect",
            "industry": "SaaS", "tags": ["vip"], "website": "https://t.co",
            "company_size": "10-50",
        }
        r = client.post("/api/clients", headers=h, json=payload)
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        r = client.get("/api/clients", headers=h)
        assert r.status_code == 200
        found = next((c for c in r.json() if c["id"] == cid), None)
        assert found is not None
        client.delete(f"/api/clients/{cid}", headers=h)
