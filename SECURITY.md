# Security

## Reporting Vulnerabilities

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: ois.protocol@gmail.com

## Security Model

### PWA (client-side identity generation)

- **No passwords, no server secrets.** Identity is derived entirely on-device.
- **WebAuthn / Passkey** — the private key is generated and stored in your device's secure enclave (TPM, Secure Element, or OS-managed keystore). It never leaves the hardware.
- **Symbol derivation** — `SHA-256(SPKI DER bytes of public key)` produces a deterministic, globally unique identity. Knowing the symbol ID reveals nothing about the private key.
- **IndexedDB** — credential metadata is stored locally in IndexedDB (no cloud sync by default).
- **Offline-capable** — a service worker caches all app assets; no network calls are made during identity generation.

### Discovery Server (optional)

- Stores only **public** data: symbol ID, alias, public key (SPKI bytes), and a WebAuthn assertion used as proof of ownership.
- Publishing requires a valid WebAuthn assertion signed by the private key corresponding to the published public key.
- The server never sees or stores private keys.
- CORS is restricted to configured origins.

## Known Limitations

- **Single-device by default** — passkeys are device-bound unless the device supports synced passkeys (e.g. iCloud Keychain, Google Password Manager). Cross-device identity portability is a planned feature.
- **No revocation** — once published to a discovery server, there is no built-in revocation mechanism yet.
- **Discovery servers are independent** — there is no global federation layer yet; each server is its own namespace.
