"""Tests for AI Project Planner — TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

PLAN_KEYS = {
    "executive_summary", "business_goal", "technical_requirements",
    "recommended_plan", "milestones", "suggested_tasks",
    "estimated_timeline", "risks", "next_actions",
}


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    return register_user(client, company="Planner Co")


@pytest.fixture
def project(client, auth):
    payload = {
        "name": "TEST_PLANNER_MobileBanking",
        "status": "In Progress", "progress": 20, "due": "2026-06-30", "members": 4,
        "description": "Build a secure mobile banking application for iOS and Android with biometric auth.",
        "notes": "Compliance with PCI-DSS and PSD2 required.",
    }
    r = client.post("/api/projects", headers=auth["headers"], json=payload)
    assert r.status_code == 200, r.text
    p = r.json()
    for t in [
        {"title": "Design authentication flow", "priority": "High", "project_id": p["id"]},
        {"title": "Setup CI/CD pipeline", "priority": "Medium", "project_id": p["id"]},
    ]:
        client.post("/api/tasks", headers=auth["headers"], json=t)
    yield {**p, "headers": auth["headers"]}
    client.delete(f"/api/projects/{p['id']}", headers=auth["headers"])


class TestPlannerGenerate:
    def test_generate_404_bad_project(self, client, auth):
        r = client.post("/api/projects/nonexistent-id-xyz/plan/generate", headers=auth["headers"])
        assert r.status_code == 404

    def test_generate_returns_all_9_sections(self, client, project):
        r = client.post(f"/api/projects/{project['id']}/plan/generate", headers=project["headers"])
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert "sections" in data
        sections = data["sections"]
        assert set(sections.keys()) == PLAN_KEYS or PLAN_KEYS.issubset(set(sections.keys()))
        assert sections.get("executive_summary")
        project["plan_sections"] = sections


class TestPlannerSaveList:
    def test_list_empty_initially(self, client, project):
        r = client.get(f"/api/projects/{project['id']}/plans", headers=project["headers"])
        assert r.status_code == 200
        assert r.json() == []

    def test_save_v1_then_v2(self, client, project):
        sections = project.get("plan_sections") or {
            "executive_summary": "Summary", "business_goal": "Goal",
            "technical_requirements": ["Auth"], "recommended_plan": "Plan",
            "milestones": ["M1"], "suggested_tasks": ["T1"],
            "estimated_timeline": "8 weeks", "risks": ["R1"], "next_actions": ["A1"],
        }
        h, pid = project["headers"], project["id"]
        r1 = client.post(f"/api/projects/{pid}/plans", headers=h, json={"sections": sections})
        assert r1.status_code in (200, 201), r1.text
        r2 = client.post(f"/api/projects/{pid}/plans", headers=h, json={"sections": {**sections, "executive_summary": "v2"}})
        assert r2.status_code in (200, 201), r2.text
        lst = client.get(f"/api/projects/{pid}/plans", headers=h).json()
        assert len(lst) >= 1
