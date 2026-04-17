"""
WebAuthn assertion verification (server-side, no external WebAuthn library).

Spec: W3C WebAuthn Level 2, §7.2 "Verifying an Authentication Assertion"

Supports:
  ES256  (-7)  — ECDSA P-256, most common passkey algorithm
  RS256  (-257) — RSASSA-PKCS1-v1_5 SHA-256
  EdDSA  (-8)  — Ed25519

Usage
─────
    from discovery.services.webauthn_verify import verify_assertion, AssertionError

    try:
        verify_assertion(
            public_key_spki_b64url = identity.public_key_spki,
            client_data_json_b64url = assertion.client_data_json,
            authenticator_data_b64url = assertion.authenticator_data,
            signature_b64url = assertion.signature,
            expected_challenge_hex = challenge.token,
            expected_origin = request_origin,           # e.g. "https://foo.github.io"
            verify_origin = settings.WEBAUTHN_VERIFY_ORIGIN,
        )
    except AssertionError as e:
        raise HTTPException(401, str(e))
"""

import base64
import hashlib
import json
from urllib.parse import urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_der_public_key


class AssertionError(Exception):
    """Raised when any step of assertion verification fails."""


# ─────────────────────────────────────────────────────────────────────────────
# Encoding helpers
# ─────────────────────────────────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    """Decode base64url, tolerant of missing padding."""
    s = s.replace("-", "+").replace("_", "/")
    pad = (4 - len(s) % 4) % 4
    return base64.b64decode(s + "=" * pad)


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


# ─────────────────────────────────────────────────────────────────────────────
# Main verification function
# ─────────────────────────────────────────────────────────────────────────────

def verify_assertion(
    public_key_spki_b64url: str,
    client_data_json_b64url: str,
    authenticator_data_b64url: str,
    signature_b64url: str,
    expected_challenge_hex: str,
    expected_origin: str,
    verify_origin: bool = True,
) -> None:
    """
    Verify a WebAuthn assertion.

    Parameters
    ──────────
    public_key_spki_b64url
        The credential's SPKI DER public key, base64url-encoded.
        Comes from AuthenticatorAttestationResponse.getPublicKey() at registration.
    client_data_json_b64url
        The raw clientDataJSON bytes, base64url-encoded.
    authenticator_data_b64url
        The authenticatorData bytes, base64url-encoded.
    signature_b64url
        The signature bytes, base64url-encoded.
    expected_challenge_hex
        The challenge token the server issued (hex string, 64 chars = 32 bytes).
    expected_origin
        The origin the PWA is hosted at (e.g. "https://foo.github.io").
        Used to derive the expected RP ID hash.
    verify_origin
        If False, skips origin and rpIdHash checks.  Set to False only in dev.

    Raises
    ──────
    AssertionError  on any verification failure.
    """

    # ── 1. Decode inputs ────────────────────────────────────────────────────
    try:
        client_data_raw = _b64url_decode(client_data_json_b64url)
        auth_data       = _b64url_decode(authenticator_data_b64url)
        signature       = _b64url_decode(signature_b64url)
        spki_bytes      = _b64url_decode(public_key_spki_b64url)
    except Exception as exc:
        raise AssertionError(f"Failed to decode assertion fields: {exc}") from exc

    # ── 2. Parse clientDataJSON ─────────────────────────────────────────────
    try:
        client_data = json.loads(client_data_raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"clientDataJSON is not valid JSON: {exc}") from exc

    # ── 3. Verify type ──────────────────────────────────────────────────────
    if client_data.get("type") != "webauthn.get":
        raise AssertionError(
            f"clientDataJSON.type must be 'webauthn.get', got {client_data.get('type')!r}"
        )

    # ── 4. Verify challenge ─────────────────────────────────────────────────
    # The challenge stored server-side is hex. The PWA decoded it to bytes and
    # passed those bytes to credentials.get().  The browser base64url-encoded
    # those bytes and wrote them into clientDataJSON.challenge.
    expected_challenge_bytes = bytes.fromhex(expected_challenge_hex)
    expected_challenge_b64url = _b64url_encode(expected_challenge_bytes)
    actual_challenge = client_data.get("challenge", "")
    # Normalise both sides (strip padding differences)
    try:
        actual_bytes = _b64url_decode(actual_challenge)
    except Exception:
        raise AssertionError("clientDataJSON.challenge is not valid base64url")
    if actual_bytes != expected_challenge_bytes:
        raise AssertionError("Challenge mismatch")

    # ── 5. Verify origin & rpIdHash ─────────────────────────────────────────
    if verify_origin:
        if client_data.get("origin") != expected_origin:
            raise AssertionError(
                f"Origin mismatch: expected {expected_origin!r}, "
                f"got {client_data.get('origin')!r}"
            )

        if len(auth_data) < 37:
            raise AssertionError("authenticatorData is too short")

        rp_id = urlparse(expected_origin).hostname or ""
        expected_rp_hash = hashlib.sha256(rp_id.encode()).digest()
        actual_rp_hash = auth_data[:32]
        if actual_rp_hash != expected_rp_hash:
            raise AssertionError("RP ID hash mismatch")

    # ── 6. Verify user-presence flag (bit 0 of flags byte) ─────────────────
    if len(auth_data) < 33:
        raise AssertionError("authenticatorData too short for flags")
    flags = auth_data[32]
    if not (flags & 0x01):
        raise AssertionError("User Presence flag not set in authenticatorData")

    # ── 7. Build verification data ──────────────────────────────────────────
    # verificationData = authenticatorData || SHA-256(clientDataJSON)
    client_data_hash   = hashlib.sha256(client_data_raw).digest()
    verification_data  = auth_data + client_data_hash

    # ── 8. Load public key and verify signature ─────────────────────────────
    try:
        public_key = load_der_public_key(spki_bytes)
    except Exception as exc:
        raise AssertionError(f"Failed to load public key: {exc}") from exc

    try:
        if isinstance(public_key, EllipticCurvePublicKey):
            public_key.verify(signature, verification_data, ECDSA(SHA256()))
        elif isinstance(public_key, RSAPublicKey):
            public_key.verify(signature, verification_data, PKCS1v15(), SHA256())
        elif isinstance(public_key, Ed25519PublicKey):
            public_key.verify(signature, verification_data)
        else:
            raise AssertionError(f"Unsupported public key type: {type(public_key).__name__}")
    except InvalidSignature:
        raise AssertionError("Signature verification failed")
    except AssertionError:
        raise
    except Exception as exc:
        raise AssertionError(f"Signature verification error: {exc}") from exc
