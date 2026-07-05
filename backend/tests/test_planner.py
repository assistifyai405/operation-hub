"""Tests for AI Project Planner feature."""
import os
import time
import requests
import pytest

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if os.environ.get('REACT_APP_BACKEND_URL') else None
if not BASE_URL:
    # fallback to frontend .env for tests running from backend context
    from pathlib import Path
    envp = Path('/app/frontend/.env')
    for line in envp.read_text().splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip()
            break

API = f"{BASE_URL}/api"

PLAN_KEYS = {
    "executive_summary", "business_goal", "technical_requirements",
    "recommended_plan", "milestones", "suggested_tasks",
    "estimated_timeline", "risks", "next_actions",
}


@pytest.fixture(scope="module")
def project():
    """Create a project with distinctive context for planner tests."""
    payload = {
        "name": "TEST_PLANNER_MobileBanking",
        "status": "In Progress", "progress": 20, "due": "2026-06-30", "members": 4,
        "description": "Build a secure mobile banking application for iOS and Android with biometric auth, real-time balance updates, and instant P2P transfers.",
        "notes": "Compliance with PCI-DSS and PSD2 required. Team includes 2 iOS devs and 2 Android devs.",
    }
    r = requests.post(f"{API}/projects", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json()
    # Add some tasks for context
    for t in [
        {"title": "Design authentication flow", "priority": "High", "project_id": p["id"]},
        {"title": "Setup CI/CD pipeline", "priority": "Medium", "project_id": p["id"]},
    ]:
        requests.post(f"{API}/tasks", json=t, timeout=15)
    yield p
    # cleanup
    requests.delete(f"{API}/projects/{p['id']}", timeout=15)


class TestPlannerGenerate:
    def test_generate_404_bad_project(self):
        r = requests.post(f"{API}/projects/nonexistent-id-xyz/plan/generate", timeout=60)
        assert r.status_code == 404

    def test_generate_returns_all_9_sections(self, project):
        r = requests.post(f"{API}/projects/{project['id']}/plan/generate", timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "sections" in data
        sections = data["sections"]
        assert set(sections.keys()) == PLAN_KEYS, f"Missing keys: {PLAN_KEYS - set(sections.keys())}"
        # Non-empty content check
        assert sections["executive_summary"], "executive_summary is empty"
        assert isinstance(sections["technical_requirements"], list)
        assert len(sections["technical_requirements"]) > 0
        # Context-awareness: check that response references the domain
        blob = str(sections).lower()
        assert any(w in blob for w in ["bank", "mobile", "biometric", "auth", "pci", "psd2", "p2p"]), \
            f"Plan does not reference project context: {blob[:400]}"
        # Stash for later
        pytest.plan_sections = sections


class TestPlannerSaveList:
    def test_list_empty_initially(self, project):
        r = requests.get(f"{API}/projects/{project['id']}/plans", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_save_v1_then_v2(self, project):
        s = getattr(pytest, "plan_sections", None) or {
            "executive_summary": "Summary", "business_goal": "Goal",
            "technical_requirements": ["req1"], "recommended_plan": ["p1"],
            "milestones": ["m1"], "suggested_tasks": ["High: task"],
            "estimated_timeline": "3 months", "risks": ["r1"], "next_actions": ["a1"],
        }
        r1 = requests.post(f"{API}/projects/{project['id']}/plans", json={"sections": s}, timeout=15)
        assert r1.status_code == 200, r1.text
        v1 = r1.json()
        assert v1["version"] == 1
        assert v1["project_id"] == project["id"]
        assert "created_at" in v1
        # edit and save v2
        s2 = {**s, "executive_summary": "EDITED_SUMMARY_XYZ"}
        r2 = requests.post(f"{API}/projects/{project['id']}/plans", json={"sections": s2}, timeout=15)
        assert r2.status_code == 200
        v2 = r2.json()
        assert v2["version"] == 2

        # list newest-first
        lst = requests.get(f"{API}/projects/{project['id']}/plans", timeout=15).json()
        assert len(lst) == 2
        assert lst[0]["version"] == 2
        assert lst[1]["version"] == 1
        assert lst[0]["sections"]["executive_summary"] == "EDITED_SUMMARY_XYZ"

    def test_activity_logged(self, project):
        acts = requests.get(f"{API}/activities?project_id={project['id']}", timeout=15).json()
        plan_acts = [a for a in acts if a["type"] == "plan_generated"]
        assert len(plan_acts) >= 2


class TestPlannerCascade:
    def test_delete_project_cascades_plans(self):
        # create a project, save a plan, delete project, verify plans gone
        r = requests.post(f"{API}/projects", json={"name": "TEST_PLANNER_CASCADE"}, timeout=15)
        pid = r.json()["id"]
        empty_sections = {k: ("x" if k in ("executive_summary", "business_goal", "estimated_timeline") else ["x"]) for k in PLAN_KEYS}
        requests.post(f"{API}/projects/{pid}/plans", json={"sections": empty_sections}, timeout=15)
        pre = requests.get(f"{API}/projects/{pid}/plans", timeout=15).json()
        assert len(pre) == 1
        # delete
        d = requests.delete(f"{API}/projects/{pid}", timeout=15)
        assert d.status_code == 200
        # Now project is gone. Verify plans collection has no docs for it by re-creating same id impossible; check list still returns 200 empty for a fresh project.
        # We check directly: create a new project — its plans list must be empty (proves cascade for previous did not leak to new project).
        # Better: query the DB — but via API, listing plans for the deleted project id should return [] (endpoint doesn't verify existence).
        after = requests.get(f"{API}/projects/{pid}/plans", timeout=15).json()
        assert after == []
