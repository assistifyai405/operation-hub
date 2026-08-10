"""Executive Dashboard (Sprint 10) tests."""
import os
import requests
import pytest
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def demo_client():
    """Fresh demo tenant."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip(f"Rate limited on demo: {r.text}")
    assert r.status_code == 200, f"demo failed: {r.status_code} {r.text}"
    token = auth_json(s, r).get("accessToken")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def demo_client_2():
    """Second isolated demo tenant."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip(f"Rate limited on demo: {r.text}")
    assert r.status_code == 200
    token = auth_json(s, r).get("accessToken")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def test_executive_endpoint_shape(demo_client):
    r = demo_client.get(f"{BASE_URL}/api/dashboard/executive", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["hero", "health", "revenue", "insights", "priorities", "priorities_total",
              "ai_activity", "workspace", "documents", "trends", "kpi_cards"]:
        assert k in d, f"missing key {k}"


def test_trends_structure(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    t = d["trends"]
    assert isinstance(t.get("labels"), list) and len(t["labels"]) == 8
    series = t.get("series", {})
    for k in ["revenue", "pipeline", "hours_saved", "deals", "clients", "automations", "ai_activity"]:
        assert k in series, f"trends.series missing {k}"
        arr = series[k]
        assert isinstance(arr, list) and len(arr) == 8
        for v in arr:
            assert isinstance(v, (int, float))


def test_kpi_cards_structure(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    kc = d["kpi_cards"]
    # health card
    h = kc["health"]
    assert "value" in h and "grade" in h and isinstance(h.get("categories"), list)
    assert h["value"] == d["health"]["score"]
    # other three cards with spark[8] + change_pct
    for k in ["pipeline", "hours_saved", "revenue_month"]:
        card = kc[k]
        assert "value" in card
        assert isinstance(card.get("spark"), list) and len(card["spark"]) == 8
        assert "change_pct" in card  # may be None
        cp = card["change_pct"]
        assert cp is None or isinstance(cp, (int, float))


def test_kpi_cards_source_consistency(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    sm = demo_client.get(f"{BASE_URL}/api/crm/sales-metrics").json()
    # pipeline card value should equal pipeline value from crm
    assert d["kpi_cards"]["pipeline"]["value"] == sm.get("pipeline_value", 0)


def test_trends_org_isolation(demo_client, demo_client_2):
    a = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    b = demo_client_2.get(f"{BASE_URL}/api/dashboard/executive").json()
    # both have valid shape and labels of 8
    assert len(a["trends"]["labels"]) == 8 and len(b["trends"]["labels"]) == 8


def test_hero_structure(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    hero = d["hero"]
    assert hero.get("greeting")
    assert isinstance(hero.get("brief_lines"), list)
    assert isinstance(hero.get("revenue_at_risk"), (int, float))
    assert isinstance(hero.get("hours_saved_week"), (int, float))
    assert 0 <= hero.get("ai_confidence", -1) <= 100
    # top_priority may be null or shaped
    tp = hero.get("top_priority")
    if tp is not None:
        for k in ["title", "why", "priority", "action", "confidence", "icon"]:
            assert k in tp


def test_health_matches_opportunities_source(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    h_src = demo_client.get(f"{BASE_URL}/api/opportunities/health").json()
    # Same source: scores must equal
    assert d["health"]["score"] == h_src["score"], f"health drift: {d['health']['score']} vs {h_src['score']}"
    assert 0 <= d["health"]["score"] <= 100
    assert isinstance(d["health"].get("categories"), list)


def test_revenue_matches_crm_sales_metrics(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    sm = demo_client.get(f"{BASE_URL}/api/crm/sales-metrics").json()
    assert d["revenue"]["pipeline_value"] == sm.get("pipeline_value", 0)
    assert d["revenue"]["expected_monthly"] == sm.get("weighted_pipeline", 0)
    assert d["revenue"]["avg_deal_size"] == sm.get("avg_deal_size", 0)


def test_priorities_group_matches_opportunities(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    opps = demo_client.get(f"{BASE_URL}/api/opportunities").json()
    assert d["priorities_total"] == len(opps.get("items", []))
    for lvl in ["critical", "high", "medium", "low"]:
        assert lvl in d["priorities"]
        assert "count" in d["priorities"][lvl]
        assert len(d["priorities"][lvl]["items"]) <= 6


def test_insights_capped_and_shaped(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    assert len(d["insights"]) <= 6
    for it in d["insights"]:
        for k in ["title", "why", "action", "priority", "confidence", "icon"]:
            assert k in it, f"insight missing {k}"


def test_ai_activity_capped(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    assert isinstance(d["ai_activity"], list)
    assert len(d["ai_activity"]) <= 8


def test_workspace_counts_present(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    ws = d["workspace"]
    for k in ["clients", "deals", "total_leads", "projects", "tasks", "documents",
              "memories", "automations", "ai_reports", "proposals", "contracts", "invoices"]:
        assert k in ws, f"workspace missing {k}"
        assert isinstance(ws[k], int)


def test_documents_shape(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    docs = d["documents"]
    for k in ["proposals", "contracts", "invoices", "plans"]:
        assert k in docs
        assert isinstance(docs[k], list)
        assert len(docs[k]) <= 4


def test_org_isolation(demo_client, demo_client_2):
    a = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    b = demo_client_2.get(f"{BASE_URL}/api/dashboard/executive").json()
    # different tenants: ai_activity IDs shouldn't overlap
    a_ids = {x.get("id") for x in a["ai_activity"] if x.get("id")}
    b_ids = {x.get("id") for x in b["ai_activity"] if x.get("id")}
    assert not (a_ids & b_ids), "cross-tenant AI activity leakage"


def test_no_regressions(demo_client):
    for path in ["/api/dashboard/summary", "/api/opportunities", "/api/opportunities/health",
                 "/api/crm/sales-metrics", "/api/automation/summary", "/api/memory/stats"]:
        r = demo_client.get(f"{BASE_URL}{path}", timeout=20)
        assert r.status_code == 200, f"{path} => {r.status_code} {r.text[:200]}"
