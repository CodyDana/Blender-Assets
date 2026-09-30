"""Panel layout of References/Dojo/dojo_japanese_pine_ref.png (1448 x 1086) and the per-panel mask rules.

The sheet (REFERENCE_LOG.md, "Japanese pine sheet") shows FOUR pines, each as front + side + 3/4:
    top row    : pine 1 (small garden) T1-T3 at x 0-724, pine 2 (medium S) T4-T6 at x 724-1448
    middle row : pine 3 (large leaning) M1-M3 at x 0-845, pine 4 (cliff, on a boulder) M4-M6 at x 845-1448
    bottom row : close-ups: bark, pad side, pad from above, branch fork.
Separators were found by column/row contrast (the study's section 6.2 step 1). Boxes are full-image pixels.

``base``   = trunk centre where it leaves the mound (pines 1-3) or enters the rock (pine 4), full-image px.
``ground`` = the bottom of the mound / rock (ground contact), full-image px row.
``figure`` = the 1.8 m scale figure's (top, bottom) rows in that group (task text: 1.8 m silhouette).
``exclude`` = rectangles (x0, y0, x1, y1) blanked before masking (a neighbour's crown or trunk).
"""
SHEET = "References/Dojo/dojo_japanese_pine_ref.png"
SHEET_SHA256_PREFIX = "00d7b60f"

# Spec heights from the task / REFERENCE_LOG (the spec wins over the sheet's figure scale, study 8.2).
SPEC_HEIGHT_M = {1: 2.5, 2: 4.5, 3: 7.0, 4: 4.0}

FIGURE_M = 1.8

PANELS = {
    # pine 1: small garden pine
    "P1F": dict(pine=1, view="front", box=(62, 100, 296, 352), base=(161, 316), ground=333, figure=(179, 333)),
    "P1S": dict(pine=1, view="side", box=(296, 100, 457, 352), base=(384, 317), ground=333, figure=(179, 333)),
    "P1Q": dict(pine=1, view="3q", box=(457, 100, 724, 352), base=(588, 314), ground=333, figure=(179, 333)),
    # pine 2: medium S-curve
    "P2F": dict(pine=2, view="front", box=(790, 10, 1040, 352), base=(903, 314), ground=333, figure=(180, 334)),
    "P2S": dict(pine=2, view="side", box=(1040, 10, 1201, 352), base=(1123, 314), ground=333, figure=(180, 334)),
    "P2Q": dict(pine=2, view="3q", box=(1201, 10, 1448, 352), base=(1334, 314), ground=333, figure=(180, 334)),
    # pine 3: large leaning pine with the reaching limb
    "P3F": dict(pine=3, view="front", box=(8, 362, 452, 750), base=(412, 700), ground=738, figure=(590, 735),
                exclude=[(432, 362, 452, 640)]),
    "P3S": dict(pine=3, view="side", box=(432, 362, 569, 750), base=(519, 700), ground=738, figure=(590, 735),
                exclude=[(432, 590, 472, 750)]),
    "P3Q": dict(pine=3, view="3q", box=(569, 362, 845, 750), base=(740, 700), ground=738, figure=(590, 735)),
    # pine 4: cliff pine on a granite boulder (the boulder is part of the asset)
    "P4F": dict(pine=4, view="front", box=(856, 400, 1091, 750), base=(1003, 606), ground=735, figure=(590, 735),
                exclude=[(856, 585, 902, 750)]),
    "P4S": dict(pine=4, view="side", box=(1091, 400, 1222, 750), base=(1157, 640), ground=735, figure=(590, 735)),
    "P4Q": dict(pine=4, view="3q", box=(1222, 400, 1448, 750), base=(1336, 590), ground=735, figure=(590, 735)),
}

# The four close-ups (bottom row).
CLOSEUPS = {
    "bark": (0, 757, 371, 1086),
    "pad_side": (374, 757, 787, 1086),
    "pad_top": (790, 757, 1077, 1086),
    "fork": (1080, 757, 1448, 1086),
}


def figure_px_per_m(name):
    top, bottom = PANELS[name]["figure"]
    return (bottom - top) / FIGURE_M
