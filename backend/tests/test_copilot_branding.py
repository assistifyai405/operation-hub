"""
Iteration 16 - Copilot 2.0 + Branded exports
Covers:
 - Copilot read queries (no action), snapshot uses real org data
 - Copilot create_client / create_project confirmation + execute
 - Copilot history persistence
 - Copilot suggestions
 - Copilot generate_proposal execute (graceful 502 acceptable)
 - Branded exports: PDF/DOCX for proposal, contract, invoice (6 endpoints)
 - Auth guards + org isolation
"""
import os
import io
import uuid
import time
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DEMO_EMAIL = "jordan@assistify.io"
DEMO_PASSWORD = "Assistify2026!"

SESSION_ID = f"test-sess-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def demo_client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "remember": False}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    token = r.json().get("accessToken")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def fresh_client():
    s = requests.Session()
    email = f"test_iter16_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"firstName": "Iter", "lastName": "Sixteen", "email": email, "password": "Pass1234!",
                     "company": "IsoOrg"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    token = r.json().get("accessToken")
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ---------------- COPILOT ----------------
class TestCopilotAuth:
    def test_message_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/copilot/message",
                          json={"session_id": SESSION_ID, "message": "hi"}, timeout=10)
        assert r.status_code in (401, 403)

    def test_execute_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/copilot/execute",
                          json={"session_id": SESSION_ID, "action": {"tool": "create_client", "params": {}}}, timeout=10)
        assert r.status_code in (401, 403)

    def test_history_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/copilot/history/{SESSION_ID}", timeout=10)
        assert r.status_code in (401, 403)

    def test_suggestions_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/copilot/suggestions", timeout=10)
        assert r.status_code in (401, 403)


class TestCopilotReadQueries:
    """Read-only questions must reply with real data and NO action."""

    def test_read_clients(self, demo_client):
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": SESSION_ID + "-read", "message": "Show my highest value clients"},
                             timeout=60)
        # LLM may 502 if key balance depleted - acceptable env limitation
        if r.status_code == 502:
            pytest.skip(f"LLM unavailable: {r.text[:120]}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("action") is None, f"read query should not produce action: {data.get('action')}"
        assert isinstance(data.get("reply"), str) and len(data["reply"]) > 0

    def test_read_projects(self, demo_client):
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": SESSION_ID + "-read", "message": "Which projects are behind schedule?"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        assert r.status_code == 200
        assert r.json().get("action") is None


class TestCopilotCreateClient:
    def test_create_client_confirmation_and_execute(self, demo_client):
        sid = SESSION_ID + "-nike"
        # 1. Ask copilot -> expect action card
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid,
                                   "message": "Create a new client called TEST_NikeIter16 Inc, contact John Smith, email john@nike.test"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        assert r.status_code == 200, r.text
        data = r.json()
        action = data.get("action")
        assert action is not None, f"expected action card, got: {data}"
        assert action.get("tool") == "create_client"
        assert action.get("requires_confirmation") is True
        assert action.get("action_id"), "server must issue a confirmation token"
        params = action.get("params", {})
        assert "nike" in (params.get("name") or "").lower()

        # 2. Confirm execute using the server-issued token (client cannot forge params)
        r2 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": action["action_id"]},
                              timeout=30)
        assert r2.status_code == 200, r2.text
        created = r2.json().get("created") or {}
        assert created.get("type") == "client"
        client_id = created.get("id")
        assert client_id

        # 3. Verify persistence via /api/clients
        r3 = demo_client.get(f"{BASE_URL}/api/clients", timeout=10)
        assert r3.status_code == 200
        match = next((c for c in r3.json() if c.get("id") == client_id), None)
        assert match is not None and "nikeiter16" in (match.get("name") or "").lower()

        # cleanup
        demo_client.delete(f"{BASE_URL}/api/clients/{client_id}", timeout=10)


class TestCopilotCreateProject:
    def test_create_project_confirmation_and_execute(self, demo_client):
        sid = SESSION_ID + "-proj"
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid,
                                   "message": "Create a project called TEST_Q3Website Iter16 for client Halcyon Group"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        assert r.status_code == 200, r.text
        action = r.json().get("action")
        assert action is not None
        assert action.get("tool") == "create_project"
        assert action.get("action_id"), "server must issue a confirmation token"

        r2 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": action["action_id"]},
                              timeout=30)
        assert r2.status_code == 200, r2.text
        created = r2.json().get("created") or {}
        assert created.get("type") == "project"
        pid = created.get("id")
        assert pid

        r3 = demo_client.get(f"{BASE_URL}/api/projects", timeout=10)
        assert r3.status_code == 200
        proj = next((p for p in r3.json() if p["id"] == pid), None)
        assert proj is not None
        assert "q3website" in proj["name"].lower()
        # Should be linked to Halcyon Group client if found
        clients = demo_client.get(f"{BASE_URL}/api/clients", timeout=10).json()
        halcyon = next((c for c in clients if "halcyon" in c["name"].lower()), None)
        if halcyon:
            assert proj.get("client_id") == halcyon["id"], "project must be linked to Halcyon Group"

        # cleanup
        demo_client.delete(f"{BASE_URL}/api/projects/{pid}", timeout=10)


class TestCopilotSuggestions:
    def test_suggestions_shape(self, demo_client):
        r = demo_client.get(f"{BASE_URL}/api/copilot/suggestions", timeout=10)
        assert r.status_code == 200
        body = r.json()
        # Response is a list or object with suggestions key
        if isinstance(body, dict):
            items = body.get("suggestions") or body.get("items") or []
        else:
            items = body
        assert isinstance(items, list)
        # It's OK to be empty for a clean org, but for demo we expect at least 1
        for it in items:
            assert "prompt" in it and "text" in it


class TestCopilotHistory:
    def test_history_persists(self, demo_client):
        sid = SESSION_ID + "-hist"
        # send one message
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid, "message": "Summarize today's activity"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        assert r.status_code == 200
        # fetch history
        h = demo_client.get(f"{BASE_URL}/api/copilot/history/{sid}", timeout=10)
        assert h.status_code == 200
        msgs = h.json()
        assert isinstance(msgs, list)
        assert len(msgs) >= 2  # user + assistant
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


class TestCopilotGenerateProposal:
    def test_generate_proposal_action(self, demo_client):
        # find a project
        pr = demo_client.get(f"{BASE_URL}/api/projects", timeout=10).json()
        assert pr, "demo org must have projects"
        target = next((p for p in pr if "brand" in p["name"].lower()), pr[0])
        sid = SESSION_ID + "-gen"

        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid, "message": f'Generate a proposal for {target["name"]}'},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable for message step")
        assert r.status_code == 200, r.text
        action = r.json().get("action")
        assert action is not None
        assert action.get("tool") == "generate_proposal"
        assert action.get("action_id"), "server must issue a confirmation token"

        r2 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": action["action_id"]}, timeout=120)
        # generation can 502 (LLM balance) - acceptable
        assert r2.status_code in (200, 502), r2.text
        if r2.status_code == 502:
            # graceful error
            assert "Generation failed" in r2.text or "unavailable" in r2.text.lower()


# ---------------- BRANDING EXPORTS ----------------
def _find_project_with(demo_client, kind):
    """Return a project id which has a saved doc of the given kind (proposal/contract/invoice)."""
    projs = demo_client.get(f"{BASE_URL}/api/projects", timeout=10).json()
    for p in projs:
        pid = p["id"]
        if kind == "proposal":
            r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/proposal", timeout=10)
        elif kind == "contract":
            r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/contract", timeout=10)
        elif kind == "invoice":
            r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/invoice", timeout=10)
        else:
            return None
        if r.status_code == 200 and r.json():
            return pid
    return None


class TestBrandedExports:
    def test_proposal_pdf(self, demo_client):
        pid = _find_project_with(demo_client, "proposal")
        assert pid, "demo needs a saved proposal"
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf", timeout=30)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_proposal_docx(self, demo_client):
        pid = _find_project_with(demo_client, "proposal")
        assert pid
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/docx", timeout=30)
        assert r.status_code == 200
        # docx is a zip - starts with PK
        assert r.content[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert "word/document.xml" in z.namelist()

    def test_contract_pdf(self, demo_client):
        pid = _find_project_with(demo_client, "contract")
        assert pid, "demo needs a saved contract"
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/contract/export/pdf", timeout=30)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_contract_docx(self, demo_client):
        pid = _find_project_with(demo_client, "contract")
        assert pid
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/contract/export/docx", timeout=30)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"

    def test_invoice_pdf(self, demo_client):
        pid = _find_project_with(demo_client, "invoice")
        assert pid, "demo needs a saved invoice"
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/invoice/export/pdf", timeout=30)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_invoice_docx(self, demo_client):
        pid = _find_project_with(demo_client, "invoice")
        assert pid
        r = demo_client.get(f"{BASE_URL}/api/projects/{pid}/invoice/export/docx", timeout=30)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"

    def test_exports_require_auth(self, demo_client):
        pid = _find_project_with(demo_client, "proposal")
        assert pid
        r = requests.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf", timeout=10)
        assert r.status_code in (401, 403)


class TestBrandingIsolation:
    def test_fresh_org_cannot_access_demo_project_export(self, demo_client, fresh_client):
        pid = _find_project_with(demo_client, "proposal")
        assert pid
        r = fresh_client.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf", timeout=10)
        # Should be 403 or 404 - not another org's project
        assert r.status_code in (403, 404)


# ---------------- REGRESSION SMOKE ----------------
class TestRegressionSmoke:
    @pytest.mark.parametrize("path", [
        "/api/auth/me", "/api/clients", "/api/projects", "/api/tasks",
        "/api/dashboard/summary", "/api/settings", "/api/notifications",
    ])
    def test_smoke_endpoints(self, demo_client, path):
        r = demo_client.get(f"{BASE_URL}{path}", timeout=10)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:120]}"



# ---------------- COPILOT EXECUTE SECURITY ----------------
class TestCopilotExecuteSecurity:
    def test_execute_rejects_missing_token(self, demo_client):
        # Old-style client-supplied action payload must be refused (bypass attempt).
        r = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                             json={"session_id": "sec-notoken",
                                   "action": {"tool": "create_client", "params": {"name": "HACKER Corp"}}},
                             timeout=15)
        assert r.status_code == 400, r.text

    def test_execute_rejects_forged_token(self, demo_client):
        r = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                             json={"session_id": "sec-forged", "action_id": "forged-" + uuid.uuid4().hex},
                             timeout=15)
        assert r.status_code == 404, r.text

    def test_execute_is_single_use(self, demo_client):
        sid = "sec-single-" + uuid.uuid4().hex[:6]
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid, "message": "Create a new client called TEST_SingleUse Ltd"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        action = r.json().get("action")
        assert action and action.get("action_id")
        aid = action["action_id"]
        r1 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": aid}, timeout=30)
        assert r1.status_code == 200, r1.text
        client_id = (r1.json().get("created") or {}).get("id")
        # Second execution of same token must be rejected (no double-create)
        r2 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": aid}, timeout=30)
        assert r2.status_code == 409, r2.text
        if client_id:
            demo_client.delete(f"{BASE_URL}/api/clients/{client_id}", timeout=10)

    def test_cross_org_cannot_execute_others_token(self, demo_client, fresh_client):
        sid = "sec-xorg-" + uuid.uuid4().hex[:6]
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid, "message": "Create a new client called TEST_XOrgProbe LLC"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        action = r.json().get("action")
        assert action and action.get("action_id")
        aid = action["action_id"]
        # A different org must not be able to execute the pending action.
        rx = fresh_client.post(f"{BASE_URL}/api/copilot/execute",
                               json={"session_id": sid, "action_id": aid}, timeout=30)
        assert rx.status_code == 404, rx.text
        # Original org's action must still be intact (attacker did not consume it)
        ro = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": aid}, timeout=30)
        assert ro.status_code == 200, ro.text
        cid = (ro.json().get("created") or {}).get("id")
        if cid:
            demo_client.delete(f"{BASE_URL}/api/clients/{cid}", timeout=10)

    def test_execute_logs_activity(self, demo_client):
        sid = "sec-log-" + uuid.uuid4().hex[:6]
        r = demo_client.post(f"{BASE_URL}/api/copilot/message",
                             json={"session_id": sid, "message": "Create a project called TEST_LogProbe Site"},
                             timeout=60)
        if r.status_code == 502:
            pytest.skip("LLM unavailable")
        action = r.json().get("action")
        assert action and action.get("action_id")
        r2 = demo_client.post(f"{BASE_URL}/api/copilot/execute",
                              json={"session_id": sid, "action_id": action["action_id"]}, timeout=30)
        assert r2.status_code == 200, r2.text
        pid = (r2.json().get("created") or {}).get("id")
        # A copilot_action activity should be logged for the project
        acts = demo_client.get(f"{BASE_URL}/api/activities?project_id={pid}", timeout=10)
        if acts.status_code == 200:
            types = [a.get("type") for a in acts.json()]
            assert "copilot_action" in types, types
        if pid:
            demo_client.delete(f"{BASE_URL}/api/projects/{pid}", timeout=10)
