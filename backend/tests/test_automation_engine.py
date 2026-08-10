"""Backend tests for AI Automation Engine (Assistify)."""
import os
import time
import pytest
import requests
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://operations-hub-75.preview.emergentagent.com").rstrip("/")


def _new_demo():
    r = requests.post(f"{BASE_URL}/api/auth/demo", timeout=30)
    assert r.status_code == 200, r.text
    data = auth_json(None, r)
    tok = data.get("accessToken")
    assert tok, "demo login did not set access_token cookie"
    return {"Authorization": f"Bearer {tok}"}, data["user"]["organizationId"]


@pytest.fixture(scope="module")
def h():
    hdr, org = _new_demo()
    return hdr


@pytest.fixture(scope="module")
def h2():
    hdr, org = _new_demo()
    return hdr


# -------- Defaults & seed --------
def test_settings_enabled_and_prepare_default(h):
    r = requests.get(f"{BASE_URL}/api/automation/settings", headers=h, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is True
    assert d["default_mode"] == "prepare"
    assert d["safe_internal_auto"] is True


def test_summary_defaults(h):
    r = requests.get(f"{BASE_URL}/api/automation/summary", headers=h, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is True
    assert d["default_mode"] == "prepare"
    assert d["total_automations"] == 12


def test_twelve_templates_seeded(h):
    r = requests.get(f"{BASE_URL}/api/automation/automations", headers=h, timeout=15)
    assert r.status_code == 200
    autos = r.json()
    assert len(autos) == 12
    assert all(a["enabled"] for a in autos)
    assert all(a.get("trigger_label") for a in autos)


def test_pending_approvals_seeded(h):
    # Run to force evaluation
    requests.post(f"{BASE_URL}/api/automation/run", headers=h, timeout=30)
    r = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=h, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert isinstance(d["items"], list)
    # demo seed should produce at least 1 pending
    assert len(d["items"]) > 0


def test_builder_options(h):
    r = requests.get(f"{BASE_URL}/api/automation/builder-options", headers=h, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["triggers"]) == 13
    assert len(d["actions"]) == 11
    assert len(d["modes"]) == 3
    assert "fields" in d["conditions"] and "ops" in d["conditions"]


# -------- Approve/reject flow --------
def test_approve_creates_task():
    hdr, org = _new_demo()
    requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    ap = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    # find create_task approval
    target = None
    for it in ap["items"]:
        if any(x["type"] == "create_task" for x in it["actions"]):
            target = it
            break
    assert target, "No create_task approval seeded"
    r = requests.post(f"{BASE_URL}/api/automation/approvals/{target['id']}/approve", headers=hdr, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["status"] == "executed"


def test_reject_flow():
    hdr, _ = _new_demo()
    requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    ap = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    assert ap["items"]
    apid = ap["items"][0]["id"]
    r = requests.post(f"{BASE_URL}/api/automation/approvals/{apid}/reject", headers=hdr, timeout=15)
    assert r.status_code == 200
    # verify status
    lst = requests.get(f"{BASE_URL}/api/automation/approvals?status=rejected", headers=hdr, timeout=15).json()
    assert any(x["id"] == apid for x in lst["items"])


def test_edit_pending_approval():
    hdr, _ = _new_demo()
    requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    ap = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    # find email approval
    target = None
    for it in ap["items"]:
        if any(x["type"] in ("prepare_email", "prepare_followup") for x in it["actions"]):
            target = it; break
    assert target, "No email approval"
    new_actions = target["actions"]
    for a in new_actions:
        if a["type"] in ("prepare_email", "prepare_followup"):
            a["payload"]["email"]["subject"] = "EDITED SUBJECT"
    r = requests.put(f"{BASE_URL}/api/automation/approvals/{target['id']}",
                     headers=hdr, json={"actions": new_actions}, timeout=15)
    assert r.status_code == 200


# -------- Suggest mode --------
def test_suggest_mode_no_payload_then_prepare():
    hdr, _ = _new_demo()
    autos = requests.get(f"{BASE_URL}/api/automation/automations", headers=hdr, timeout=15).json()
    # pick new_client automation (has matches in demo)
    a = next(x for x in autos if x["trigger"]["type"] == "new_client")
    # Reject existing pending approvals for it first
    old = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    for it in old["items"]:
        if it["automation_id"] == a["id"]:
            requests.post(f"{BASE_URL}/api/automation/approvals/{it['id']}/reject", headers=hdr, timeout=15)
    r = requests.patch(f"{BASE_URL}/api/automation/automations/{a['id']}/mode",
                       headers=hdr, json={"mode": "suggest"}, timeout=15)
    assert r.status_code == 200
    # force re-run
    requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    sug = requests.get(f"{BASE_URL}/api/automation/approvals?status=suggested", headers=hdr, timeout=15).json()
    matches = [x for x in sug["items"] if x["automation_id"] == a["id"]]
    assert matches, "No suggestions created"
    s = matches[0]
    # actions should have empty payloads
    assert all(not x.get("payload") for x in s["actions"])
    # prepare
    r = requests.post(f"{BASE_URL}/api/automation/approvals/{s['id']}/prepare", headers=hdr, timeout=15)
    assert r.status_code == 200
    # verify it's now pending
    pen = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    assert any(x["id"] == s["id"] for x in pen["items"])


# -------- Safety downgrade --------
def test_safety_downgrade_external_and_generative():
    hdr, _ = _new_demo()
    autos = requests.get(f"{BASE_URL}/api/automation/automations", headers=hdr, timeout=15).json()
    # lead_needs_followup has prepare_followup (external) — matches exist in demo
    email_auto = next(x for x in autos if x["trigger"]["type"] == "lead_needs_followup")
    # clear existing approvals first (so dedup allows re-creation)
    old = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    for it in old["items"]:
        if it["automation_id"] == email_auto["id"]:
            requests.post(f"{BASE_URL}/api/automation/approvals/{it['id']}/reject", headers=hdr, timeout=15)
    r = requests.patch(f"{BASE_URL}/api/automation/automations/{email_auto['id']}/mode",
                       headers=hdr, json={"mode": "auto"}, timeout=15)
    assert r.status_code == 200
    requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    pen = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    matches = [x for x in pen["items"] if x["automation_id"] == email_auto["id"]]
    assert matches, "External/mixed action should have been downgraded to pending"
    assert all(not x.get("auto_executed") for x in matches)


def test_safe_internal_auto_executes():
    hdr, _ = _new_demo()
    autos = requests.get(f"{BASE_URL}/api/automation/automations", headers=hdr, timeout=15).json()
    # new_client automation has only create_task (safe internal) AND matches in demo
    proj = next(x for x in autos if x["trigger"]["type"] == "new_client")
    assert all(a["type"] == "create_task" for a in proj["actions"])
    # Clear existing pendings
    old = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=hdr, timeout=15).json()
    for it in old["items"]:
        if it["automation_id"] == proj["id"]:
            requests.post(f"{BASE_URL}/api/automation/approvals/{it['id']}/reject", headers=hdr, timeout=15)
    r = requests.patch(f"{BASE_URL}/api/automation/automations/{proj['id']}/mode",
                       headers=hdr, json={"mode": "auto"}, timeout=15)
    assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=30)
    assert r.status_code == 200
    ex = requests.get(f"{BASE_URL}/api/automation/approvals?status=executed", headers=hdr, timeout=15).json()
    matches = [x for x in ex["items"] if x["automation_id"] == proj["id"] and x.get("auto_executed")]
    assert matches, "Safe internal auto action should have auto-executed"


# -------- Master controls --------
def test_master_disable_pauses_evaluation():
    hdr, _ = _new_demo()
    r = requests.patch(f"{BASE_URL}/api/automation/settings", headers=hdr,
                       json={"enabled": False}, timeout=15)
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    res = requests.post(f"{BASE_URL}/api/automation/run", headers=hdr, timeout=15).json()
    assert res["prepared"] == 0 and res["executed"] == 0 and res["suggested"] == 0


def test_pause_resume():
    hdr, _ = _new_demo()
    r = requests.post(f"{BASE_URL}/api/automation/pause", headers=hdr, json={"duration": "1h"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["paused"] is True
    assert d["paused_until"]
    s = requests.get(f"{BASE_URL}/api/automation/summary", headers=hdr, timeout=15).json()
    assert s["paused"] is True
    r = requests.post(f"{BASE_URL}/api/automation/resume", headers=hdr, timeout=15)
    assert r.status_code == 200
    assert r.json()["paused"] is False
    # invalid duration
    r = requests.post(f"{BASE_URL}/api/automation/pause", headers=hdr, json={"duration": "bogus"}, timeout=15)
    assert r.status_code == 400


# -------- Per-automation toggle --------
def test_per_automation_toggle(h):
    autos = requests.get(f"{BASE_URL}/api/automation/automations", headers=h, timeout=15).json()
    a = autos[0]
    r = requests.patch(f"{BASE_URL}/api/automation/automations/{a['id']}/toggle",
                       headers=h, json={"enabled": False}, timeout=15)
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    autos2 = requests.get(f"{BASE_URL}/api/automation/automations", headers=h, timeout=15).json()
    match = next(x for x in autos2 if x["id"] == a["id"])
    assert match["enabled"] is False and match["status"] == "Paused"
    # restore
    requests.patch(f"{BASE_URL}/api/automation/automations/{a['id']}/toggle",
                   headers=h, json={"enabled": True}, timeout=15)


# -------- Builder CRUD --------
def test_create_update_delete_custom_automation(h):
    body = {
        "name": "TEST_Custom rule",
        "description": "Custom",
        "trigger": {"type": "task_overdue", "days": 0},
        "conditions": [],
        "actions": [{"type": "add_note", "config": {}}],
        "mode": "prepare",
    }
    r = requests.post(f"{BASE_URL}/api/automation/automations", headers=h, json=body, timeout=15)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    # Unknown trigger
    bad = {**body, "trigger": {"type": "not_a_trigger"}}
    r = requests.post(f"{BASE_URL}/api/automation/automations", headers=h, json=bad, timeout=15)
    assert r.status_code == 400
    # Unknown action
    bad = {**body, "actions": [{"type": "fake_action"}]}
    r = requests.post(f"{BASE_URL}/api/automation/automations", headers=h, json=bad, timeout=15)
    assert r.status_code == 400
    # Update
    upd = {**body, "name": "TEST_Custom renamed"}
    r = requests.put(f"{BASE_URL}/api/automation/automations/{aid}", headers=h, json=upd, timeout=15)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Custom renamed"
    # Delete
    r = requests.delete(f"{BASE_URL}/api/automation/automations/{aid}", headers=h, timeout=15)
    assert r.status_code == 200


# -------- Logs --------
def test_logs_have_event_labels(h):
    r = requests.get(f"{BASE_URL}/api/automation/logs", headers=h, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["items"]
    assert all("event_label" in x for x in d["items"])


# -------- Run now --------
def test_run_now(h):
    r = requests.post(f"{BASE_URL}/api/automation/run", headers=h, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert "prepared" in d and "executed" in d and "suggested" in d


# -------- Org isolation --------
def test_org_isolation(h, h2):
    # Approvals from h should not be visible via h2
    a_items = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=h, timeout=15).json()["items"]
    b_items = requests.get(f"{BASE_URL}/api/automation/approvals?status=pending", headers=h2, timeout=15).json()["items"]
    a_ids = {x["id"] for x in a_items}
    b_ids = {x["id"] for x in b_items}
    assert not (a_ids & b_ids)
    # Approving A's item via B should 404
    if a_items:
        r = requests.post(f"{BASE_URL}/api/automation/approvals/{a_items[0]['id']}/approve",
                          headers=h2, timeout=15)
        assert r.status_code == 404


# -------- Regression --------
def test_regression_other_endpoints(h):
    for path in ("/api/memory/stats", "/api/opportunities", "/api/crm/sales-metrics", "/api/assistant/suggestions"):
        r = requests.get(f"{BASE_URL}{path}", headers=h, timeout=20)
        assert r.status_code == 200, f"{path} => {r.status_code}"
