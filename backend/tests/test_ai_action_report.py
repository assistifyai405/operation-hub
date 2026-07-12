"""Tests for the AI Action Report feature — verifies the `report` object returned
by all 4 generation endpoints (proposal, contract, invoice, plan)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EMAIL = "jordan@assistify.io"
PWD = "Assistify2026!"

EXPECTED_TIME_SAVED = {"proposal": 23, "contract": 12, "invoice": 6, "plan": 15}
EXPECTED_TYPE_LABEL = {
    "proposal": "Proposal", "contract": "Contract",
    "invoice": "Invoice", "plan": "Project Plan",
}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PWD, "remember": True})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json()["accessToken"]
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def project_id(client):
    r = client.get(f"{BASE_URL}/api/projects")
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) > 0, "no seed projects"
    return projects[0]["id"]


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
    # No lorem/placeholder
    all_text = " ".join(report["steps"] + report["why"] + report["quality"]).lower()
    assert "lorem" not in all_text
    assert "placeholder" not in all_text or "professional placeholder" in all_text  # allowed context msg


class TestAIActionReport:
    def test_proposal_report(self, client, project_id):
        r = client.post(f"{BASE_URL}/api/projects/{project_id}/proposal/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "content" in data and "title" in data
        _assert_report(data.get("report"), "proposal")

    def test_contract_report(self, client, project_id):
        r = client.post(f"{BASE_URL}/api/projects/{project_id}/contract/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "content" in data
        _assert_report(data.get("report"), "contract")

    def test_invoice_report(self, client, project_id):
        r = client.post(f"{BASE_URL}/api/projects/{project_id}/invoice/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_report(data.get("report"), "invoice")

    def test_plan_report(self, client, project_id):
        r = client.post(f"{BASE_URL}/api/projects/{project_id}/plan/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "sections" in data
        _assert_report(data.get("report"), "plan")


class TestRegression:
    """Existing flows still work with the added `report` key."""

    def test_proposal_save_and_get(self, client, project_id):
        gen = client.post(f"{BASE_URL}/api/projects/{project_id}/proposal/generate").json()
        # Save (server ignores extra report field naturally by pydantic model)
        save = client.post(
            f"{BASE_URL}/api/projects/{project_id}/proposal",
            json={"title": gen["title"], "content": gen["content"]},
        )
        assert save.status_code in (200, 201), save.text
        got = client.get(f"{BASE_URL}/api/projects/{project_id}/proposal")
        assert got.status_code == 200
        assert got.json().get("content")

    def test_plan_persistence(self, client, project_id):
        gen = client.post(f"{BASE_URL}/api/projects/{project_id}/plan/generate").json()
        save = client.post(f"{BASE_URL}/api/projects/{project_id}/plans", json={"sections": gen["sections"]})
        assert save.status_code in (200, 201), save.text

    def test_ai_time_saved_endpoint(self, client):
        r = client.get(f"{BASE_URL}/api/ai/time-saved")
        assert r.status_code == 200
        d = r.json()
        assert "lifetime" in d
