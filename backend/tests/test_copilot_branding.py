"""Copilot 2.0 + Branded exports — TestClient (no demo login)."""

from __future__ import annotations

import io
import sys
import uuid
import zipfile
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SESSION_ID = f"test-sess-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    a = register_user(client, company="CopilotOrg")
    h = a["headers"]
    cr = client.post("/api/clients", headers=h, json={
        "name": "Halcyon Group", "contact": "Ava", "email": "ava@halcyon.test", "value": 12000,
    })
    assert cr.status_code == 200
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=h, json={
        "name": "Brand Redesign", "client_id": cid, "status": "In Progress",
    })
    assert pr.status_code == 200
    pid = pr.json()["id"]
    # Save minimal proposal/contract/invoice docs for export tests
    client.post(f"/api/projects/{pid}/proposal", headers=h, json={
        "title": "Brand Redesign — Proposal", "status": "Draft",
        "content": {"overview": "We will rebrand."},
    })
    client.post(f"/api/projects/{pid}/contract", headers=h, json={
        "title": "Brand Redesign — Contract", "status": "Draft",
        "content": {"terms": "Net 30."},
    })
    client.post(f"/api/projects/{pid}/invoice", headers=h, json={
        "title": "Brand Redesign — Invoice", "status": "Generated",
        "content": {"line_items": [{"description": "Design", "qty": 1, "unitPrice": 1000}]},
    })
    a["project_id"] = pid
    a["client_id"] = cid
    return a


@pytest.fixture
def auth2(client):
    return register_user(client, company="IsoOrg")


# ---------------- COPILOT AUTH ----------------
class TestCopilotAuth:
    def test_message_requires_auth(self, client):
        client.cookies.clear()
        r = client.post("/api/copilot/message", json={"session_id": SESSION_ID, "message": "hi"})
        assert r.status_code in (401, 403)

    def test_execute_requires_auth(self, client):
        client.cookies.clear()
        r = client.post("/api/copilot/execute",
                        json={"session_id": SESSION_ID, "action": {"tool": "create_client", "params": {}}})
        assert r.status_code in (401, 403)

    def test_history_requires_auth(self, client):
        client.cookies.clear()
        r = client.get(f"/api/copilot/history/{SESSION_ID}")
        assert r.status_code in (401, 403)

    def test_suggestions_requires_auth(self, client):
        client.cookies.clear()
        r = client.get("/api/copilot/suggestions")
        assert r.status_code in (401, 403)


class TestCopilotReadQueries:
    def test_read_clients(self, client, auth):
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": SESSION_ID + "-read", "message": "Show my highest value clients"})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        assert data.get("action") is None
        assert isinstance(data.get("reply"), str) and len(data["reply"]) > 0

    def test_read_projects(self, client, auth):
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": SESSION_ID + "-read", "message": "Which projects are behind schedule?"})
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        if r.status_code == 200:
            assert r.json().get("action") is None


class TestCopilotCreateClient:
    def test_create_client_confirmation_and_execute(self, client, auth):
        sid = SESSION_ID + "-nike"
        r = client.post("/api/copilot/message", headers=auth["headers"], json={
            "session_id": sid,
            "message": "Create a new client called TEST_NikeIter16 Inc, contact John Smith, email john@nike.test",
        })
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        data = r.json()
        action = data.get("action")
        assert action is not None, f"expected action card, got: {data}"
        assert action.get("tool") == "create_client"
        assert action.get("requires_confirmation") is True
        assert action.get("action_id")
        params = action.get("params", {})
        assert "nike" in (params.get("name") or "").lower()

        r2 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": action["action_id"]})
        assert r2.status_code == 200, r2.text
        created = r2.json().get("created") or {}
        assert created.get("type") == "client"
        client_id = created.get("id")
        assert client_id

        r3 = client.get("/api/clients", headers=auth["headers"])
        match = next((c for c in r3.json() if c.get("id") == client_id), None)
        assert match is not None and "nikeiter16" in (match.get("name") or "").lower()
        client.delete(f"/api/clients/{client_id}", headers=auth["headers"])


class TestCopilotCreateProject:
    def test_create_project_confirmation_and_execute(self, client, auth):
        sid = SESSION_ID + "-proj"
        r = client.post("/api/copilot/message", headers=auth["headers"], json={
            "session_id": sid,
            "message": "Create a project called TEST_Q3Website Iter16 for client Halcyon Group",
        })
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        action = r.json().get("action")
        assert action is not None
        assert action.get("tool") == "create_project"
        assert action.get("action_id")

        r2 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": action["action_id"]})
        assert r2.status_code == 200, r2.text
        created = r2.json().get("created") or {}
        assert created.get("type") == "project"
        pid = created.get("id")
        assert pid

        r3 = client.get("/api/projects", headers=auth["headers"])
        proj = next((p for p in r3.json() if p["id"] == pid), None)
        assert proj is not None
        assert "q3website" in proj["name"].lower()
        clients = client.get("/api/clients", headers=auth["headers"]).json()
        halcyon = next((c for c in clients if "halcyon" in c["name"].lower()), None)
        if halcyon:
            assert proj.get("client_id") == halcyon["id"]
        client.delete(f"/api/projects/{pid}", headers=auth["headers"])


class TestCopilotSuggestions:
    def test_suggestions_shape(self, client, auth):
        r = client.get("/api/copilot/suggestions", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        if isinstance(body, dict):
            items = body.get("suggestions") or body.get("items") or []
        else:
            items = body
        assert isinstance(items, list)
        for it in items:
            assert "prompt" in it and "text" in it


class TestCopilotHistory:
    def test_history_persists(self, client, auth):
        sid = SESSION_ID + "-hist"
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": sid, "message": "Summarize today's activity"})
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        h = client.get(f"/api/copilot/history/{sid}", headers=auth["headers"])
        assert h.status_code == 200
        msgs = h.json()
        assert isinstance(msgs, list)
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


class TestCopilotGenerateProposal:
    def test_generate_proposal_action(self, client, auth):
        target_name = "Brand Redesign"
        sid = SESSION_ID + "-gen"
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": sid, "message": f"Generate a proposal for {target_name}"})
        assert r.status_code in (200, 502, 503), r.text
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        action = r.json().get("action")
        assert action is not None
        assert action.get("tool") == "generate_proposal"
        assert action.get("action_id")

        r2 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": action["action_id"]})
        assert r2.status_code in (200, 502, 503), r2.text
        assert "sk-" not in r2.text.lower()


# ---------------- BRANDING EXPORTS ----------------
def _find_project_with(client, headers, kind):
    projs = client.get("/api/projects", headers=headers).json()
    for p in projs:
        pid = p["id"]
        r = client.get(f"/api/projects/{pid}/{kind}", headers=headers)
        if r.status_code == 200 and r.json():
            return pid
    return None


class TestBrandedExports:
    def test_proposal_pdf(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "proposal") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/proposal/export/pdf", headers=auth["headers"])
        assert r.status_code in (200, 404), r.text
        if r.status_code == 200:
            assert r.content[:4] == b"%PDF"

    def test_proposal_docx(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "proposal") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/proposal/export/docx", headers=auth["headers"])
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.content[:2] == b"PK"
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                assert "word/document.xml" in z.namelist()

    def test_contract_pdf(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "contract") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/contract/export/pdf", headers=auth["headers"])
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.content[:4] == b"%PDF"

    def test_contract_docx(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "contract") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/contract/export/docx", headers=auth["headers"])
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.content[:2] == b"PK"

    def test_invoice_pdf(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "invoice") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/invoice/export/pdf", headers=auth["headers"])
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.content[:4] == b"%PDF"

    def test_invoice_docx(self, client, auth):
        pid = _find_project_with(client, auth["headers"], "invoice") or auth["project_id"]
        r = client.get(f"/api/projects/{pid}/invoice/export/docx", headers=auth["headers"])
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.content[:2] == b"PK"

    def test_exports_require_auth(self, client, auth):
        pid = auth["project_id"]
        client.cookies.clear()
        r = client.get(f"/api/projects/{pid}/proposal/export/pdf")
        assert r.status_code in (401, 403)


class TestBrandingIsolation:
    def test_fresh_org_cannot_access_other_project_export(self, client, auth, auth2):
        pid = auth["project_id"]
        r = client.get(f"/api/projects/{pid}/proposal/export/pdf", headers=auth2["headers"])
        assert r.status_code in (403, 404)


# ---------------- REGRESSION SMOKE ----------------
class TestRegressionSmoke:
    @pytest.mark.parametrize("path", [
        "/api/auth/me", "/api/clients", "/api/projects", "/api/tasks",
        "/api/dashboard/summary", "/api/settings", "/api/notifications",
    ])
    def test_smoke_endpoints(self, client, auth, path):
        r = client.get(path, headers=auth["headers"])
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:120]}"


# ---------------- COPILOT EXECUTE SECURITY ----------------
class TestCopilotExecuteSecurity:
    def test_execute_rejects_missing_token(self, client, auth):
        r = client.post("/api/copilot/execute", headers=auth["headers"],
                        json={"session_id": "sec-notoken",
                              "action": {"tool": "create_client", "params": {"name": "HACKER Corp"}}})
        assert r.status_code == 400, r.text

    def test_execute_rejects_forged_token(self, client, auth):
        r = client.post("/api/copilot/execute", headers=auth["headers"],
                        json={"session_id": "sec-forged", "action_id": "forged-" + uuid.uuid4().hex})
        assert r.status_code == 404, r.text

    def test_execute_is_single_use(self, client, auth):
        sid = "sec-single-" + uuid.uuid4().hex[:6]
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": sid, "message": "Create a new client called TEST_SingleUse Ltd"})
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        action = r.json().get("action")
        assert action and action.get("action_id")
        aid = action["action_id"]
        r1 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": aid})
        assert r1.status_code == 200, r1.text
        client_id = (r1.json().get("created") or {}).get("id")
        r2 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": aid})
        assert r2.status_code == 409, r2.text
        if client_id:
            client.delete(f"/api/clients/{client_id}", headers=auth["headers"])

    def test_cross_org_cannot_execute_others_token(self, client, auth, auth2):
        sid = "sec-xorg-" + uuid.uuid4().hex[:6]
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": sid, "message": "Create a new client called TEST_XOrgProbe LLC"})
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        action = r.json().get("action")
        assert action and action.get("action_id")
        aid = action["action_id"]
        rx = client.post("/api/copilot/execute", headers=auth2["headers"],
                         json={"session_id": sid, "action_id": aid})
        assert rx.status_code == 404, rx.text
        ro = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": aid})
        assert ro.status_code == 200, ro.text
        cid = (ro.json().get("created") or {}).get("id")
        if cid:
            client.delete(f"/api/clients/{cid}", headers=auth["headers"])

    def test_execute_logs_activity(self, client, auth):
        sid = "sec-log-" + uuid.uuid4().hex[:6]
        r = client.post("/api/copilot/message", headers=auth["headers"],
                        json={"session_id": sid, "message": "Create a project called TEST_LogProbe Site"})
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        if r.status_code != 200:
            return
        action = r.json().get("action")
        assert action and action.get("action_id")
        r2 = client.post("/api/copilot/execute", headers=auth["headers"],
                         json={"session_id": sid, "action_id": action["action_id"]})
        assert r2.status_code == 200, r2.text
        pid = (r2.json().get("created") or {}).get("id")
        acts = client.get(f"/api/activities?project_id={pid}", headers=auth["headers"])
        if acts.status_code == 200:
            types = [a.get("type") for a in acts.json()]
            assert "copilot_action" in types, types
        if pid:
            client.delete(f"/api/projects/{pid}", headers=auth["headers"])
