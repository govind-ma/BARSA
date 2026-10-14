"""Tests for Content-Addressed Storage (CAS) hashing, canonical JSON, and AES-256-GCM encryption."""

import pytest

from barsa.sync.crypto import (
    SyncEncryptor,
    canonical_json_bytes,
    compute_sha256,
    verify_sha256,
)


def test_canonical_json_deterministic():
    """Verify key order and formatting differences produce identical canonical bytes."""
    obj1 = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}
    obj2 = {"nested": {"y": 25, "z": 26}, "a": 1, "b": 2}

    b1 = canonical_json_bytes(obj1)
    b2 = canonical_json_bytes(obj2)
    assert b1 == b2
    assert compute_sha256(b1) == compute_sha256(b2)


def test_compute_and_verify_sha256():
    """Verify SHA-256 calculation and verification for strings and bytes."""
    data_str = "hello barsa cloud sync"
    data_bytes = data_str.encode("utf-8")

    digest_str = compute_sha256(data_str)
    digest_bytes = compute_sha256(data_bytes)
    assert digest_str == digest_bytes
    assert len(digest_str) == 64

    assert verify_sha256(data_bytes, digest_str) is True
    assert verify_sha256(data_str, digest_str) is True
    assert verify_sha256(b"corrupted data", digest_str) is False


def test_sync_encryptor_roundtrip():
    """Verify AES-256-GCM encryption and decryption roundtrip."""
    passphrase = "SuperSecureBarsaKey2026!"
    encryptor = SyncEncryptor(passphrase=passphrase)

    payload = b'{"record_type": "knowledge", "title": "Secret Agent Strategy"}'
    envelope = encryptor.encrypt(payload)

    # Validate envelope format: salt(16) + nonce(12) + ciphertext + tag(16)
    assert len(envelope) == 16 + 12 + len(payload) + 16

    # Plaintext should not appear in raw envelope
    assert b"Secret Agent Strategy" not in envelope

    # Decrypt and verify
    decrypted = encryptor.decrypt(envelope)
    assert decrypted == payload


def test_sync_encryptor_wrong_passphrase():
    """Verify decryption fails when an incorrect passphrase is used."""
    encryptor_correct = SyncEncryptor(passphrase="correct-password")
    encryptor_wrong = SyncEncryptor(passphrase="wrong-password")

    payload = b"Top secret operational memory"
    envelope = encryptor_correct.encrypt(payload)

    with pytest.raises(ValueError, match="Decryption failed"):
        encryptor_wrong.decrypt(envelope)


def test_sync_encryptor_tamper_detection():
    """Verify AES-256-GCM authentication detects tampered ciphertext and tags."""
    encryptor = SyncEncryptor(passphrase="passphrase123")
    envelope = bytearray(encryptor.encrypt(b"unaltered payload"))

    # Tamper with the last byte (auth tag)
    envelope[-1] ^= 0xFF

    with pytest.raises(ValueError, match="Decryption failed"):
        encryptor.decrypt(bytes(envelope))

    # Tamper with header/nonce
    envelope2 = bytearray(encryptor.encrypt(b"unaltered payload"))
    envelope2[20] ^= 0xFF

    with pytest.raises(ValueError, match="Decryption failed"):
        encryptor.decrypt(bytes(envelope2))
