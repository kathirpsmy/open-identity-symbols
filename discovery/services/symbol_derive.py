"""
Server-side symbol derivation.

Reuses the same SYMBOL_POOL and ALIAS_MAP from data/ so the Python
derivation is byte-for-byte identical to the JS derivation in pwa/app.js.
Algorithm spec: docs/architecture.md § Symbol Derivation Algorithm.
"""

import hashlib
import sys
from pathlib import Path

# Allow import of data/ when running the discovery server as a package
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data.unicode_pool import SYMBOL_POOL
from data.alias_map import build_alias_map

_ALIAS_MAP = build_alias_map()
_POOL = SYMBOL_POOL
_ALIAS = [_ALIAS_MAP[s] for s in _POOL]
_POOL_SIZE = len(_POOL)


def _uint32_be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def derive_symbol(public_key_spki_bytes: bytes) -> tuple[str, str]:
    """
    Derive (symbol_id, alias) from SPKI DER public key bytes.

    Returns:
        (symbol_id, alias) e.g. ("⥐-📡-🏕", "filth-satellite-camping")

    Raises:
        ValueError: if derivation produces indices out of pool bounds (should never happen)
    """
    digest = hashlib.sha256(public_key_spki_bytes).digest()

    idx_a = _uint32_be(digest, 0) % _POOL_SIZE
    idx_b = _uint32_be(digest, 4) % _POOL_SIZE
    idx_c = _uint32_be(digest, 8) % _POOL_SIZE

    # Collision within the triple → shift window +3 bytes, retry once
    if idx_a == idx_b or idx_b == idx_c or idx_a == idx_c:
        idx_a = _uint32_be(digest, 3) % _POOL_SIZE
        idx_b = _uint32_be(digest, 6) % _POOL_SIZE
        idx_c = _uint32_be(digest, 9) % _POOL_SIZE

    symbol_id = f"{_POOL[idx_a]}-{_POOL[idx_b]}-{_POOL[idx_c]}"
    alias     = f"{_ALIAS[idx_a]}-{_ALIAS[idx_b]}-{_ALIAS[idx_c]}"
    return symbol_id, alias


def public_key_id(public_key_spki_bytes: bytes) -> str:
    """Return the globally unique key fingerprint: SHA-256(SPKI bytes) as hex."""
    return hashlib.sha256(public_key_spki_bytes).hexdigest()
