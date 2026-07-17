"""Sprint 11 — AI Morning Brief tests."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def demo_client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip(f"Rate limited on demo: {r.text}")
    assert r.status_code == 200, f"demo failed: {r.status_code} {r.text}"
    s.headers.update({"Authorization": f"Bearer {r.json()['accessToken']}"})
    return s


@pytest.fixture(scope="module")
def demo_client_2():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    if r.status_code == 429:
        pytest.skip(f"Rate limited on demo: {r.text}")
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['accessToken']}"})
    return s


def test_morning_brief_shape(demo_client):
    r = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["greeting", "summary", "wins", "risks", "recommendations", "numbers", "what_ai_did"]:
        assert k in d, f"missing key {k}"
    assert isinstance(d["greeting"], str) and d["greeting"]
    for k in ["summary", "wins", "risks", "recommendations", "what_ai_did"]:
        assert isinstance(d[k], list)


def test_morning_brief_numbers(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    n = d["numbers"]
    for k in ["revenue", "pipeline", "hours_saved", "business_health", "clients_active", "deals_closing"]:
        assert k in n
        assert isinstance(n[k], (int, float))


def test_morning_brief_matches_executive(demo_client):
    mb = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    ex = demo_client.get(f"{BASE_URL}/api/dashboard/executive").json()
    assert mb["numbers"]["pipeline"] == ex["kpi_cards"]["pipeline"]["value"]
    assert mb["numbers"]["revenue"] == ex["kpi_cards"]["revenue_month"]["value"]
    assert mb["numbers"]["hours_saved"] == ex["kpi_cards"]["hours_saved"]["value"]
    assert mb["numbers"]["business_health"] == ex["health"]["score"]


def test_summary_never_empty(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    assert len(d["summary"]) >= 1
    for s in d["summary"]:
        assert "icon" in s and "text" in s and s["text"]


def test_wins_shape(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    for w in d["wins"]:
        for k in ["icon", "title", "detail"]:
            assert k in w
    assert len(d["wins"]) <= 6


def test_risks_shape(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    for r in d["risks"]:
        for k in ["icon", "severity", "title", "detail"]:
            assert k in r
    assert len(d["risks"]) <= 6


def test_recommendations_shape(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    assert len(d["recommendations"]) <= 4
    for it in d["recommendations"]:
        for k in ["title", "priority", "confidence", "action", "icon"]:
            assert k in it
        # revenue_impact must be present (from _enrich_impact)
        assert "revenue_impact" in it


def test_what_ai_did_capped(demo_client):
    d = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    assert len(d["what_ai_did"]) <= 8


def test_org_isolation(demo_client, demo_client_2):
    a = demo_client.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    b = demo_client_2.get(f"{BASE_URL}/api/dashboard/morning-brief").json()
    a_ids = {x.get("id") for x in a["what_ai_did"] if x.get("id")}
    b_ids = {x.get("id") for x in b["what_ai_did"] if x.get("id")}
    assert not (a_ids & b_ids), "cross-tenant leakage"


def test_no_regressions(demo_client):
    for path in [
        "/api/dashboard/executive", "/api/dashboard/summary", "/api/opportunities",
        "/api/crm/sales-metrics", "/api/automation/summary", "/api/memory/stats",
    ]:
        r = demo_client.get(f"{BASE_URL}{path}", timeout=20)
        assert r.status_code == 200, f"{path} => {r.status_code}"
