"""Assistify Workspace Assistant — the omnipresent, context-aware AI employee.

Coexists with Copilot (which owns create/generate actions). This assistant adds
document intelligence (rewrite/improve/translate/summarize/etc.) with an "Explain
Everything" report, plus context-aware streaming chat. Reuses ai_service and the
copilot workspace snapshot — no duplicated logic.
"""
import json
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from core import db, now_iso, ai_service, EMERGENT_LLM_KEY
from ai_service import extract_json
from dependencies import current_org
from routers.copilot import _copilot_snapshot
from routers.memory import build_memory_context

router = APIRouter(prefix="/api/assistant")

# action -> (label, instruction verb, mode, minutes saved)
# mode: "transform" = produces text to APPLY to the document; "info" = chat answer only
ACTIONS = {
    "improve": ("Improve writing", "Improve the writing so it is clearer, more persuasive and professional", "transform", 6),
    "rewrite": ("Rewrite professionally", "Rewrite in a polished, professional business tone", "transform", 7),
    "shorten": ("Shorten", "Make it more concise and punchy without losing meaning", "transform", 4),
    "expand": ("Expand", "Expand with relevant, specific and useful detail", "transform", 6),
    "fix_grammar": ("Fix grammar", "Fix grammar, spelling and punctuation only, preserving meaning and tone", "transform", 3),
    "translate": ("Translate", "Translate the content into {arg}", "transform", 8),
    "exec_summary": ("Executive summary", "Write a compelling, concise executive summary", "transform", 9),
    "explain": ("Explain this", "Explain in plain language what this means and why it matters", "info", 4),
    "summarize": ("Summarize", "Write a concise, well-structured summary", "info", 8),
    "pricing": ("Suggest pricing", "Recommend sensible pricing with a short rationale", "info", 7),
    "timeline": ("Suggest timeline", "Propose a realistic project timeline broken into phases", "info", 6),
    "deliverables": ("Suggest deliverables", "Propose a clear, client-ready list of deliverables", "info", 6),
    "weak": ("Find weak sections", "Identify weak, vague or unconvincing wording and suggest concrete fixes", "info", 6),
    "risks": ("Highlight risks", "Highlight risks and things a client might push back on", "info", 6),
    "missing": ("Missing information", "List important information that appears to be missing and should be added", "info", 5),
    "tone": ("Review tone", "Assess the tone and suggest adjustments to better suit the client", "info", 4),
    "faq": ("Generate FAQs", "Generate a helpful FAQ the client is likely to ask, with answers", "info", 9),
    "email": ("Follow-up email", "Write a professional, warm follow-up email to send to the client", "info", 9),
    "cover": ("Cover letter", "Write a short, warm cover letter to accompany this document", "info", 9),
    "brainstorm": ("Brainstorm", "Brainstorm useful ideas, angles and options", "info", 5),
}

_BASE_PERSONA = (
    "You are Assistify, a sharp, warm and highly capable AI business assistant working alongside a founder — "
    "like a blend of ChatGPT, Notion AI and Cursor. You are concise, professional and genuinely helpful. "
    "You never invent facts that aren't supported by the provided context."
)


class ActionRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command: str
    instruction: Optional[str] = ""
    arg: Optional[str] = ""  # e.g. target language for translate
    context: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    context: dict = Field(default_factory=dict)


def _confidence(text_len: int, has_ctx: bool) -> int:
    score = 88 + (4 if has_ctx else 0) + (min(4, text_len // 400))
    return min(98, score)


def _ctx_line(ctx: dict) -> str:
    scope = ctx.get("scope")
    name = ctx.get("entityName")
    dt = ctx.get("documentType")
    if scope == "document" and dt:
        return f"the {name} {dt}" if name else f"this {dt}"
    if scope == "project":
        return f"the {name} project" if name else "this project"
    if scope == "client":
        return f"the client {name}" if name else "this client"
    if ctx.get("label"):
        return ctx["label"]
    return "your workspace"


async def _persist(session_id, org, role, content, extra=None):
    doc = {"id": str(uuid.uuid4()), "session_id": session_id, "organizationId": org,
           "role": role, "content": content, "created_at": now_iso()}
    if extra:
        doc.update(extra)
    await db.assistant_messages.insert_one(doc)


@router.get("/history/{session_id}")
async def assistant_history(session_id: str, org: str = Depends(current_org)):
    return await db.assistant_messages.find(
        {"session_id": session_id, "organizationId": org}, {"_id": 0}).sort("created_at", 1).to_list(500)


@router.get("/suggestions")
async def assistant_suggestions(scope: str = "generic", document_type: str = ""):
    """Context-aware suggested action chips shown when the assistant / a doc opens."""
    doc_chips = {
        "proposal": ["improve", "exec_summary", "pricing", "weak", "tone", "translate", "email", "faq"],
        "contract": ["explain", "risks", "missing", "rewrite", "translate", "summarize"],
        "invoice": ["explain", "email", "tone", "fix_grammar", "translate"],
        "plan": ["improve", "timeline", "deliverables", "risks", "summarize", "brainstorm"],
    }
    keys = doc_chips.get(document_type) if scope == "document" else None
    if not keys:
        if scope == "project":
            keys = ["summarize", "risks", "timeline", "deliverables", "brainstorm"]
        elif scope == "client":
            keys = ["summarize", "email", "brainstorm"]
        else:
            keys = ["summarize", "brainstorm", "email"]
    return [{"command": k, "label": ACTIONS[k][0], "mode": ACTIONS[k][2]} for k in keys if k in ACTIONS]


def _sections_payload(ctx: dict):
    return ctx.get("sections") or []


@router.post("/action")
async def assistant_action(payload: ActionRequest, org: str = Depends(current_org)):
    spec = ACTIONS.get(payload.command)
    if not spec:
        raise HTTPException(status_code=400, detail="Unknown assistant command")
    label, verb, mode, minutes = spec
    verb = verb.replace("{arg}", payload.arg or "the requested language")
    ctx = payload.context or {}
    section = ctx.get("section")
    sections = _sections_payload(ctx)
    where = _ctx_line(ctx)
    mem = await build_memory_context(org)
    instr = (payload.instruction or "").strip()
    await _persist(payload.session_id, org, "user", f"/{payload.command}" + (f" {instr}" if instr else ""),
                   {"command": payload.command})

    try:
        if mode == "transform" and section:
            # Single-section transform → apply to that section.
            stype = section.get("type", "text")
            value = section.get("value")
            val_str = "\n".join(value) if isinstance(value, list) else (value or "")
            fmt = "a JSON array of strings" if stype == "list" else "a string"
            system = (f"{_BASE_PERSONA}\n{verb}. You are editing the \"{section.get('label')}\" section of {where}. "
                      f"Return ONLY a JSON object: {{\"result\": {fmt}, \"what\": string, \"why\": string, \"impact\": string}}. "
                      f"\"result\" is the rewritten section content ONLY. what/why/impact are one short sentence each.")
            prompt = f"CURRENT SECTION CONTENT:\n{val_str}\n\nADDITIONAL INSTRUCTION: {instr or '(none)'}{mem}"
            raw = await ai_service.complete(system, prompt, session_id=f"asst-{payload.session_id}")
            data = extract_json(raw)
            result = data.get("result", "")
            report = {"what": data.get("what", label), "why": data.get("why", ""),
                      "impact": data.get("impact", ""), "time_saved": minutes,
                      "confidence": _confidence(len(val_str), True)}
            answer = f"I updated the **{section.get('label')}** section. Review the change below and apply it if it looks good."
            apply = {"mode": "section", "target": section.get("key"), "value": result}

        elif mode == "transform":
            # Whole-document transform → return per-section results.
            body = [{"key": s.get("key"), "label": s.get("label"), "type": s.get("type", "text"),
                     "value": s.get("value")} for s in sections]
            system = (f"{_BASE_PERSONA}\n{verb} across the whole document ({where}). "
                      "Return ONLY a JSON object: {\"sections\": { \"<key>\": <new value>, ... }, "
                      "\"what\": string, \"why\": string, \"impact\": string}. "
                      "Preserve each section's type: text=string, list=array of strings. "
                      "Include ONLY sections you actually changed. Keep it professional and client-ready.")
            prompt = f"DOCUMENT SECTIONS (JSON):\n{json.dumps(body, default=str)}\n\nADDITIONAL INSTRUCTION: {instr or '(none)'}{mem}"
            raw = await ai_service.complete(system, prompt, session_id=f"asst-{payload.session_id}")
            data = extract_json(raw)
            values = data.get("sections", {}) or {}
            report = {"what": data.get("what", label), "why": data.get("why", ""),
                      "impact": data.get("impact", ""), "time_saved": minutes + 3,
                      "confidence": _confidence(sum(len(str(s.get("value"))) for s in sections), bool(sections))}
            answer = f"I applied **{label}** across {len(values)} section(s) of {where}. Apply the changes when ready."
            apply = {"mode": "document", "values": values}

        else:
            # Info: produce a helpful markdown answer (not applied to the doc).
            has_sections = bool(sections)
            ctx_blob = json.dumps([{"label": s.get("label"), "value": s.get("value")} for s in sections], default=str) if has_sections else ""
            extra_ctx = ""
            if not has_sections and ctx.get("scope") in ("project", "client") and ctx.get("entityId"):
                extra_ctx = await _entity_context(org, ctx)
            system = (f"{_BASE_PERSONA}\n{verb}. Context: you are looking at {where}. "
                      "Answer in clear, well-structured GitHub-flavored markdown (use headings, bold and bullet lists where helpful). "
                      "Then append a line that starts with '@@META@@' followed by a compact JSON object "
                      "{\"what\": string, \"why\": string, \"impact\": string} (one short sentence each). Output nothing after that JSON.")
            prompt = f"DOCUMENT CONTENT:\n{ctx_blob or extra_ctx or '(no document content provided)'}\n\nUSER INSTRUCTION: {instr or '(none)'}{mem}"
            raw = await ai_service.complete(system, prompt, session_id=f"asst-{payload.session_id}")
            answer, meta = _split_meta(raw)
            report = {"what": meta.get("what", label), "why": meta.get("why", ""),
                      "impact": meta.get("impact", ""), "time_saved": minutes,
                      "confidence": _confidence(len(answer), has_sections or bool(extra_ctx))}
            apply = None

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="The assistant returned an unexpected format. Please try again.")
    except Exception as e:
        logging.exception("assistant action failed")
        raise HTTPException(status_code=502, detail=f"The assistant is unavailable right now: {e}")

    await _persist(payload.session_id, org, "assistant", answer,
                   {"report": report, "apply": apply, "command": payload.command})
    return {"answer": answer, "apply": apply, "report": report, "session_id": payload.session_id}


def _split_meta(raw: str):
    text = (raw or "").strip()
    if "@@META@@" in text:
        body, _, meta_str = text.partition("@@META@@")
        try:
            meta = extract_json(meta_str)
        except Exception:
            meta = {}
        return body.strip(), meta
    return text, {}


async def _entity_context(org: str, ctx: dict) -> str:
    scope, eid = ctx.get("scope"), ctx.get("entityId")
    if scope == "project":
        p = await db.projects.find_one({"id": eid, "organizationId": org}, {"_id": 0})
        if not p:
            return ""
        tasks = await db.tasks.find({"project_id": eid, "organizationId": org}, {"_id": 0, "title": 1, "done": 1, "due": 1}).to_list(50)
        return json.dumps({"project": {"name": p.get("name"), "status": p.get("status"), "description": p.get("description"),
                                       "notes": p.get("notes"), "due": p.get("due"), "progress": p.get("progress")},
                           "tasks": tasks}, default=str)
    if scope == "client":
        c = await db.clients.find_one({"id": eid, "organizationId": org}, {"_id": 0})
        if not c:
            return ""
        projs = await db.projects.find({"client_id": eid, "organizationId": org}, {"_id": 0, "name": 1, "status": 1}).to_list(50)
        return json.dumps({"client": {"name": c.get("name"), "contact": c.get("contact"), "email": c.get("email"),
                                      "value": c.get("value"), "status": c.get("status")}, "projects": projs}, default=str)
    return ""


@router.post("/chat/stream")
async def assistant_chat_stream(payload: ChatRequest, org: str = Depends(current_org)):
    ctx = payload.context or {}
    where = _ctx_line(ctx)
    await _persist(payload.session_id, org, "user", payload.message)

    snapshot = await _copilot_snapshot(org)
    doc_ctx = ""
    sections = _sections_payload(ctx)
    if sections:
        doc_ctx = "\nOPEN DOCUMENT SECTIONS:\n" + json.dumps(
            [{"label": s.get("label"), "value": s.get("value")} for s in sections], default=str)[:6000]
    elif ctx.get("scope") in ("project", "client") and ctx.get("entityId"):
        doc_ctx = "\nCURRENT ENTITY:\n" + (await _entity_context(org, ctx))[:6000]

    system = (
        f"{_BASE_PERSONA}\n"
        f"The user is currently viewing {where}. Be proactively aware of that — never ask them what page they're on. "
        "You have READ access to their workspace data and the open document (below). Answer questions helpfully using this data. "
        "Respond in clean, GitHub-flavored markdown (headings, bold, bullet lists, and code blocks when relevant). "
        "If the user wants to CREATE or GENERATE something (a new client, project, proposal, contract, invoice or plan), "
        "tell them you'll open the Copilot command center to do it — do not fabricate that it's done. Keep replies focused and concise."
    )
    prompt = f"WORKSPACE DATA (JSON):\n{snapshot}{doc_ctx}{await build_memory_context(org)}\n\nUSER MESSAGE:\n{payload.message}"

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"asst-chat-{payload.session_id}",
                   system_message=system).with_model("openai", "gpt-5.4")

    async def gen():
        full = ""
        try:
            async for event in chat.stream_message(UserMessage(text=prompt)):
                if isinstance(event, TextDelta):
                    full += event.content
                    yield f"data: {json.dumps({'delta': event.content})}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as e:
            logging.exception("assistant stream error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            report = {"time_saved": 4, "confidence": _confidence(len(full), bool(doc_ctx))}
            if full:
                await _persist(payload.session_id, org, "assistant", full, {"report": report})
            yield f"data: {json.dumps({'done': True, 'report': report})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
