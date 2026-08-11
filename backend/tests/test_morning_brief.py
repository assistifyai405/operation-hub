"""Sprint 11 — AI Morning Brief tests (TestClient)."""

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
    a = register_user(client, company="Morning A")
    client.post("/api/clients", headers=a["headers"], json={"name": "MB Client", "email": "mb@m.com", "value": 1000})
    client.post("/api/crm/leads", headers=a["headers"], json={"title": "MB Lead", "stage": "New", "value": 8000})
    return a


@pytest.fixture
def auth2(client):
    return register_user(client, company="Morning B")


def test_morning_brief_shape(client, auth):
    r = client.get("/api/dashboard/morning-brief", headers=auth["headers"])
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["greeting", "summary", "wins", "risks", "recommendations", "numbers", "what_ai_did"]:
        assert k in d, f"missing key {k}"
    assert isinstance(d["greeting"], str) and d["greeting"]
    for k in ["summary", "wins", "risks", "recommendations", "what_ai_did"]:
        assert isinstance(d[k], list)


def test_morning_brief_numbers(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    n = d["numbers"]
    for k in ["revenue", "pipeline", "hours_saved", "business_health", "clients_active", "deals_closing"]:
        assert k in n
        assert isinstance(n[k], (int, float))


def test_morning_brief_matches_executive(client, auth):
    mb = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    ex = client.get("/api/dashboard/executive", headers=auth["headers"]).json()
    assert mb["numbers"]["pipeline"] == ex["kpi_cards"]["pipeline"]["value"]
    assert mb["numbers"]["revenue"] == ex["kpi_cards"]["revenue_month"]["value"]
    assert mb["numbers"]["hours_saved"] == ex["kpi_cards"]["hours_saved"]["value"]
    assert mb["numbers"]["business_health"] == ex["health"]["score"]


def test_summary_never_empty(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    assert len(d["summary"]) >= 1
    for s in d["summary"]:
        assert "icon" in s and "text" in s and s["text"]


def test_wins_shape(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    for w in d["wins"]:
        for k in ["icon", "title", "detail"]:
            assert k in w
    assert len(d["wins"]) <= 6


def test_risks_shape(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    for r in d["risks"]:
        for k in ["icon", "severity", "title", "detail"]:
            assert k in r
    assert len(d["risks"]) <= 6


def test_recommendations_shape(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    assert len(d["recommendations"]) <= 4
    for it in d["recommendations"]:
        for k in ["title", "priority", "confidence", "action", "icon"]:
            assert k in it
        assert "revenue_impact" in it


def test_what_ai_did_capped(client, auth):
    d = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    assert len(d["what_ai_did"]) <= 8


def test_org_isolation(client, auth, auth2):
    a = client.get("/api/dashboard/morning-brief", headers=auth["headers"]).json()
    b = client.get("/api/dashboard/morning-brief", headers=auth2["headers"]).json()
    a_ids = {x.get("id") for x in a["what_ai_did"] if x.get("id")}
    b_ids = {x.get("id") for x in b["what_ai_did"] if x.get("id")}
    assert not (a_ids & b_ids), "cross-tenant leakage"


def test_no_regressions(client, auth):
    for path in [
        "/api/dashboard/executive", "/api/dashboard/summary", "/api/opportunities",
        "/api/crm/sales-metrics", "/api/automation/summary", "/api/memory/stats",
    ]:
        r = client.get(path, headers=auth["headers"])
        assert r.status_code == 200, f"{path} => {r.status_code}"
