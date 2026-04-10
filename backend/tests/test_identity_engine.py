"""Tests for the Unicode identity engine."""

import pytest
from backend.data.unicode_pool import SYMBOL_POOL, pool_size
from backend.data.alias_map import build_alias_map
from backend.services.identity_engine import (
    generate_symbol_id,
    validate_symbol_id,
    parse_symbol_id,
    capacity_info,
)


class TestUnicodePool:
    def test_pool_size_meets_requirement(self):
        """Pool must have at least 5000 symbols."""
        assert pool_size() >= 5000

    def test_all_symbols_are_single_chars(self):
        for sym in SYMBOL_POOL:
            assert isinstance(sym, str)

    def test_no_duplicates_in_pool(self):
        assert len(SYMBOL_POOL) == len(set(SYMBOL_POOL))

    def test_theoretical_capacity(self):
        n = pool_size()
        capacity = n * (n - 1) * (n - 2)
        # Must support at least 10 billion identities
        assert capacity >= 10_000_000_000


class TestAliasMap:
    def test_alias_map_covers_full_pool(self):
        m = build_alias_map()
        assert len(m) == pool_size()

    def test_all_aliases_unique(self):
        m = build_alias_map()
        vals = list(m.values())
        assert len(vals) == len(set(vals))

    def test_aliases_are_lowercase_alpha(self):
        m = build_alias_map()
        for alias in m.values():
            assert alias.isalpha() and alias == alias.lower(), f"Bad alias: {alias}"


class TestIDGenerator:
    def test_generates_valid_format(self):
        result = generate_symbol_id()
        assert "symbol_id" in result
        assert "alias" in result
        assert result["symbol_id"].count("-") == 2
        assert result["alias"].count("-") == 2

    def test_generated_id_passes_validation(self):
        for _ in range(50):
            result = generate_symbol_id()
            assert validate_symbol_id(result["symbol_id"])

    def test_no_duplicate_symbols_in_id(self):
        for _ in range(100):
            result = generate_symbol_id()
            parts = parse_symbol_id(result["symbol_id"])
            assert parts is not None
            assert len(set(parts)) == 3, "Symbol ID must have 3 distinct symbols"

    def test_uniqueness_at_scale(self):
        """Generate 10,000 IDs and check for no duplicates."""
        ids = {generate_symbol_id()["symbol_id"] for _ in range(10_000)}
        assert len(ids) == 10_000

    def test_validate_rejects_bad_format(self):
        assert not validate_symbol_id("x-y")
        assert not validate_symbol_id("x-y-z")  # not in pool
        assert not validate_symbol_id("")

    def test_capacity_info(self):
        info = capacity_info()
        assert info["pool_size"] >= 5000
        assert info["theoretical_max_ids"] >= 10_000_000_000
