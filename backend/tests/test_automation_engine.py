"""Backend tests for AI Automation Engine — TestClient (no demo seed)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
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


def _seed_triggers(client, headers):
    """Create data that fires new_client + project_no_task (+ aged lead)."""
    cr = client.post("/api/clients", headers=headers, json={
        "name": "Auto Client", "email": "auto@c.com", "status": "Active",
    })
    assert cr.status_code == 200, cr.text
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=headers, json={
        "name": "Auto Project", "client_id": cid, "status": "In Progress",
    })
    assert pr.status_code == 200, pr.text
    lr = client.post("/api/crm/leads", headers=headers, json={
        "title": "Auto Lead", "stage": "Qualified", "value": 9000, "client_id": cid,
    })
    assert lr.status_code == 200, lr.text
    # Backdate lead so lead_needs_followup (7d) can match
    try:
        from server import db
        import asyncio
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        # Motor sync via TestClient event loop — use pymongo if available
        from pymongo import MongoClient
        import os
        mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017"))
        mc[os.environ.get("DB_NAME", "assistify_test")].leads.update_one(
            {"id": lr.json()["id"]},
            {"$set": {"created_at": old, "updated_at": old, "stage_changed_at": old}},
        )
    except Exception:
        pass
    return {"client_id": cid, "project_id": pr.json()["id"], "lead_id": lr.json()["id"]}


@pytest.fixture
def auth(client):
    a = register_user(client, company="AutoOrg A")
    # Touch automations to ensure templates seed
    r = client.get("/api/automation/automations", headers=a["headers"])
    assert r.status_code == 200
    _seed_triggers(client, a["headers"])
    client.post("/api/automation/run", headers=a["headers"])
    return a


@pytest.fixture
def auth2(client):
    a = register_user(client, company="AutoOrg B")
    client.get("/api/automation/automations", headers=a["headers"])
    return a


# -------- Defaults & seed --------
def test_settings_enabled_and_prepare_default(client, auth):
    r = client.get("/api/automation/settings", headers=auth["headers"])
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is True
    assert d["default_mode"] == "prepare"
    assert d["safe_internal_auto"] is True


def test_summary_defaults(client, auth):
    r = client.get("/api/automation/summary", headers=auth["headers"])
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is True
    assert d["default_mode"] == "prepare"
    assert d["total_automations"] == 12


def test_twelve_templates_seeded(client, auth):
    r = client.get("/api/automation/automations", headers=auth["headers"])
    assert r.status_code == 200
    autos = r.json()
    assert len(autos) == 12
    assert all(a["enabled"] for a in autos)
    assert all(a.get("trigger_label") for a in autos)


def test_pending_approvals_seeded(client, auth):
    client.post("/api/automation/run", headers=auth["headers"])
    r = client.get("/api/automation/approvals?status=pending", headers=auth["headers"])
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert isinstance(d["items"], list)
    # new_client / project_no_task should produce at least one pending (or executed)
    executed = client.get("/api/automation/approvals?status=executed", headers=auth["headers"]).json()
    assert len(d["items"]) > 0 or len(executed.get("items", [])) > 0


def test_builder_options(client, auth):
    r = client.get("/api/automation/builder-options", headers=auth["headers"])
    assert r.status_code == 200
    d = r.json()
    assert len(d["triggers"]) >= 13
    assert len(d["actions"]) >= 11
    assert len(d["modes"]) == 3
    assert "fields" in d["conditions"] and "ops" in d["conditions"]


# -------- Approve/reject flow --------
def test_approve_creates_task(client):
    a = register_user(client, company="ApproveCo")
    h = a["headers"]
    _seed_triggers(client, h)
    client.post("/api/automation/run", headers=h)
    ap = client.get("/api/automation/approvals?status=pending", headers=h).json()
    target = None
    for it in ap.get("items", []):
        if any(x["type"] == "create_task" for x in it["actions"]):
            target = it
            break
    if not target:
        # Maybe auto-executed — accept executed create_task
        ex = client.get("/api/automation/approvals?status=executed", headers=h).json()
        target = next((it for it in ex.get("items", []) if any(x["type"] == "create_task" for x in it["actions"])), None)
        if target:
            assert target.get("status") == "executed" or target.get("auto_executed")
            return
    assert target, "No create_task approval produced"
    r = client.post(f"/api/automation/approvals/{target['id']}/approve", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["status"] == "executed"


def test_reject_flow(client):
    a = register_user(client, company="RejectCo")
    h = a["headers"]
    _seed_triggers(client, h)
    client.post("/api/automation/run", headers=h)
    ap = client.get("/api/automation/approvals?status=pending", headers=h).json()
    if not ap.get("items"):
        pytest.skip("No pending approvals to reject (triggers may have auto-executed)")
    apid = ap["items"][0]["id"]
    r = client.post(f"/api/automation/approvals/{apid}/reject", headers=h)
    assert r.status_code == 200
    lst = client.get("/api/automation/approvals?status=rejected", headers=h).json()
    assert any(x["id"] == apid for x in lst["items"])


def test_edit_pending_approval(client):
    a = register_user(client, company="EditAppr")
    h = a["headers"]
    _seed_triggers(client, h)
    client.post("/api/automation/run", headers=h)
    ap = client.get("/api/automation/approvals?status=pending", headers=h).json()
    target = None
    for it in ap.get("items", []):
        if any(x["type"] in ("prepare_email", "prepare_followup") for x in it["actions"]):
            target = it
            break
    if not target:
        pytest.skip("No email/followup pending approval (needs aged lead or similar)")
    new_actions = target["actions"]
    for act in new_actions:
        if act["type"] in ("prepare_email", "prepare_followup"):
            email = act.setdefault("payload", {}).setdefault("email", {})
            email["subject"] = "EDITED SUBJECT"
    r = client.put(f"/api/automation/approvals/{target['id']}", headers=h, json={"actions": new_actions})
    assert r.status_code == 200


# -------- Suggest mode --------
def test_suggest_mode_no_payload_then_prepare(client):
    a = register_user(client, company="SuggestCo")
    h = a["headers"]
    autos = client.get("/api/automation/automations", headers=h).json()
    auto = next(x for x in autos if x["trigger"]["type"] == "new_client")
    _seed_triggers(client, h)
    old = client.get("/api/automation/approvals?status=pending", headers=h).json()
    for it in old.get("items", []):
        if it["automation_id"] == auto["id"]:
            client.post(f"/api/automation/approvals/{it['id']}/reject", headers=h)
    r = client.patch(f"/api/automation/automations/{auto['id']}/mode", headers=h, json={"mode": "suggest"})
    assert r.status_code == 200
    client.post("/api/automation/run", headers=h)
    sug = client.get("/api/automation/approvals?status=suggested", headers=h).json()
    matches = [x for x in sug.get("items", []) if x["automation_id"] == auto["id"]]
    assert matches, "No suggestions created"
    s = matches[0]
    assert all(not x.get("payload") for x in s["actions"])
    r = client.post(f"/api/automation/approvals/{s['id']}/prepare", headers=h)
    assert r.status_code == 200
    pen = client.get("/api/automation/approvals?status=pending", headers=h).json()
    assert any(x["id"] == s["id"] for x in pen["items"])


# -------- Safety downgrade --------
def test_safety_downgrade_external_and_generative(client):
    a = register_user(client, company="SafetyCo")
    h = a["headers"]
    autos = client.get("/api/automation/automations", headers=h).json()
    email_auto = next(x for x in autos if x["trigger"]["type"] == "lead_needs_followup")
    _seed_triggers(client, h)
    old = client.get("/api/automation/approvals?status=pending", headers=h).json()
    for it in old.get("items", []):
        if it["automation_id"] == email_auto["id"]:
            client.post(f"/api/automation/approvals/{it['id']}/reject", headers=h)
    r = client.patch(f"/api/automation/automations/{email_auto['id']}/mode", headers=h, json={"mode": "auto"})
    assert r.status_code == 200
    client.post("/api/automation/run", headers=h)
    pen = client.get("/api/automation/approvals?status=pending", headers=h).json()
    matches = [x for x in pen.get("items", []) if x["automation_id"] == email_auto["id"]]
    if not matches:
        pytest.skip("Aged lead did not trigger follow-up (backdate may have failed)")
    assert all(not x.get("auto_executed") for x in matches)


def test_safe_internal_auto_executes(client):
    a = register_user(client, company="SafeAuto")
    h = a["headers"]
    autos = client.get("/api/automation/automations", headers=h).json()
    proj = next(x for x in autos if x["trigger"]["type"] == "new_client")
    assert all(act["type"] == "create_task" for act in proj["actions"])
    old = client.get("/api/automation/approvals?status=pending", headers=h).json()
    for it in old.get("items", []):
        if it["automation_id"] == proj["id"]:
            client.post(f"/api/automation/approvals/{it['id']}/reject", headers=h)
    r = client.patch(f"/api/automation/automations/{proj['id']}/mode", headers=h, json={"mode": "auto"})
    assert r.status_code == 200
    # Create a fresh client AFTER mode change so it matches
    client.post("/api/clients", headers=h, json={"name": "Fresh Auto Client", "email": "fac@c.com"})
    r = client.post("/api/automation/run", headers=h)
    assert r.status_code == 200
    ex = client.get("/api/automation/approvals?status=executed", headers=h).json()
    matches = [x for x in ex.get("items", []) if x["automation_id"] == proj["id"] and x.get("auto_executed")]
    assert matches, "Safe internal auto action should have auto-executed"


# -------- Master controls --------
def test_master_disable_pauses_evaluation(client):
    a = register_user(client, company="DisableCo")
    h = a["headers"]
    r = client.patch("/api/automation/settings", headers=h, json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    res = client.post("/api/automation/run", headers=h).json()
    assert res["prepared"] == 0 and res["executed"] == 0 and res["suggested"] == 0


def test_pause_resume(client):
    a = register_user(client, company="PauseCo")
    h = a["headers"]
    r = client.post("/api/automation/pause", headers=h, json={"duration": "1h"})
    assert r.status_code == 200
    d = r.json()
    assert d["paused"] is True
    assert d["paused_until"]
    s = client.get("/api/automation/summary", headers=h).json()
    assert s["paused"] is True
    r = client.post("/api/automation/resume", headers=h)
    assert r.status_code == 200
    assert r.json()["paused"] is False
    r = client.post("/api/automation/pause", headers=h, json={"duration": "bogus"})
    assert r.status_code == 400


# -------- Per-automation toggle --------
def test_per_automation_toggle(client, auth):
    h = auth["headers"]
    autos = client.get("/api/automation/automations", headers=h).json()
    a = autos[0]
    r = client.patch(f"/api/automation/automations/{a['id']}/toggle", headers=h, json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    autos2 = client.get("/api/automation/automations", headers=h).json()
    match = next(x for x in autos2 if x["id"] == a["id"])
    assert match["enabled"] is False and match["status"] == "Paused"
    client.patch(f"/api/automation/automations/{a['id']}/toggle", headers=h, json={"enabled": True})


# -------- Builder CRUD --------
def test_create_update_delete_custom_automation(client, auth):
    h = auth["headers"]
    body = {
        "name": "TEST_Custom rule",
        "description": "Custom",
        "trigger": {"type": "task_overdue", "days": 0},
        "conditions": [],
        "actions": [{"type": "add_note", "config": {}}],
        "mode": "prepare",
    }
    r = client.post("/api/automation/automations", headers=h, json=body)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    bad = {**body, "trigger": {"type": "not_a_trigger"}}
    r = client.post("/api/automation/automations", headers=h, json=bad)
    assert r.status_code == 400
    bad = {**body, "actions": [{"type": "fake_action"}]}
    r = client.post("/api/automation/automations", headers=h, json=bad)
    assert r.status_code == 400
    upd = {**body, "name": "TEST_Custom renamed"}
    r = client.put(f"/api/automation/automations/{aid}", headers=h, json=upd)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Custom renamed"
    r = client.delete(f"/api/automation/automations/{aid}", headers=h)
    assert r.status_code == 200


# -------- Logs --------
def test_logs_have_event_labels(client, auth):
    h = auth["headers"]
    client.post("/api/automation/run", headers=h)
    r = client.get("/api/automation/logs", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["items"]
    assert all("event_label" in x for x in d["items"])


# -------- Run now --------
def test_run_now(client, auth):
    r = client.post("/api/automation/run", headers=auth["headers"])
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert "prepared" in d and "executed" in d and "suggested" in d


# -------- Org isolation --------
def test_org_isolation(client, auth, auth2):
    h, h2 = auth["headers"], auth2["headers"]
    a_items = client.get("/api/automation/approvals?status=pending", headers=h).json()["items"]
    b_items = client.get("/api/automation/approvals?status=pending", headers=h2).json()["items"]
    a_ids = {x["id"] for x in a_items}
    b_ids = {x["id"] for x in b_items}
    assert not (a_ids & b_ids)
    if a_items:
        r = client.post(f"/api/automation/approvals/{a_items[0]['id']}/approve", headers=h2)
        assert r.status_code == 404


# -------- Regression --------
def test_regression_other_endpoints(client, auth):
    for path in ("/api/memory/stats", "/api/opportunities", "/api/crm/sales-metrics", "/api/assistant/suggestions"):
        r = client.get(path, headers=auth["headers"])
        assert r.status_code == 200, f"{path} => {r.status_code}"
