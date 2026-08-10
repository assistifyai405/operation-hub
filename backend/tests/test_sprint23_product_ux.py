"""Sprint 23 — product experience, onboarding checklist, empty-workspace dashboard."""
import os
import uuid
import requests
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")


def _register():
    email = f"s23+{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "firstName": "S23",
            "lastName": "User",
            "email": email,
            "password": "NewPass123!",
            "company": "Sprint23 Co",
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = auth_json(None, r)
    return email, data["accessToken"], data.get("user", {})


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_new_user_workspace_empty_no_fake_metrics():
    _, tok, user = _register()
    assert user.get("onboardingCompleted") is False
    r = requests.get(f"{BASE_URL}/api/dashboard/executive", headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("workspace_empty") is True
    # No invented clients / pipeline revenue in empty workspace
    hero = body.get("hero") or {}
    assert (hero.get("revenue_at_risk") or 0) == 0


def test_checklist_real_data_progress():
    _, tok, _ = _register()
    j = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    assert j["percent"] == 0
    keys = {i["key"] for i in j["items"]}
    assert keys == {"profile", "client", "project", "task", "copilot", "agents"}

    requests.post(
        f"{BASE_URL}/api/clients",
        headers=_h(tok),
        json={"name": "S23 Client", "contact": "A", "email": "a@a.com"},
    )
    requests.post(
        f"{BASE_URL}/api/projects",
        headers=_h(tok),
        json={"name": "S23 Project", "status": "Active"},
    )
    # find project id
    projects = requests.get(f"{BASE_URL}/api/projects", headers=_h(tok)).json()
    items = projects if isinstance(projects, list) else projects.get("items") or projects.get("projects") or []
    pid = items[0]["id"] if items else None
    if pid:
        requests.post(
            f"{BASE_URL}/api/tasks",
            headers=_h(tok),
            json={"title": "S23 Task", "project_id": pid, "priority": "Medium"},
        )
    requests.post(f"{BASE_URL}/api/onboarding/flag", headers=_h(tok), json={"key": "copilot"})
    j2 = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    st = {i["key"]: i["done"] for i in j2["items"]}
    assert st["client"] is True
    assert st["project"] is True
    assert st["copilot"] is True
    assert j2["done"] >= 3


def test_skip_onboarding_marks_complete_for_returning_user():
    _, tok, _ = _register()
    requests.post(
        f"{BASE_URL}/api/onboarding/state",
        headers=_h(tok),
        json={"step": 0, "data": {}, "completed": True},
    )
    requests.post(f"{BASE_URL}/api/onboarding/complete", headers=_h(tok))
    st = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert st["completed"] is True
    me = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(tok)).json()
    assert me.get("onboardingCompleted") is True


def test_cookie_auth_still_required_for_checklist():
    assert requests.get(f"{BASE_URL}/api/onboarding/checklist").status_code == 401
