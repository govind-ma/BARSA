"""Canonical serialization, SHA-256 CAS hashing, and client-side AEAD encryption for sync."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 100_000
SALT_SIZE_BYTES = 16
NONCE_SIZE_BYTES = 12


def canonical_json_bytes(data: Any) -> bytes:
    """Deterministically serialize Python primitives to canonical UTF-8 JSON bytes.

    Features:
    - Keys sorted lexicographically
    - Compact delimiters (no extra whitespace around separators)
    - Full UTF-8 preserving characters without ASCII escaping
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_sha256(data: bytes | str) -> str:
    """Compute standard SHA-256 hexadecimal hash string for content-addressing."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_sha256(data: bytes | str, expected_hash: str) -> bool:
    """Constant-time comparison of actual payload SHA-256 against expected hash."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    actual = compute_sha256(data)
    return secrets.compare_digest(actual.lower(), expected_hash.lower())


class SyncEncryptor:
    """Client-side Authenticated Encryption (AES-256-GCM) for BYOS Cloud Sync."""

    def __init__(self, key: bytes | None = None, passphrase: str | None = None) -> None:
        """Initialize encryptor with a 256-bit key or derive one from passphrase."""
        if key:
            if len(key) != 32:
                raise ValueError("AES-256-GCM encryption requires a 32-byte (256-bit) key")
            self._key = key
        elif passphrase:
            self._passphrase = passphrase.encode("utf-8")
            self._key = None
        else:
            raise ValueError("Must provide either a 32-byte key or a passphrase")

    def _derive_key(self, salt: bytes) -> bytes:
        if self._key is not None:
            return self._key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._passphrase)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt payload using AES-256-GCM.

        Output envelope format:
        [16 bytes salt] + [12 bytes nonce] + [ciphertext + 16 bytes GCM auth tag]
        """
        salt = os.urandom(SALT_SIZE_BYTES)
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(NONCE_SIZE_BYTES)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return salt + nonce + ciphertext

    def decrypt(self, envelope: bytes) -> bytes:
        """Decrypt AES-256-GCM payload. Raises ValueError if corrupted or invalid key."""
        header_len = SALT_SIZE_BYTES + NONCE_SIZE_BYTES
        if len(envelope) < header_len + 16:
            raise ValueError("Invalid encrypted envelope: payload too short")

        salt = envelope[:SALT_SIZE_BYTES]
        nonce = envelope[SALT_SIZE_BYTES:header_len]
        ciphertext = envelope[header_len:]

        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError("Decryption failed: corrupted data, tampered tag, or incorrect passphrase") from exc
