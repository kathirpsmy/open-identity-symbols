"""
Alias Map for Open Identity Symbols (OIS)

Maps each symbol in SYMBOL_POOL to a unique, memorable English word.
Vocabulary: ~1500 real words + systematic color-nature compounds (~4000)
Total vocabulary: 5500+ unique words — covers pool of ~5400 symbols.
"""

import unicodedata
from typing import Dict, Optional
from functools import lru_cache

from backend.data.unicode_pool import SYMBOL_POOL


# ──────────────────────────────────────────────────────────────────────────────
# Vocabulary: real English words (Tier 1 — preferred, most human-readable)
# ──────────────────────────────────────────────────────────────────────────────

_REAL_WORDS = """
acid acorn acre adapt adder agave agile aglow agate aisle alarm albedo aleph
alert algae alien align alloy altar amber amble amend angel angle anvil aorta
aphid apple apron ardor arena argon armor aroma array ashen aspen asset aster
axiom azure bacon badge bagel balsa basal basin batch bayou beach beech belle
birch bison bloom blown bluff boron bower brace braid brake brash brave brawn
brier brine brink brisk brood brook broth brunt brush brute bulge burst cacao
cache cairn canal caper cedar chalk charm chart chase chasm chest chive chord
churn cilia cinch clamp clasp cleat clerk cliff cling clover cobra coil comet
copse coral crane creed creep crest crimp crisp croft crone crust crypt cumin
cupid curd curie cusp cycle dagger daisy datum delta dense depot derby dingo
dirge disco divan dizzy dodger dolce dogma dome domino dowel draft drape drift
drill drone drool droop ducat dunce duvet dwarf eagle easel ebony eddy edict
effigy elbow elegy elfin elite ember epoch erode ether ethos evoke exalt exile
fable facet faery fauna feral ferry fetch fiber filth firth flare flash flask
flora floss flout fluke flume flute focal focus foray forge forte forum frond
frost froth gauge gauze gavel gecko gimp girth gleam glide glint gloss glyph
gnarl gnome goblin golem grace graft grain grant grasp graze grebe greed grime
gripe grit groan grove guard guile guise gusto gypsy habit haiku halve haven
hazel heady helix heron hinge hippo hitch hoary hoist holly horde hovel hover
humid hyena ichor ideal idyll image impel inert infix ingot inlay inset ionic
knack knave kneel knob knurl lapse larch lasso latex lathe libra lichen lilac
lingo litmus livid llama lodge loupe lucid lustre lychee lyric macro magma
maize manor marsh mason mirth miter mocha mogul molar mossy mount mudra mulch
mural murky myrrh nadir nectar nettle niche nickel nimble noble nonce nymph
oaken oasis ochre odeum onyx optic orate orchid ozone paean parcel pasha pastel
patio pearl pedal petal pewter pigment pilot pinion piton pivot pixel plaid
plait plasm pleat plinth plover plumb plume poise polar poplar porch portal
prism probe prone prong psalm pygmy quaff quail quartz quench quill quota
rafter ramus ranch raptor ratio raven realm rebus redwood regent relay relic
resin retina rhomb rivet rochet roller rosette rouge rowan ruddy ruffle runic
sable sachet sallow salvia samite sapphire satay scalar scarp scone scrub sepal
serif shale shoal shogun shrine signal simile sinew sisal skulk sluice smelt
snipe snout solstice spade spall sparse spawn speck spelt spent spire splay
spore sprig squal squib stave stern stilt stoat stomp stout straw stray strife
strop strut suede sullen swale swamp sweep swell swipe swirl swoop tabard tacit
talon taper tapir tartan tawny telic tendril tenet thatch thorn tidal tinge
totem toxin tracer trawl triad tribe trice troll troth trove truant tunic ulna
ultra umbra unify unity uplift upshot urchin usher utter uvula valve vaunt
vector veldt venom vesper viable vigor viper vireo visor vista vital vixen
vizier vocal vogue voile vouch vulcan vulture wader walrus warrant warble wedge
weevil wharf whisker whorl willow windfall wispy wizard wrath wreath xenon xylem
yacht yeast yield yodel yonder zenith zipper zircon zombie bract brome bursa
chaff cleft clime codon cubit cubic cyme delphic dorsal drupe dryad dunes dyke
ellipse emmet enigma enzyme ermine estray etape fovea fulcrum gambit garner
gauche gelid gleam goby gondola gravel guano gullet gully hapax hausse helot
henna hiatus hollow hone hosta howdah hummus hydra hyperon iamb ictus ileum
imago impasse incisor ingrown inkwell joule jugal kaolin kernite kestrel kloof
labrum lacuna lagoon lamina lariat larva laurel lavabo layered lectern legume
lentil lierne lignin litoral loess lupin macle macula medina merlon mesne meson
miasma micelle milieu mitral morel mottle murein mycete nauplius nepheline neuston
nutmeg nympha ocellus ocelot ocotillo olivine omenta operon orogen osmole ossicle
paunch peduncle pergola perylene petrel phloem phyllo pieta pinole plait pollex
pommel pongee popple pore praline primrose propylene proviso pueril pumice purine
pyrite quadrat raffia rampart rasher ratafia ravine razorbill redox redpoll reflex
rhizome ribose riffle rinose riprap rivulet rosary rugate sacrum samara saxifrage
sedum senna septum shard shorl silique silkworm simoom skipper sliver smolt snivel
sodic solute sorel sorrel sparge spicate spinel spiral sprue squama stamen stolon
striate striger stroma suberose sulfate suture synapse tabula tarsal tektite tenon
tephrite thole tilth torque torus toyon trabecula trachyte tramel transept travail
trestle trilobite trochee trophic tropism truant tufted turion tussock ulcer
umbilicus uncial undine ungulate upland uralite vacuole valence valine vascular
vassal veduta velum verdure vesicle vibrio vinculum vinegar viridian viscose
vitreal viverra vulgate wattle welkin wetland windrow winkle wireworm woodruff
xenogamy xeroderma xerophyte xiphoid xylose yawl yeoman zelkova zoeae zonate
abaft abeam abele abhor abide aboil aboon abore abort abray abrim abris abuzz
acred acred acrid acted acusp adage adagio addax adeem adept adieu adjoin adman
adnex adopt adore adorn adoze adrue adust afoul after again agene agene agest
agone agony agora agued aguti ahead aheap ahead ainee airts airts ajiva ajuga
alamo alarm albas alcid alday alder aldir aldis aleak aleck alefs aleft aleph
aleve alews alfas algae algal algo alike aliky alima allee alley allot allow
alloy allyl almah almas almes almud almug alods aloft alow alowe alpha alter
alula alums alure alway amble ameer amend amide amine amino amiss amity amnia
amnio among amour amove amuse amyls anear anele anent angel angry angst anigh
anime anion anise annex annoy annul anode antic antra antre anvil apers apian
arbol arbor arcus ardor ardeb arena arene arête argal argot argus ariel ariel
arish armet arpen arses arsis arson artel artic ascot ashen aspen assay asset
astir atilt atoll atomy atone attic audit augur auric aural aurar aures auric
avant avast avens avert avian avify avine avion aviso avize avout awash aweto
awing awned axial axile axing axion axman ayahs aylet azine azote azyme
babka baddy badge bagel baize balas balky balsa bandy banco baned banns barer
barky barmy barny baron barry barry batty bedim beech belam belle belly berme
beryls beryl beset bialy biome biont birch biros biter bites bitte bivia blank
blare blase blate blest bliny bliss blite blob bloch block bloom blore blout
blown blues bluff blunt blurs blype bolas bolts bonze booby borax borts botch
boule bower brand braze brick brill brisk brome brook broth brume brung brush
bubal buffy burse bushy buxom byway cabal caeca camel capot carex carol carse
carve caste caste cauld chafe champ chant chapt chard chela chert chime china
chirk chive chose circa civvy clamp clart clast clavi clear cleat cleft cleve
cline clivy cloak clop cloze coaly cobra coign coils combs condo corgi cornu
corse could coupl coupe coups couze craft crake crane creak creel creep crena
cress crone crude cruel cruck cruet cruse cruse crush crust cruve crypt cubby
curry culch culls curbs curdy cushy cutis cymar cymae cymar cymbal dace daffy
dairy dandy dashi datum deary debut defog delve dense deter deuce devil dicer
ditsy dodge doily doit dolce doltish dolly dolor domed donee dormy dotal doted
dotty douce dowdy doyen draft drail drape drawl droit dross drove druse ducat
""".split()

# ──────────────────────────────────────────────────────────────────────────────
# Tier 2: systematic color + nature compounds  (60 × 80 = 4800 unique combos)
# ──────────────────────────────────────────────────────────────────────────────

_COLORS = [
    "amber", "aqua", "ash", "azure", "birch", "black", "blaze", "bloom", "blue",
    "blush", "bone", "brass", "bronze", "brown", "cedar", "chalk", "char",
    "chrome", "clay", "cloud", "coal", "cobalt", "copper", "coral", "cream",
    "crimson", "cyan", "dusk", "ebony", "ecru", "fawn", "fern", "flax",
    "frost", "gold", "gray", "green", "hazel", "holly", "ice", "indigo",
    "iron", "ivory", "jade", "khaki", "lapis", "lemon", "lilac", "lime",
    "linen", "magenta", "maple", "mauve", "mint", "moss", "navy", "ochre",
    "olive", "opal", "pine", "plum", "rose", "ruby", "rust", "sage",
    "sand", "scarlet", "sepia", "silver", "sky", "slate", "smoke", "snow",
    "steel", "storm", "straw", "tan", "teal", "umber", "violet", "wheat",
    "white", "wine",
]

_NATURES = [
    "arc", "axe", "bay", "beam", "bear", "beck", "bolt", "bow", "brace",
    "branch", "brook", "bryn", "bud", "burr", "cap", "cave", "claw", "cliff",
    "cove", "creek", "crest", "crop", "crown", "dale", "dart", "dell", "den",
    "dew", "drift", "drop", "dune", "edge", "fang", "fen", "fern", "fin",
    "flake", "flame", "flare", "flow", "flume", "foam", "fold", "ford", "forge",
    "fork", "fume", "gale", "gash", "gate", "glade", "glen", "glow", "gorge",
    "grove", "gulf", "gust", "hail", "haze", "helm", "hive", "hoar", "hull",
    "keel", "knoll", "loch", "mast", "mead", "mire", "mist", "moor", "nook",
    "peat", "peak", "pool", "pore", "rift", "rind", "rook", "root", "rush",
    "salt", "shoal", "silt", "slab", "spar", "spit", "spore", "spray", "spur",
    "tern", "tide", "tine", "tor", "vale", "vane", "veil", "vent", "vine",
    "wake", "wold", "wynd",
]


def _build_compound_words():
    """Generate color+nature compound words, skip any that clash with real words."""
    compounds = []
    for color in _COLORS:
        for nature in _NATURES:
            compounds.append(f"{color}{nature}")
    return compounds


# ──────────────────────────────────────────────────────────────────────────────
# Assemble full vocabulary
# ──────────────────────────────────────────────────────────────────────────────

def _build_vocabulary():
    seen = set()
    vocab = []
    for w in _REAL_WORDS:
        w = w.lower()
        if w.isalpha() and w not in seen:
            seen.add(w)
            vocab.append(w)
    for w in _build_compound_words():
        if w not in seen:
            seen.add(w)
            vocab.append(w)
    return vocab


WORD_LIST = _build_vocabulary()

_pool_size = len(SYMBOL_POOL)
assert len(WORD_LIST) >= _pool_size, (
    f"Vocabulary ({len(WORD_LIST)}) must be ≥ pool ({_pool_size}). "
    "Add more words or compounds."
)


# ──────────────────────────────────────────────────────────────────────────────
# Hand-picked Unicode → alias overrides (best readability)
# ──────────────────────────────────────────────────────────────────────────────

_OVERRIDES: Dict[int, str] = {
    0x2190: "leftarrow",  0x2192: "rightarrow", 0x2191: "uparrow",   0x2193: "downarrow",
    0x2194: "lrarrow",    0x2195: "udarrow",     0x21D0: "dbleft",    0x21D2: "dbright",
    0x221E: "infinity",   0x2202: "partial",     0x2211: "sum",        0x220F: "product",
    0x221A: "sqrt",       0x2208: "element",     0x2229: "intersect",  0x222A: "union",
    0x2248: "approx",     0x2260: "notequal",    0x2264: "lte",        0x2265: "gte",
    0x00B1: "plusminus",  0x2207: "nabla",       0x2234: "therefore",  0x2235: "because",
    0x25A0: "blksquare",  0x25A1: "whtsquare",   0x25B2: "blktri",     0x25B3: "whttri",
    0x25C6: "blkdiam",    0x25C7: "whtdiam",     0x25CB: "whtcircle",  0x25CF: "blkcircle",
    0x2605: "blkstar",    0x2606: "whtstar",     0x2665: "blkheart",   0x2661: "whtheart",
    0x2318: "command",    0x2325: "option",      0x238B: "escape",
    0x267B: "recycle",    0x269B: "atom",        0x2744: "snowflake",  0x221E: "infinity",
    0x2764: "heartred",   0x2763: "heartexcl",   0x2762: "heartorn",
}


def _derive_from_name(cp: int) -> Optional[str]:
    """Try to get a short, clean word from the Unicode character name."""
    if cp in _OVERRIDES:
        return _OVERRIDES[cp]
    try:
        name = unicodedata.name(chr(cp))
    except ValueError:
        return None
    _noise = {
        "sign", "symbol", "letter", "small", "capital", "latin", "greek",
        "with", "and", "for", "the", "black", "white", "heavy", "light",
        "medium", "mathematical", "combining", "modifier", "regional",
        "indicator", "enclosed", "negative", "squared", "pattern", "tile",
        "card", "musical", "note", "braille", "domino", "zero", "one", "two",
        "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve",
    }
    import re
    tokens = re.split(r"[\s\-_]+", name.lower())
    for tok in tokens:
        if tok.isalpha() and 3 <= len(tok) <= 10 and tok not in _noise:
            return tok
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Build alias map
# ──────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def build_alias_map() -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    used: set = set()
    word_iter = iter(WORD_LIST)

    for symbol in SYMBOL_POOL:
        cp = ord(symbol)
        candidate = _derive_from_name(cp)

        if candidate is None or candidate in used:
            candidate = None
            for word in word_iter:
                if word not in used:
                    candidate = word
                    break
            if candidate is None:
                raise RuntimeError("Vocabulary exhausted — add more words.")

        used.add(candidate)
        alias_map[symbol] = candidate

    return alias_map


def get_alias(symbol: str) -> str:
    return build_alias_map().get(symbol, "unknown")


if __name__ == "__main__":
    m = build_alias_map()
    vals = list(m.values())
    print(f"Pool size      : {len(SYMBOL_POOL)}")
    print(f"Vocab size     : {len(WORD_LIST)}")
    print(f"Alias map size : {len(m)}")
    print(f"Unique aliases : {len(set(vals))} / {len(vals)}")
    for sym, alias in list(m.items())[:10]:
        try:
            name = unicodedata.name(sym)[:40]
        except ValueError:
            name = "?"
        print(f"  {alias:20s}  {name}")
