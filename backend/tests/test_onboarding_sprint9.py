"""Sprint 9 WOW Onboarding backend tests.

Covers: state persistence, restart, flag, website analysis (real + graceful failure),
profile generation (LLM+fallback), memory seed, PUT profile, seed-demo idempotent,
demo-status, DELETE demo-data (preserves onboarding memories), checklist, org isolation,
and non-regression on core endpoints.
"""
import os
import uuid
import requests
import pytest
from conftest import auth_json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"


def _register():
    email = f"onb9+{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "firstName": "Onb", "lastName": "Nine",
        "email": email, "password": "NewPass123!", "company": "OnbCo9"
    }, timeout=30)
    assert r.status_code == 200, r.text
    d = auth_json(None, r)
    return email, d["accessToken"], d.get("user", {})


def _demo_session():
    r = requests.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    assert r.status_code == 200, r.text
    d = auth_json(None, r)
    return d["accessToken"], d["user"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- state / restart / flag ----------

def test_state_defaults_and_persistence():
    _, tok, user = _register()
    assert user.get("onboardingCompleted") is False
    r = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok))
    assert r.status_code == 200
    j = r.json()
    assert j["step"] == 0 and j["completed"] is False
    assert j["demo_seeded"] is False
    assert isinstance(j["flags"], dict)

    # persist step + data
    r = requests.post(f"{BASE_URL}/api/onboarding/state", headers=_h(tok),
                      json={"step": 3, "data": {"company_name": "TEST_Co"}})
    assert r.status_code == 200 and r.json()["ok"] is True
    j2 = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert j2["step"] == 3 and j2["data"]["company_name"] == "TEST_Co"


def test_flag_sets_and_reflects_in_state():
    _, tok, _ = _register()
    r = requests.post(f"{BASE_URL}/api/onboarding/flag", headers=_h(tok), json={"key": "workspace"})
    assert r.status_code == 200
    j = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert j["flags"].get("workspace") is True


def test_restart_resets_state_and_completed():
    _, tok, _ = _register()
    requests.post(f"{BASE_URL}/api/onboarding/state", headers=_h(tok),
                  json={"step": 5, "data": {"x": 1}, "completed": True})
    j = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert j["completed"] is True
    r = requests.post(f"{BASE_URL}/api/onboarding/restart", headers=_h(tok))
    assert r.status_code == 200
    j = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert j["completed"] is False and j["step"] == 0 and j["data"] == {}


def test_state_requires_auth():
    assert requests.get(f"{BASE_URL}/api/onboarding/state").status_code == 401
    assert requests.post(f"{BASE_URL}/api/onboarding/restart").status_code == 401


# ---------- website analysis ----------

def test_analyze_website_bad_url_graceful():
    _, tok, _ = _register()
    r = requests.post(f"{BASE_URL}/api/onboarding/analyze-website",
                      headers=_h(tok), json={"url": "not-a-real-domain-xyzzy-999.tld"}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is False and "reason" in j and j["fields"] == {}


def test_analyze_website_real_url():
    _, tok, _ = _register()
    r = requests.post(f"{BASE_URL}/api/onboarding/analyze-website",
                      headers=_h(tok), json={"url": "example.com"}, timeout=45)
    assert r.status_code == 200, r.text
    j = r.json()
    # Either LLM parsed it (ok=True) or it fell through gracefully (ok=False, no 500).
    assert "ok" in j and "fields" in j


def test_analyze_website_empty_url_400():
    _, tok, _ = _register()
    r = requests.post(f"{BASE_URL}/api/onboarding/analyze-website",
                      headers=_h(tok), json={"url": ""})
    assert r.status_code == 400


# ---------- profile ----------

@pytest.fixture(scope="module")
def profile_ctx():
    email, tok, _ = _register()
    payload = {"company_name": "TEST_Aster Studio", "industry": "Design agency",
               "website": "https://aster.example", "employees": "1-5",
               "main_services": "Branding, Web design, Motion",
               "target_customers": "Early stage startups",
               "language": "en", "country": "US"}
    r = requests.post(f"{BASE_URL}/api/onboarding/profile", headers=_h(tok),
                      json=payload, timeout=90)
    assert r.status_code == 200, r.text
    return {"email": email, "tok": tok, "resp": r.json()}


def test_profile_returns_sections_memories_and_automations(profile_ctx):
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


def test_profile_memories_appear_in_memory_list(profile_ctx):
    tok = profile_ctx["tok"]
    r = requests.get(f"{BASE_URL}/api/memory/memories", headers=_h(tok), timeout=30)
    assert r.status_code == 200
    mems = r.json()
    if isinstance(mems, dict):
        mems = mems.get("memories") or mems.get("items") or []
    sources = [m.get("source") for m in mems]
    assert any(s == "Onboarding" for s in sources), f"no Onboarding-sourced memory, sources={sources}"


def test_profile_put_updates_sections(profile_ctx):
    tok = profile_ctx["tok"]
    new = {"sections": {"company_summary": "TEST_updated summary", "industry": "Design",
                        "services": ["Branding"], "communication_style": "Warm",
                        "proposal_style": "Concise", "brand_voice": "Confident",
                        "writing_style": "Scannable"}}
    r = requests.put(f"{BASE_URL}/api/onboarding/profile", headers=_h(tok), json=new)
    assert r.status_code == 200 and r.json()["ok"] is True


# ---------- demo workspace ----------

def test_seed_demo_idempotent_and_status_and_clear():
    _, tok, _ = _register()
    r1 = requests.post(f"{BASE_URL}/api/onboarding/seed-demo", headers=_h(tok), timeout=60)
    assert r1.status_code == 200, r1.text
    c1 = r1.json()["counts"]
    assert c1["clients"] > 0

    r2 = requests.post(f"{BASE_URL}/api/onboarding/seed-demo", headers=_h(tok), timeout=60)
    assert r2.status_code == 200
    c2 = r2.json()["counts"]
    assert c2["clients"] == c1["clients"], f"seed-demo not idempotent: {c1} vs {c2}"

    st = requests.get(f"{BASE_URL}/api/onboarding/demo-status", headers=_h(tok)).json()
    assert st["has_demo"] is True and st["counts"]["clients"] == c1["clients"]

    r = requests.delete(f"{BASE_URL}/api/onboarding/demo-data", headers=_h(tok))
    assert r.status_code == 200
    st2 = requests.get(f"{BASE_URL}/api/onboarding/demo-status", headers=_h(tok)).json()
    assert st2["has_demo"] is False and st2["counts"]["clients"] == 0


def test_clear_demo_preserves_onboarding_memories():
    _, tok, _ = _register()
    # generate real onboarding memories
    r = requests.post(f"{BASE_URL}/api/onboarding/profile", headers=_h(tok), json={
        "company_name": "TEST_Preserve", "industry": "Test", "main_services": "A, B, C"
    }, timeout=90)
    assert r.status_code == 200
    # seed demo, then clear
    requests.post(f"{BASE_URL}/api/onboarding/seed-demo", headers=_h(tok), timeout=60)
    requests.delete(f"{BASE_URL}/api/onboarding/demo-data", headers=_h(tok))
    # Onboarding memories must remain
    mems = requests.get(f"{BASE_URL}/api/memory/memories", headers=_h(tok)).json()
    if isinstance(mems, dict):
        mems = mems.get("memories") or mems.get("items") or []
    assert any(m.get("source") == "Onboarding" for m in mems), "Onboarding memories were wiped by clear-demo!"


# ---------- checklist ----------

def test_checklist_shape_for_new_user():
    _, tok, _ = _register()
    r = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok))
    assert r.status_code == 200
    j = r.json()
    assert j["total"] == 6 and j["done"] == 0 and j["percent"] == 0
    keys = [i["key"] for i in j["items"]]
    assert set(keys) == {"profile", "client", "project", "task", "copilot", "agents"}
    for i in j["items"]:
        assert i["done"] is False and "to" in i and "label" in i
    assert j.get("dismissed") is False
    assert "Assistify" in (j.get("title") or "")


def test_checklist_reflects_flags_and_profile():
    _, tok, _ = _register()
    requests.post(f"{BASE_URL}/api/onboarding/flag", headers=_h(tok), json={"key": "copilot"})
    requests.post(f"{BASE_URL}/api/onboarding/flag", headers=_h(tok), json={"key": "agents"})
    j = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["copilot"] is True and st["agents"] is True
    assert j["done"] >= 2


def test_checklist_client_counts_only_non_demo():
    _, tok, _ = _register()
    # seed demo — client count should NOT flip
    requests.post(f"{BASE_URL}/api/onboarding/seed-demo", headers=_h(tok), timeout=60)
    j = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["client"] is False, "demo clients incorrectly counted in checklist"
    # create a REAL client
    requests.post(f"{BASE_URL}/api/clients", headers=_h(tok),
                  json={"name": "TEST_Real Client", "contact": "R", "email": "r@r.com", "phone": "1"})
    j = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    st = {i["key"]: i["done"] for i in j["items"]}
    assert st["client"] is True


def test_checklist_dismiss_persists():
    _, tok, _ = _register()
    r = requests.post(f"{BASE_URL}/api/onboarding/checklist/dismiss", headers=_h(tok))
    assert r.status_code == 200
    j = requests.get(f"{BASE_URL}/api/onboarding/checklist", headers=_h(tok)).json()
    assert j.get("dismissed") is True


def test_onboarding_primary_goal_persists_on_state():
    _, tok, _ = _register()
    requests.post(
        f"{BASE_URL}/api/onboarding/state",
        headers=_h(tok),
        json={"step": 2, "data": {"primaryGoal": "save_time_ai", "company": {"company_name": "GoalCo"}}},
    )
    # complete so returning users are not forced through wizard
    requests.post(f"{BASE_URL}/api/onboarding/complete", headers=_h(tok))
    st = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tok)).json()
    assert st.get("completed") is True
    assert (st.get("data") or {}).get("primaryGoal") == "save_time_ai"


# ---------- org isolation ----------

def test_org_isolation_between_two_new_users():
    _, tokA, _ = _register()
    _, tokB, _ = _register()
    requests.post(f"{BASE_URL}/api/onboarding/state", headers=_h(tokA),
                  json={"step": 4, "data": {"marker": "A"}})
    requests.post(f"{BASE_URL}/api/onboarding/seed-demo", headers=_h(tokA), timeout=60)
    stA = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tokA)).json()
    stB = requests.get(f"{BASE_URL}/api/onboarding/state", headers=_h(tokB)).json()
    assert stA["step"] == 4 and stB["step"] == 0
    dsB = requests.get(f"{BASE_URL}/api/onboarding/demo-status", headers=_h(tokB)).json()
    assert dsB["has_demo"] is False


# ---------- regression / demo user ----------

def test_demo_user_completed_true_and_has_demo():
    tok, user = _demo_session()
    assert user.get("onboardingCompleted") is True
    ds = requests.get(f"{BASE_URL}/api/onboarding/demo-status", headers=_h(tok)).json()
    assert ds["has_demo"] is True


def test_regression_core_endpoints_still_200():
    _, tok, _ = _register()
    for path in ("/api/memory/stats", "/api/opportunities", "/api/automation/summary", "/api/crm/sales-metrics"):
        r = requests.get(f"{BASE_URL}{path}", headers=_h(tok), timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
