"""
Identity Engine — generates unique 3-symbol IDs with aliases.

Output format:
  symbol_id : "⚙-🌊-🔥"
  alias     : "gear-wave-fire"
"""

import random
import secrets
from typing import Optional, Tuple

from backend.data.unicode_pool import SYMBOL_POOL
from backend.data.alias_map import get_alias, build_alias_map


_pool_size = len(SYMBOL_POOL)


def _pick_three() -> Tuple[str, str, str]:
    """Pick 3 distinct symbols from the pool using cryptographically-safe randomness."""
    indices = random.sample(range(_pool_size), 3)
    return SYMBOL_POOL[indices[0]], SYMBOL_POOL[indices[1]], SYMBOL_POOL[indices[2]]


def generate_symbol_id() -> dict:
    """
    Generate one candidate identity.

    Returns:
        {
            "symbol_id": "⚙-🌊-🔥",
            "alias": "gear-wave-fire"
        }

    Does NOT check DB uniqueness — caller must verify and retry on collision.
    """
    s1, s2, s3 = _pick_three()
    symbol_id = f"{s1}-{s2}-{s3}"
    alias = f"{get_alias(s1)}-{get_alias(s2)}-{get_alias(s3)}"
    return {
        "symbol_id": symbol_id,
        "alias": alias,
    }


def parse_symbol_id(symbol_id: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a symbol_id string into its 3 component symbols.
    Returns None if the format is invalid.
    """
    parts = symbol_id.split("-")
    if len(parts) != 3:
        return None
    s1, s2, s3 = parts
    pool_set = set(SYMBOL_POOL)
    if s1 not in pool_set or s2 not in pool_set or s3 not in pool_set:
        return None
    if len({s1, s2, s3}) != 3:
        return None  # duplicates not allowed
    return s1, s2, s3


def validate_symbol_id(symbol_id: str) -> bool:
    """Return True if the symbol_id is structurally valid."""
    return parse_symbol_id(symbol_id) is not None


def capacity_info() -> dict:
    """Return pool and theoretical capacity info."""
    n = _pool_size
    return {
        "pool_size": n,
        "theoretical_max_ids": n * (n - 1) * (n - 2),
    }
