#!/usr/bin/env python
"""props_lib.smokebomb_layout - WHERE every tape strip of SM_SmokeBomb runs (round 2).

numpy only.  The numbers below are REFERENCE_SPEC.md's own: its edge control points
(image px, the reference's 1254 px frame), its strip widths, its over/under table and its
designed far side.  Where the spec is silent (a hidden edge, the far side, the order inside
a family) the value is a DESIGN choice and says so.  Nothing here is read from the reference
image or from the metrology agent's trace or debug files at build time: the build imports
these constants and nothing else.

ROUND 2: EVERY STRIP IS A CLOSED LOOP
-------------------------------------
Round 1 ended strips under covers ("tucks") and filled bare patches with low loops; the
render showed cut tape ends and short shingled tabs the reference never shows.  Here every
strip is one closed band round the ball, so a strip can only disappear by passing UNDER
another one, exactly as the reference's strips do (T-junctions, REFERENCE_SPEC 4.4).

    belt      W, A, B/C and X: the diagonal belt (REFERENCE_SPEC 4.2 / 4.3)
    meridians M0 - M5: each runs from the top whorl down the upper front (the U fan,
              U0 - U5), passes under the belt, comes out below it as one of the bottom
              family (D, E) and closes over the back through the bottom whorl.  Left
              alone, a strip leaving the whorl down the front lands exactly where the
              reference's bottom family lies, so the two families are one set of loops.
    rim       R3, R2, R_in: loops round a pole on the upper-left limb; R_in continues down
              the left limb (L5) and passes under C
    left      L3, L4: rings round a pole on the front-left, hidden everywhere except the
              arc the reference shows on the left side

RANKS - the woven order of REFERENCE_SPEC 4.4
---------------------------------------------
A strip's rank is constant except where the reference weaves: R_in is over A and W at the
top-left but under C at its lower end (the cycle R_in > A > C > L5), and a meridian's U
part and D part sit at different heights in their families.  Each such strip carries two
ranks and a probe point for each; the SWITCHES between them are placed automatically where
no strip of an in-between rank touches the strip's cross-section, so a switch never shows
(``resolve_switches``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

#: the chart radius every strip's millimetres are measured on (the mean tape surface)
CHART_RADIUS_MM = 35.0

#: the top whorl (REFERENCE_SPEC 4.5): V-gap apex, image px
WHORL_TOP_PX = (690.0, 252.0)
#: the bottom convergence: DESIGNED (REFERENCE_SPEC 9.5)
WHORL_BOTTOM_CAM = SS.normalize(np.array([0.05, -0.97, -0.25]))


def _img(pts) -> np.ndarray:
    """Reference px -> camera-frame unit vectors.  Inside the outline: the orthographic
    back-projection (``smokebomb_strips.img_to_cam``).  Past the outline (DESIGNED points
    only): continued round the limb, (r - R) / R radians behind it, so an edge can be
    written as running on beyond the silhouette."""
    a = np.asarray(pts, np.float64).reshape(-1, 2)
    dx = (a[:, 0] - SS.REF_CENTRE_PX[0]) / SS.REF_RADIUS_PX
    dy = -(a[:, 1] - SS.REF_CENTRE_PX[1]) / SS.REF_RADIUS_PX
    r = np.hypot(dx, dy)
    out = SS.img_to_cam(a[:, 0], a[:, 1])
    far = r > 1.0
    if far.any():
        th = math.pi / 2 + (r[far] - 1.0)
        u = np.stack([dx[far], dy[far]], axis=1) / r[far][:, None]
        out[far] = np.stack([np.sin(th) * u[:, 0], np.sin(th) * u[:, 1], np.cos(th)], axis=1)
    return out


def mm_to_deg(mm: float) -> float:
    return math.degrees(mm / CHART_RADIUS_MM)


def beyond_limb(theta_deg: float, delta_deg: float) -> np.ndarray:
    """A point ``delta_deg`` behind the outline at image angle ``theta_deg`` (camera frame)."""
    t, d = math.radians(theta_deg), math.radians(delta_deg)
    return np.array([math.cos(t) * math.cos(d), math.sin(t) * math.cos(d), -math.sin(d)])


def _point(p) -> np.ndarray:
    """A point spec: image px (x, y) on the front, ("ll", lat, lon) camera frame, or
    ("limb", image angle, degrees behind the outline)."""
    if isinstance(p, tuple) and len(p) == 3 and p[0] == "ll":
        return SS.latlon(p[1], p[2])
    if isinstance(p, tuple) and len(p) == 3 and p[0] == "limb":
        return beyond_limb(p[1], p[2])
    if isinstance(p, np.ndarray) and p.shape == (3,):
        return SS.normalize(p)
    return _img([p])[0]


@dataclass
class Design:
    name: str
    family: str
    #: front edges, image px (either may be None when ``centre`` is given)
    hi: Optional[Sequence[Tuple[float, float]]] = None
    lo: Optional[Sequence[Tuple[float, float]]] = None
    #: a second pair of edges elsewhere on the same strip (a meridian's D part)
    hi2: Optional[Sequence[Tuple[float, float]]] = None
    lo2: Optional[Sequence[Tuple[float, float]]] = None
    #: front centre line, image px, with a TRUE width in mm (used where an edge is hidden)
    centre: Optional[Sequence[Tuple[float, float]]] = None
    centre_width_mm: float = 10.0
    #: one edge + a width: (edge points, width mm, +1 if the strip lies on the side of
    #: larger phi... resolved automatically from ``toward`` - a point on the strip's side)
    edge_w: Sequence[Tuple[Sequence[Tuple[float, float]], float, Tuple[float, float]]] = ()
    #: extra centre-line points anywhere: (point spec, width mm) - hidden runs, the back
    path: Sequence[Tuple[object, float]] = ()
    back_width_mm: float = 10.0
    #: lift knots in tape layers: (point spec, layers)
    lift: Sequence[Tuple[object, float]] = ()
    pole: Optional[Tuple[float, float, float]] = None
    #: "gc": the strip's own great circle; "plane": the best-fit SMALL circle
    fit: str = "gc"
    #: fit the frame to the front only (default) or to front + path points
    path_in_fit: bool = True
    rank: float = 5.0
    #: woven: (rank_a, probe_a, rank_b, probe_b) - switches placed automatically
    rank2: Optional[Tuple[float, object, float, object]] = None
    #: woven, any number of ranks: [(rank, probe point), ...] - switches placed automatically
    ranks: Sequence[Tuple[float, object]] = ()
    #: take the frame pole of an already-built strip (a strip parallel to it)
    pole_like: Optional[str] = None
    #: phi of the automatic far side: None = the frame's own circle, "auto" = the mean phi
    #: of the front (a ring concentric with the front arc)
    back_phi: object = None
    #: fill the largest lam gap with the frame's own circle (off for a loop given in full)
    back_fill: bool = True
    note: str = ""


# =========================================================================== the designs
#
# Every image point below that sits on a VISIBLE edge is a REFERENCE_SPEC control point
# (section 4.2 table + reference_spec.json "edge_control_points"), copied as numbers.
# Points on hidden edges and every back point are DESIGNED.

# --- REFERENCE_SPEC edge control points (image px) ---------------------------------
WTW = [(363, 390), (402, 420), (438, 451), (478, 482), (520, 509), (563, 530), (609, 550)]
WUP = [(610, 550), (682, 581), (757, 602), (831, 625), (902, 656), (974, 687), (1048, 712)]
WLO = [(540, 522), (620, 581), (703, 635), (787, 688), (875, 736), (957, 789), (1044, 837)]
ALO = [(282, 455), (330, 612), (435, 732), (574, 817), (727, 876), (882, 920), (1027, 861)]
BUP = [(556, 510), (639, 476), (722, 441), (805, 412), (893, 393), (983, 393), (1069, 417)]
BLO = [(705, 586), (769, 584), (830, 573), (892, 558), (954, 544), (1016, 536), (1079, 535)]
CUP = [(190, 768), (216, 746), (242, 728), (271, 710), (302, 697), (333, 686), (365, 676)]
CLO = [(270, 935), (326, 908), (385, 891), (444, 881), (503, 862), (563, 845), (623, 843)]
LIN = [(580, 306), (478, 329), (385, 378), (293, 434), (223, 513), (215, 616), (258, 712)]
LC = [(473, 314), (415, 335), (360, 363), (305, 387), (260, 429), (221, 477), (188, 529)]
LA = [(600, 238), (542, 242), (484, 248), (429, 256), (373, 269), (319, 292), (273, 326)]
L3L = [(270, 452), (252, 491), (252, 535), (257, 579), (266, 624), (283, 664), (309, 699)]
UA = [(496, 486), (529, 448), (567, 416), (596, 379), (630, 343), (660, 302), (690, 262)]
UC = [(640, 462), (647, 427), (652, 393), (664, 361), (689, 334), (708, 307), (725, 275)]
UD = [(738, 432), (741, 404), (744, 376), (749, 349), (763, 322), (774, 297), (785, 271)]
UE = [(825, 237), (833, 264), (840, 289), (847, 316), (855, 343), (863, 368), (871, 394)]
UF = [(882, 264), (899, 281), (914, 299), (919, 322), (917, 344), (917, 367), (925, 390)]
D14 = [(300, 925), (329, 950), (358, 977), (384, 1004), (413, 1029), (447, 1051), (480, 1070)]
D57 = [(436, 865), (448, 888), (461, 911), (472, 932), (484, 955), (497, 977), (510, 1000)]
D9 = [(527, 866), (546, 897), (567, 928), (590, 958), (614, 985), (639, 1011), (664, 1039)]
D19 = [(517, 1029), (545, 1034), (568, 1044), (591, 1057), (616, 1068), (644, 1075), (669, 1080)]
D27 = [(700, 1050), (730, 1045), (760, 1043), (791, 1042), (821, 1038), (850, 1030), (878, 1021)]


def _shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def beyond(angles_deg, r_px: float):
    """Image points on a circle of radius ``r_px`` about the reference centre (image angles,
    CCW from 3 o'clock).  Past the outline they map BEHIND the limb (``_img``)."""
    return [(SS.REF_CENTRE_PX[0] + r_px * math.cos(math.radians(a)),
             SS.REF_CENTRE_PX[1] - r_px * math.sin(math.radians(a))) for a in angles_deg]


def arc_points(a, b, n: int, via=None) -> List[np.ndarray]:
    """``n`` points strictly between unit vectors a and b along the great circle (through
    ``via`` when given: n points on each half)."""
    a = SS.normalize(np.asarray(a, float))
    b = SS.normalize(np.asarray(b, float))
    if via is not None:
        v = SS.normalize(np.asarray(via, float))
        return arc_points(a, v, n) + [v] + arc_points(v, b, n)
    om = math.acos(max(-1.0, min(1.0, float(a @ b))))
    out = []
    for t in np.linspace(0.0, 1.0, n + 2)[1:-1]:
        if om < 1e-9:
            p = a
        else:
            p = (math.sin((1 - t) * om) * a + math.sin(t * om) * b) / math.sin(om)
        out.append(SS.normalize(p))
    return out


def back_path(exit_pt, entry_pt, front_mid_px, width_mm: float, n: int = 3):
    """Hidden / far-side waypoints closing a loop: from ``exit_pt`` (behind the outline where
    the strip leaves the front) round the BACK to ``entry_pt``, through the mirror image
    (z -> -z) of the front part's middle, so the far half echoes the near half."""
    m = _point(front_mid_px).copy()
    m[2] = -abs(m[2])
    return [(p, width_mm) for p in arc_points(_point(exit_pt), _point(entry_pt), n, via=m)] + \
        [(_point(exit_pt), width_mm), (_point(entry_pt), width_mm)]


def designs() -> List[Design]:
    """The strip list.  Order does not matter; rank decides what is on top."""
    out: List[Design] = []
    lim = lambda th, d: ("limb", th, d)

    # ------------------------------------------------------------------ the belt
    # W: the narrow top strip.  Its left end is TWISTED edge-on (WTW, a narrow ridge
    # standing proud) and opens between x 540 and ~790 into the flat 79 px strip bounded by
    # WUP / WLO.  Left of (363, 390) it runs on, hidden under the rim family.
    w_hi = [(330, 364), (363, 383)] + [(x, y - 7) for x, y in WTW[1:5]] + [(563, 524), (609, 546)] + WUP[1:]
    w_lo = [(330, 378), (363, 397)] + [(x, y + 7) for x, y in WTW[1:4]] + [(520, 515)] + WLO
    out.append(Design("W", "belt", hi=w_hi, lo=w_lo, back_width_mm=6.0, rank=9.0,
                      lift=[((250, 330), 1.0), ((520, 509), 1.0), ((640, 565), 0.35), ((720, 590), 0.0),
                            (("limb", 330.0, 60.0), 0.0)],
                      note="twisted end = a narrow ridge standing one layer proud (WTW)"))
    # A: wide, under W.  Upper edge HIDDEN along W's ridge and then under W (DESIGNED).
    a_hi = [(300, 350), (363, 390)] + WTW[1:] + [(703, 611), (787, 649), (875, 690), (957, 734), (1044, 774)]
    a_lo = [(262, 400)] + ALO
    out.append(Design("A", "belt", hi=a_hi, lo=a_lo, back_width_mm=17.0, rank=8.0))
    # B / C: ONE strip (REFERENCE_SPEC 4.3): C enters at the lower-left limb, dives under A
    # and W, comes out above W as B.  DESIGNED: the hidden stretch under A.
    bc_hi = CUP + [(430, 620), (500, 556)] + BUP
    bc_lo = CLO + [(660, 760), (690, 660)] + BLO
    out.append(Design("BC", "belt", hi=bc_hi, lo=bc_lo, back_width_mm=14.0, rank=7.0))
    # X: its own strip lying under A (REFERENCE_SPEC 4.3), showing only as the wedge between
    # B and W on the right.  Left of B's tip it stays inside A's footprint and leaves the
    # front under the rim family.
    x_hi = [(705, 572), (769, 562), (830, 551), (892, 536), (954, 522), (1016, 514), (1079, 512)]
    x_lo = [(757, 700), (831, 735), (902, 770), (974, 800), (1048, 830)]
    out.append(Design("X", "belt", hi=x_hi, lo=x_lo, back_width_mm=12.0, rank=6.0,
                      path=[((600, 630), 8.0), ((500, 575), 8.0), ((420, 500), 7.0), ((360, 410), 7.0),
                            (lim(142.0, 10.0), 8.0)]))

    # ------------------------------------------------------------------ the rim family
    # Loops round a pole on the upper-left limb.  R2 over R3 (LA is R2's own outer edge) and
    # over R_in (LC is R2's own inner edge).  R3 hugs the top-left outline; R2 leaves the
    # front over the upper-left limb at 140-167 deg; R_in runs on down the left limb (L5).
    RIM_POLE = tuple(beyond_limb(125.0, 15.0).tolist())
    out.append(Design("R2", "rim", hi=LC, lo=LA, rank=10.5, pole=RIM_POLE, back_phi="auto",
                      back_width_mm=12.0,
                      path=[((592, 246), 9.0), ((608, 205), 8.0), (lim(96.0, 6.0), 8.0),
                            (lim(158.0, 10.0), 12.0)]))
    out.append(Design("R3", "rim", hi=_shift(LA, 4, 20), lo=beyond([150, 140, 130, 120, 110, 100, 94], 565.0),
                      rank=10.3, pole=tuple(beyond_limb(118.0, 30.0).tolist()),
                      back_phi="auto", back_width_mm=12.0,
                      path=[(lim(100.0, 8.0), 10.0), (lim(142.0, 8.0), 12.0)]))
    # R_in / L5: ONE ring round a point on the front-left (LIN is nearly a circle round
    # image (520, 620)), wholly on the front: visible from beside the whorl round the upper
    # left and down the left limb (L5); the rest of the ring runs out of sight under R2, the
    # U fan, the belt and C (DESIGNED).  Rank 10 on the visible arc, 4.5 everywhere else,
    # which puts L5 under C: REFERENCE_SPEC 4.4's woven cycle R_in > A > C > L5.
    r_in_w = [7.0, 7.0, 7.0, 8.0, 14.0, 20.0, 20.0]
    out.append(Design("R_in", "rim", edge_w=[(LIN, r_in_w, (300, 400))], rank=10.0,
                      pole=tuple(SS.img_to_cam(np.array([520.0]), np.array([620.0]))[0].tolist()),
                      path=[((590, 268), 5.0), ((640, 245), 5.0), ((700, 300), 5.0), ((760, 450), 5.0),
                            ((820, 620), 5.0), ((740, 780), 5.0), ((600, 790), 5.0), ((520, 790), 5.0),
                            ((440, 760), 6.0), ((320, 750), 7.0)], back_fill=False,
                      rank2=(10.0, (300, 420), 4.5, (760, 450))))
    # ------------------------------------------------------------------ the left pair
    # L4 over L3 (L3L is L4's own right edge).  Both come out from under R_in at the top-left
    # and pass under C at the bottom, then on under Da and Db to the bottom limb.
    out.append(Design("L4", "left", edge_w=[(L3L, [6.5, 8.0, 8.5, 8.5, 8.5, 8.5, 9.0], (225, 560))],
                      rank=4.2, fit="plane",
                      path=[((250, 420), 6.0), ((212, 378), 6.0), (lim(152.0, 10.0), 6.0),
                            ((340, 760), 6.0), ((400, 860), 5.5), ((440, 960), 5.0), (lim(258.0, 10.0), 5.0)]
                      + back_path(lim(258.0, 10.0), lim(152.0, 10.0), (260, 560), 6.0)))
    l3_hi = [(296, 452), (318, 530), (345, 612), (400, 680), (445, 735)]
    out.append(Design("L3", "left", hi=l3_hi, lo=_shift(L3L, -10, 0), rank=4.0, fit="plane",
                      path=[((290, 420), 6.0), ((250, 372), 6.0), (lim(146.0, 10.0), 6.0),
                            ((390, 780), 6.0), ((450, 870), 5.5), ((480, 960), 5.0), (lim(262.0, 10.0), 5.0)]
                      + back_path(lim(262.0, 10.0), lim(146.0, 10.0), (300, 580), 6.0)))

    # ------------------------------------------------------------------ the meridians
    # U part above the belt (REFERENCE_SPEC U edges), D part below it, joined out of sight
    # under the belt.  U1 > U2 > U3 > U4 > U5: each one's right edge is its own and its left
    # edge lies under its left neighbour; U0 / U1 meet at an open V-gap.  At the bottom
    # Da > Db (D57 is Da's own edge) > DcE (D9 is Db's own edge).
    # U0 / U1 meet at the spec's open V-gap: from (496, 486) it opens to ~30 px at (585, 390)
    # and closes again toward the whorl apex (690, 252).  The gap shows the deepest layer.
    u0_lo = [(496, 488), (527, 438), (556, 392), (590, 352), (625, 314), (660, 282), (684, 262)]
    out.append(Design("M0", "meridian", hi=_shift(LIN[:4], -2, -16), lo=u0_lo, fit="plane",
                      path=[((712, 222), 9.0), (lim(88.0, 10.0), 9.0),
                            ((470, 620), 12.0), ((400, 780), 15.0), ((310, 905), 18.0), (lim(222.0, 6.0), 16.0),
                            (lim(245.0, 10.0), 14.0)]
                      + back_path(lim(245.0, 8.0), lim(88.0, 10.0), (450, 600), 9.0),
                      rank2=(5.0, (523, 360), 3.0, lim(236.0, 5.0))))
    # U1: UA / UC.  At the whorl it CURLS LEFT over the top (UA runs on as the whorl's rolled
    # edge WHV, REFERENCE_SPEC 4.5: apex (690, 252), the V-gap below-left of it) and goes over
    # the top outline at ~92 deg, stacked on the rim strips it crosses (the +14.9 px bump at
    # 88 deg).  Below the belt it is D_a (D14 / D57).  Three ranks: over the rim family at the
    # whorl, in the U order below it, under C at the bottom.
    whv = [(695, 246), (692, 228), (680, 212), (662, 200), (640, 192)]
    whv_out = [(744, 242), (738, 214), (720, 192), (696, 178), (668, 168)]
    out.append(Design("M1", "meridian", hi=UA + whv, lo=UC + whv_out, hi2=D14, lo2=D57, fit="plane",
                      path=[(lim(89.0, 6.0), 4.2), (lim(96.0, 18.0), 5.0),
                            ((520, 640), 9.0), ((440, 790), 12.0), (lim(254.0, 12.0), 14.0)]
                      + back_path(lim(254.0, 12.0), lim(96.0, 18.0), (520, 640), 11.0),
                      ranks=[(11.0, (690, 215)), (5.5, (640, 380)), (4.6, (400, 960))],
                      lift=[((600, 470), 0.0), ((660, 300), 0.0), ((690, 240), 0.0), ((650, 190), 0.0),
                            (lim(89.0, 4.0), 0.0), (lim(96.0, 25.0), 0.0)]))
    out.append(Design("M2", "meridian", hi=UD, lo=_shift(UC, -15, 0), hi2=_shift(D57, -14, 4), lo2=D9,
                      fit="plane",
                      path=[((760, 212), 6.0), (lim(76.0, 12.0), 7.0),
                            ((620, 640), 8.0), ((530, 800), 9.0), (lim(262.0, 12.0), 9.0)]
                      + back_path(lim(262.0, 12.0), lim(76.0, 12.0), (620, 640), 8.0),
                      rank2=(5.4, (700, 380), 4.4, (500, 940))))
    out.append(Design("M3", "meridian", hi=UE, lo=_shift(UD, -15, 0), fit="plane",
                      path=[(lim(66.0, 12.0), 8.0),
                            ((760, 600), 9.0), ((720, 800), 9.0), ((700, 960), 9.0), (lim(282.0, 12.0), 9.0)]
                      + back_path(lim(282.0, 12.0), lim(66.0, 12.0), (740, 650), 9.0),
                      rank2=(5.3, (800, 330), 3.0, (720, 800))))
    out.append(Design("M4", "meridian", hi=UF, lo=_shift(UE, -15, 0), fit="plane",
                      path=[(lim(60.0, 12.0), 7.0),
                            ((930, 600), 7.0), ((900, 800), 7.0), ((840, 960), 7.0), (lim(295.0, 12.0), 7.0)]
                      + back_path(lim(295.0, 12.0), lim(60.0, 12.0), (920, 650), 7.0),
                      rank2=(5.2, (880, 330), 2.9, (900, 800))))
    out.append(Design("M5", "meridian", edge_w=[(_shift(UF, -15, 0), 26.0, (1000, 330))],
                      pole=(0.6, 0.1, -0.79), back_width_mm=8.0,
                      path=[(lim(52.0, 12.0), 9.0),
                            ((1000, 520), 8.0), ((990, 700), 8.0), ((950, 880), 8.0), (lim(300.0, 12.0), 8.0)],
                      rank2=(5.1, (955, 320), 2.8, (960, 880))))
    # DcE: one strip lying under A, parallel to it, below it on the right (between ALO and
    # D27); its left end dives under Db (D9 is Db's own edge) and runs on under C to the
    # left limb.  REFERENCE_SPEC's "D_c" and "E" regions are this one band.
    dce_hi = [(300, 800), (400, 790), (500, 820)] + _shift(ALO[3:], 0, -24)
    dce_lo = [(290, 900), (420, 900), (560, 960), (650, 1035)] + _shift(D27, 0, 14) + [(935, 1010), (985, 975)]
    out.append(Design("DcE", "bottom", hi=dce_hi, lo=dce_lo, rank=3.25, fit="plane",
                      path=[(lim(210.0, 8.0), 10.0), (lim(318.0, 10.0), 11.0)]
                      + back_path(lim(318.0, 10.0), lim(210.0, 8.0), (620, 900), 11.0)))
    # Rb: the band hugging the bottom outline, over Db and DcE (D19 and D27 are its own
    # edges), under Da; a loop round the bottom whorl (DESIGNED).
    out.append(Design("Rb", "bottom", edge_w=[(D19 + D27, 12.0, (640, 1090))], rank=4.45,
                      pole=tuple(beyond_limb(280.0, 40.0).tolist()), back_phi="auto", back_width_mm=9.0,
                      path=[((470, 1062), 9.0), (lim(250.0, 8.0), 10.0), (lim(308.0, 8.0), 10.0)]))
    return out


# =========================================================================== building
def fit_plane(P: np.ndarray) -> Tuple[np.ndarray, float]:
    """Best-fit plane n.p = c through unit vectors P: a small circle on the sphere."""
    P = np.asarray(P, np.float64)
    m = P.mean(axis=0)
    w, v = np.linalg.eigh((P - m).T @ (P - m))
    n = v[:, 0]
    c = float(n @ m)
    if c < 0:
        n, c = -n, -c
    return n, c


def _knots(P, n, e1, e2):
    lam = np.degrees(np.arctan2(P @ e2, P @ e1))
    phi = np.degrees(np.arcsin(np.clip(P @ n, -1, 1)))
    return lam, phi


def _edge_pair_knots(hi, lo, n, e1, e2):
    ea, eb = _knots(hi, n, e1, e2), _knots(lo, n, e1, e2)
    if ea[1].mean() < eb[1].mean():
        ea, eb = eb, ea
    return list(zip(ea[0].tolist(), ea[1].tolist())), list(zip(eb[0].tolist(), eb[1].tolist()))


#: knot priorities: a REFERENCE_SPEC edge point outranks a derived edge (edge + width), which
#: outranks a hidden path point, which outranks the automatic back fill
P_SPEC, P_DERIVED, P_PATH, P_BACK = 3, 2, 1, 0
#: the steepest an edge may turn against its own circle between knots (deg of phi per deg
#: of lam); steeper stretches are where two knot sources disagree, and they fold the chart
MAX_KNOT_SLOPE = 1.25


def _tag(pairs, prio):
    return [(float(a), float(b), prio) for a, b in pairs]


def build_strip(d: Design, built: Optional[Dict[str, SS.Strip]] = None) -> SS.Strip:
    hi = _img(d.hi) if d.hi is not None else None
    lo = _img(d.lo) if d.lo is not None else None
    hi2 = _img(d.hi2) if d.hi2 is not None else None
    lo2 = _img(d.lo2) if d.lo2 is not None else None
    cen = _img(d.centre) if d.centre is not None else None
    ew = [_img(e) for e, _, _ in d.edge_w]
    front = np.concatenate([a for a in (hi, lo, hi2, lo2, cen) if a is not None] + ew, axis=0)
    pathp = np.array([_point(pp) for pp, _ in d.path]).reshape(-1, 3)
    fitpts = np.concatenate([front] + ([pathp] if (d.path_in_fit and len(pathp)) else []), axis=0)
    back_phi = 0.0
    if d.pole_like is not None and built and d.pole_like in built:
        n = built[d.pole_like].n.copy()
    elif d.pole is not None:
        n = SS.normalize(np.asarray(d.pole, np.float64))
    elif d.fit == "plane":
        n, c = fit_plane(fitpts)
        back_phi = math.degrees(math.asin(max(-1.0, min(1.0, c))))
    else:
        n = SS.fit_pole(fitpts)
    zero = SS.normalize(front.mean(axis=0))
    e1 = SS.normalize(zero - np.dot(zero, n) * n)
    e2 = np.cross(n, e1)
    hi_k, lo_k = [], []
    if hi is not None and lo is not None:
        a, b = _edge_pair_knots(hi, lo, n, e1, e2)
        hi_k += _tag(a, P_SPEC)
        lo_k += _tag(b, P_SPEC)
    elif (hi is not None or lo is not None) and cen is not None:
        one = hi if hi is not None else lo
        lam, phi = _knots(one, n, e1, e2)
        cl, cp = _knots(cen, n, e1, e2)
        o = np.argsort(cl)
        side_hi = phi.mean() > np.interp(lam.mean(), cl[o], cp[o])
        w = mm_to_deg(d.centre_width_mm)
        if side_hi:
            hi_k += _tag(zip(lam, phi), P_SPEC)
            lo_k += _tag(zip(lam, phi - w), P_DERIVED)
        else:
            lo_k += _tag(zip(lam, phi), P_SPEC)
            hi_k += _tag(zip(lam, phi + w), P_DERIVED)
        cen = None
    if cen is not None:
        cl, cp = _knots(cen, n, e1, e2)
        hw = mm_to_deg(d.centre_width_mm) * 0.5
        hi_k += _tag(zip(cl, cp + hw), P_DERIVED)
        lo_k += _tag(zip(cl, cp - hw), P_DERIVED)
    for epts, widths, side_pt in d.edge_w:
        E = _img(epts)
        lam, phi = _knots(E, n, e1, e2)
        wv = np.broadcast_to(np.asarray(widths, float), lam.shape)
        sl, sp = _knots(_point(side_pt)[None, :], n, e1, e2)
        o = np.argsort(lam)
        side_up = float(sp[0]) > float(np.interp(sl[0], lam[o], phi[o]))
        wd = np.array([mm_to_deg(w) for w in wv])
        if side_up:
            lo_k += _tag(zip(lam, phi), P_SPEC)
            hi_k += _tag(zip(lam, phi + wd), P_DERIVED)
        else:
            hi_k += _tag(zip(lam, phi), P_SPEC)
            lo_k += _tag(zip(lam, phi - wd), P_DERIVED)
    if hi2 is not None and lo2 is not None:
        a, b = _edge_pair_knots(hi2, lo2, n, e1, e2)
        hi_k += _tag(a, P_SPEC)
        lo_k += _tag(b, P_SPEC)
    for pspec, wmm in d.path:
        el, ep = _knots(_point(pspec)[None, :], n, e1, e2)
        hw = mm_to_deg(wmm) * 0.5
        hi_k.append((float(el[0]), float(ep[0] + hw), P_PATH))
        lo_k.append((float(el[0]), float(ep[0] - hw), P_PATH))
    # the far side: the strip's own circle continued across the largest lam gap
    if d.back_phi == "auto":
        back_phi = float(np.mean([b for _, b, _ in hi_k] + [b for _, b, _ in lo_k]))
    elif d.back_phi is not None:
        back_phi = float(d.back_phi)
    fl = np.array([a for a, _, _ in hi_k + lo_k])
    core_lam = fl.copy()
    hwb = mm_to_deg(d.back_width_mm) * 0.5
    srt = np.sort(((fl + 180.0) % 360.0) - 180.0)
    gaps = np.diff(np.concatenate([srt, [srt[0] + 360.0]]))
    g = int(np.argmax(gaps))
    a, b = srt[g], srt[g] + gaps[g]
    if d.back_fill and gaps[g] > 50.0:
        margin = min(30.0, 0.25 * gaps[g])
        for t in np.linspace(a + margin, b - margin, 5):
            hi_k.append((float(t), back_phi + hwb, P_BACK))
            lo_k.append((float(t), back_phi - hwb, P_BACK))
    hi_k, dh = _clean_knots(_dedupe(hi_k))
    lo_k, dl = _clean_knots(_dedupe(lo_k))
    rl0 = _rank_list(d)
    rank_k = [(0.0, d.rank if rl0 is None else rl0[0][0])]
    lift_k = []
    for p, v in d.lift:
        l, _ = _knots(_point(p)[None, :], n, e1, e2)
        lift_k.append((float(l[0]), float(v)))
    if not lift_k:
        lift_k = [(0.0, 0.0)]
    st = SS.Strip(d.name, n, zero, hi_k, lo_k, rank_k, family=d.family, lift=lift_k, note=d.note)
    st.core_lam = core_lam
    st.knots_dropped = dh + dl
    return st


def _dedupe(k, min_gap=0.4):
    """Sort by lam; knots closer than ``min_gap`` merge (the higher priority wins; equal
    priorities average)."""
    k = sorted(((((a + 180.0) % 360.0) - 180.0), b, p) for a, b, p in k)
    out = []
    for a, b, p in k:
        if out and abs(a - out[-1][0]) < min_gap:
            a0, b0, p0 = out[-1]
            if p > p0:
                out[-1] = (a, b, p)
            elif p == p0:
                out[-1] = (0.5 * (a + a0), 0.5 * (b + b0), p)
        else:
            out.append((a, b, p))
    return out


def _clean_knots(k, max_slope: float = MAX_KNOT_SLOPE):
    """Drop the lower-priority end of any stretch steeper than ``max_slope`` until none is
    left (a stretch between two knots of the same, highest priority is the reference's own
    shape and stays).  Returns ((lam, phi) knots, dropped list)."""
    k = list(k)
    dropped = []
    while len(k) > 3:
        lam = np.array([a for a, _, _ in k])
        ph = np.array([b for _, b, _ in k])
        pr = np.array([p for _, _, p in k])
        dl = np.diff(np.concatenate([lam, [lam[0] + 360.0]]))
        dp = np.diff(np.concatenate([ph, [ph[0]]]))
        sl = np.abs(dp) / np.maximum(dl, 1e-6)
        order = np.argsort(-sl)
        done = True
        for i in order:
            if sl[i] <= max_slope:
                break
            j = (i + 1) % len(k)
            if pr[i] == pr[j] == P_SPEC:
                continue
            drop = i if pr[i] < pr[j] else j if pr[j] < pr[i] else (j if pr[j] < P_SPEC else i)
            dropped.append((round(float(lam[drop]), 2), round(float(ph[drop]), 2), int(pr[drop])))
            del k[drop]
            done = False
            break
        if done:
            break
    return [(a, b) for a, b, _ in k], dropped


# =========================================================================== woven switches
SWITCH_STEP_DEG = 0.5
SWITCH_PAD_MM = 1.5


def _cross_section(st: SS.Strip, lam: float, pad_mm: float = 0.3, n: int = 13) -> np.ndarray:
    lo, hi, _ = st.at(np.array([lam]))
    pad = mm_to_deg(pad_mm)
    ph = np.linspace(lo[0] - pad, hi[0] + pad, n)
    lr, pr = math.radians(lam), np.radians(ph)[:, None]
    return np.cos(pr) * (math.cos(lr) * st.e1 + math.sin(lr) * st.e2) + np.sin(pr) * st.n


def _rank_list(d: "Design"):
    if d.ranks:
        return list(d.ranks)
    if d.rank2 is not None:
        ra, pa, rb, pb = d.rank2
        return [(ra, pa), (rb, pb)]
    return None


def resolve_switches(ds: List[Design], strips: List[SS.Strip], log=None, passes: int = 2) -> List[SS.Strip]:
    """Give every multi-rank strip its switches.  The strip holds rank r_i at probe p_i; on
    the arc from one probe to the next (in the strip's own direction) it switches once, in
    the middle of the longest stretch where the switch is INVISIBLE: at every point of the
    cross-section (and SWITCH_PAD_MM either side along the strip) the highest other strip
    there ranks above both ranks (buried either way) or below both (on top either way)."""
    out = list(strips)
    for _pass in range(passes):
        cur = list(out)
        for i, d in enumerate(ds):
            rl = _rank_list(d)
            if rl is None:
                continue
            st = strips[i]
            lams = [float(st.coords(_point(p)[None, :])[0][0]) for _, p in rl]
            order = np.argsort(lams)
            rl = [rl[k] for k in order]
            lams = [lams[k] for k in order]
            others = [(j, t) for j, t in enumerate(cur) if j != i]
            pad_deg = mm_to_deg(SWITCH_PAD_MM)
            knots = []
            ok_all = True
            for q in range(len(rl)):
                ra, rb = rl[q][0], rl[(q + 1) % len(rl)][0]
                start, end = lams[q], lams[(q + 1) % len(rl)]
                lo_r, hi_r = min(ra, rb), max(ra, rb)

                def ok_at(lam):
                    for dl in (-pad_deg, 0.0, pad_deg):
                        P = _cross_section(st, lam + dl, pad_mm=0.4, n=17)
                        top = np.full(len(P), -np.inf)
                        for j, t in others:
                            e = t.evaluate(P, CHART_RADIUS_MM)
                            top = np.where(e["d"] > -0.3, np.maximum(top, e["rank"]), top)
                        if ((top > lo_r) & (top < hi_r)).any():
                            return False
                    return True
                span = (end - start) % 360.0
                if span < 1e-6:
                    span = 360.0
                ls = start + np.arange(SWITCH_STEP_DEG, span, SWITCH_STEP_DEG)
                good = np.array([ok_at(float(l)) for l in ls]) if abs(ra - rb) > 1e-9 else np.ones(len(ls), bool)
                if not good.any():
                    ok_all = False
                    if log and _pass == passes - 1:
                        log(f"  switch {d.name}: NO invisible place between ranks {ra} and {rb}")
                    sw = start + 0.5 * span
                else:
                    best, c0 = (0, 0), None
                    for qq, gq in enumerate(good.tolist() + [False]):
                        if gq and c0 is None:
                            c0 = qq
                        if not gq and c0 is not None:
                            if qq - c0 > best[1] - best[0]:
                                best = (c0, qq)
                            c0 = None
                    sw = float(ls[(best[0] + best[1] - 1) // 2])
                knots.append((((sw + 180.0) % 360.0) - 180.0, rb))
            ns = SS.Strip(st.name, st.n, st.zero, st.hi, st.lo, knots, family=st.family, lift=st.lift,
                          note=st.note)
            ns.core_lam = getattr(st, "core_lam", None)
            ns.switch_ok = ok_all
            out[i] = ns
            if log and _pass == passes - 1:
                log(f"  switch {d.name}: " + ", ".join(f"lam {k:7.1f} -> {r}" for k, r in knots)
                    + ("" if ok_all else "  (NOT all invisible)"))
    return out


# =========================================================================== fillers
#: the deepest layer: great-circle loops at the lowest rank, chosen to cover whatever the
#: designed strips leave bare (on the far side).  DESIGNED, deterministic.
FILL_WIDTH_MM = 11.0
FILL_RANK = 0.30
FILL_MAX = 14
FILL_SAMPLES = 24000
FILL_CANDIDATES = 3000
FILL_CLEAR_MM = 0.8


def fibonacci_sphere(n: int) -> np.ndarray:
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    th = math.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], axis=1)


def _bare(strips: List[SS.Strip], P: np.ndarray) -> np.ndarray:
    ok = np.zeros(len(P), bool)
    for st in strips:
        ok |= st.evaluate(P, CHART_RADIUS_MM)["d"] >= FILL_CLEAR_MM
    return ~ok


def fillers(strips: List[SS.Strip], log=None) -> List[SS.Strip]:
    P = fibonacci_sphere(FILL_SAMPLES)
    bare = _bare(strips, P)
    cand = fibonacci_sphere(FILL_CANDIDATES * 2)
    cand = cand[cand[:, 2] >= 0.0]
    hw = math.sin(math.radians(mm_to_deg(FILL_WIDTH_MM) * 0.5 - 0.6))
    out: List[SS.Strip] = []
    for i in range(FILL_MAX):
        if not bare.any():
            break
        Q = P[bare]
        score = (np.abs(Q @ cand.T) < hw).sum(axis=0)
        j = int(np.argmax(score))
        n = cand[j]
        zero = SS.normalize(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
        half = mm_to_deg(FILL_WIDTH_MM) * 0.5
        st = SS.Strip(f"F{i}", n, zero, [(0.0, half)], [(0.0, -half)], [(0.0, FILL_RANK - 0.01 * i)],
                      family="fill", note="deepest layer: covers what the designed strips leave bare")
        out.append(st)
        bare &= st.evaluate(P, CHART_RADIUS_MM)["d"] < FILL_CLEAR_MM
        if log:
            log(f"  filler F{i}: covers {int(score[j])} bare samples, {int(bare.sum())} left")
    return out


def build_strips(ds: Optional[List[Design]] = None, fill: bool = True, log=None, **_ignored) -> List[SS.Strip]:
    ds = ds or designs()
    built: Dict[str, SS.Strip] = {}
    strips = []
    for d in ds:
        st = build_strip(d, built)
        built[d.name] = st
        strips.append(st)
    strips = resolve_switches(ds, strips, log=log)
    if fill:
        strips = strips + fillers(strips, log=log)
    return strips


__all__ = ["CHART_RADIUS_MM", "WHORL_TOP_PX", "WHORL_BOTTOM_CAM", "Design", "designs",
           "build_strip", "build_strips", "mm_to_deg", "resolve_switches", "fillers"]
