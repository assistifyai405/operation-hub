"""AI service layer — provider-agnostic wrapper.

Future-ready: swap providers/models via env (AI_PROVIDER, AI_MODEL) or per-call
with_model(). Today it routes through emergentintegrations (OpenAI / Anthropic /
Gemini). Prompts live in config modules, never hardcoded in endpoints.
"""
import os
import json
import uuid
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, api_key: str, provider: str = None, model: str = None):
        self.api_key = api_key
        self.provider = provider or os.environ.get("AI_PROVIDER", "openai")
        self.model = model or os.environ.get("AI_MODEL", "gpt-5.4")

    def with_model(self, provider: str, model: str):
        return AIService(self.api_key, provider, model)

    async def complete(self, system_message: str, prompt: str, session_id: str = None) -> str:
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id or str(uuid.uuid4()),
            system_message=system_message,
        ).with_model(self.provider, self.model)
        resp = await chat.send_message(UserMessage(text=prompt))
        return resp if isinstance(resp, str) else str(resp)

    async def complete_json(self, system_message: str, prompt: str, keys: list, session_id: str = None) -> dict:
        text = await self.complete(system_message, prompt, session_id)
        return parse_json(text, keys)


def extract_json(text: str) -> dict:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1:
        t = t[s:e + 1]
    return json.loads(t)


def parse_json(text: str, keys: list) -> dict:
    data = extract_json(text)
    return {k["key"]: data.get(k["key"], "" if k["type"] == "text" else []) for k in keys}
