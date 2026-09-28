#!/usr/bin/env python
"""props_lib.smokebomb_layout3 - WHERE every tape strip of SM_SmokeBomb runs (round 3).

numpy only.  The FRONT is round 2's (props_lib.smokebomb_layout.designs(), unchanged): the
REFERENCE_SPEC edge control points, widths, order and the hidden routes on the visible side
that keep each strip under the right neighbours.  What changed is the FAR SIDE.

Round 2 closed every loop round the back through hand-placed waypoints (``back_path`` - the
mirror image of the front - plus limb points and a 5-knot fill of the largest gap), each at
its own width, and splined the edges through all of them with a slope limiter dropping the
knots that disagreed.  The adversary's views from below and above showed the result: bands
that meander and pinch, and crumpled, pointed tape ends round the bottom pole.

Round 3 keeps every knot on the visible side and just behind the limb (camera z above
``BACK_Z``: where the strip leaves the silhouette) and drops every far-side waypoint.  Across
the far side each edge fades, with a cosine taper over the unseen gap, from where it leaves
the limb to its own BASE circle - the strip's frame circle at its back width - and back to
where it re-enters on the other limb.  So behind the ball every strip is a smooth band of
nearly constant width: the wound ball the front implies, with no ends, no pinches and no
meanders.  Ranks, woven switches and the deepest filler layer are round 2's.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import smokebomb_strips as SS
from . import smokebomb_layout as L1
from .smokebomb_layout import (Design, _img, _point, _knots, _edge_pair_knots, _tag, _dedupe,
                               _clean_knots, _rank_list, fit_plane, mm_to_deg, P_SPEC, P_DERIVED,
                               P_PATH, P_BACK)

#: knots at or in front of this camera z are kept (0 = the limb; -0.26 = 15 deg behind it)
BACK_Z = -0.26
#: shortest far-side taper (deg of lam); a shorter gap is splined straight across
MIN_GAP_DEG = 40.0
GRID_DEG = 0.5
#: W's edge-on ridge height, as a share of round 2's one layer
W_LIFT_SCALE = 0.5
#: per-strip design overrides (dataclasses.replace keyword sets), applied in designs()
OVERRIDES: Dict[str, dict] = {}


def _pchip(x, y, xs):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if len(x) == 1:
        return np.full_like(xs, y[0])
    m = SS._pchip_slopes(x, y)
    i = np.clip(np.searchsorted(x, xs, side="right") - 1, 0, len(x) - 2)
    h = x[i + 1] - x[i]
    t = (xs - x[i]) / h
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * y[i] + (t3 - 2 * t2 + t) * h * m[i]
            + (-2 * t3 + 3 * t2) * y[i + 1] + (t3 - t2) * h * m[i + 1])


def edge_table(knots, base: float, grid: np.ndarray, gap_mid: Optional[float] = None):
    """A periodic edge through ``knots`` [(lam, phi)] that fades to ``base`` across the
    largest gap between them (the far side), smoothly (cosine), and is a monotone spline
    between them.  Returns phi on ``grid`` (deg, -180..180)."""
    k = sorted(((((a + 180.0) % 360.0) - 180.0), b) for a, b in knots)
    lam = np.array([a for a, _ in k])
    phi = np.array([b for _, b in k])
    gaps = np.diff(np.concatenate([lam, [lam[0] + 360.0]]))
    g = int(np.argmax(gaps))
    start = lam[(g + 1) % len(lam)]              # the knot run starts after the gap
    lu = (lam - start) % 360.0                    # unwrapped: 0 .. span
    o = np.argsort(lu)
    lu, pu = lu[o], phi[o]
    span = lu[-1]
    gl = (grid - start) % 360.0
    out = np.empty_like(grid)
    ins = gl <= span
    out[ins] = _pchip(lu, pu, gl[ins])
    gap = 360.0 - span
    if gap < MIN_GAP_DEG:
        # a short gap: a straight cubic join (no base)
        xx = np.concatenate([lu[-2:], lu[:2] + 360.0])
        yy = np.concatenate([pu[-2:], pu[:2]])
        out[~ins] = _pchip(xx, yy, gl[~ins])
        return out
    t = (gl[~ins] - span) / gap                   # 0 at the last knot, 1 at the first again
    a, b = pu[-1], pu[0]
    # leave the last knot along the edge's own direction for a few degrees, then ease to base
    w = 0.5 * (1.0 - np.cos(np.pi * np.clip(t * 3.0, 0.0, 1.0)))       # 0 -> 1 over the first third
    w2 = 0.5 * (1.0 - np.cos(np.pi * np.clip((1.0 - t) * 3.0, 0.0, 1.0)))
    out[~ins] = np.where(t < 0.5, a + (base - a) * w, b + (base - b) * w2)
    return out


def build_strip(d: Design, built: Optional[Dict[str, SS.Strip]] = None) -> SS.Strip:
    """Round 2's build_strip (smokebomb_layout.build_strip) with the far side replaced."""
    hi = _img(d.hi) if d.hi is not None else None
    lo = _img(d.lo) if d.lo is not None else None
    hi2 = _img(d.hi2) if d.hi2 is not None else None
    lo2 = _img(d.lo2) if d.lo2 is not None else None
    cen = _img(d.centre) if d.centre is not None else None
    ew = [_img(e) for e, _, _ in d.edge_w]
    front = np.concatenate([a for a in (hi, lo, hi2, lo2, cen) if a is not None] + ew, axis=0)
    path_all = [(_point(pp), w) for pp, w in d.path]
    path_keep = [(p, w) for p, w in path_all if p[2] >= BACK_Z]
    pathp = np.array([p for p, _ in path_keep]).reshape(-1, 3)
    fitpts = np.concatenate([front] + ([pathp] if (d.path_in_fit and len(pathp)) else []), axis=0)
    back_phi = None
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
    for p, wmm in path_keep:
        el, ep = _knots(p[None, :], n, e1, e2)
        hw = mm_to_deg(wmm) * 0.5
        hi_k.append((float(el[0]), float(ep[0] + hw), P_PATH))
        lo_k.append((float(el[0]), float(ep[0] - hw), P_PATH))
    hi_c, dh = _clean_knots(_dedupe(hi_k))
    lo_c, dl = _clean_knots(_dedupe(lo_k))
    # the base circle: the frame's own (small) circle for a plane fit, else the mean of the
    # kept knots' centre line
    if back_phi is None or d.back_phi == "auto":
        back_phi = float(np.mean([b for _, b in hi_c] + [b for _, b in lo_c]))
    elif d.back_phi is not None:
        back_phi = float(d.back_phi)
    hwb = mm_to_deg(d.back_width_mm) * 0.5
    grid = np.arange(-180.0, 180.0, GRID_DEG)
    th = edge_table(hi_c, back_phi + hwb, grid)
    tl = edge_table(lo_c, back_phi - hwb, grid)
    rl0 = _rank_list(d)
    rank_k = [(0.0, d.rank if rl0 is None else rl0[0][0])]
    lift_k = []
    for p, v in d.lift:
        l, _ = _knots(_point(p)[None, :], n, e1, e2)
        lift_k.append((float(l[0]), float(v)))
    if not lift_k:
        lift_k = [(0.0, 0.0)]
    st = SS.Strip(d.name, n, zero, list(zip(grid.tolist(), th.tolist())), list(zip(grid.tolist(), tl.tolist())),
                  rank_k, family=d.family, lift=lift_k, note=d.note)
    st.knots_dropped = dh + dl
    st.base = {"phi_deg": round(back_phi, 3), "half_width_deg": round(hwb, 3),
               "front_knots": [len(hi_c), len(lo_c)],
               "far_side_waypoints_dropped": len(path_all) - len(path_keep)}
    return st


def designs() -> List[Design]:
    """Round 2's designs, with ONE change at the bottom outline.

    Round 2 took REFERENCE_SPEC's D19 and D27 as ONE edge of one ring (Rb) round a pole
    40 deg behind the bottom limb.  In that ring's own frame the two run as a saw-tooth
    (phi 19 -> 37 deg along D19, then back to 27 -> 45 along D27): they are the edges of
    TWO bands meeting in a V near the bottom limb (image angle ~275 deg, where
    REFERENCE_SPEC 4 puts the bottom family's convergence).  Seen from below, the single
    ring zig-zagged through that saw-tooth - the adversary's "crumpled, pointed tape ends"
    at the bottom pole.  Round 3 makes them two bands, Rb1 (D19 its own upper edge) and Rb2
    (D27 its own upper edge), each on its own great circle, at round 2's rank for Rb."""
    import dataclasses
    out = []
    for d in L1.designs():
        if d.name == "Rb":
            # their great circles climb the front-left limb, where the reference shows L3 / L4
            # / R_in: there they pass under those (woven, switched where invisible)
            out.append(Design("Rb1", "bottom", edge_w=[(L1.D19, 11.0, (600, 1085))], rank=4.45,
                              rank2=(4.45, (600, 1070), 3.5, (238, 550)),
                              back_width_mm=10.0, note="D19 is its own upper edge"))
            out.append(Design("Rb2", "bottom", edge_w=[(L1.D27, 11.0, (790, 1060))], rank=4.43,
                              rank2=(4.43, (790, 1050), 3.45, (289, 665)),
                              back_width_mm=10.0, note="D27 is its own upper edge"))
            continue
        if d.name == "R2":
            # R2's lower edge LC runs nearly ALONG the outline where it meets it (188, 529);
            # round 2's waypoints just behind the limb (96 deg and 158 deg) bent it across the
            # outline there, which rendered as a square-cut flap.  Its own edges and the two
            # visible points by the whorl are all it needs.
            d = dataclasses.replace(d, path=[p for p in d.path if not (isinstance(p[0], tuple) and p[0][0] == "limb")])
        if d.name == "W":
            # W's twisted, edge-on end stands proud of the tape it lies on (REFERENCE_SPEC 4.2
            # WTW, ~9 px wide; its height is not measurable).  Round 3 raises it half a layer
            # (round 2: a full layer): with round 3's thicker tape (0.65 mm) a full layer made
            # a 1.3 mm ridge that LOD1 (3.5 mm vertex spacing) could not follow within its
            # 1.5 mm deviation budget
            d = dataclasses.replace(d, lift=[(p, v * W_LIFT_SCALE) for p, v in d.lift])
        if d.name in OVERRIDES:
            d = dataclasses.replace(d, **OVERRIDES[d.name])
        out.append(d)
    return out


def build_strips(ds: Optional[List[Design]] = None, fill: bool = True, log=None, **_ignored) -> List[SS.Strip]:
    ds = ds or designs()
    built: Dict[str, SS.Strip] = {}
    strips = []
    for d in ds:
        st = build_strip(d, built)
        built[d.name] = st
        strips.append(st)
    bases = {st.name: getattr(st, "base", None) for st in strips}
    strips = L1.resolve_switches(ds, strips, log=log)
    for st in strips:
        st.base = bases.get(st.name)
    if fill:
        strips = strips + L1.fillers(strips, log=log)
    return strips


__all__ = ["BACK_Z", "edge_table", "build_strip", "build_strips", "designs"]
