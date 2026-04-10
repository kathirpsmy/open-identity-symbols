"""
Unicode Symbol Pool for Open Identity Symbols (OIS)

Curated pool of ~5000+ safe Unicode symbols.
Excludes: religious, political, national flags, gendered symbols.

Categories included:
  - Geometric shapes
  - Mathematical operators & symbols
  - Arrows (all directions)
  - Box drawing & block elements
  - Braille patterns
  - Dingbats (filtered)
  - Miscellaneous symbols (filtered)
  - Playing cards, Mahjong, Dominos
  - Nature, weather, animals (emoji subset)
  - Food & drink
  - Objects & tools
  - Activities & sports
  - Musical notes & art
  - Technical & science symbols
"""

from typing import List

# ──────────────────────────────────────────────────────────────────────────────
# EXCLUSION SETS — code points to always skip
# ──────────────────────────────────────────────────────────────────────────────

# Religious / spiritual
_RELIGIOUS = {
    0x271D,  # ✝ LATIN CROSS
    0x2626,  # ☦ ORTHODOX CROSS
    0x262A,  # ☪ STAR AND CRESCENT
    0x2627,  # ☧ CHI RHO
    0x2628,  # ☨ CROSS OF LORRAINE
    0x2629,  # ☩ CROSS OF JERUSALEM
    0x262B,  # ☫ FARSI SYMBOL
    0x262C,  # ☬ ADI SHAKTI
    0x262D,  # ☭ HAMMER AND SICKLE
    0x262E,  # ☮ PEACE SYMBOL (keep neutral — actually fine, but keep for safety)
    0x262F,  # ☯ YIN YANG
    0x2670,  # ♰ WEST SYRIAC CROSS
    0x2671,  # ♱ EAST SYRIAC CROSS
    0x2625,  # ☥ ANKH
    0x2624,  # ☤ CADUCEUS (medical but ancient)
    0x2BD1,  # keep out
    0x1F549, # 🕉 OM
    0x1F54E, # 🕎 MENORAH
    0x1F6D0, # 🕍... wait, check
    0x2721,  # ✡ STAR OF DAVID
    0x1F54B, # 🕋 KAABA
    0x1F54C, # 🕌 MOSQUE
    0x1F54D, # 🕍 SYNAGOGUE
    0x26E9,  # ⛩ SHINTO SHRINE
    0x1F6D5, # 🛕 HINDU TEMPLE
}

# Political / national symbols
_POLITICAL = {
    0x262D,  # ☭ HAMMER AND SICKLE
    0x1F3F4, # 🏴 BLACK FLAG
    0x1F3F3, # 🏳 WHITE FLAG (surrender)
    # Flag sequences are emoji ZWJ sequences — handled by excluding the range
}

# Gendered symbols
_GENDERED = {
    0x2640,  # ♀ FEMALE SIGN
    0x2642,  # ♂ MALE SIGN
    0x26A5,  # ⚥ MALE AND FEMALE SIGN
    0x26A6,  # ⚦ MALE WITH STROKE SIGN
    0x26A7,  # ⚧ TRANSGENDER SYMBOL
    0x26A8,  # ⚨ VERTICAL MALE WITH STROKE SIGN
    0x26A9,  # ⚩ HORIZONTAL MALE WITH STROKE AND MALE AND FEMALE SIGN
    0x1F6BA, # 🚺 WOMENS SYMBOL
    0x1F6B9, # 🚹 MENS SYMBOL
    0x1F6BB, # 🚻 RESTROOM
    0x1F46A, # 👪 FAMILY
    0x1F46B, # 👫 MAN AND WOMAN HOLDING HANDS
    0x1F46C, # 👬 TWO MEN HOLDING HANDS
    0x1F46D, # 👭 TWO WOMEN HOLDING HANDS
}

# Skin-tone modifiers & human face emoji (privacy / bias concerns)
_HUMAN_FACES = set(range(0x1F466, 0x1F480))  # people emoji
_SKIN_TONES = set(range(0x1F3FB, 0x1F400))

# Country flags (regional indicator pairs — exclude the base indicators)
_FLAGS = set(range(0x1F1E0, 0x1F200))  # Regional Indicator Symbols A-Z

EXCLUSIONS = _RELIGIOUS | _POLITICAL | _GENDERED | _HUMAN_FACES | _SKIN_TONES | _FLAGS


# ──────────────────────────────────────────────────────────────────────────────
# SYMBOL RANGES — (start, end_inclusive) tuples
# ──────────────────────────────────────────────────────────────────────────────

_RANGES = [
    # Arrows
    (0x2190, 0x21FF),  # Arrows (~112)
    (0x27F0, 0x27FF),  # Supplemental Arrows-A (~16)
    (0x2900, 0x297F),  # Supplemental Arrows-B (~128)
    (0x2B00, 0x2BFF),  # Miscellaneous Symbols and Arrows (~256)

    # Mathematical
    (0x2200, 0x22FF),  # Mathematical Operators (~256)
    (0x2A00, 0x2AFF),  # Supplemental Mathematical Operators (~256)
    (0x27C0, 0x27EF),  # Miscellaneous Mathematical Symbols-A (~48)
    (0x2980, 0x29FF),  # Miscellaneous Mathematical Symbols-B (~128)

    # Geometric Shapes
    (0x25A0, 0x25FF),  # Geometric Shapes (~96)
    (0x1F700, 0x1F77F),  # Alchemical Symbols (~128)
    (0x2B1B, 0x2B55),  # Additional geometric

    # Box Drawing & Blocks
    (0x2500, 0x257F),  # Box Drawing (~128)
    (0x2580, 0x259F),  # Block Elements (~32)

    # Braille Patterns (256 — all safe, abstract)
    (0x2800, 0x28FF),

    # Miscellaneous Symbols (filtered via EXCLUSIONS)
    (0x2600, 0x26FF),  # Misc Symbols (~256)
    (0x2700, 0x27BF),  # Dingbats (~192)

    # Technical / Enclosed
    (0x2300, 0x23FF),  # Miscellaneous Technical (~256)
    (0x2400, 0x243F),  # Control Pictures (~64)
    (0x2440, 0x245F),  # Optical Character Recognition (~32)
    (0x2460, 0x24FF),  # Enclosed Alphanumerics (~160)
    (0x2460, 0x24FF),  # Enclosed Alphanumerics
    (0x3200, 0x32FF),  # Enclosed CJK Letters and Months (~256)
    (0x3300, 0x33FF),  # CJK Compatibility (~256)

    # Playing Cards
    (0x1F0A0, 0x1F0FF),  # Playing Cards (~96)

    # Mahjong + Dominos
    (0x1F000, 0x1F02F),  # Mahjong Tiles (~48)
    (0x1F030, 0x1F09F),  # Domino Tiles (~112)

    # Miscellaneous Symbols and Pictographs (emoji, filtered)
    (0x1F300, 0x1F3FF),  # Misc Symbols and Pictographs (~256, filtered)
    (0x1F400, 0x1F4FF),  # Emoticons / Animals / Objects (~256, filtered)
    (0x1F500, 0x1F5FF),  # Transport & Map / Objects (~256, filtered)
    (0x1F680, 0x1F6FF),  # Transport and Map Symbols (~128, filtered)
    (0x1F780, 0x1F7FF),  # Geometric Shapes Extended (~128)
    (0x1F800, 0x1F8FF),  # Supplemental Arrows-C (~256)
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs (~256, filtered)
    (0x1FA00, 0x1FA6F),  # Chess Symbols, etc.
    (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A

    # Letterlike symbols
    (0x2100, 0x214F),  # Letterlike Symbols (~80)
    (0x2150, 0x218F),  # Number Forms (~64)

    # Currency
    (0x20A0, 0x20CF),  # Currency Symbols (~48)

    # Musical
    (0x2669, 0x266F),  # Musical notes subset
    (0x1D100, 0x1D1FF),  # Musical Symbols (~256)

    # Stars, snowflakes, flowers (dingbats sub-range)
    (0x2733, 0x2764),
]

# Additional individual code points worth including
_EXTRA = [
    0x221E,  # ∞ INFINITY
    0x2022,  # • BULLET
    0x2023,  # ‣ TRIANGULAR BULLET
    0x2043,  # ⁃ HYPHEN BULLET
    0x204C,  # ⁌ BLACK LEFTWARDS BULLET
    0x204D,  # ⁍ BLACK RIGHTWARDS BULLET
    0x2318,  # ⌘ PLACE OF INTEREST SIGN
    0x2325,  # ⌥ OPTION KEY
    0x238B,  # ⎋ BROKEN CIRCLE WITH NORTHWEST ARROW (ESC)
    0x2B50,  # ⭐ WHITE MEDIUM STAR
    0x2B51,  # ⭑ BLACK SMALL STAR
    0x2B52,  # ⭒ WHITE SMALL STAR
    0x1F4A0, # 💠 DIAMOND SHAPE WITH A DOT INSIDE
    0x1F539, # 🔹 SMALL BLUE DIAMOND
    0x1F538, # 🔸 SMALL ORANGE DIAMOND
    0x1F537, # 🔷 LARGE BLUE DIAMOND
    0x1F536, # 🔶 LARGE ORANGE DIAMOND
    0x1F535, # 🔵 LARGE BLUE CIRCLE
    0x1F534, # 🔴 LARGE RED CIRCLE
    0x1F7E0, # 🟠 ORANGE CIRCLE
    0x1F7E1, # 🟡 YELLOW CIRCLE
    0x1F7E2, # 🟢 GREEN CIRCLE
    0x1F7E3, # 🟣 PURPLE CIRCLE
    0x1F7E4, # 🟤 BROWN CIRCLE
    0x1F7E5, # 🟥 RED SQUARE
    0x1F7E6, # 🟦 BLUE SQUARE
    0x1F7E7, # 🟧 ORANGE SQUARE
    0x1F7E8, # 🟨 YELLOW SQUARE
    0x1F7E9, # 🟩 GREEN SQUARE
    0x1F7EA, # 🟪 PURPLE SQUARE
    0x1F7EB, # 🟫 BROWN SQUARE
]


def _build_pool() -> List[str]:
    """Build and return the deduplicated, filtered symbol pool."""
    seen = set()
    pool = []

    def add(cp: int):
        if cp in seen or cp in EXCLUSIONS:
            return
        try:
            ch = chr(cp)
            # Skip control characters, surrogates, private-use areas
            import unicodedata
            cat = unicodedata.category(ch)
            if cat in ('Cc', 'Cf', 'Cs', 'Co', 'Cn'):
                return
            seen.add(cp)
            pool.append(ch)
        except (ValueError, OverflowError):
            pass

    for start, end in _RANGES:
        for cp in range(start, end + 1):
            add(cp)

    for cp in _EXTRA:
        add(cp)

    return pool


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

SYMBOL_POOL: List[str] = _build_pool()


def get_pool() -> List[str]:
    """Return the full curated symbol pool."""
    return SYMBOL_POOL


def pool_size() -> int:
    return len(SYMBOL_POOL)


if __name__ == "__main__":
    p = get_pool()
    print(f"Pool size: {len(p)}")
    print("Sample (first 20):", p[:20])
    print("Sample (last 20):", p[-20:])
