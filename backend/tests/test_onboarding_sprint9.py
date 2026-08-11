"""Sprint 9 WOW Onboarding — TestClient.

Demo seed/login intentionally disabled: seed-demo/demo endpoints assert 401/403/404.
Checklist coverage overlaps sprint23 but keeps wizard state/profile/isolation coverage.
"""

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


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- state / restart / flag ----------

def test_state_defaults_and_persistence(client):
    a = register_user(client, company="OnbCo9")
    assert a["user"].get("onboardingCompleted") is False
    r = client.get("/api/onboarding/state", headers=a["headers"])
    assert r.status_code == 200
    j = r.json()
    assert j["step"] == 0 and j["completed"] is False
    assert j["demo_seeded"] is False
    assert isinstance(j["flags"], dict)

    r = client.post("/api/onboarding/state", headers=a["headers"],
                    json={"step": 3, "data": {"company_name": "TEST_Co"}})
    assert r.status_code == 200 and r.json()["ok"] is True
    j2 = client.get("/api/onboarding/state", headers=a["headers"]).json()
    assert j2["step"] == 3 and j2["data"]["company_name"] == "TEST_Co"


def test_flag_sets_and_reflects_in_state(client):
    a = register_user(client, company="FlagCo")
    r = client.post("/api/onboarding/flag", headers=a["headers"], json={"key": "workspace"})
    assert r.status_code == 200
    j = client.get("/api/onboarding/state", headers=a["headers"]).json()
    assert j["flags"].get("workspace") is True


def test_restart_resets_state_and_completed(client):
    a = register_user(client, company="RestartCo")
    client.post("/api/onboarding/state", headers=a["headers"],
                json={"step": 5, "data": {"x": 1}, "completed": True})
    j = client.get("/api/onboarding/state", headers=a["headers"]).json()
    assert j["completed"] is True
    r = client.post("/api/onboarding/restart", headers=a["headers"])
    assert r.status_code == 200
    j = client.get("/api/onboarding/state", headers=a["headers"]).json()
    assert j["completed"] is False and j["step"] == 0 and j["data"] == {}


def test_state_requires_auth(client):
    client.cookies.clear()
    assert client.get("/api/onboarding/state").status_code == 401
    assert client.post("/api/onboarding/restart").status_code == 401


# ---------- website analysis ----------

def test_analyze_website_bad_url_graceful(client):
    a = register_user(client, company="WebBad")
    r = client.post("/api/onboarding/analyze-website",
                    headers=a["headers"], json={"url": "not-a-real-domain-xyzzy-999.tld"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is False and "reason" in j and j["fields"] == {}


def test_analyze_website_real_url(client):
    a = register_user(client, company="WebReal")
    r = client.post("/api/onboarding/analyze-website",
                    headers=a["headers"], json={"url": "example.com"})
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    if r.status_code == 200:
        j = r.json()
        assert "ok" in j and "fields" in j


def test_analyze_website_empty_url_400(client):
    a = register_user(client, company="WebEmpty")
    r = client.post("/api/onboarding/analyze-website", headers=a["headers"], json={"url": ""})
    assert r.status_code == 400


# ---------- profile ----------

@pytest.fixture
def profile_ctx(client):
    a = register_user(client, company="Aster Studio")
    payload = {
        "company_name": "TEST_Aster Studio", "industry": "Design agency",
        "website": "https://aster.example", "employees": "1-5",
        "main_services": "Branding, Web design, Motion",
        "target_customers": "Early stage startups",
        "language": "en", "country": "US",
    }
    r = client.post("/api/onboarding/profile", headers=a["headers"], json=payload)
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    return {"auth": a, "resp": r.json() if r.status_code == 200 else None, "status": r.status_code}


def test_profile_returns_sections_memories_and_automations(profile_ctx):
    if profile_ctx["status"] != 200:
        pytest.skip("profile generation LLM unavailable (sanitized error)")
    j = profile_ctx["resp"]
    assert j["ok"] is True
    s = j["sections"]
    for k in ("company_summary", "industry", "services",
              "communication_style", "proposal_style", "brand_voice", "writing_style"):
        assert k in s, f"missing {k}"
    assert j["memories_seeded"] >= 1
    assert isinstance(j["automations"], list) and len(j["automations"]) == 5
    for a in j["automations"]:
        assert "key" in a and "name" in a


def test_profile_memories_appear_in_memory_list(client, profile_ctx):
    if profile_ctx["status"] != 200:
        pytest.skip("profile generation LLM unavailable")
    tok = profile_ctx["auth"]["token"]
    r = client.get("/api/memory/memories", headers=_h(tok))
    assert r.status_code == 200
    mems = r.json()
    if isinstance(mems, dict):
        mems = mems.get("memories") or mems.get("items") or []
    sources = [m.get("source") for m in mems]
    assert any(s == "Onboarding" for s in sources), f"no Onboarding-sourced memory, sources={sources}"


def test_profile_put_updates_sections(client, profile_ctx):
    tok = profile_ctx["auth"]["token"]
    new = {
        "sections": {
            "company_summary": "TEST_updated summary", "industry": "Design",
            "services": ["Branding"], "communication_style": "Warm",
            "proposal_style": "Concise", "brand_voice": "Confident",
            "writing_style": "Scannable",
        }
    }
    r = client.put("/api/onboarding/profile", headers=_h(tok), json=new)
    assert r.status_code == 200 and r.json()["ok"] is True


# ---------- demo workspace intentionally disabled ----------

def test_seed_demo_disabled(client):
    a = register_user(client, company="SeedOff")
    r1 = client.post("/api/onboarding/seed-demo", headers=a["headers"])
    assert r1.status_code in (401, 403, 404), r1.text

    st = client.get("/api/onboarding/demo-status", headers=a["headers"])
    assert st.status_code == 200
    body = st.json()
    assert body.get("has_demo") is False or body.get("counts", {}).get("clients", 0) == 0

    r = client.delete("/api/onboarding/demo-data", headers=a["headers"])
    assert r.status_code in (200, 401, 403, 404)


def test_clear_demo_preserves_onboarding_memories(client):
    a = register_user(client, company="PreserveMem")
    r = client.post("/api/onboarding/profile", headers=a["headers"], json={
        "company_name": "TEST_Preserve", "industry": "Test", "main_services": "A, B, C",
    })
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    # seed-demo disabled — still exercise delete path
    client.post("/api/onboarding/seed-demo", headers=a["headers"])
    client.delete("/api/onboarding/demo-data", headers=a["headers"])
    if r.status_code == 200:
        mems = client.get("/api/memory/memories", headers=a["headers"]).json()
        if isinstance(mems, dict):
            mems = mems.get("memories") or mems.get("items") or []
        assert any(m.get("source") == "Onboarding" for m in mems), "Onboarding memories wiped!"


# ---------- checklist ----------

def test_checklist_shape_for_new_user(client):
    a = register_user(client, company="CheckShape")
    r = client.get("/api/onboarding/checklist", headers=a["headers"])
    assert r.status_code == 200
    j = r.json()
    assert j["total"] == 6 and j["done"] == 0 and j["percent"] == 0
    keys = [i["key"] for i in j["items"]]
    assert set(keys) == {"profile", "client", "project", "task", "copilot", "agents"}
    for i in j["items"]:
        assert i["done"] is False and "to" in i and "label" in i
    assert j.get("dismissed") is False
    assert "Assistify" in (j.get("title") or "")


def test_checklist_reflects_flags_and_profile(client):
    a = register_user(client, company="CheckFlags")
    client.post("/api/onboarding/flag", headers=a["headers"], json={"key": "copilot"})
    client.post("/api/onboarding/flag", headers=a["headers"], json={"key": "agents"})
    j = client.get("/api/onboarding/checklist", headers=a["headers"]).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["copilot"] is True and st["agents"] is True
    assert j["done"] >= 2


def test_checklist_client_counts_only_non_demo(client):
    a = register_user(client, company="CheckClient")
    # seed-demo disabled — checklist still false until real client
    client.post("/api/onboarding/seed-demo", headers=a["headers"])
    j = client.get("/api/onboarding/checklist", headers=a["headers"]).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["client"] is False
    client.post("/api/clients", headers=a["headers"],
                json={"name": "TEST_Real Client", "contact": "R", "email": "r@r.com", "phone": "1"})
    j = client.get("/api/onboarding/checklist", headers=a["headers"]).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["client"] is True


def test_checklist_dismiss_persists(client):
    a = register_user(client, company="DismissCo")
    r = client.post("/api/onboarding/checklist/dismiss", headers=a["headers"])
    assert r.status_code == 200
    j = client.get("/api/onboarding/checklist", headers=a["headers"]).json()
    assert j.get("dismissed") is True


def test_onboarding_primary_goal_persists_on_state(client):
    a = register_user(client, company="GoalCo")
    client.post(
        "/api/onboarding/state",
        headers=a["headers"],
        json={"step": 2, "data": {"primaryGoal": "save_time_ai", "company": {"company_name": "GoalCo"}}},
    )
    client.post("/api/onboarding/complete", headers=a["headers"])
    st = client.get("/api/onboarding/state", headers=a["headers"]).json()
    assert st.get("completed") is True
    assert (st.get("data") or {}).get("primaryGoal") == "save_time_ai"


# ---------- org isolation ----------

def test_org_isolation_between_two_new_users(client):
    a = register_user(client, company="IsoA9")
    b = register_user(client, company="IsoB9")
    client.post("/api/onboarding/state", headers=a["headers"],
                json={"step": 4, "data": {"marker": "A"}})
    # seed-demo disabled for A — isolation still holds on state
    client.post("/api/onboarding/seed-demo", headers=a["headers"])
    stA = client.get("/api/onboarding/state", headers=a["headers"]).json()
    stB = client.get("/api/onboarding/state", headers=b["headers"]).json()
    assert stA["step"] == 4 and stB["step"] == 0
    dsB = client.get("/api/onboarding/demo-status", headers=b["headers"]).json()
    assert dsB["has_demo"] is False


# ---------- demo login disabled ----------

def test_demo_login_disabled(client):
    r = client.post("/api/auth/demo")
    assert r.status_code in (401, 403, 404)


def test_regression_core_endpoints_still_200(client):
    a = register_user(client, company="Regress9")
    for path in ("/api/memory/stats", "/api/opportunities", "/api/automation/summary", "/api/crm/sales-metrics"):
        r = client.get(path, headers=a["headers"])
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
