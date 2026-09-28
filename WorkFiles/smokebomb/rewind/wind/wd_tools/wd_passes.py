"""wd_passes - the table of visible passes: which REFERENCE_SPEC edges each pass owns,
which it hides under, its travel direction, and the probes that say where it must SHOW.

Sides: +1 = left of travel, -1 = right of travel, 0 = centre line.  Rule of thumb in the
image: heading right -> left is UP; heading down -> left is RIGHT; heading left -> left is
DOWN; heading up -> left is LEFT.
"""
from __future__ import annotations

import numpy as np

from wd_fitlib import (CX, CY, RPX, EdgeTerm, PassFit, edge_px, inside_disc, probes_between,
                       resample_poly, to_limb_px)
FL_resample = resample_poly


def shift_toward(P: np.ndarray, ref, d: float) -> np.ndarray:
    """polyline P shifted by d px along its local normal, toward the side ref lies on."""
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    s = np.sign(np.sum((np.asarray(ref, float) - P) * N, axis=1))
    s[s == 0] = 1
    return P + N * (s * d)[:, None]


def radial(P: np.ndarray, r_frac: float) -> np.ndarray:
    return to_limb_px(P, r_frac)


def midline(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = []
    for p in a:
        j = int(np.argmin(np.linalg.norm(b - p, axis=1)))
        out.append(0.5 * (p + b[j]))
    return np.array(out)


#: REFERENCE_SPEC 4.5: the whorl V-gap, apex (690,252), ~90 px long up-left, ~20 px open
VGAP = np.array([(686, 248), (678, 240), (670, 232), (662, 224), (654, 216), (646, 208), (638, 200), (632, 194),
                 (676, 244), (668, 236), (660, 226), (650, 214), (642, 204), (682, 238), (672, 226), (662, 214),
                 (652, 202), (644, 194)], float)
#: DESIGNED: past the apex the R family runs on under the U fan and leaves over the top-right
#: limb (image angle ~70 deg), hidden all the way
R_ROUTE = np.array([(700, 248), (722, 236), (744, 222), (764, 208), (780, 197), (792, 189)], float)


def past_limb(route_px, degs=(4.0, 9.0, 14.0, 19.0)):
    """camera-frame points continuing a route straight on (a geodesic) past its last point,
    over the limb and onto the far side."""
    from wd_fitlib import px2cam
    import props_lib.smokebomb_wind as W
    P = px2cam(np.asarray(route_px, float)[-2:])
    p1 = W.normalize(P[1])
    t = P[1] - P[0]
    t = W.normalize(t - np.dot(t, p1) * p1)
    return np.array([np.cos(np.radians(d)) * p1 + np.sin(np.radians(d)) * t for d in degs])


def pass_table():
    E = edge_px
    wup, wlo, wtw = E("WUP"), E("WLO"), E("WTW")
    bup, blo = E("BUP"), E("BLO")
    wmid = midline(E("WUP", xr=(610, 1050)), wlo)
    bmid = midline(E("BUP", xr=(700, 1075)), blo)
    lin = E("LIN")
    lin_up = lin[lin[:, 1] <= 440]
    lin_lo = lin[lin[:, 1] >= 480]
    lc, la = E("LC"), E("LA")
    alo = E("ALO")
    T = []
    # ------------------------------------------------------------------ bottom families
    e_region = probes_between(E("ALO", xr=(720, 1000)), E("D27"), fr=(0.2, 0.5, 0.8))
    rimL_region = probes_between(E("D19", xr=(545, 700)), to_limb_px(E("D19", xr=(545, 700)), 0.99), fr=(0.1, 0.3, 0.5, 0.7, 0.9))
    dc_region = shift_toward(E("D9", yr=(880, 1030)), (700, 900), 30)
    T.append(PassFit("Dc", ("D_c",), (560, 860), (700, 1040), [
        EdgeTerm(shift_toward(E("D9"), (560, 990), 12), -1, 0.6, "hide", "D9 under Db"),
        EdgeTerm(e_region, +1, 1.0, "keepout", "E's region"),
        EdgeTerm(shift_toward(E("ALO", xr=(560, 690)), (600, 950), 7), 0, 1.0, "inside", "up to A's lower edge"),
    ], width=0.13, width_w=0.2))
    T.append(PassFit("Db", ("D_b",), (480, 860), (600, 1030), [
        EdgeTerm(E("D9"), +1, 1.0, "own", "D9"),
        EdgeTerm(shift_toward(E("D57"), (380, 960), 12), -1, 0.6, "hide", "D57 under Da"),
    ], width=0.12, width_w=0.1))
    T.append(PassFit("E", ("E",), (690, 960), (1040, 850), [
        EdgeTerm(shift_toward(E("ALO", xr=(690, 1030)), (800, 800), 14), +1, 0.6, "hide", "ALO under A"),
        EdgeTerm(shift_toward(E("D27"), (800, 1100), 12), -1, 0.6, "hide", "D27 under L4"),
        EdgeTerm(dc_region, +1, 1.0, "keepout", "D_c's region"),
        EdgeTerm(shift_toward(E("ALO", xr=(700, 1020)), (850, 1000), 7), 0, 1.0, "inside", "up to A's lower edge"),
    ], width=0.16, width_w=0.3))
    # the L family: limb-hugging passes down the left side and along the bottom outline
    T.append(PassFit("L4", ("L4", "rimR"), (240, 450), (890, 1030), [
        EdgeTerm(shift_toward(E("L3L"), (330, 560), 10), +1, 0.6, "hide", "L3L under L3"),
        EdgeTerm(E("D27"), +1, 1.0, "own", "D27"),
        EdgeTerm(shift_toward(lin_lo, (150, 600), 12), -1, 0.6, "hide", "LIN under L5"),
        EdgeTerm(radial(E("D27"), 1.03), -1, 0.3, "hide", "beyond the limb"),
    ], width=0.17, width_w=0.1, knot_deg=12.0, smooth=1.0))
    T.append(PassFit("L3", ("L3", "rimL"), (268, 440), (690, 1085), [
        EdgeTerm(shift_toward(E("ALO", xr=(270, 345)), (400, 500), 14), +1, 0.6, "hide", "ALO under A"),
        EdgeTerm(E("L3L"), -1, 1.0, "own", "L3L"),
        EdgeTerm(E("D19"), +1, 1.0, "own", "D19"),
        EdgeTerm(radial(E("D19"), 1.03), -1, 0.3, "hide", "beyond the limb"),
    ], width=0.12, width_w=0.1, knot_deg=12.0, smooth=1.0))
    # D_a runs straight on up-left from its visible end and leaves over the left limb under C
    da_route = np.array([(330, 868), (300, 850), (270, 832), (242, 818), (218, 806), (200, 798)], float)
    T.append(PassFit("Da", ("D_a",), (320, 880), (495, 1040), [
        EdgeTerm(E("D57"), +1, 1.0, "own", "D57"),
        EdgeTerm(E("D14"), -1, 1.0, "own", "D14"),
        EdgeTerm(FL_resample(da_route, 6.0), 0, 0.6, "own", "on under C to the left limb"),
        EdgeTerm(rimL_region, +1, 3.0, "keepout", "rim (L3) region"),
    ], width=0.237, width_w=0.05))
    # ------------------------------------------------------------------ upper family (fan)
    T.append(PassFit("U5", ("U5",), (930, 420), (880, 240), [
        EdgeTerm(shift_toward(E("UF"), (870, 330), 10), +1, 0.6, "hide", "UF under U4"),
        EdgeTerm(radial(E("UF"), 1.04), -1, 0.3, "hide", "beyond the limb"),
    ], width=0.10, width_w=0.2))
    T.append(PassFit("U4", ("U4",), (880, 420), (850, 230), [
        EdgeTerm(shift_toward(E("UE"), (820, 330), 10), +1, 0.6, "hide", "UE under U3"),
        EdgeTerm(E("UF"), -1, 1.0, "own", "UF"),
    ], width=0.11, width_w=0.1))
    T.append(PassFit("U3", ("U3",), (800, 440), (800, 240), [
        EdgeTerm(shift_toward(E("UD"), (720, 360), 10), +1, 0.6, "hide", "UD under U2"),
        EdgeTerm(E("UE"), -1, 2.0, "own", "UE"),
    ], width=0.15, width_w=0.05, width_d1=0.05))
    T.append(PassFit("U2", ("U2",), (690, 450), (755, 270), [
        EdgeTerm(shift_toward(E("UC"), (620, 400), 10), +1, 0.6, "hide", "UC under U1"),
        EdgeTerm(E("UD"), -1, 1.0, "own", "UD"),
    ], width=0.10, width_w=0.1))
    rope = np.array([(704, 272), (697, 250), (688, 226), (676, 202), (662, 178), (648, 158), (640, 146)], float)
    T.append(PassFit("U1", ("U1",), (560, 480), (645, 150), [
        EdgeTerm(E("UA"), +1, 1.0, "own", "UA"),
        EdgeTerm(E("UC"), -1, 1.0, "own", "UC"),
        EdgeTerm(FL_resample(rope, 5.0), 0, 1.2, "own", "whorl rope (gathered)"),
    ], width=0.07, width_w=0.1, knot_deg=6.0, smooth=0.3, max_strain=0.06,
        gather_px=[((496, 486), 0.0), ((640, 380), 0.0), ((700, 290), 0.25), ((706, 270), 0.85), ((640, 146), 0.9)]))
    # U0: its right edge leaves the V-gap open (0 px at W, 30 px at (585,390)), closes at the apex
    ua = E("UA")
    gap = np.interp(ua[:, 1], [262, 330, 390, 486], [4, 22, 30, 0])
    u0r = shift_toward(ua, (450, 300), 1.0)
    u0r = ua + (u0r - ua) * gap[:, None]
    r2_region = probes_between(E("LC"), E("LA"), fr=(0.3, 0.5, 0.7))
    # U0 runs straight on: down-left under W, A and C to the lower-left limb, and past the apex
    # on under the U fan to the top-right limb (with the R family)
    u0_route = np.vstack([[(360, 610), (300, 680), (250, 745), (215, 790)], R_ROUTE + [0, 14]])
    T.append(PassFit("U0", ("U0",), (470, 470), (660, 270), [
        EdgeTerm(shift_toward(lin_up[(lin_up[:, 0] > 370)], (450, 250), 8), +1, 1.5, "hide", "LIN under R_in"),
        EdgeTerm(u0r, -1, 1.0, "own", "UA - V-gap"),
        EdgeTerm(shift_toward(E("WTW", xr=(390, 540)), (480, 400), 3), +1, 1.0, "hide", "its foot under W's cord"),
        EdgeTerm(shift_toward(E("WTW", xr=(440, 495)), (480, 400), 9), 0, 2.0, "inside", "just above W's cord"),
        EdgeTerm(FL_resample(u0_route, 6.0), 0, 0.2, "own", "straight on, hidden, both ways"),
        EdgeTerm(r2_region, +1, 1.0, "keepout", "R2's region"),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.17, width_w=0.08, knot_deg=8.0, smooth=0.6, width_d1=0.1))
    # ------------------------------------------------------------------ the belt
    T.append(PassFit("X", ("X",), (420, 600), (1085, 610), [
        EdgeTerm(bmid, +1, 0.8, "hide", "under B"),
        EdgeTerm(wmid, -1, 0.8, "hide", "under W"),
    ], width=0.20, width_w=0.05))
    T.append(PassFit("C", ("C",), (180, 850), (700, 700), [
        EdgeTerm(E("CUP"), +1, 1.0, "own", "CUP"),
        EdgeTerm(E("CLO"), -1, 1.0, "own", "CLO"),
    ], width=0.227, width_w=0.1, max_strain=0.04))
    T.append(PassFit("B", ("B",), (500, 600), (1080, 470), [
        EdgeTerm(bup, +1, 1.0, "own", "BUP"),
        EdgeTerm(blo, -1, 1.0, "own", "BLO"),
    ], width=0.173, width_w=0.1, max_strain=0.04))
    T.append(PassFit("A", ("A",), (300, 380), (1030, 861), [
        EdgeTerm(alo, -1, 1.0, "own", "ALO"),
        EdgeTerm(E("ALO", yr=(450, 520)), -1, 3.0, "own", "ALO's end at R_in's crevice"),
        EdgeTerm(shift_toward(E("WTW", xr=(360, 545)), (500, 600), 2), +1, 1.0, "hide", "under W's cord"),
        EdgeTerm(shift_toward(E("WTW", xr=(380, 545)), (450, 300), 7), +1, 1.0, "keepout", "not past W's cord (U0 is there)"),
        EdgeTerm(probes_between(E("WTW", xr=(430, 530)), E("LIN", xr=(400, 520)), fr=(0.35, 0.6, 0.85), max_d=120),
                 +1, 1.5, "keepout", "U0's foot above the cord"),
        EdgeTerm(wmid, +1, 0.5, "hide", "under W"),
        EdgeTerm(shift_toward(E("WUP", xr=(620, 1040)), (800, 400), 8), +1, 1.0, "keepout", "not past W (X is there)"),
    ], width=0.26, width_w=0.03, max_strain=0.12))
    T.append(PassFit("W", ("W",), (363, 390), (1048, 775), [
        EdgeTerm(wup, +1, 1.0, "own", "WUP"),
        EdgeTerm(wlo, -1, 1.0, "own", "WLO"),
        EdgeTerm(E("WTW", xr=(360, 530)), 0, 1.0, "own", "WTW (gathered)"),
        EdgeTerm(E("WTW", xr=(535, 612)), +1, 2.0, "own", "WTW (opening: its upper edge still on the cord)"),
    ], width=0.0855, width_w=0.05,
        gather_px=[((330, 365), 1.0), ((363, 390), 1.0), ((525, 514), 1.0), ((600, 556), 0.55),
                   ((700, 600), 0.0), ((1048, 775), 0.0)]))
    # ------------------------------------------------------------------ the rim family
    # the R family: all three run into the whorl apex and on (woven under the U fan) to the
    # top-right limb; travel toward the whorl, so +1 (left of travel) is the outer side
    rin_route = np.vstack([[(600, 296), (630, 282), (660, 268), (686, 256)], R_ROUTE + [0, 8]])
    T.append(PassFit("Rin", ("R_in", "L5"), (258, 712), (600, 300), [
        EdgeTerm(lin, -1, 2.0, "own", "LIN"),
        EdgeTerm(shift_toward(lc[lc[:, 0] < 470], (300, 300), 16), +1, 0.5, "hide", "under R2"),
        EdgeTerm(radial(lin_lo[lin_lo[:, 1] < 640], 1.0), +1, 0.3, "hide", "L5 outer edge at the limb"),
        EdgeTerm(FL_resample(np.array([(236, 745), (234, 790), (236, 835), (240, 880), (244, 915)], float), 6.0), 0, 0.5,
                 "own", "L5's lower end: straight down under C to the left limb"),
        EdgeTerm(FL_resample(rin_route, 6.0), 0, 0.5, "own", "on under R2, into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(rin_route)),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.09, width_w=0.15, knot_deg=6.0, smooth=0.3, max_strain=0.06))
    r3_route = np.vstack([[(640, 236), (668, 244)], R_ROUTE + [0, -6]])
    T.append(PassFit("R3", ("R3",), (240, 350), (640, 230), [
        EdgeTerm(shift_toward(la, (400, 300), 10), -1, 0.6, "hide", "LA under R2"),
        EdgeTerm(radial(la, 1.0), +1, 0.3, "hide", "beyond the limb"),
        EdgeTerm(FL_resample(r3_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(r3_route)),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.10, width_w=0.15))
    r2_route = np.vstack([[(640, 262), (672, 256)], R_ROUTE])
    T.append(PassFit("R2", ("R2",), (200, 520), (600, 250), [
        EdgeTerm(lc, -1, 1.0, "own", "LC"),
        EdgeTerm(la, +1, 1.0, "own", "LA"),
        EdgeTerm(FL_resample(r2_route, 6.0), 0, 0.4, "own", "into the apex and under the fan"),
        EdgeTerm(np.zeros((4, 2)), 0, 1.0, "own", "over the top-right limb", cam=past_limb(r2_route)),
        EdgeTerm(VGAP, +1, 1.0, "keepout", "the whorl V-gap"),
    ], width=0.17, width_w=0.05))
    # every band must cover its own visible region
    bp = band_probes()
    for pf in T:
        pts = [bp[b] for b in pf.shows if b in bp]
        if pts:
            pf.terms.append(EdgeTerm(np.vstack(pts), 0, 2.0 if pf.name == "U0" else 0.8, "inside",
                                     "covers its own visible region"))
    return T


def band_probes():
    """band -> probe points (image px) where that band must be the top layer
    (REFERENCE_SPEC 4.2 regions, from the traced edges only)."""
    E = edge_px
    lin = E("LIN")
    P = {}
    P["W"] = np.vstack([probes_between(E("WUP", xr=(700, 1040)), E("WLO"), fr=(0.5,)), E("WTW", xr=(380, 520))[::2]])
    P["A"] = np.vstack([probes_between(E("WLO", xr=(560, 1030)), E("ALO"), fr=(0.2, 0.5, 0.8)),
                        probes_between(E("WTW", xr=(380, 540)), E("ALO", xr=(282, 600)), fr=(0.3, 0.6))])
    P["B"] = probes_between(E("BUP", xr=(700, 1060)), E("BLO"), fr=(0.25, 0.5, 0.75))
    P["X"] = probes_between(E("BLO", xr=(760, 1070)), E("WUP"), fr=(0.4, 0.6))
    P["C"] = probes_between(E("CUP"), E("CLO"), fr=(0.25, 0.5, 0.75))
    P["R2"] = probes_between(E("LC"), E("LA"), fr=(0.3, 0.5, 0.7))
    P["R_in"] = np.vstack([probes_between(E("LIN", xr=(330, 470)), E("LC"), fr=(0.5,)),
                           probes_between(E("LIN", yr=(520, 700)), to_limb_px(E("LIN", yr=(520, 700)), 0.985), fr=(0.5,))])
    P["R3"] = probes_between(E("LA", xr=(290, 560)), to_limb_px(E("LA", xr=(290, 560)), 0.99), fr=(0.5,))
    P["L3"] = probes_between(E("L3L", yr=(470, 690)), E("ALO", xr=(282, 345)), fr=(0.35, 0.65), max_d=90)
    P["L4"] = probes_between(E("L3L", yr=(480, 690)), E("LIN", yr=(470, 700)), fr=(0.5,), max_d=90)
    P["U0"] = np.vstack([probes_between(E("UA", yr=(330, 470)), E("LIN", xr=(378, 580)), fr=(0.3, 0.5, 0.7)),
                         probes_between(E("WTW", xr=(430, 530)), E("LIN", xr=(400, 520)), fr=(0.35, 0.6, 0.85), max_d=120)])
    P["U1"] = probes_between(E("UA", yr=(290, 480)), E("UC"), fr=(0.5,))
    P["U2"] = probes_between(E("UC", yr=(290, 460)), E("UD"), fr=(0.5,))
    P["U3"] = probes_between(E("UD", yr=(280, 430)), E("UE"), fr=(0.35, 0.65))
    P["U4"] = probes_between(E("UE", yr=(250, 390)), E("UF"), fr=(0.5,))
    P["U5"] = probes_between(E("UF"), to_limb_px(E("UF"), 0.99), fr=(0.5,))
    P["D_a"] = probes_between(E("D14", yr=(930, 1060)), E("D57"), fr=(0.3, 0.5, 0.7))
    P["D_b"] = probes_between(E("D57", yr=(870, 990)), E("D9"), fr=(0.5,))
    P["D_c"] = shift_toward(E("D9", yr=(880, 1030)), (700, 900), 30)
    P["E"] = probes_between(E("ALO", xr=(720, 1000)), E("D27"), fr=(0.4, 0.6))
    P["rimL"] = probes_between(E("D19", xr=(560, 700)), to_limb_px(E("D19", xr=(560, 700)), 0.99), fr=(0.5,))
    P["rimR"] = probes_between(E("D27", xr=(700, 860)), to_limb_px(E("D27", xr=(700, 860)), 0.99), fr=(0.5,))
    return {k: inside_disc(v, 0.985) for k, v in P.items() if len(v)}


#: every spec edge: (the band on top along it, the band it lies on).  The band on top owns
#: the edge; the probe test puts one on each side.
EDGE_OWNERS = {
    "WUP": ("W", "X"), "WLO": ("W", "A"), "WTW": ("W", "A"), "BUP": ("B", "U"), "BLO": ("B", "X"),
    "CUP": ("C", "L"), "CLO": ("C", "D"), "ALO": ("A", "C/L3/D/E"), "LIN": ("R_in", "W/A/U0/L4"),
    "LC": ("R2", "R_in"), "LA": ("R3", "R2"), "L3L": ("L4", "L3"), "UA": ("U0|U1", "gap"),
    "UC": ("U1", "U2"), "UD": ("U2", "U3"), "UE": ("U3", "U4"), "UF": ("U4", "U5"),
    "D14": ("D_a", "?"), "D57": ("D_a", "D_b"), "D9": ("D_b", "D_c"), "D19": ("D_bottom", "?"),
    "D27": ("E", "D_bottom"),
}


#: stretch-level tucks: (pass, image point on the pass, 'after' | 'before' that point, under)
#: 'under' may be '@first:<names>' = the earliest of those passes in the order
TUCKS = [
    # the pinwheel: the R family dives under the U fan at the whorl apex
    ("R2", (672, 256), "after", "@all:U1,U2,U3,U4,U5"),
    ("R3", (668, 244), "after", "@all:U1,U2,U3,U4,U5"),
    ("Rin", (686, 256), "after", "@all:U1,U2,U3,U4,U5"),
    # the woven cycle: R_in's lower end (L5) threaded under C
    ("Rin", (262, 706), "before", "C"),
]


#: order facts the probes are too coarse to see (an edge owned by the band on top):
#: (lower, upper) pairs, enforced by the order solver
PINS = [
    ("R3", "R2"),     # LA is R2's edge
    ("Rin", "R2"),    # LC is R2's edge
    ("U2", "U1"), ("U3", "U2"), ("U4", "U3"), ("U5", "U4"),   # UC UD UE UF
    ("L4", "L3"),     # L3L
    ("Db", "Da"), ("Dc", "Db"),   # D57 D9
    ("E", "L4"),      # D27
    ("X", "W"), ("X", "B"), ("U0", "W"), ("B", "W"), ("A", "W"), ("C", "A"),
    ("W", "Rin"), ("A", "Rin"), ("U0", "Rin"),
    ("U0", "U1"), ("U0", "U2"), ("U0", "U3"), ("U0", "U4"), ("U0", "U5"),
    ("W", "R3"), ("A", "R3"),
]

#: spec edge -> the pass on top along it (scoring)
OWNERS = {"WUP": "W", "WLO": "W", "WTW": "W", "BUP": "B", "BLO": "B", "CUP": "C", "CLO": "C", "ALO": "A",
          "LIN": "Rin", "LC": "R2", "LA": "R2", "L3L": "L3", "UA": "U1", "UC": "U1", "UD": "U2", "UE": "U3",
          "UF": "U4", "D14": "Da", "D57": "Da", "D9": "Db", "D19": "L3", "D27": "L4"}
