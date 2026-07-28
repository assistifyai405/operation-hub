"""Central environment configuration and startup validation.

Load order: call ``load_settings()`` once after dotenv is loaded (see core.py).
Development defaults are ONLY applied when ENVIRONMENT=development.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Secrets that must never be used outside local development.
WEAK_JWT_SECRETS = {
    "",
    "secret",
    "changeme",
    "change-me",
    "change-me-to-a-long-random-string",
    "jwt_secret",
    "jwt-secret",
    "your-secret",
    "your-secret-here",
    "assistify",
    "assistify-secret",
    "dev",
    "development",
    "test",
    "testing",
}


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unsafe."""


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip()


def _truthy(name: str, default: bool = False) -> bool:
    v = _env(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str  # development | production | test
    mongo_url: str
    db_name: str
    jwt_secret: str
    cors_origins: list
    frontend_url: str
    enable_demo_seed: bool
    demo_email: str
    demo_password: str
    ai_provider: str  # openai | emergent
    ai_model: str
    openai_api_key: Optional[str]
    emergent_llm_key: Optional[str]
    storage_provider: str  # local | emergent
    upload_dir: str
    resend_api_key: Optional[str]
    from_email: str
    cookie_secure: bool
    cookie_samesite: str  # lax | none | strict

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    if _settings is None:
        raise ConfigError("Settings not loaded — call load_settings() first")
    return _settings


def reset_settings_for_tests() -> None:
    """Clear cached settings (unit tests only)."""
    global _settings
    _settings = None


def _resolve_environment() -> str:
    raw = (_env("ENVIRONMENT") or _env("ENV") or "development").lower()
    if raw in {"prod", "production"}:
        return "production"
    if raw in {"dev", "development", "local"}:
        return "development"
    if raw in {"test", "testing"}:
        return "test"
    # Unknown values: treat as production for safety
    logger.warning("Unknown ENVIRONMENT=%r — treating as production", raw)
    return "production"


def _resolve_cookie(environment: str, frontend_url: str) -> tuple[bool, str]:
    """Return (secure, samesite).

    Development/local HTTP → secure=False, samesite=lax (works on localhost).
    Production (or HTTPS frontend) → secure=True, samesite=none (cross-origin SPA).
    Explicit overrides: COOKIE_SECURE, COOKIE_SAMESITE.
    """
    fe = (frontend_url or "").lower()
    https_frontend = fe.startswith("https://")
    if environment == "development" and not https_frontend:
        secure, samesite = False, "lax"
    elif environment == "test":
        secure, samesite = False, "lax"
    else:
        secure, samesite = True, "none"

    override_secure = _env("COOKIE_SECURE")
    if override_secure is not None:
        secure = override_secure.lower() in {"1", "true", "yes", "on"}
    override_samesite = _env("COOKIE_SAMESITE")
    if override_samesite:
        samesite = override_samesite.lower()
    if samesite not in {"lax", "none", "strict"}:
        raise ConfigError(f"COOKIE_SAMESITE must be lax|none|strict, got {samesite!r}")
    if samesite == "none" and not secure:
        # Browsers reject SameSite=None without Secure — fall back safely in dev.
        if environment == "development":
            samesite = "lax"
        else:
            raise ConfigError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
    return secure, samesite


def _validate_jwt(secret: str, environment: str) -> None:
    if not secret:
        raise ConfigError("JWT_SECRET is required")
    lowered = secret.strip().lower()
    if environment == "production":
        if lowered in WEAK_JWT_SECRETS or len(secret) < 32:
            raise ConfigError(
                "JWT_SECRET is missing, too short (<32 chars), or matches a known weak/default value. "
                "Set a strong random secret in production."
            )
    elif lowered in WEAK_JWT_SECRETS:
        logger.warning("JWT_SECRET looks weak — acceptable only for local development")


def load_settings(*, strict: bool = True) -> Settings:
    """Validate and cache settings. Raises ConfigError when strict and invalid."""
    global _settings
    environment = _resolve_environment()

    mongo_url = _env("MONGO_URL")
    db_name = _env("DB_NAME")
    jwt_secret = _env("JWT_SECRET")

    missing = [n for n, v in [("MONGO_URL", mongo_url), ("DB_NAME", db_name), ("JWT_SECRET", jwt_secret)] if not v]
    if missing:
        msg = f"Missing required environment variable(s): {', '.join(missing)}"
        if strict:
            raise ConfigError(msg)
        logger.error(msg)

    if jwt_secret:
        _validate_jwt(jwt_secret, environment)

    cors_raw = _env("CORS_ORIGINS")
    if environment == "production":
        if not cors_raw or cors_raw.strip() == "*":
            raise ConfigError(
                "CORS_ORIGINS must be set to an explicit comma-separated allow-list in production "
                "(wildcard '*' is not allowed)."
            )
        cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
        if not cors_origins:
            raise ConfigError("CORS_ORIGINS is empty after parsing")
    else:
        # Development convenience: allow all when unset
        cors_origins = [o.strip() for o in (cors_raw or "*").split(",") if o.strip()] or ["*"]

    frontend_url = _env("FRONTEND_URL", "http://localhost:3000") or "http://localhost:3000"
    cookie_secure, cookie_samesite = _resolve_cookie(environment, frontend_url)

    ai_provider = (_env("AI_PROVIDER", "openai") or "openai").lower()
    if ai_provider not in {"openai", "emergent"}:
        raise ConfigError(f"AI_PROVIDER must be 'openai' or 'emergent', got {ai_provider!r}")
    default_model = "gpt-5.4" if ai_provider == "emergent" else "gpt-4o-mini"
    ai_model = _env("AI_MODEL", default_model) or default_model

    storage_provider = (_env("STORAGE_PROVIDER", "local" if environment != "production" else "emergent") or "local").lower()
    if storage_provider not in {"local", "emergent"}:
        raise ConfigError(f"STORAGE_PROVIDER must be 'local' or 'emergent', got {storage_provider!r}")

    upload_dir = _env("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads")) or "uploads"

    # Demo seed: NEVER default-on in production. Explicit ENABLE_DEMO_SEED=true required.
    if environment == "production":
        enable_demo_seed = _truthy("ENABLE_DEMO_SEED", False)
    else:
        enable_demo_seed = _truthy("ENABLE_DEMO_SEED", False)

    settings = Settings(
        environment=environment,
        mongo_url=mongo_url or "",
        db_name=db_name or "",
        jwt_secret=jwt_secret or "",
        cors_origins=cors_origins,
        frontend_url=frontend_url.rstrip("/"),
        enable_demo_seed=enable_demo_seed,
        demo_email=(_env("DEMO_EMAIL", "jordan@assistify.io") or "jordan@assistify.io").lower(),
        demo_password=_env("DEMO_PASSWORD", "change-me-demo-password") or "change-me-demo-password",
        ai_provider=ai_provider,
        ai_model=ai_model,
        openai_api_key=_env("OPENAI_API_KEY"),
        emergent_llm_key=_env("EMERGENT_LLM_KEY"),
        storage_provider=storage_provider,
        upload_dir=upload_dir,
        resend_api_key=_env("RESEND_API_KEY"),
        from_email=_env("FROM_EMAIL", "onboarding@resend.dev") or "onboarding@resend.dev",
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
    )
    _settings = settings
    return settings


def resolve_ai_api_key(settings: Optional[Settings] = None) -> str:
    """Return the API key for the configured AI provider, or raise a clear error."""
    s = settings or get_settings()
    if s.ai_provider == "openai":
        if s.openai_api_key:
            return s.openai_api_key
        # Backward-compatible: some Emergent keys also work via their OpenAI-compatible proxy,
        # but for AI_PROVIDER=openai we require OPENAI_API_KEY explicitly.
        raise ConfigError(
            "AI_PROVIDER=openai requires OPENAI_API_KEY to be set. "
            "Set OPENAI_API_KEY or switch AI_PROVIDER=emergent with EMERGENT_LLM_KEY."
        )
    if s.ai_provider == "emergent":
        if s.emergent_llm_key:
            return s.emergent_llm_key
        raise ConfigError(
            "AI_PROVIDER=emergent requires EMERGENT_LLM_KEY to be set. "
            "Set EMERGENT_LLM_KEY or switch AI_PROVIDER=openai with OPENAI_API_KEY."
        )
    raise ConfigError(f"Unknown AI_PROVIDER: {s.ai_provider}")
