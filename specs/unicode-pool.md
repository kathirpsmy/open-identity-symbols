# Unicode Pool Specification

## Summary

- **Pool size**: 5,390 symbols (as of v0.1)
- **Source**: `backend/data/unicode_pool.py`
- **Theoretical capacity**: ~156 billion unique 3-symbol IDs

## Inclusion Criteria

A symbol is included if:

1. It is a valid Unicode code point
2. Its Unicode category is NOT: Cc (control), Cf (format), Cs (surrogate), Co (private-use), Cn (unassigned)
3. It is NOT in the exclusion set (see below)

## Exclusion Categories

| Category | Examples | Reason |
|----------|----------|--------|
| Religious symbols | ✝ ☪ ✡ ☯ 🕉 ☦ | Avoid association with specific beliefs |
| Political symbols | ☭ | Avoid political connotation |
| National flags | 🇺🇸 🇬🇧 etc. | Regional bias, rendering inconsistency |
| Gendered symbols | ♀ ♂ ⚧ | Avoid gender assignment to identities |
| Human faces / people emoji | 👶-👿 | Privacy, skin-tone bias |
| Skin-tone modifiers | 🏻-🏿 | Compound character issues |

## Included Unicode Ranges

| Range | Name | Count |
|-------|------|-------|
| U+2190–21FF | Arrows | ~112 |
| U+2200–22FF | Mathematical Operators | ~256 |
| U+2300–23FF | Miscellaneous Technical | ~256 |
| U+2460–24FF | Enclosed Alphanumerics | ~160 |
| U+2500–257F | Box Drawing | ~128 |
| U+2580–259F | Block Elements | ~32 |
| U+25A0–25FF | Geometric Shapes | ~96 |
| U+2600–26FF | Miscellaneous Symbols (filtered) | ~200 |
| U+2700–27BF | Dingbats (filtered) | ~150 |
| U+2800–28FF | Braille Patterns | 256 |
| U+2900–297F | Supplemental Arrows-B | ~128 |
| U+2A00–2AFF | Supplemental Mathematical Operators | ~256 |
| U+2B00–2BFF | Miscellaneous Symbols and Arrows | ~200 |
| U+3200–33FF | Enclosed CJK / Compatibility | ~400 |
| U+1F000–1F09F | Mahjong + Domino Tiles | ~160 |
| U+1F0A0–1F0FF | Playing Cards | ~96 |
| U+1F300–1F9FF | Emoji (filtered) | ~600 |
| U+1FA00–1FAFF | Extended Symbols | ~128 |

## Stability Guarantee

Once a symbol is assigned to a user, it must never be removed from the pool. New symbols may be added in future versions (increasing pool capacity), but existing assignments are permanent.
