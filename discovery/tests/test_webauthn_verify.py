"""
Unit tests for discovery/services/webauthn_verify.py

Uses synthetic P-256 signatures — no browser or hardware authenticator needed.
"""

import hashlib
import json
import os

import pytest

from discovery.services.webauthn_verify import AssertionError, verify_assertion
from discovery.tests.conftest import _b64url, make_assertion, make_keypair


ORIGIN = "http://localhost:8001"


@pytest.fixture
def key_and_challenge():
    private, _, spki = make_keypair()
    challenge_hex = os.urandom(32).hex()
    return private, spki, challenge_hex


def call_verify(private, spki, challenge_hex, origin=ORIGIN):
    assertion = make_assertion(private, spki, challenge_hex, origin)
    verify_assertion(
        public_key_spki_b64url    = _b64url(spki),
        client_data_json_b64url   = assertion["client_data_json"],
        authenticator_data_b64url = assertion["authenticator_data"],
        signature_b64url          = assertion["signature"],
        expected_challenge_hex    = challenge_hex,
        expected_origin           = origin,
        verify_origin             = True,
    )


class TestHappyPath:
    def test_valid_assertion_passes(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        call_verify(private, spki, challenge_hex)

    def test_verify_origin_false_skips_origin_and_rp_check(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        assertion = make_assertion(private, spki, challenge_hex, "http://other-origin:9999")
        # Should pass because verify_origin=False
        verify_assertion(
            public_key_spki_b64url    = _b64url(spki),
            client_data_json_b64url   = assertion["client_data_json"],
            authenticator_data_b64url = assertion["authenticator_data"],
            signature_b64url          = assertion["signature"],
            expected_challenge_hex    = challenge_hex,
            expected_origin           = ORIGIN,  # different from what was signed
            verify_origin             = False,
        )


class TestChallengeMismatch:
    def test_wrong_challenge_fails(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        wrong_hex = os.urandom(32).hex()
        with pytest.raises(AssertionError, match="Challenge mismatch"):
            assertion = make_assertion(private, spki, challenge_hex, ORIGIN)
            verify_assertion(
                public_key_spki_b64url    = _b64url(spki),
                client_data_json_b64url   = assertion["client_data_json"],
                authenticator_data_b64url = assertion["authenticator_data"],
                signature_b64url          = assertion["signature"],
                expected_challenge_hex    = wrong_hex,  # different challenge
                expected_origin           = ORIGIN,
                verify_origin             = True,
            )


class TestOriginMismatch:
    def test_wrong_origin_fails(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        assertion = make_assertion(private, spki, challenge_hex, ORIGIN)
        with pytest.raises(AssertionError, match="Origin mismatch"):
            verify_assertion(
                public_key_spki_b64url    = _b64url(spki),
                client_data_json_b64url   = assertion["client_data_json"],
                authenticator_data_b64url = assertion["authenticator_data"],
                signature_b64url          = assertion["signature"],
                expected_challenge_hex    = challenge_hex,
                expected_origin           = "https://evil.example.com",
                verify_origin             = True,
            )


class TestSignatureTampering:
    def test_tampered_signature_fails(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        assertion = make_assertion(private, spki, challenge_hex, ORIGIN)
        # Flip a byte in the signature
        import base64
        sig_bytes = bytearray(base64.urlsafe_b64decode(assertion["signature"] + "=="))
        sig_bytes[0] ^= 0xFF
        assertion["signature"] = _b64url(bytes(sig_bytes))
        with pytest.raises(AssertionError, match="Signature verification failed"):
            verify_assertion(
                public_key_spki_b64url    = _b64url(spki),
                client_data_json_b64url   = assertion["client_data_json"],
                authenticator_data_b64url = assertion["authenticator_data"],
                signature_b64url          = assertion["signature"],
                expected_challenge_hex    = challenge_hex,
                expected_origin           = ORIGIN,
                verify_origin             = True,
            )

    def test_different_key_fails(self, key_and_challenge):
        private, spki, challenge_hex = key_and_challenge
        other_private, other_spki, _ = make_keypair()
        # Sign with a different private key but verify against original public key
        assertion = make_assertion(other_private, other_spki, challenge_hex, ORIGIN)
        with pytest.raises(AssertionError, match="Signature verification failed"):
            verify_assertion(
                public_key_spki_b64url    = _b64url(spki),
                client_data_json_b64url   = assertion["client_data_json"],
                authenticator_data_b64url = assertion["authenticator_data"],
                signature_b64url          = assertion["signature"],
                expected_challenge_hex    = challenge_hex,
                expected_origin           = ORIGIN,
                verify_origin             = True,
            )


class TestBadInputs:
    def test_invalid_base64_raises(self):
        with pytest.raises(AssertionError, match="Failed to decode"):
            verify_assertion(
                public_key_spki_b64url    = "not-valid!!!",
                client_data_json_b64url   = "not-valid!!!",
                authenticator_data_b64url = "not-valid!!!",
                signature_b64url          = "not-valid!!!",
                expected_challenge_hex    = "aa" * 32,
                expected_origin           = ORIGIN,
            )

    def test_wrong_type_in_client_data_fails(self, key_and_challenge):
        import base64
        private, spki, challenge_hex = key_and_challenge
        assertion = make_assertion(private, spki, challenge_hex, ORIGIN)
        # Replace type with "webauthn.create"
        raw = base64.urlsafe_b64decode(assertion["client_data_json"] + "==")
        data = json.loads(raw)
        data["type"] = "webauthn.create"
        tampered = _b64url(json.dumps(data, separators=(",", ":")).encode())
        with pytest.raises(AssertionError, match="type must be"):
            verify_assertion(
                public_key_spki_b64url    = _b64url(spki),
                client_data_json_b64url   = tampered,
                authenticator_data_b64url = assertion["authenticator_data"],
                signature_b64url          = assertion["signature"],
                expected_challenge_hex    = challenge_hex,
                expected_origin           = ORIGIN,
            )
