"""AI service layer — provider-agnostic wrapper.

Supports:
  - AI_PROVIDER=openai   → direct OpenAI API via OPENAI_API_KEY
  - AI_PROVIDER=emergent → Emergent LLM proxy via EMERGENT_LLM_KEY (optional fallback)

Prompts live in config modules. Product code should call AIService.complete /
complete_json / stream — not provider SDKs directly.
"""
from __future__ import annotations

import os
import json
import uuid
import logging
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class AIConfigError(RuntimeError):
    """Raised when the selected AI provider has no usable API key."""


_SECRETISH = ("sk-", "api_key", "apikey", "bearer ", "authorization", "emergent")


def public_ai_error(exc: BaseException, fallback: str = "AI is unavailable right now. Please try again.") -> str:
    """Return a user-safe AI error string — never include API keys or raw provider payloads."""
    msg = str(exc or "")
    low = msg.lower()
    if any(s in low for s in _SECRETISH):
        if "incorrect api key" in low or "invalid_api_key" in low or "authentication" in low:
            return "AI is not configured correctly. Ask your admin to check the API key."
        return fallback
    # Keep short, non-sensitive operational messages
    cleaned = msg.strip().split("\n")[0][:180]
    if not cleaned or cleaned.startswith("Error code:"):
        return fallback
    return cleaned or fallback


class AIService:
    def __init__(self, api_key: str = None, provider: str = None, model: str = None):
        # Lazy import config to avoid circular imports at module load in tests
        self.provider = (provider or os.environ.get("AI_PROVIDER") or "openai").lower()
        self.model = model or os.environ.get("AI_MODEL") or "gpt-4o-mini"
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._resolve_key(self.provider)

    def _resolve_key(self, provider: str) -> str:
        try:
            from config import resolve_ai_api_key, get_settings, ConfigError
            try:
                return resolve_ai_api_key(get_settings())
            except ConfigError:
                # Settings may not be loaded yet — fall back to env directly
                pass
        except Exception:
            pass
        if provider == "openai":
            key = (os.environ.get("OPENAI_API_KEY") or "").strip()
            if not key:
                raise AIConfigError(
                    "AI_PROVIDER=openai requires OPENAI_API_KEY. "
                    "Set OPENAI_API_KEY or use AI_PROVIDER=emergent with EMERGENT_LLM_KEY."
                )
            return key
        if provider == "emergent":
            key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
            if not key:
                raise AIConfigError(
                    "AI_PROVIDER=emergent requires EMERGENT_LLM_KEY. "
                    "Set EMERGENT_LLM_KEY or use AI_PROVIDER=openai with OPENAI_API_KEY."
                )
            return key
        raise AIConfigError(f"Unknown AI_PROVIDER: {provider!r} (expected openai|emergent)")

    def with_model(self, provider: str, model: str):
        return AIService(self.api_key, provider, model)

    async def complete(self, system_message: str, prompt: str, session_id: str = None) -> str:
        if self.provider == "openai":
            return await self._complete_openai(system_message, prompt)
        if self.provider == "emergent":
            return await self._complete_emergent(system_message, prompt, session_id)
        raise AIConfigError(f"Unsupported AI_PROVIDER: {self.provider}")

    async def complete_json(self, system_message: str, prompt: str, keys: list, session_id: str = None) -> dict:
        text = await self.complete(system_message, prompt, session_id)
        return parse_json(text, keys)

    async def stream(self, system_message: str, prompt: str, session_id: str = None) -> AsyncIterator[str]:
        """Yield text deltas for SSE endpoints."""
        if self.provider == "openai":
            async for chunk in self._stream_openai(system_message, prompt):
                yield chunk
            return
        if self.provider == "emergent":
            async for chunk in self._stream_emergent(system_message, prompt, session_id):
                yield chunk
            return
        raise AIConfigError(f"Unsupported AI_PROVIDER: {self.provider}")

    # ---- OpenAI ----
    async def _complete_openai(self, system_message: str, prompt: str) -> str:
        if not self.api_key:
            raise AIConfigError("OPENAI_API_KEY is not configured")
        try:
            from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIStatusError
        except ImportError as e:
            raise AIConfigError("openai package is not installed") from e
        client = AsyncOpenAI(api_key=self.api_key)
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
            )
        except AuthenticationError as e:
            logger.warning("openai auth failed: %s", public_ai_error(e))
            raise AIConfigError("OPENAI_API_KEY is invalid or missing") from e
        except RateLimitError as e:
            logger.warning("openai rate limited")
            raise RuntimeError("AI rate limit reached. Please try again shortly.") from e
        except APIStatusError as e:
            logger.warning("openai api status %s", getattr(e, "status_code", "?"))
            raise RuntimeError("AI provider returned an error. Please try again.") from e
        return (resp.choices[0].message.content or "").strip()

    async def _stream_openai(self, system_message: str, prompt: str) -> AsyncIterator[str]:
        if not self.api_key:
            raise AIConfigError("OPENAI_API_KEY is not configured")
        try:
            from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIStatusError
        except ImportError as e:
            raise AIConfigError("openai package is not installed") from e
        client = AsyncOpenAI(api_key=self.api_key)
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            async for event in stream:
                try:
                    delta = event.choices[0].delta.content
                except Exception:
                    delta = None
                if delta:
                    yield delta
        except AuthenticationError as e:
            logger.warning("openai stream auth failed: %s", public_ai_error(e))
            raise AIConfigError("OPENAI_API_KEY is invalid or missing") from e
        except RateLimitError as e:
            logger.warning("openai stream rate limited")
            raise RuntimeError("AI rate limit reached. Please try again shortly.") from e
        except APIStatusError as e:
            logger.warning("openai stream api status %s", getattr(e, "status_code", "?"))
            raise RuntimeError("AI provider returned an error. Please try again.") from e

    # ---- Emergent (optional) ----
    async def _complete_emergent(self, system_message: str, prompt: str, session_id: str = None) -> str:
        if not self.api_key:
            raise AIConfigError("EMERGENT_LLM_KEY is not configured")
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
        except ImportError as e:
            raise AIConfigError(
                "emergentintegrations is not installed. "
                "Install it or set AI_PROVIDER=openai with OPENAI_API_KEY."
            ) from e
        # Emergent routes through its own model namespace; keep openai/* as before.
        model = self.model
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id or str(uuid.uuid4()),
            system_message=system_message,
        ).with_model("openai", model)
        resp = await chat.send_message(UserMessage(text=prompt))
        return resp if isinstance(resp, str) else str(resp)

    async def _stream_emergent(self, system_message: str, prompt: str, session_id: str = None) -> AsyncIterator[str]:
        if not self.api_key:
            raise AIConfigError("EMERGENT_LLM_KEY is not configured")
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
        except ImportError as e:
            raise AIConfigError(
                "emergentintegrations is not installed. "
                "Install it or set AI_PROVIDER=openai with OPENAI_API_KEY."
            ) from e
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id or str(uuid.uuid4()),
            system_message=system_message,
        ).with_model("openai", self.model)
        async for event in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(event, TextDelta):
                yield event.content
            elif isinstance(event, StreamDone):
                break


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


def build_ai_service_from_settings():
    """Construct AIService from validated settings (used by core.py)."""
    from config import get_settings, resolve_ai_api_key, ConfigError
    s = get_settings()
    try:
        key = resolve_ai_api_key(s)
    except ConfigError as e:
        # Defer hard failure until first AI call — app can still boot for CRUD/auth.
        logger.warning("AI provider not fully configured: %s", e)
        return AIService(api_key="", provider=s.ai_provider, model=s.ai_model)
    return AIService(api_key=key, provider=s.ai_provider, model=s.ai_model)
