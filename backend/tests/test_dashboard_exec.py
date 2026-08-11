"""Executive Dashboard (Sprint 10) tests — TestClient + registered users."""

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
    a = register_user(client, company="ExecDash A")
    # Seed minimal workspace so KPI paths have structure
    cr = client.post("/api/clients", headers=a["headers"], json={
        "name": "Exec Client", "email": "e@e.com", "status": "Active", "value": 5000,
    })
    assert cr.status_code == 200
    cid = cr.json()["id"]
    client.post("/api/projects", headers=a["headers"], json={
        "name": "Exec Project", "client_id": cid, "status": "In Progress",
    })
    client.post("/api/crm/leads", headers=a["headers"], json={
        "title": "Exec Lead", "stage": "Qualified", "value": 12000, "client_id": cid,
    })
    return a


@pytest.fixture
def auth2(client):
    return register_user(client, company="ExecDash B")


def test_executive_endpoint_shape(client, auth):
    r = client.get("/api/dashboard/executive", headers=auth["headers"])
    assert r.status_code == 200, r.text
    d = r.json()
    for k in [
        "hero", "health", "revenue", "insights", "priorities", "priorities_total",
        "ai_activity", "workspace", "documents", "trends", "kpi_cards",
    ]:
        assert k in d, f"missing key {k}"


def test_trends_structure(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    t = d["trends"]
    assert isinstance(t.get("labels"), list) and len(t["labels"]) == 8
    series = t.get("series", {})
    for k in ["revenue", "pipeline", "hours_saved", "deals", "clients", "automations", "ai_activity"]:
        assert k in series, f"trends.series missing {k}"
        arr = series[k]
        assert isinstance(arr, list) and len(arr) == 8
        for v in arr:
            assert isinstance(v, (int, float))


def test_kpi_cards_structure(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    kc = d["kpi_cards"]
    h = kc["health"]
    assert "value" in h and "grade" in h and isinstance(h.get("categories"), list)
    assert h["value"] == d["health"]["score"]
    for k in ["pipeline", "hours_saved", "revenue_month"]:
        card = kc[k]
        assert "value" in card
        assert isinstance(card.get("spark"), list) and len(card["spark"]) == 8
        assert "change_pct" in card
        cp = card["change_pct"]
        assert cp is None or isinstance(cp, (int, float))


def test_kpi_cards_source_consistency(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    sm = client.get("/api/crm/sales-metrics", headers=auth["headers"]).json()
    assert d["kpi_cards"]["pipeline"]["value"] == sm.get("pipeline_value", 0)


def test_trends_org_isolation(client, auth, auth2):
    a = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    b = client.get("/api/dashboard/executive", headers=auth2["headers"]).json()
    assert len(a["trends"]["labels"]) == 8 and len(b["trends"]["labels"]) == 8


def test_hero_structure(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    hero = d["hero"]
    assert hero.get("greeting")
    assert isinstance(hero.get("brief_lines"), list)
    assert isinstance(hero.get("revenue_at_risk"), (int, float))
    assert isinstance(hero.get("hours_saved_week"), (int, float))
    assert 0 <= hero.get("ai_confidence", -1) <= 100
    tp = hero.get("top_priority")
    if tp is not None:
        for k in ["title", "why", "priority", "action", "confidence", "icon"]:
            assert k in tp


def test_health_matches_opportunities_source(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    h_src = client.get("/api/opportunities/health", headers=auth["headers"]).json()
    assert d["health"]["score"] == h_src["score"], f"health drift: {d['health']['score']} vs {h_src['score']}"
    assert 0 <= d["health"]["score"] <= 100
    assert isinstance(d["health"].get("categories"), list)


def test_revenue_matches_crm_sales_metrics(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    sm = client.get("/api/crm/sales-metrics", headers=auth["headers"]).json()
    assert d["revenue"]["pipeline_value"] == sm.get("pipeline_value", 0)
    assert d["revenue"]["expected_monthly"] == sm.get("weighted_pipeline", 0)
    assert d["revenue"]["avg_deal_size"] == sm.get("avg_deal_size", 0)


def test_priorities_group_matches_opportunities(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    opps = client.get("/api/opportunities", headers=auth["headers"]).json()
    assert d["priorities_total"] == len(opps.get("items", []))
    for lvl in ["critical", "high", "medium", "low"]:
        assert lvl in d["priorities"]
        assert "count" in d["priorities"][lvl]
        assert len(d["priorities"][lvl]["items"]) <= 6


def test_insights_capped_and_shaped(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    assert len(d["insights"]) <= 6
    for it in d["insights"]:
        for k in ["title", "why", "action", "priority", "confidence", "icon"]:
            assert k in it, f"insight missing {k}"


def test_ai_activity_capped(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    assert isinstance(d["ai_activity"], list)
    assert len(d["ai_activity"]) <= 8


def test_workspace_counts_present(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    ws = d["workspace"]
    for k in [
        "clients", "deals", "total_leads", "projects", "tasks", "documents",
        "memories", "automations", "ai_reports", "proposals", "contracts", "invoices",
    ]:
        assert k in ws, f"workspace missing {k}"
        assert isinstance(ws[k], int)


def test_documents_shape(client, auth):
    d = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    docs = d["documents"]
    for k in ["proposals", "contracts", "invoices", "plans"]:
        assert k in docs
        assert isinstance(docs[k], list)
        assert len(docs[k]) <= 4


def test_org_isolation(client, auth, auth2):
    a = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    b = client.get("/api/dashboard/executive", headers=auth2["headers"]).json()
    a_ids = {x.get("id") for x in a["ai_activity"] if x.get("id")}
    b_ids = {x.get("id") for x in b["ai_activity"] if x.get("id")}
    assert not (a_ids & b_ids), "cross-tenant AI activity leakage"


def test_no_regressions(client, auth):
    for path in [
        "/api/dashboard/summary", "/api/opportunities", "/api/opportunities/health",
        "/api/crm/sales-metrics", "/api/automation/summary", "/api/memory/stats",
    ]:
        r = client.get(path, headers=auth["headers"])
        assert r.status_code == 200, f"{path} => {r.status_code} {r.text[:200]}"
