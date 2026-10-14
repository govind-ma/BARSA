# Client-Side Zero-Knowledge Encryption

## 1. Cryptographic Architecture

BARSA BYOS provides optional end-to-end client-side encryption. When enabled:
- The remote cloud provider (AWS, MinIO, Cloudflare R2, or remote disk) receives only encrypted ciphertext.
- Even if the cloud bucket is compromised or made public, no plaintext knowledge, decisions, code snippets, or metadata can be extracted.

```
+---------------------------------------------------------------------------------+
|                                 Sync Envelope                                   |
|---------------------------------------------------------------------------------|
|  16 Bytes Salt  |  12 Bytes Nonce / IV  |  Ciphertext Payload  |  16 Bytes Tag  |
+---------------------------------------------------------------------------------+
```

---

## 2. Specification & Parameters

- **Symmetric Cipher**: `AES-256-GCM` (Galois/Counter Mode).
- **Key Derivation Function**: `PBKDF2-HMAC-SHA256`.
- **Iteration Count**: `100,000` rounds.
- **Salt Length**: 16 bytes cryptographically random (`os.urandom(16)`).
- **Nonce / IV Length**: 12 bytes cryptographically random (`os.urandom(12)`).
- **Authentication Tag**: 16 bytes (128-bit MAC) verified before any plaintext payload is returned.

---

## 3. Envelope Format

Every encrypted CAS object, manifest, and branch reference is packaged as a binary envelope:

1. **Bytes 0–15**: Cryptographic Salt (16 bytes).
2. **Bytes 16–27**: Initialization Vector / Nonce (12 bytes).
3. **Bytes 28 to End-16**: Encrypted AES-256-GCM Ciphertext.
4. **Last 16 Bytes**: GCM Authentication Tag.

---

## 4. Key Management & Security Best Practices

1. **Passphrase Strength**: Use a high-entropy passphrase or pass a direct 32-byte (256-bit) raw key via environment variables.
2. **Zero Plaintext Storage**: Passphrases are never persisted in the remote repository or in plaintext on disk.
3. **Tamper Rejection**: Any bit flipped in the IV, ciphertext, or auth tag causes `SyncEncryptor.decrypt` to raise a `ValueError("Decryption failed: corrupted data, tampered tag, or incorrect passphrase")`.
