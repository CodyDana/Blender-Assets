"""Card Shop Kit numbers for the G1 standards spike (CARDSHOP_KIT_SPEC.md sections 3, 4.2-4.6).

Every length is millimetres. The flag after each value is the spec's: M = measured (source key), D = derived,
E = estimate / design choice. Nothing here imports bpy, so the numbers are testable under any Python.

Frames (spec 4.2): every item's pivot is its ``Seat``: the centre of the face it rests on, +X to the viewer's right,
+Y away from the customer, +Z up. Items are modelled lying in their display pose (a card, slab or pack lies on its
back, face up; a booster box stands on its bottom).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

SPEC_VERSION = "g1-1"      # the G1 spike subset; the full kit grows this module per family (spec 7.2)
MM = 0.001                 # Blender metres per spec millimetre

# --------------------------------------------------------------------------- items

CARD_STD = dict(w=63.0, h=88.0, t=0.30, r=3.0, corner_segs=5)     # 63 x 88 M [D1]; 0.30 E; R3 E
CARD_SMALL = dict(w=59.0, h=86.0, t=0.30, r=3.0, corner_segs=5)   # M [D1]; the Small card is not in G1

TOPLOADER_35 = dict(
    w=76.2, h=101.6,          # outer, M [D4]
    in_w=69.0, in_h=97.0,     # inner pocket, E* (another source gives 69.9 x 98.4)
    t=2.0,                    # overall thickness, E
    gap=0.89,                 # card gap, D from 35 pt [D4]
    corner_r=3.5,             # reference sheet 2 (measured off the picture), replaces square corners
    notch_w=20.8, notch_d=8.4,  # reference sheet 2 measured at 3x: a shallow arc 20.8 wide x 8.4 deep (spec E: 20)
)
TOPLOADER_130 = dict(t=4.8, gap=3.30)   # the thick holder: overall 4.8 E, gap 3.30 D from 130 pt [D4]

SLAB_STD = dict(
    w=84.0, h=134.0, t=7.0,   # E, inside the measured ranges W 81-86, H 130-139, T 5-8 (M [D7])
    chamfer=4.0,              # 45-degree corner chamfers (reference sheet 3: 4.0 measured)
    # the face layout, measured on reference sheet 3 (csk_slab.png, 3.55 px/mm); the same on the back face
    rim=2.0,                  # the outer rim: full height
    step=1.0, step_d=0.6,     # the step inside the rim, 0.6 lower
    label=(71.0, 20.5, 51.75),   # label opening W x H, centre Y
    label_d=0.6,              # label recess depth: the insert lies flush with the step
    window=(68.5, 95.3, -13.75),  # window opening W x H, centre Y (cross bar 7.6 between label and window)
    window_d=0.8,             # window recess depth
    gasket=(67.6, 92.6, 3.8),  # filled slab: the white gasket ring round the card, outer W x H, corner R
    lug=(8.0, 3.0, 0.5, 50.0),   # stacking lugs on both long sides: length Y, height Z, proud X, |centre Y|
    well=(65.0, 90.0, 1.0),   # card well W x H x depth: card + 1 mm a side; depth >= 0.76 max card (M)
    well_floor_z=3.0,         # E: 3.0 bottom skin, 1.0 well, 3.0 top skin
)

PACK_STD = dict(
    w=67.0, h=117.0,          # M [D2][D9]
    t=4.0,                    # overall, incl. the back fin (reference sheet 4 call-out: 4 mm)
    edge_t=0.3,               # sealed crimp / fold thickness, E
    crimp=9.0,                # crimp depth at both short ends (sheet 4: 7.1 ribbed band incl. teeth + 1.9 flat seal)
    seal=1.9,                 # the flat seal strip between the ribbed band and the pillow
    teeth=27,                 # sheet 4, counted at 5x: 27 teeth, 2.48 pitch
    tooth_d=1.4,              # tooth depth, sheet 4
    rib=0.3,                  # crimp rib amplitude (sheet 4 close-up: strong pleats, about 25 deg) (one rib per tooth; the film is pressed, so both skins move)
    fin=(25, 29, 24, 30, 0.4),  # back fin seal: flat k 25..29 (|x| <= 2.48), walls to k 24 / 30, 0.4 proud
)

BOX_BOOSTER_S = dict(
    w=140.0, d=80.0, h=125.0,  # E: sized so 36 packs fit (the pack -> box map, spec 3.B)
    board=2.0,                 # E
    packs=(2, 18),             # 2 across x 18 deep, standing
    pack_pitch=4.0,            # D: = PACK_STD t
    # reference sheet 5 (csk_booster_box.png)
    window=(126.0, 100.0, 70.0, 6.0),   # front die-cut: width at the rim, width at the bottom, depth, bottom corner R
    divider=(2.0, 15.0),       # centre divider: board thickness, top below the rim
    tab=(77.0, 20.0, 6.0),     # the lid's tuck flap (the display header's tab): W x H, corner R
    header_rot=-100.0,         # display pose: the lid stands up behind the box, 10 deg past vertical
    film=0.4,                  # sealed state: shrink film clearance
)

SHOWCASE_FULL = dict(
    lengths=(1219.0, 1778.0),  # M [D23]; G1 builds 1778
    d=508.0, h=965.0,          # M [D22]
    glass=6.35,                # M [D24]
    kick=152.0,                # E*
    deck=23.0,                 # deck board on the kick base, E
    post=25.0,                 # aluminium corner post section, E
    rail=20.0,                 # aluminium rail section, E
    shelves=((356.0, 253.0), (305.0, 253.0)),  # (depth, clear height below it) S1, S2; depths E*, spacing E
    track=(15.0, 25.0),        # rear door track height x depth, E
    door_overlap=25.0,         # door W = L/2 + 25 (E)
    door_travel_off=50.0,      # travel = L/2 - 50 (E)
    stile=15.0,                # door edge stile, E
)

# --------------------------------------------------------------------------- classes (spec 4.2)

@dataclass(frozen=True)
class ItemClass:
    code: str
    footprint: Tuple[float, float, float]   # W x D x H as displayed (mm)
    pitch: Tuple[float, float]               # grid pitch X x Y (mm)


CLASSES: Dict[str, ItemClass] = {c.code: c for c in (
    ItemClass("Card", (66.7, 92.1, 0.5), (77.0, 102.0)),
    ItemClass("CardProt", (84.1, 123.8, 6.0), (94.0, 134.0)),
    ItemClass("Slab", (84.0, 134.0, 7.0), (94.0, 144.0)),
    ItemClass("Pack", (67.0, 117.0, 4.0), (77.0, 127.0)),
    ItemClass("BoxS", (140.0, 80.0, 125.0), (150.0, 90.0)),
    ItemClass("Deck", (82.0, 86.0, 116.0), (92.0, 96.0)),
)}

# which class each G1 item belongs to (its .csk.json "class")
ITEM_CLASS = {
    "SM_CSK_Card_Std": "Card",
    "SM_CSK_TopLoader_35pt": "CardProt",
    "SM_CSK_TopLoader_130pt": "CardProt",
    "SM_CSK_Slab_Std": "Slab",
    "SM_CSK_Slab_Std_Filled": "Slab",
    "SM_CSK_Pack_Std_Sealed": "Pack",
    "SM_CSK_Box_Booster_S": "BoxS",
    "SM_CSK_Box_Booster_S_Sealed": "BoxS",
}

SHOWCASE_ACCEPTS = ("Card", "CardProt", "Slab", "Pack", "BoxS", "Deck")
GRID_MARGIN = 10.0     # clear margin inside a level before the first slot (spec 4.2 example: (1740 - 20) / 94)

# --------------------------------------------------------------------------- LODs and budgets (spec 4.6)

LOD0_ONLY_MAX_TRIS = 150     # meshes at or under this ship LOD0 only (the general rule of section 3)


@dataclass(frozen=True)
class LodClass:
    name: str
    lod1_m: float
    lod2_m: float


LOD_CLASSES = {
    "handheld": LodClass("handheld", 1.5, 4.0),   # R < 100 mm
    "medium": LodClass("medium", 4.0, 10.0),      # 100-500 mm
    "fixture": LodClass("fixture", 8.0, 20.0),    # > 500 mm
}


def lod_class(radius_mm: float) -> LodClass:
    if radius_mm < 100.0:
        return LOD_CLASSES["handheld"]
    if radius_mm <= 500.0:
        return LOD_CLASSES["medium"]
    return LOD_CLASSES["fixture"]


def screen_sizes(radius_mm: float, lod_count: int) -> List[float]:
    """The kit rule S = 1.778 R / d (16:9, 90 deg HFOV), capped at 1.0 for LOD0 (spec 4.6)."""
    lc = lod_class(radius_mm)
    r = radius_mm * MM
    sizes = [1.0, min(1.0, 1.778 * r / lc.lod1_m), min(1.0, 1.778 * r / lc.lod2_m)]
    return [round(s, 6) for s in sizes[:lod_count]]


# LOD0 triangle budgets (spec section 3 "Tris" column)
BUDGETS = {
    "SM_CSK_Card_Std": 96,
    "SM_CSK_TopLoader_35pt": 300,
    "SM_CSK_TopLoader_130pt": 300,
    "SM_CSK_Slab_Std": 1200,
    "SM_CSK_Slab_Std_Filled": 1300,
    "SM_CSK_Pack_Std_Sealed": 1500,     # was 300 (E); sheet 4 ribs + 27 teeth + fin seal need ~1.4k
    "SM_CSK_Box_Booster_S": 400,
    "SM_CSK_Box_Booster_S_Lid": 150,
    "SM_CSK_Box_Booster_S_Sealed": 400,
    "SM_CSK_Showcase_Full_1778": 3000,
    "SM_CSK_Showcase_Full_Glass_1778": 600,
    "SM_CSK_Showcase_Full_Door_1778": 150,
}

HANDHELD_HULL_MIN_T = 2.0    # box hulls of handheld items are at least 2 mm thick, centred (spec 4.6)

# --------------------------------------------------------------------------- IP deny scan (spec 6.3)

CSK_DENY_TERMS = (
    "pokemon", "pokémon", "magic the gathering", "gathering", "yu-gi-oh", "yugioh", "lorcana", "one piece", "topps",
    "panini", "upper deck", "beckett", "ultra pro", "ultrapro", "dragon shield", "ultimate guard", "one-touch",
    "onetouch", "card saver", "cardsaver", "deck protector", "elite trainer", "gem mt", "gem mint",
    "tcg card shop simulator", "sports card shop simulator", "card shop simulator", "tetramon",
)
CSK_DENY_WORDS = ("tag", "psa", "bgs", "cgc", "sgc", "kmc", "bcw")
CSK_ALLOW = ("price tag", "pricetag", "hang tag", "hangtag")


def deny_hits(text: str) -> List[str]:
    """Deny terms found in ``text`` (substrings) and deny words as whole tokens (split on non-alphanumerics and
    ``_``, NOT on CamelCase, so ``PriceTag`` and ``Stage`` pass). The allow-list is removed first."""
    import re
    low = text.lower()
    for allowed in CSK_ALLOW:
        low = low.replace(allowed, " ")
    hits = [t for t in CSK_DENY_TERMS if t in low]
    tokens = set(re.split(r"[^0-9a-z]+", low))
    hits += [w for w in CSK_DENY_WORDS if w in tokens]
    return hits


# --------------------------------------------------------------------------- helpers

def bounds_radius(size_mm: Tuple[float, float, float]) -> float:
    return 0.5 * math.sqrt(sum(s * s for s in size_mm))
