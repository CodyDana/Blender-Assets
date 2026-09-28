#!/usr/bin/env python
"""props_lib.smokebomb_layout4 - WHERE every tape strip of SM_SmokeBomb runs (round 4).

numpy only.  Round 3's layout (props_lib.smokebomb_layout3: round 2's REFERENCE_SPEC front
plus the base-circle far side) with the changes the round-3 fidelity adversary and blind
judge asked for.  Everything below that is not a REFERENCE_SPEC control point is DESIGNED
by eye from the reference, the way rounds 1 - 3 designed hidden edges; no reference pixel
is read at build time.

1. THE TOP WHORL.  Round 2 curled U1 (strip M1) left over the top as a 3 - 5 mm band - the
   "twisted S-shaped bundle".  At 3x the reference's whorl is a thin KNUCKLED RIDGE - a
   tape seen edge-on, ~9 px (0.7 mm) wide - rising almost straight from the V-gap apex
   (~(703, 265)) to the top outline at ~(665, 152), with the U fan converging on its
   right and the rim family sweeping into it from the left.  M1 now narrows over its last
   30 px above the apex into that ridge and follows it over the outline, standing half a
   layer proud (as W's twisted end does).  The ridge carries the cord's knuckles on both
   edges (props_lib.smokebomb_cloth4).
2. THE LOWER RIGHT.  Round 2's DcE filled everything between A's lower edge (ALO) and
   REFERENCE_SPEC's D27 as one band; the reference shows a second edge between them
   (at 3x: a crevice from ~(600, 915) curving through (840, 975) to (1000, 916)).  DcE is
   split into two shingled bands, E1 (over) and E2 (under), each on its own small circle.
3. THE V-NOTCH.  M1's lower part ended its REFERENCE_SPEC edge D57 at (510, 1000) and
   jumped to a waypoint behind the limb, which bent the edge into a notch at ~(515, 1000).
   D57 now runs on along its own direction to the outline.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional

import numpy as np

from . import smokebomb_strips as SS
from . import smokebomb_layout as L1
from . import smokebomb_layout3 as L3
from .smokebomb_layout import Design

#: DESIGNED: the whorl's knuckled ridge (M1 above the V-gap apex), image px, its two edges
RIDGE_HI = [(700, 251), (694, 229), (687, 206), (679, 186), (671, 167)]
RIDGE_LO = [(707, 253), (701, 230), (694, 207), (686, 187), (678, 168)]
RIDGE_EXIT = ("limb", 85.5, 4.0)
#: DESIGNED: the edge between E1 and E2 (lower right)
E_SPLIT = [(300, 850), (420, 862), (520, 890), (600, 915), (680, 945), (760, 967), (840, 975),
           (910, 963), (960, 942), (1000, 916)]
#: DESIGNED: D57 continued along its own direction to the bottom outline
D57_ON = [(523, 1023), (536, 1046)]


def designs() -> List[Design]:
    lim = lambda th, d: ("limb", th, d)
    out = []
    for d in L3.designs():
        if d.name == "M1":
            d = dataclasses.replace(
                d, hi=list(L1.UA) + RIDGE_HI, lo=list(L1.UC) + RIDGE_LO, lo2=list(L1.D57) + D57_ON,
                path=[(RIDGE_EXIT, 0.8), (lim(96.0, 18.0), 5.0),
                      ((520, 640), 9.0), ((440, 790), 12.0), (lim(254.0, 12.0), 14.0)],
                ranks=[(11.0, (690, 225)), (5.5, (640, 380)), (4.6, (400, 960))],
                lift=[((600, 470), 0.0), ((660, 300), 0.0), ((700, 250), 0.35), ((687, 206), 0.5),
                      ((671, 167), 0.5), (RIDGE_EXIT, 0.3), (lim(96.0, 25.0), 0.0)],
                note="U1 / D_a; above the V-gap apex it is the whorl's knuckled ridge (edge-on)")
            out.append(d)
            continue
        if d.name == "DcE":
            dce_hi = list(d.hi)
            dce_lo = list(d.lo)
            out.append(dataclasses.replace(d, name="E1", hi=dce_hi, lo=E_SPLIT, rank=3.25, back_width_mm=9.0,
                                           path=[(lim(210.0, 8.0), 9.0), (lim(318.0, 10.0), 9.0)],
                                           note="REFERENCE_SPEC D_c / E: the upper of two shingled bands"))
            out.append(dataclasses.replace(d, name="E2", hi=[(x, y - 26) for x, y in E_SPLIT], lo=dce_lo,
                                           rank=3.20, back_width_mm=9.0,
                                           path=[(lim(215.0, 10.0), 9.0), (lim(312.0, 10.0), 9.0)],
                                           note="REFERENCE_SPEC D_c / E: the lower band, D27 + 14 px its lower edge"))
            continue
        out.append(d)
    return out


def build_strips(ds: Optional[List[Design]] = None, fill: bool = True, log=None, **_ignored) -> List[SS.Strip]:
    return L3.build_strips(ds or designs(), fill=fill, log=log)


__all__ = ["designs", "build_strips", "RIDGE_HI", "RIDGE_LO", "E_SPLIT", "D57_ON"]
