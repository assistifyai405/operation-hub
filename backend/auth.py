"""Authentication helpers: password hashing, JWT tokens, secure token generation."""
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 7


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str, org_id: str) -> str:
    payload = {
        "sub": user_id, "email": email, "org": org_id, "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, jti: str, remember: bool = True) -> str:
    days = REFRESH_TOKEN_DAYS if remember else 1
    payload = {
        "sub": user_id, "jti": jti, "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=days),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])


def gen_token() -> str:
    return secrets.token_urlsafe(32)


def gen_id() -> str:
    return str(uuid.uuid4())
