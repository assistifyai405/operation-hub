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
    "local-dev-secret-change-me-32chars!!",
    "unit-test-secret-key-with-32plus-chars!!",
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
    enable_demo_login: bool
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
    from_name: str
    reply_to_email: Optional[str]
    email_provider: str  # resend | console
    email_sending_enabled: bool
    email_daily_limit: int
    resend_webhook_secret: Optional[str]
    integration_encryption_key: Optional[str]
    google_client_id: Optional[str]
    google_client_secret: Optional[str]
    google_redirect_uri: Optional[str]
    microsoft_client_id: Optional[str]
    microsoft_client_secret: Optional[str]
    microsoft_tenant: str
    microsoft_redirect_uri: Optional[str]
    slack_client_id: Optional[str]
    slack_client_secret: Optional[str]
    slack_redirect_uri: Optional[str]
    cookie_secure: bool
    cookie_samesite: str  # lax | none | strict
    invitation_expiry_days: int
    # Sprint 18 ops / deployment
    redis_url: Optional[str]
    log_level: str
    trusted_hosts: list
    worker_enabled: bool
    scheduler_enabled: bool
    require_redis: bool
    sentry_dsn: Optional[str]
    release_version: str
    app_url: Optional[str]
    api_url: Optional[str]
    inbox_sync_interval_minutes: int
    integration_health_interval_minutes: int
    email_reconciliation_interval_minutes: int
    json_logs: bool

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

    # Demo tooling: NEVER default-on. Explicit ENABLE_DEMO_SEED / ENABLE_DEMO_LOGIN required.
    enable_demo_seed = _truthy("ENABLE_DEMO_SEED", False)
    enable_demo_login = _truthy("ENABLE_DEMO_LOGIN", False)
    allow_demo_in_production = _truthy("ALLOW_DEMO_IN_PRODUCTION", False)

    # Production hard-disable: demo features stay off unless explicitly allowed.
    if environment == "production" and not allow_demo_in_production:
        if enable_demo_seed or enable_demo_login:
            logger.warning(
                "Demo flags requested in production but ALLOW_DEMO_IN_PRODUCTION is false — forcing demo off"
            )
        enable_demo_seed = False
        enable_demo_login = False

    demo_email = (_env("DEMO_EMAIL", "jordan@assistify.io") or "jordan@assistify.io").lower()
    demo_password = _env("DEMO_PASSWORD", "change-me-demo-password") or "change-me-demo-password"
    _WEAK_DEMO_PASSWORDS = {"change-me-demo-password", "Assistify2026!", "password", "demo", "changeme"}
    if enable_demo_seed and environment == "production" and demo_password in _WEAK_DEMO_PASSWORDS:
        raise ConfigError(
            "DEMO_PASSWORD must be set to a strong unique value when ENABLE_DEMO_SEED=true in production"
        )
    if enable_demo_seed and environment == "production" and not demo_password.strip():
        raise ConfigError("DEMO_PASSWORD is required when ENABLE_DEMO_SEED=true in production")

    # Production URL sanity — refuse localhost frontend/CORS in production.
    if environment == "production":
        fe_l = frontend_url.lower()
        if "localhost" in fe_l or "127.0.0.1" in fe_l:
            raise ConfigError("FRONTEND_URL must be a public HTTPS origin in production (not localhost)")
        if not fe_l.startswith("https://"):
            raise ConfigError("FRONTEND_URL must use https:// in production")
        for o in cors_origins:
            ol = o.lower()
            if "localhost" in ol or "127.0.0.1" in ol:
                raise ConfigError(f"CORS_ORIGINS must not include localhost in production: {o!r}")
            if not ol.startswith("https://"):
                raise ConfigError(f"CORS_ORIGINS entries must use https:// in production: {o!r}")

    # Production encryption key for OAuth tokens at rest
    integration_encryption_key = _env("INTEGRATION_ENCRYPTION_KEY")
    if environment == "production" and not integration_encryption_key:
        raise ConfigError(
            "INTEGRATION_ENCRYPTION_KEY is required in production "
            "(generate a Fernet key or a long random secret)"
        )

    # AI provider keys required in production (smoke/deploy without AI is not first-launch ready)
    openai_api_key = _env("OPENAI_API_KEY")
    emergent_llm_key = _env("EMERGENT_LLM_KEY")
    if environment == "production":
        if ai_provider == "openai" and not openai_api_key:
            raise ConfigError("OPENAI_API_KEY is required in production when AI_PROVIDER=openai")
        if ai_provider == "emergent" and not emergent_llm_key:
            raise ConfigError("EMERGENT_LLM_KEY is required in production when AI_PROVIDER=emergent")

    try:
        invitation_expiry_days = int(_env("INVITATION_EXPIRY_DAYS", "7") or "7")
    except ValueError as e:
        raise ConfigError("INVITATION_EXPIRY_DAYS must be an integer") from e
    if invitation_expiry_days < 1 or invitation_expiry_days > 90:
        raise ConfigError("INVITATION_EXPIRY_DAYS must be between 1 and 90")

    email_provider = (_env("EMAIL_PROVIDER") or ("console" if environment != "production" else "resend")).lower()
    if email_provider not in {"resend", "console"}:
        raise ConfigError(f"EMAIL_PROVIDER must be 'resend' or 'console', got {email_provider!r}")
    email_sending_enabled = _truthy("EMAIL_SENDING_ENABLED", False)
    try:
        email_daily_limit = int(_env("EMAIL_DAILY_LIMIT", "100") or "100")
    except ValueError as e:
        raise ConfigError("EMAIL_DAILY_LIMIT must be an integer") from e
    if email_daily_limit < 1 or email_daily_limit > 10000:
        raise ConfigError("EMAIL_DAILY_LIMIT must be between 1 and 10000")

    # Reject credentialed CORS that includes wildcard mixed with origins in production
    if environment == "production" and any(o == "*" for o in cors_origins):
        raise ConfigError("CORS_ORIGINS must not include '*' in production")

    redis_url = _env("REDIS_URL")
    worker_enabled = _truthy("WORKER_ENABLED", False)
    scheduler_enabled = _truthy("SCHEDULER_ENABLED", False)
    # Production with workers/scheduler implies Redis is required.
    require_redis_default = bool(
        environment == "production" and (worker_enabled or scheduler_enabled)
    )
    require_redis = _truthy("REQUIRE_REDIS", require_redis_default)
    if environment == "production" and (worker_enabled or scheduler_enabled or require_redis) and not redis_url:
        raise ConfigError("REDIS_URL is required in production when WORKER_ENABLED, SCHEDULER_ENABLED, or REQUIRE_REDIS is true")
    if environment == "production" and scheduler_enabled and not worker_enabled:
        logger.warning("SCHEDULER_ENABLED without WORKER_ENABLED — scheduled jobs will enqueue but may not process")

    def _int_env(name: str, default: str, lo: int, hi: int) -> int:
        try:
            v = int(_env(name, default) or default)
        except ValueError as e:
            raise ConfigError(f"{name} must be an integer") from e
        if v < lo or v > hi:
            raise ConfigError(f"{name} must be between {lo} and {hi}")
        return v

    trusted_raw = _env("TRUSTED_HOSTS", "") or ""
    trusted_hosts = [h.strip() for h in trusted_raw.split(",") if h.strip()]

    settings = Settings(
        environment=environment,
        mongo_url=mongo_url or "",
        db_name=db_name or "",
        jwt_secret=jwt_secret or "",
        cors_origins=cors_origins,
        frontend_url=frontend_url.rstrip("/"),
        enable_demo_seed=enable_demo_seed,
        enable_demo_login=enable_demo_login,
        demo_email=demo_email,
        demo_password=demo_password,
        ai_provider=ai_provider,
        ai_model=ai_model,
        openai_api_key=openai_api_key,
        emergent_llm_key=emergent_llm_key,
        storage_provider=storage_provider,
        upload_dir=upload_dir,
        resend_api_key=_env("RESEND_API_KEY"),
        from_email=_env("FROM_EMAIL", "onboarding@resend.dev") or "onboarding@resend.dev",
        from_name=_env("FROM_NAME", "Assistify OS") or "Assistify OS",
        reply_to_email=_env("REPLY_TO_EMAIL"),
        email_provider=email_provider,
        email_sending_enabled=email_sending_enabled,
        email_daily_limit=email_daily_limit,
        resend_webhook_secret=_env("RESEND_WEBHOOK_SECRET"),
        integration_encryption_key=integration_encryption_key,
        google_client_id=_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_env("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=_env("GOOGLE_REDIRECT_URI"),
        microsoft_client_id=_env("MICROSOFT_CLIENT_ID"),
        microsoft_client_secret=_env("MICROSOFT_CLIENT_SECRET"),
        microsoft_tenant=_env("MICROSOFT_TENANT", "common") or "common",
        microsoft_redirect_uri=_env("MICROSOFT_REDIRECT_URI"),
        slack_client_id=_env("SLACK_CLIENT_ID"),
        slack_client_secret=_env("SLACK_CLIENT_SECRET"),
        slack_redirect_uri=_env("SLACK_REDIRECT_URI"),
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
        invitation_expiry_days=invitation_expiry_days,
        redis_url=redis_url,
        log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        trusted_hosts=trusted_hosts,
        worker_enabled=worker_enabled,
        scheduler_enabled=scheduler_enabled,
        require_redis=require_redis,
        sentry_dsn=_env("SENTRY_DSN"),
        release_version=_env("RELEASE_VERSION", "dev") or "dev",
        app_url=_env("APP_URL"),
        api_url=_env("API_URL"),
        inbox_sync_interval_minutes=_int_env("INBOX_SYNC_INTERVAL_MINUTES", "15", 1, 1440),
        integration_health_interval_minutes=_int_env("INTEGRATION_HEALTH_INTERVAL_MINUTES", "60", 1, 1440),
        email_reconciliation_interval_minutes=_int_env("EMAIL_RECONCILIATION_INTERVAL_MINUTES", "10", 1, 1440),
        json_logs=_truthy("JSON_LOGS", environment == "production"),
    )
    _settings = settings
    # Safe startup log (no secrets)
    logger.info(
        "Settings loaded env=%s worker=%s scheduler=%s redis=%s release=%s",
        settings.environment,
        settings.worker_enabled,
        settings.scheduler_enabled,
        "configured" if settings.redis_url else "unset",
        settings.release_version,
    )
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
