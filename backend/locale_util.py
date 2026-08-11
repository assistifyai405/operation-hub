"""UI locale helpers — nl | en only (Sprint 29)."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

ALLOWED_LOCALES = {"nl", "en"}
DEFAULT_LOCALE = "en"

_ai_locale: ContextVar[Optional[str]] = ContextVar("ai_locale", default=None)


def normalize_locale(raw: Optional[str]) -> str:
    if not raw or not isinstance(raw, str):
        return DEFAULT_LOCALE
    lower = raw.strip().lower().replace("_", "-")
    if lower == "nl" or lower.startswith("nl-"):
        return "nl"
    if lower == "en" or lower.startswith("en-"):
        return "en"
    return DEFAULT_LOCALE


def bind_ai_locale(locale: Optional[str]):
    return _ai_locale.set(normalize_locale(locale) if locale else DEFAULT_LOCALE)


def get_bound_ai_locale() -> str:
    return _ai_locale.get() or DEFAULT_LOCALE


def is_allowed_locale(raw: Optional[str]) -> bool:
    if not raw or not isinstance(raw, str):
        return False
    lower = raw.strip().lower().replace("_", "-")
    if lower in ALLOWED_LOCALES:
        return True
    if lower.startswith("nl-") or lower.startswith("en-"):
        return True
    return False


def language_instruction_for_user(user: Optional[dict] = None, locale: Optional[str] = None) -> str:
    """Append to AI system prompts. Explicit user prompt language still wins."""
    code = normalize_locale(
        locale or (user or {}).get("language") or (user or {}).get("locale") or get_bound_ai_locale()
    )
    if code == "nl":
        return (
            "Preferred response language: Dutch (Nederlands). "
            "Write all assistant replies and generated document content in Dutch "
            "unless the user explicitly asks for another language."
        )
    return (
        "Preferred response language: English. "
        "Write all assistant replies and generated document content in English "
        "unless the user explicitly asks for another language."
    )


def with_language_instruction(system_message: str, user: Optional[dict] = None, locale: Optional[str] = None) -> str:
    base = (system_message or "").rstrip()
    instr = language_instruction_for_user(user, locale)
    if "Preferred response language:" in base:
        return base
    return f"{base}\n\n{instr}"
