"""Cryptographic primitives, key derivation, and secret scanning for Barsa (Phase 10)."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import argon2
import jwt

# Argon2id password hasher configured with OWASP recommended minimum parameters
_PASSWORD_HASHER = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID,
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id with unique cryptographic salt."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against Argon2id hash in constant time."""
    try:
        return _PASSWORD_HASHER.verify(hashed, password)
    except Exception:
        return False


def generate_api_key(prefix: str = "barsa_ak") -> tuple[str, str, str, str]:
    """Generate cryptographically secure API key.

    Returns:
        (raw_key, key_prefix, key_hash, salt)
    """
    random_part = secrets.token_urlsafe(32)
    raw_key = f"{prefix}_{random_part}"
    key_prefix = raw_key[:12]
    salt = secrets.token_hex(16)
    key_hash = hashlib.sha256(f"{raw_key}:{salt}".encode()).hexdigest()
    return raw_key, key_prefix, key_hash, salt


def verify_api_key(raw_key: str, key_hash: str, salt: str) -> bool:
    """Verify raw API key matches salted SHA-256 hash in constant time."""
    computed = hashlib.sha256(f"{raw_key}:{salt}".encode()).hexdigest()
    return hmac.compare_digest(computed, key_hash)


def create_access_token(
    principal_id: str,
    secret_key: str,
    expires_in_seconds: int = 86400,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT bearer token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": principal_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    """Decode and validate a signed JWT bearer token."""
    return jwt.decode(token, secret_key, algorithms=["HS256"])


# Defense-in-depth secret detection patterns
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----"
    ),
    "aws_access_key": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "aws_secret_key": re.compile(r"\b[0-9a-zA-Z/+]{40}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b"),
    "openai_api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b"),
    "jwt_token": re.compile(r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b"),
}


class SecretScanner:
    """Scans text content for inadvertently exposed secrets and credentials."""

    @staticmethod
    def scan_text(text: str) -> list[str]:
        """Detect secret patterns in text; returns names of matched secret types."""
        if not text or len(text) < 10:
            return []
        detected: list[str] = []
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                detected.append(name)
        return detected

    @classmethod
    def contains_secret(cls, text: str) -> bool:
        """Check if any secret pattern is present."""
        return len(cls.scan_text(text)) > 0

    @classmethod
    def redact_secrets(cls, text: str) -> str:
        """Replace detected secret strings with redacted placeholders."""
        redacted = text
        for name, pattern in SECRET_PATTERNS.items():
            redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)
        return redacted
