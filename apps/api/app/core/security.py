from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .config import Settings

_hasher = PasswordHasher()  # Argon2id по умолчанию


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(settings: Settings, user_id: uuid.UUID, auth_session_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": str(auth_session_id),
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_ttl_seconds),
    }
    return jwt.encode(payload, settings.app_secret, algorithm="HS256")


def decode_access_token(settings: Settings, token: str) -> dict[str, Any] | None:
    try:
        data = jwt.decode(token, settings.app_secret, algorithms=["HS256"], options={"require": ["exp", "sub", "sid"]})
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "access" else None
