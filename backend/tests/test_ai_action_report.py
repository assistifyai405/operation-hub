"""AI Action Report feature — TestClient (soften LLM generate)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

EXPECTED_TIME_SAVED = {"proposal": 23, "contract": 12, "invoice": 6, "plan": 15}
EXPECTED_TYPE_LABEL = {
    "proposal": "Proposal", "contract": "Contract",
    "invoice": "Invoice", "plan": "Project Plan",
}


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="AI Report")
    cr = client.post("/api/clients", headers=a["headers"], json={"name": "Report Client", "email": "r@r.com"})
    pr = client.post("/api/projects", headers=a["headers"], json={
        "name": "Report Project", "client_id": cr.json()["id"], "status": "In Progress",
    })
    a["project_id"] = pr.json()["id"]
    return a


def _assert_report(report, atype):
    assert report is not None, f"missing report for {atype}"
    assert report["type"] == atype
    assert report["type_label"] == EXPECTED_TYPE_LABEL[atype]
    assert report["time_saved"] == EXPECTED_TIME_SAVED[atype]
    assert isinstance(report["confidence"], int)
    assert 88 <= report["confidence"] <= 99
    assert isinstance(report["confidence_note"], str) and len(report["confidence_note"]) > 10
    assert isinstance(report["steps"], list) and len(report["steps"]) >= 4
    assert isinstance(report["why"], list) and 3 <= len(report["why"]) <= 6
    assert isinstance(report["quality"], list) and len(report["quality"]) == 4
    all_text = " ".join(report["steps"] + report["why"] + report["quality"]).lower()
    assert "lorem" not in all_text


class TestAIActionReport:
    def test_proposal_report(self, client, auth):
        r = client.post(f"/api/projects/{auth['project_id']}/proposal/generate", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert "content" in data and "title" in data
        _assert_report(data.get("report"), "proposal")

    def test_contract_report(self, client, auth):
        r = client.post(f"/api/projects/{auth['project_id']}/contract/generate", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert "content" in data
        _assert_report(data.get("report"), "contract")

    def test_invoice_report(self, client, auth):
        r = client.post(f"/api/projects/{auth['project_id']}/invoice/generate", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        _assert_report(data.get("report"), "invoice")

    def test_plan_report(self, client, auth):
        r = client.post(f"/api/projects/{auth['project_id']}/plan/generate", headers=auth["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert "sections" in data
        _assert_report(data.get("report"), "plan")


class TestRegression:
    def test_proposal_save_and_get(self, client, auth):
        pid = auth["project_id"]
        h = auth["headers"]
        # Save without generate if LLM fails
        save = client.post(f"/api/projects/{pid}/proposal", headers=h, json={
            "title": "Manual Proposal", "content": {"executive_summary": "Hello"},
        })
        assert save.status_code in (200, 201), save.text
        got = client.get(f"/api/projects/{pid}/proposal", headers=h)
        assert got.status_code == 200
        assert got.json().get("content")

    def test_plan_persistence(self, client, auth):
        pid = auth["project_id"]
        h = auth["headers"]
        save = client.post(f"/api/projects/{pid}/plans", headers=h, json={
            "sections": {"executive_summary": "Plan", "business_goal": "Grow"},
        })
        assert save.status_code in (200, 201), save.text

    def test_ai_time_saved_endpoint(self, client, auth):
        r = client.get("/api/ai/time-saved", headers=auth["headers"])
        assert r.status_code == 200
        d = r.json()
        assert "lifetime" in d
