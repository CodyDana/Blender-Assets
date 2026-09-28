#!/usr/bin/env python
"""props_lib.fan_geom - SK_Fan's meshes (numpy; no bpy): sticks, pleated leaf, glued flaps, rivet, per LOD.

Every vertex belongs to exactly ONE bone (weight 1.0).  Vertices are authored through ``FanMesh``, a
position-keyed factory (1 nm keys) whose key also carries the vertex's bone, so two parts that touch
(a leaf face and its neighbour along a fold) never share a vertex and never merge by accident.

PARTS (FanSpec numbers; FAN_REPORT.md 2 has the table)

    sticks   26 plates stacked on the rivet.  Inner ribs: rounded butt, straight taper 0.030 L -> the pitch
             arc at the leaf edge, rounded shoulders on an arc 0.4 mm inside the leaf's inner edge, solid
             (no piercing).  Guards: RS 5's visible widths, square tip cut on the leaf arc with softened
             corners, chamfered long edges, rounded butt.  The front guard's inner edge in the leaf zone is
             centred on its axis (round 2: the leaf falls away from it); rib 1 is widened behind the front
             guard near the leaf so no daylight shows between them.  A SPACER on the front guard's bone fills
             the stack's gap under the guard in the bare zone (FanSpec.front_gap_mm: the leaf's first panel
             lies in that gap beyond it).  LOD0 sticks carry the pivot hole the eyelet's barrel passes through.
    leaf     50 rigid faces (between a leaf line and a mid-gap fold, inner arc to the scalloped outer edge),
             each cut into strips from the inner to the outer edge (LEAF_STRIPS) so the outer edge follows a
             sinusoid (bumps at the ribs' mountains, notches at the valleys: fan2's gentle ripple) and the
             normals sweep across the face (a soft rounded ridge over the rib, a sharp valley crease: fan2's
             convex silk faces).  Each face has a FRONT layer and a BACK layer 0.02 mm behind it that tapers
             to the front layer at both fold lines (LEAF_BACK_TAPER_MM), so two faces' layers meet exactly on
             every fold and never cross when the pleat closes.
    flaps    the leaf glued over the rear guard (rigid with the guard).
    prongs   (round 3) every stick but the rear guard carries a thin plate on its own bone that runs on past its rib tip
             into the leaf zone, over the silk's inner margin, to the visible leaf edge (0.437 L, RS 7 +- 0.012 L): the
             prongs shingle like the ribs (and blend onto the next stick, so they shorten as the gap closes), so the leaf's inner edge (and the valley notches under it) sits under one dark band
             and no daylight gets through there (FanSpec.prong_* has the fold argument; fan_seethrough measures it).
    rivet    a hollow eyelet: rolled heads front and back and, at LOD0, the barrel (the pin) through the stack;
             each head's hollow is a blind recess (a dark floor, as fan2's dark eyelet centre), not a hole.

UV0: leaf = the flat development of the leaf (two halves nested); sticks = one island per face side and a
strip per wall; rivet = its lathe; each part its own 0..1 texture.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .fan_spec import D2R, FAN, FanSpec
from . import fan_fold as FF

LEAF_BACK_OFFSET_MM = 0.02
#: the back layer runs from 0 at a fold line to LEAF_BACK_OFFSET_MM this far into the face: two faces' back layers
#: then stay apart for any dihedral above 2 atan(0.02 / 1.0) = 2.3 deg (the closed pleats' least is ~3.4 deg)
LEAF_BACK_TAPER_MM = 1.0
#: front-layer strip lines per LOD, as the fraction t across a face (0 = its leaf line / mountain, 1 = its mid-gap
#: fold / valley); the back layer uses (0, taper, 1 - taper, 1)
LEAF_STRIPS = {0: (0.0, 0.2, 0.4, 0.6, 0.8, 1.0), 1: (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0), 2: (0.0, 0.5, 1.0)}
#: round 3: the faces are FLAT silk facets between crisp folds (the measurer and the craft review: fan2's faces are
#: planar with sharp lines on both sides; round 2's convex normal sweep read as corrugated plastic).  The front normals
#: are the face's own normal everywhere; only the first LEAF_RIDGE_T of the face beside its mountain turns toward the
#: ridge's bisector (a hairline softening where the silk drapes over the rib), so both folds read as crisp lines
LEAF_RIDGE_T = 0.2
WALL_CHUNK_MM = 120.0
SLOTS = {"leaf": 0, "sticks": 1, "rivet": 2}


# =========================================================================== vertex factory
class FanMesh:
    def __init__(self, bone_names: Sequence[str]):
        self.bone_names = list(bone_names)
        self._bix = {n: i for i, n in enumerate(self.bone_names)}
        self._key: Dict[tuple, int] = {}
        self.P: List[Tuple[float, float, float]] = []
        self.B: List[int] = []
        self.T: List[Tuple[int, int, int]] = []          # triangles
        self.TUV: List[np.ndarray] = []                   # (3, 2) per triangle
        self.TN: List[np.ndarray] = []                    # (3, 3) per-corner normals
        self.TS: List[int] = []                           # slot
        self.TP: List[str] = []                           # part tag
        self.TG: List[str] = []                           # group (face / stick id)
        self.TL: List[np.ndarray] = []                    # (3, 2) per-corner local paint coords (mm)
        self.TK: List[str] = []                           # paint kind (leaf / top / bottom / wall / rivet)
        self.TLAY: List[str] = []                         # layer ("front" / "back" / "flap_*" / "")
        self.W: Optional[List[List[Tuple[str, float]]]] = None   # per-vertex weights when not one bone

    def vid(self, p, bone: str, layer: str = "") -> int:
        b = self._bix[bone]
        k = (b, layer, int(round(p[0] * 1e6)), int(round(p[1] * 1e6)), int(round(p[2] * 1e6)))
        i = self._key.get(k)
        if i is None:
            i = len(self.P)
            self._key[k] = i
            self.P.append((k[2] * 1e-6, k[3] * 1e-6, k[4] * 1e-6))
            self.B.append(b)
        return i

    def tri(self, pts, uvs, nrms, bone: str, slot: int, part: str, group: str, layer: str = "",
            check_normal: bool = True, locs=None, kind: str = ""):
        idx = [self.vid(p, bone, layer) for p in pts]
        if len(set(idx)) < 3:
            return
        P = np.array([self.P[i] for i in idx])
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if np.linalg.norm(n) < 1e-9:
            return
        nrms = np.asarray(nrms, np.float64)
        locs = np.zeros((3, 2)) if locs is None else np.asarray(locs, np.float64)
        if check_normal and float(n @ nrms.mean(0)) < 0:
            idx = idx[::-1]
            uvs = list(uvs)[::-1]
            nrms = nrms[::-1]
            locs = locs[::-1]
        self.T.append(tuple(idx))
        self.TUV.append(np.asarray(uvs, np.float64))
        self.TN.append(nrms / np.linalg.norm(nrms, axis=1, keepdims=True))
        self.TS.append(slot)
        self.TP.append(part)
        self.TG.append(group)
        self.TL.append(np.asarray(locs, np.float64))
        self.TK.append(kind)
        self.TLAY.append(layer)

    def triangles(self) -> int:
        return len(self.T)

    def subset(self, keep: Sequence[int]) -> "FanMesh":
        """A compact copy holding only triangles ``keep`` (unused vertices dropped)."""
        out = FanMesh(self.bone_names)
        used = sorted({v for t in keep for v in self.T[t]})
        remap = {v: k for k, v in enumerate(used)}
        out.P = [self.P[v] for v in used]
        out.B = [self.B[v] for v in used]
        if self.W is not None:
            out.W = [self.W[v] for v in used]
        for t in keep:
            out.T.append(tuple(remap[v] for v in self.T[t]))
            for a in ("TUV", "TN", "TS", "TP", "TG", "TL", "TK", "TLAY"):
                getattr(out, a).append(getattr(self, a)[t])
        return out

    def arrays(self):
        return np.asarray(self.P, np.float64), np.asarray(self.T, np.int64), np.asarray(self.B, np.int64)

    def part_triangles(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for p in self.TP:
            out[p] = out.get(p, 0) + 1
        return out


# =========================================================================== 2-D polygon tools
def _signed_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _pt_in_tri(p, a, b, c) -> bool:
    """Strictly inside (a point ON an edge - a collinear cut point on the outline - does not block an ear)."""
    d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
    d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
    d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
    e = 1e-10
    return (d1 > e and d2 > e and d3 > e) or (d1 < -e and d2 < -e and d3 < -e)


def ear_clip(poly: np.ndarray) -> List[Tuple[int, int, int]]:
    """Triangulate a simple CCW polygon (indices into poly)."""
    n = len(poly)
    idx = list(range(n))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 10 * n * n:
        guard += 1
        m = len(idx)
        clipped = False
        best = None
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = poly[i0], poly[i1], poly[i2]
            cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cr <= 1e-6:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if _pt_in_tri(poly[j], a, b, c) and not (np.allclose(poly[j], a) or np.allclose(poly[j], b)
                                                          or np.allclose(poly[j], c)):
                    ok = False
                    break
            if ok:
                # prefer the ear with the best (largest minimum) angle: fewer slivers
                ab, bc, ca = b - a, c - b, a - c
                la, lb, lc = np.linalg.norm(ab), np.linalg.norm(bc), np.linalg.norm(ca)
                q = cr / max(la * la + lb * lb + lc * lc, 1e-12)
                if best is None or q > best[0]:
                    best = (q, k, (i0, i1, i2))
        if best is None:
            raise RuntimeError("ear clipping failed (polygon not simple?)")
        _, k, t = best
        out.append(t)
        idx.pop(k)
        clipped = True
    out.append(tuple(idx))
    return out


def bridge_hole(outer: np.ndarray, hole: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """Merge a CW hole into a CCW outer polygon with a bridge; return (poly, source index list) where
    source >= 0 is an outer index and < 0 is -(hole index + 1)."""
    hi = int(np.argmax(hole[:, 0]))
    hp = hole[hi]
    # nearest outer vertex visible to the right-ish: choose nearest by distance with x >= hp.x
    d = np.linalg.norm(outer - hp, axis=1) + np.where(outer[:, 0] >= hp[0], 0.0, 1e6)
    oi = int(np.argmin(d))
    poly, src = [], []
    for k in range(len(outer) + 1):
        j = (oi + k) % len(outer)
        poly.append(outer[j])
        src.append(j)
        if k == 0:
            pass
    # after returning to oi, go into the hole
    poly = [outer[(oi + k) % len(outer)] for k in range(len(outer))] + [outer[oi]]
    src = [(oi + k) % len(outer) for k in range(len(outer))] + [oi]
    for k in range(len(hole) + 1):
        j = (hi + k) % len(hole)
        poly.append(hole[j])
        src.append(-(j + 1))
    return np.array(poly), src


def triangulate_with_hole(outer: np.ndarray, hole: Optional[np.ndarray]):
    """Triangles over outer (CCW) minus hole (CW), as index pairs (kind, idx) per corner."""
    if hole is None:
        return [[("o", a), ("o", b), ("o", c)] for a, b, c in ear_clip(outer)]
    poly, src = bridge_hole(outer, hole)
    # duplicate points make ear clipping ambiguous: nudge the duplicates apart by 1e-7 along the bridge
    tris = ear_clip(poly + _dup_nudge(poly))
    out = []
    for t in tris:
        out.append([("o", src[i]) if src[i] >= 0 else ("h", -src[i] - 1) for i in t])
    return out


def _dup_nudge(poly):
    nud = np.zeros_like(poly)
    seen = {}
    for i, p in enumerate(poly):
        k = (round(p[0], 9), round(p[1], 9))
        if k in seen:
            j = seen[k]
            prev = poly[i - 1]
            nxt = poly[(i + 1) % len(poly)]
            dirn = (nxt - prev)
            dirn = dirn / max(np.linalg.norm(dirn), 1e-12)
            nud[i] = dirn * 1e-6
        else:
            seen[k] = i
    return nud


def fillet(poly: np.ndarray, corners: Dict[int, Tuple[float, int]]) -> np.ndarray:
    """Round the listed corners (index -> (radius, segments)) of a closed polygon."""
    out = []
    n = len(poly)
    for i in range(n):
        if i not in corners:
            out.append(poly[i])
            continue
        r, seg = corners[i]
        p, a, b = poly[i], poly[i - 1], poly[(i + 1) % n]
        u = (a - p) / np.linalg.norm(a - p)
        v = (b - p) / np.linalg.norm(b - p)
        ang = math.acos(max(-1.0, min(1.0, float(u @ v))))
        t = r / math.tan(0.5 * ang)
        t = min(t, 0.45 * np.linalg.norm(a - p), 0.45 * np.linalg.norm(b - p))
        r_eff = t * math.tan(0.5 * ang)
        pa, pb = p + u * t, p + v * t
        bis = (u + v) / np.linalg.norm(u + v)
        c = p + bis * (r_eff / math.sin(0.5 * ang))
        a0 = math.atan2(pa[1] - c[1], pa[0] - c[0])
        a1 = math.atan2(pb[1] - c[1], pb[0] - c[0])
        cr = u[0] * v[1] - u[1] * v[0]
        # sweep the short way
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(seg + 1):
            th = a0 + da * k / seg
            out.append(c + r_eff * np.array([math.cos(th), math.sin(th)]))
    return np.array(out)


def inset(poly: np.ndarray, d: float) -> np.ndarray:
    """Offset a CCW polygon inward by d (vertex-normal offset with miter)."""
    n = len(poly)
    out = np.zeros_like(poly)
    for i in range(n):
        a, p, b = poly[i - 1], poly[i], poly[(i + 1) % n]
        e0 = (p - a) / np.linalg.norm(p - a)
        e1 = (b - p) / np.linalg.norm(b - p)
        n0 = np.array([-e0[1], e0[0]])
        n1 = np.array([-e1[1], e1[0]])
        m = n0 + n1
        m /= np.linalg.norm(m)
        s = d / max(float(m @ n0), 0.3)
        out[i] = p + m * s
    return out


def circle(r: float, n: int, cw: bool = False) -> np.ndarray:
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c = np.stack([r * np.cos(th), r * np.sin(th)], 1)
    return c[::-1] if cw else c


# =========================================================================== stick outlines
@dataclass
class LodPlan:
    lod: int
    butt_seg: int
    shoulder_seg: int
    top_seg: int
    guard_stations: int
    tip_seg: int
    hole_seg: int            # 0 = no pivot hole (and no barrel)
    guard_chamfer: bool
    rivet_seg: int
    rib_box: bool = False    # LOD2: ribs as a 6-point outline


LOD_PLANS = [LodPlan(0, 6, 1, 3, 12, 3, 8, True, 12),         # shoulder: one cut (a 0.12 mm fillet)
             LodPlan(1, 2, 1, 1, 6, 1, 0, False, 8),
             LodPlan(2, 1, 0, 1, 3, 0, 0, False, 6, rib_box=True)]


def front_guard_edges(spec: FanSpec, x: np.ndarray):
    """(y_outer, y_inner) of the front guard in its own frame (+y = toward the leaf): RS 5's visible width
    centred on its axis.  Round 2: the leaf falls away from the front guard (-Z), so its inner edge no longer
    has to follow a leaf line; leaf line 0 (fan2's leaf corner, 1.15 deg outside the axis) lies under it."""
    W = np.array([spec.guard_width_mm(v) for v in np.atleast_1d(x)])
    return -0.5 * W, 0.5 * W


def rear_guard_edges(spec: FanSpec, x: np.ndarray):
    """(y_inner, y_outer) of the rear guard in its own frame (+y = outward, away from the leaf): the outer
    silhouette is fan2's straight line (FanSpec.rear_guard_outer_mm), the inner edge RS 5's visible width in."""
    (x0, y0), (x1, y1) = spec.rear_guard_outer_mm
    x = np.atleast_1d(np.asarray(x, np.float64))
    line = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    W = np.array([spec.guard_width_mm(v) for v in x])
    # the line was measured over 0.2 - 1.0 L; toward the pivot the guard centres on its axis again (the rivet
    # passes through it), blended in over the last 30 mm
    u = np.clip(x / 30.0, 0.0, 1.0)
    u = u * u * (3 - 2 * u)
    yo = u * line + (1 - u) * 0.5 * W
    yi = yo - W
    # round 2: in the leaf zone the inner edge stops at leaf line 25 (the last face falls toward the guard from that
    # line); hidden from the front under the glued flap.  Blended in just inside the leaf's inner edge
    y_line = x * math.tan(spec.leaf_off_rear_deg * D2R) + spec.hinge_margin_mm
    v = np.clip((x - (spec.r_in - 1.0)) / 0.95, 0.0, 1.0)
    yi = np.where(v > 0, yi + v * (np.maximum(yi, y_line) - yi), yi)
    return yi, yo


def guard_outline(spec: FanSpec, which: str, plan: LodPlan) -> np.ndarray:
    L, butt = spec.L, spec.butt_mm
    n = plan.guard_stations
    xs = np.concatenate([np.linspace(-butt + 3.5, spec.r_in - 1.0, max(2, n // 2)),
                         np.linspace(spec.r_in, L - 3.0, max(2, n - n // 2))])
    if which == "front":
        yo, yi = front_guard_edges(spec, xs)
    else:
        yo, yi = rear_guard_edges(spec, xs)           # (inner = -y, outer = +y)
    # tip on the leaf arc r = L
    ya, yb = yo[-1], yi[-1]
    tip = [np.array([math.sqrt(L * L - ya * ya), ya]), np.array([math.sqrt(L * L - yb * yb), yb])]
    # butt: round end, semicircle through the last station's edges
    y0o, y0i = yo[0], yi[0]
    cy, rr = 0.5 * (y0o + y0i), 0.5 * (y0i - y0o)
    cx = xs[0]
    bseg = max(2, plan.butt_seg + 2)
    butt_pts = [np.array([cx + rr * math.cos(t), cy + rr * math.sin(t)])
                for t in np.linspace(0.5 * math.pi, 1.5 * math.pi, bseg + 1)[1:-1]]
    outer = [np.array([x, y]) for x, y in zip(xs, yo)]
    # (round 1's rear slip tab is gone: the valleys now fall behind the leaf lines, where it lay)
    poly = outer + tip + [np.array([x, y]) for x, y in zip(xs[::-1], yi[::-1])]
    poly = poly + butt_pts
    poly = np.array(poly)
    k_tip0, k_tip1 = len(outer), len(outer) + 1
    if plan.tip_seg > 0:
        poly = fillet(poly, {k_tip0: (spec.guard_tip_round_mm, plan.tip_seg),
                             k_tip1: (spec.guard_tip_round_mm, plan.tip_seg)})
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


def rib_outline(spec: FanSpec, i: int, plan: LodPlan, widen_minus: Optional[callable] = None,
                widen_plus: Optional[callable] = None, slip: bool = False) -> np.ndarray:
    """Inner rib i (1..24) in its own frame; widen_minus / widen_plus (x) -> extra half-width on the -y / +y side
    (rib 1 and rib 24 reach under their guards so no daylight shows between a guard and its neighbour)."""
    butt = spec.butt_mm
    r_end = spec.r_in - spec.rib_end_gap_mm
    hw0 = 0.5 * spec.rib_width_mm(0.0)
    em = widen_minus or (lambda x: 0.0)
    ep = widen_plus or (lambda x: 0.0)
    o = spec.leaf_line_offset_deg(i) * D2R
    a = spec.leaf_pitch_deg * D2R

    def polar(r, t):
        return np.array([r * math.cos(t), r * math.sin(t)])
    if plan.rib_box:
        hw_top = 0.5 * spec.rib_width_mm(r_end)
        yl, yr = -hw_top - em(r_end - 2.0), hw_top + ep(r_end - 2.0)
        return np.array([[-butt + 0.3 * hw0, -hw0], [math.sqrt(r_end ** 2 - yl ** 2), yl],
                         [math.sqrt(r_end ** 2 - yr ** 2), yr], [-butt + 0.3 * hw0, hw0]])
    cx = -butt + hw0
    r_slip = spec.r_in + spec.rib_slip_past_leaf_mm if slip else None
    xs = [cx, 0.0, r_end - 1.0]
    if widen_minus is not None or widen_plus is not None:
        xs = [cx, 0.0] + list(np.linspace(35.0, r_end - 1.0, 5))
    minus = [np.array([x, -(0.5 * spec.rib_width_mm(x) + em(x))]) for x in xs]
    plus = [np.array([x, 0.5 * spec.rib_width_mm(x) + ep(x)]) for x in xs]
    # top: an arc r = r_end between the two sides (the shoulders are filleted below).  With a slip, the -y half
    # runs on under the leaf to r_slip and steps down to r_end 0.3 mm short of the leaf line (the closed pages
    # all lie on the +y side of it, so the slip never meets them)
    yl, yr = minus[-1][1], plus[-1][1]
    pts = list(minus)
    if r_slip is not None:
        # the SLIP: behind the leaf, from 0.3 mm short of this rib's leaf line back to 0.3 mm short of the
        # previous one, out to r_slip.  The closed pages all lie on the +y side of the leaf lines, so it never
        # meets them; open, it hides the daylight under the pleats' raised inner corners.  Below the leaf edge its
        # wide part lies behind the neighbouring rib (stacked in front)
        e1 = 0.3 / r_end
        pts[-1] = np.array([r_end - 0.3, yl])
        y_lo = min(yl, r_end * math.sin(o - a + e1))            # never inside the rib's own (widened) edge
        if y_lo < yl - 1e-6:
            pts.append(np.array([r_end - 0.2, y_lo]))
        k_sh0 = None
        pts.append(np.array([math.sqrt(r_slip ** 2 - y_lo ** 2), y_lo]))
        pts.append(polar(r_slip, o - e1))
        # at the leaf line the plate runs up to 0.04 mm short of the leaf's inner edge (the closing pages' inner
        # edge there is exactly r_in), then falls back to r_end at its +y edge, where a closing pleat's inner
        # corner comes in to r_in cos(gamma): no daylight at the valley corners, no contact at any angle
        pts.append(polar(spec.r_in - 0.04, o - e1))
        a1 = math.asin(min(0.99, yr / r_end))
        top2 = [polar(r_end, t) for t in np.linspace(o - e1, a1, max(2, plan.top_seg + 1))][1:]
        pts += top2
        k_sh1 = len(pts) - 1
    else:
        a0, a1 = math.asin(max(-0.99, yl / r_end)), math.asin(min(0.99, yr / r_end))
        top = [np.array([r_end * math.cos(t), r_end * math.sin(t)]) for t in np.linspace(a0, a1, plan.top_seg + 2)]
        k_sh0 = len(pts)
        pts += top
        k_sh1 = len(pts) - 1
    pts += plus[::-1]
    # butt semicircle (from +y back round to -y)
    for t in np.linspace(0.5 * math.pi, 1.5 * math.pi, plan.butt_seg + 2)[1:-1]:
        pts.append(np.array([cx + hw0 * math.cos(t), hw0 * math.sin(t)]))
    poly = np.array(pts)
    # the two side points at x = cx coincide with the semicircle's ends: drop exact duplicates
    keep = [0] + [k for k in range(1, len(poly)) if np.linalg.norm(poly[k] - poly[k - 1]) > 1e-6]
    poly = poly[keep]
    if np.linalg.norm(poly[0] - poly[-1]) < 1e-6:
        poly = poly[:-1]
    if plan.shoulder_seg > 0:
        corners = {k_sh1: (spec.rib_shoulder_r_mm, plan.shoulder_seg)}
        if k_sh0 is not None:
            corners[k_sh0] = (spec.rib_shoulder_r_mm, plan.shoulder_seg)
        poly = fillet(poly, corners)
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


def _to_fan(poly: np.ndarray, deg: float) -> np.ndarray:
    c, s = math.cos(deg * D2R), math.sin(deg * D2R)
    return np.stack([poly[:, 0] * c - poly[:, 1] * s, poly[:, 0] * s + poly[:, 1] * c], 1)


def clip_x(poly: np.ndarray, xc: float) -> np.ndarray:
    """Sutherland-Hodgman: the part of a simple polygon with x <= xc."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ina, inb = a[0] <= xc, b[0] <= xc
        if ina:
            out.append(a)
        if ina != inb:
            u = (xc - a[0]) / (b[0] - a[0])
            out.append(a + u * (b - a))
    q = np.array(out)
    keep = [0] + [k for k in range(1, len(q)) if np.linalg.norm(q[k] - q[k - 1]) > 1e-6]
    q = q[keep]
    if np.linalg.norm(q[0] - q[-1]) < 1e-6:
        q = q[:-1]
    return q


PRONG_ARC_SEG = {0: 4, 1: 2, 2: 1}
PRONG_INWARD_MM = 1.0
#: the prong's top sits this far under its rib's top, so where the two overlap their faces never z-fight
PRONG_TOP_DROP_MM = 0.01
PRONG_W_MAX = 0.999


def prong_outline(spec: FanSpec, i: int, lod: int) -> np.ndarray:
    """Stick i's LEAF-ZONE PRONG (i = 0 .. n-2) in its own frame (x along its axis, CCW): from the rib tip's arc
    (r_in - rib_end_gap) out to r_in + prong_reach, between the line ``prong_clear_mm`` on the + side of its own leaf
    line and the line ``prong_clear_mm + prong_overlap_mm`` on the + side of the NEXT leaf line (bind positions; the
    fold never brings a face above either line there - FanSpec.prong_* has the argument)."""
    o = spec.leaf_line_offset_deg(i) * D2R
    p = o + spec.leaf_pitch_deg * D2R              # leaf line i+1 in stick i's frame at bind
    # the prong starts PRONG_INWARD_MM inside the rib tips: it laps over the step where the next rib (0.375 mm lower)
    # ends, so a ray drifting outward as it descends (the reference camera's 11.5 deg tilt, pivot-side obliques) cannot
    # slip between the prong's inner edge and the lower rib's tip (MEASURED: 94 px in the round-3 reference render with
    # abutting edges), and LOD2's chord-ended ribs (0.18 mm sagitta) leave no slit.  Nothing else lives at the prong's
    # level there (it is its own stick's level; the leaf never comes inside r_in - 0.09 mm)
    r0 = spec.r_in - spec.rib_end_gap_mm - PRONG_INWARD_MM
    r1 = spec.r_in + spec.prong_reach_mm
    ca, cb = spec.prong_clear_mm, spec.prong_clear_mm + spec.prong_overlap_mm
    if i == spec.n_sticks - 2:
        # the last rib's prong runs on over the glued rear flap (flat on the rear guard, 0.145 mm under it) to the flap's
        # corner, so the band does not end in a patch of leaf at the rear guard
        n = spec.n_sticks
        p = (spec.stick_axis_deg(n - 1, 1.0) + spec.rear_flap_past_axis_deg - spec.stick_axis_deg(i, 1.0)) * D2R
        cb = 0.0

    def meet(ang, c, r):
        """angle of the point on the circle r whose distance from the radial line at ``ang`` is c (+ side)"""
        return ang + math.asin(c / r)
    seg = PRONG_ARC_SEG[lod]
    a_in0, a_in1 = meet(o, ca, r0), meet(p, cb, r0)
    a_out0, a_out1 = meet(o, ca, r1), meet(p, cb, r1)
    outer = [np.array([r1 * math.cos(t), r1 * math.sin(t)]) for t in np.linspace(a_out0, a_out1, seg + 1)]
    inner = [np.array([r0 * math.cos(t), r0 * math.sin(t)]) for t in np.linspace(a_in1, a_in0, seg + 1)]
    poly = np.array(outer + inner)
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


def prong_edge_angles(spec: FanSpec, i: int, r: float) -> Tuple[float, float]:
    """(radians, FAN frame at bind) the prong's - edge and + edge at radius r (the lines prong_outline cuts)."""
    ax = spec.stick_axis_deg(i, 1.0) * D2R
    o = spec.leaf_line_offset_deg(i) * D2R
    p = o + spec.leaf_pitch_deg * D2R
    cb = spec.prong_clear_mm + spec.prong_overlap_mm
    if i == spec.n_sticks - 2:
        n = spec.n_sticks
        p = (spec.stick_axis_deg(n - 1, 1.0) + spec.rear_flap_past_axis_deg - spec.stick_axis_deg(i, 1.0)) * D2R
        cb = 0.0
    return ax + o + math.asin(spec.prong_clear_mm / r), ax + p + math.asin(cb / r)


def _prong_weights(spec: FanSpec, mb: "FanMesh") -> Dict[int, List[Tuple[str, float]]]:
    """vertex -> [(stick_i, 1 - w), (stick_i+1, w)] for every prong vertex (layer 'prong'), w = its angular fraction
    between the prong's two edge lines at its own radius."""
    out = {}
    for key, v in mb._key.items():
        b, layer = key[0], key[1]
        if layer != "prong":
            continue
        name = mb.bone_names[b]
        i = int(name.split("_")[1])
        x, y = mb.P[v][0], mb.P[v][1]
        r = math.hypot(x, y)
        a0, a1 = prong_edge_angles(spec, i, r)
        # capped at PRONG_W_MAX so every prong vertex keeps stick i (its owner: QA's closed-solid groups and the verifier
        # tell parts apart by the lowest stick a triangle's vertices use); the + edge then lags stick i+1 by 0.1 % of the
        # gap's closing turn, under 0.01 mm
        w = round(min(PRONG_W_MAX, max(0.0, (math.atan2(y, x) - a0) / (a1 - a0))), 6)
        nxt = f"stick_{i + 1:02d}"
        out[v] = [(name, 1.0)] if w <= 0.0 else [(name, round(1.0 - w, 6)), (nxt, w)]
    return out


def skin(mb: "FanMesh", T_by_bone: Dict[str, np.ndarray], apply_fn=None) -> np.ndarray:
    """Posed vertex positions (mm): linear blend skinning with mb.W where present, else one bone per vertex."""
    P, T, B = mb.arrays()
    ap = apply_fn or (lambda M, X: np.asarray(X, np.float64) @ M[:3, :3].T + M[:3, 3])
    Q = np.empty_like(P)
    for bi, bn in enumerate(mb.bone_names):
        m = B == bi
        if m.any():
            Q[m] = ap(T_by_bone[bn], P[m])
    if mb.W is not None:
        for v, wl in enumerate(mb.W):
            if len(wl) > 1 or wl[0][0] != mb.bone_names[mb.B[v]]:
                Q[v] = sum(w * ap(T_by_bone[bn], P[v:v + 1])[0] for bn, w in wl)
    return Q


def prong_z(spec: FanSpec, i: int) -> Tuple[float, float]:
    """(bottom, top): the top is where rib i's top face is (leaf_on_rib_mm under leaf line i; for the front guard, the
    level a rib would have there, 0.06 mm under the guard)."""
    top = spec.leaf_line_z(i) - spec.leaf_on_rib_mm - PRONG_TOP_DROP_MM
    return top - spec.prong_thick_mm, top


def spacer_outline(spec: FanSpec, plan: "LodPlan") -> np.ndarray:
    """The spacer under the front guard: the guard's outline in the bare zone (cut 1 mm inside the leaf's inner
    edge, so the leaf's first panel, which lies in the gap beyond it, never meets it)."""
    q = clip_x(guard_outline(spec, "front", plan), spec.r_in - 1.0)
    return q if _signed_area(q) > 0 else q[::-1]


def spacer_z(spec: FanSpec) -> Tuple[float, float]:
    from .fan_spec import STACK_CLEARANCE_MM
    return spec.stick_z(1)[1] + STACK_CLEARANCE_MM, spec.stick_z(0)[0] - STACK_CLEARANCE_MM


def _widening(spec: FanSpec, inner_edge: callable, sep_deg: float):
    """Extra half-width a rib needs toward a guard sep_deg away so that it reaches 0.3 mm under the guard's
    inner edge (``inner_edge(x_guard)`` = that edge's distance from the guard's axis) in the bare zone."""
    a1 = sep_deg * D2R
    xx = np.linspace(20.0, spec.r_in, 60)
    ex = []
    for x in xx:
        xg = x * math.cos(a1)
        need = (x * math.sin(a1) - (inner_edge(xg) - 0.3)) / math.cos(a1)
        ex.append(max(0.0, need - 0.5 * spec.rib_width_mm(x)))
    ex = np.array(ex)
    return lambda x: float(np.interp(x, xx, ex))


def rib1_widening(spec: FanSpec):
    """rib 1 toward the front guard (its inner edge: front_guard_edges)."""
    xs = np.linspace(0.0, spec.r_in, 80)
    _, yi = front_guard_edges(spec, xs)
    return _widening(spec, lambda xg: float(np.interp(xg, xs, yi)), spec.stick_axis_deg(1, 1.0))


def rib24_widening(spec: FanSpec):
    """rib 24 toward the rear guard (its inner edge: rear_guard_edges)."""
    n = spec.n_sticks - 1
    sep = spec.stick_axis_deg(n, 1.0) - spec.stick_axis_deg(n - 1, 1.0)
    return _widening(spec, lambda xg: -float(rear_guard_edges(spec, np.array([xg]))[0][0]), sep)


# =========================================================================== stick solids
def _extrude(mb: FanMesh, poly: np.ndarray, hole_r: float, hole_seg: int, z0: float, z1: float, frame_deg: float,
             bone: str, group: str, chamfer: float, uv_top, uv_bot, uv_wall, n_chunks: int = 1, uv_hole=None,
             wall_scale: float = 1.0, kinds: Tuple[str, str, str] = ("top", "bottom", "wall"), layer: str = ""):
    """Plate between z0 (bottom) and z1 (top) with optional pivot hole and chamfered top/bottom edges.
    The wall's UV strip is cut into ``n_chunks`` equal lengths (points are inserted at the cuts), each
    its own island: ``uv_wall(chunk, distance_along_chunk, z)``."""
    rot = lambda q: _to_fan(np.atleast_2d(q), frame_deg)
    per_full = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
    poly = _insert_cuts(poly, n_chunks)
    hole = circle(hole_r, hole_seg, cw=True) if hole_seg else None
    top_poly = inset(poly, chamfer) if chamfer > 0 else poly
    slot = SLOTS["sticks"]
    up, dn = np.array([0, 0, 1.0]), np.array([0, 0, -1.0])

    def P(q, z):
        f = rot(q)[0]
        return (f[0], f[1], z)
    # top and bottom faces
    for (zz, nrm, uvf, poly_) in ((z1, up, uv_top, top_poly), (z0, dn, uv_bot, top_poly)):
        for t in triangulate_with_hole(poly_, hole):
            pts = [poly_[k] if kind == "o" else hole[k] for kind, k in t]
            mb.tri([P(q, zz) for q in pts], [uvf(q) for q in pts], [nrm] * 3, bone, slot, "sticks", group,
                   locs=[q for q in pts], kind=kinds[0] if zz == z1 else kinds[1], layer=layer)
    # walls: chamfer ring (top), vertical wall, chamfer ring (bottom)
    n = len(poly)
    per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1))])
    # chunk boundaries: each ideal cut snapped to the outline corner nearest it (a cut point where one was made)
    bounds = np.array(sorted(float(per[:-1][np.argmin(np.abs(per[:-1] - c * per[-1] / n_chunks))])
                             for c in range(1, n_chunks)))
    # outward 2-D normals (smooth along the outline)
    nrm2 = np.zeros_like(poly)
    for i in range(n):
        a, b = poly[i - 1], poly[(i + 1) % n]
        e = b - a
        nn = np.array([e[1], -e[0]])
        nrm2[i] = nn / np.linalg.norm(nn)
    rings = []
    if chamfer > 0:
        rings = [(top_poly, z1, 0.0), (poly, z1 - chamfer, 1.0), (poly, z0 + chamfer, 1.0), (top_poly, z0, 0.0)]
    else:
        rings = [(poly, z1, 1.0), (poly, z0, 1.0)]
    zs = [r[1] for r in rings]
    for k in range(len(rings) - 1):
        (pa, za, wa), (pb, zb, wb) = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            def nr(q2, zz, w, idx):
                side = np.array([nrm2[idx][0], nrm2[idx][1], 0.0])
                if w >= 1.0 and (zz == zs[1] or zz == zs[-2]) and chamfer > 0:
                    return side
                if w < 1.0:
                    vert = up if zz >= 0.5 * (z0 + z1) else dn
                    return (side + vert) / np.linalg.norm(side + vert)
                return side
            fn = lambda idx, zz, w: _rot_n(nr(None, zz, w, idx), frame_deg)
            pa_i, pa_j, pb_i, pb_j = pa[i], pa[j], pb[i], pb[j]
            ch = int(np.searchsorted(bounds, per[i] + 1e-7, side="right"))
            base = 0.0 if ch == 0 else bounds[ch - 1]
            k = wall_scale
            uva, uvb = uv_wall(ch, k * (per[i] - base), za), uv_wall(ch, k * (per[i + 1] - base), za)
            uvc, uvd = uv_wall(ch, k * (per[i + 1] - base), zb), uv_wall(ch, k * (per[i] - base), zb)
            ca, cb = P(pa_i, za), P(pa_j, za)
            cc, cd = P(pb_j, zb), P(pb_i, zb)
            na, nb, nc, nd = fn(i, za, wa), fn(j, za, wa), fn(j, zb, wb), fn(i, zb, wb)
            la, lb = (per[i], za), (per[i + 1], za)
            lc, ld = (per[i + 1], zb), (per[i], zb)
            mb.tri([ca, cb, cc], [uva, uvb, uvc], [na, nb, nc], bone, slot, "sticks", group, locs=[la, lb, lc], kind=kinds[2],
                   layer=layer)
            mb.tri([ca, cc, cd], [uva, uvc, uvd], [na, nc, nd], bone, slot, "sticks", group, locs=[la, lc, ld], kind=kinds[2],
                   layer=layer)
    # the pivot hole's wall
    if hole is not None:
        m = len(hole)
        for i in range(m):
            j = (i + 1) % m
            a, b = hole[i], hole[j]
            na = -np.array([a[0], a[1], 0.0]) / hole_r
            nb = -np.array([b[0], b[1], 0.0]) / hole_r
            A1, B1, A0, B0 = P(a, z1), P(b, z1), P(a, z0), P(b, z0)
            u0, u1 = uv_hole(i * 0.5, z1), uv_hole((i + 1) * 0.5, z1)
            u2, u3 = uv_hole((i + 1) * 0.5, z0), uv_hole(i * 0.5, z0)
            hl = [(i * 0.5, z1), ((i + 1) * 0.5, z1), ((i + 1) * 0.5, z0), (i * 0.5, z0)]
            mb.tri([A1, B1, B0], [u0, u1, u2], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(nb, frame_deg)],
                   bone, slot, "sticks", group, locs=[hl[0], hl[1], hl[2]], kind="hole")
            mb.tri([A1, B0, A0], [u0, u2, u3], [_rot_n(na, frame_deg), _rot_n(nb, frame_deg), _rot_n(na, frame_deg)],
                   bone, slot, "sticks", group, locs=[hl[0], hl[2], hl[3]], kind="hole")
    return per[-1]


def _insert_cuts(poly: np.ndarray, n_chunks: int) -> np.ndarray:
    if n_chunks <= 1:
        return poly
    seg = np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)
    per = np.concatenate([[0.0], np.cumsum(seg)])
    clen = per[-1] / n_chunks
    out = []
    # a cut within 2 mm of an existing corner is not made (the corner serves; a cut on a short segment would
    # leave three collinear points for the caps' triangulation); the wall islands carry 3 mm of slack for it
    cuts = [c * clen for c in range(1, n_chunks) if np.min(np.abs(per[:-1] - c * clen)) > 2.0]
    for i in range(len(poly)):
        out.append(poly[i])
        a, b = per[i], per[i + 1]
        for c in cuts:
            if a + 2.0 < c < b - 2.0:
                u = (c - a) / (b - a)
                out.append(poly[i] + u * (poly[(i + 1) % len(poly)] - poly[i]))
    return np.array(out)


def _rot_n(n, deg):
    c, s = math.cos(deg * D2R), math.sin(deg * D2R)
    return np.array([n[0] * c - n[1] * s, n[0] * s + n[1] * c, n[2]])


# =========================================================================== the leaf
def leaf_faces(spec: FanSpec, tpl: FF.LeafTemplate) -> List[Dict[str, object]]:
    """The 50 faces' bind corners (inner-rib, outer-rib, outer-mid, inner-mid order as a loop) with the
    edge kinds."""
    out = []
    n = spec.n_sticks
    for i in range(n - 1):
        out.append({"j": 2 * i, "rib": i, "mid": i,
                    "quad": [tpl.rib_pts[i, 0], tpl.rib_pts[i, 1], tpl.mid_pts[i, 1], tpl.mid_pts[i, 0]],
                    "kinds": ["rib", "rib", "mid", "mid"]})
        out.append({"j": 2 * i + 1, "rib": i + 1, "mid": i,
                    "quad": [tpl.mid_pts[i, 0], tpl.mid_pts[i, 1], tpl.rib_pts[i + 1, 1], tpl.rib_pts[i + 1, 0]],
                    "kinds": ["mid", "mid", "rib", "rib"]})
    return out


def _face_normal(q):
    q = np.asarray(q)
    n = np.cross(q[1] - q[0], q[3] - q[0]) + np.cross(q[3] - q[2], q[1] - q[2])
    n = n / np.linalg.norm(n)
    return n if n[2] > 0 else -n


LEAF_PIECE_FACES = 5          # UV: the flat leaf cut into strips of 5 faces (seams fall on folds)
LEAF_PAD_PX = 8


def leaf_corners(spec: FanSpec, tpl: FF.LeafTemplate):
    """Every leaf quad (faces and the two glued flaps) with its bind corners, the flat-leaf position of
    each corner (the development: fold line k at angle k x beta, a corner at its distance along its fold
    line from the line's axis point), its bone and its piece."""
    beta = spec.face_angle_deg * D2R
    out = []
    for f in leaf_faces(spec, tpl):
        j = f["j"]
        q = np.asarray(f["quad"])
        flat = []
        for c in range(4):
            if f["kinds"][c] == "rib":
                k = 2 * f["rib"]
                dist = float(np.linalg.norm(q[c][:2]))
            else:
                k = 2 * f["mid"] + 1
                ax = np.array([0.0, 0.0, 0.5 * (tpl.z[f["mid"]] + tpl.z[f["mid"] + 1])])
                dist = float(np.linalg.norm(q[c] - ax))
            flat.append(dist * np.array([math.cos(k * beta), math.sin(k * beta)]))
        out.append({"kind": "face", "j": j, "quad": q, "flat": np.array(flat), "bone": f"leaf_{j:02d}",
                    "kinds": f["kinds"], "piece": min(j // LEAF_PIECE_FACES, (2 * (spec.n_sticks - 1) - 1) // LEAF_PIECE_FACES)})
    sc = 0.5 * spec.scallop_L * spec.L
    n = spec.n_sticks
    lam0, lam25 = tpl.lam_deg[0], tpl.lam_deg[-1]
    # the flap's edge at the leaf line meets the leaf's scallop bump there
    rear_axis = spec.stick_axis_deg(n - 1, 1.0)
    npieces = out[-1]["piece"] + 1
    # only the REAR flap: the leaf glued over the rear guard (RS 2's leaf corner past its axis).  The front guard's
    # leaf line sits beside its inner edge one rib pitch above rib 1; the leaf's corner under the front guard
    # (RS 2) is never visible from the front and is not built
    for name, a0, a1, z, bone, k_edge, piece in (
            ("rear", lam25, rear_axis + spec.rear_flap_past_axis_deg, tpl.z[-1], f"stick_{n - 1:02d}", 2 * (n - 1),
             npieces - 1),):
        r_i, r_o = spec.r_in, spec.r_out + sc
        corners, flat = [], []
        for rr, aa in ((r_i, a0), (r_o, a0), (r_o, a1), (r_i, a1)):
            corners.append(np.array([rr * math.cos(aa * D2R), rr * math.sin(aa * D2R), z]))
            th = k_edge * beta + (aa - a0) * D2R          # flat: the flap continues the development
            flat.append(rr * np.array([math.cos(th), math.sin(th)]))
        out.append({"kind": "flap", "name": name, "quad": np.array(corners), "flat": np.array(flat), "bone": bone,
                    "piece": piece})
    return out


def _piece_polygon(items):
    pts = np.vstack([it["flat"] for it in items])
    # the piece is an annular sector: its outline is the convex-ish hull of its corners; use all corners
    return pts


def leaf_uv_layout(spec: FanSpec, items, tex: int):
    """Place the pieces (strips of LEAF_PIECE_FACES faces, bisector vertical, alternately pointing up and
    down so neighbours nest) in rows; return per-piece 2x3 affine maps flat(mm) -> uv and px/mm."""
    pieces = sorted({it["piece"] for it in items})
    polys = {}
    for p in pieces:
        pts = _piece_polygon([it for it in items if it["piece"] == p])
        ang = np.arctan2(pts[:, 1], pts[:, 0])
        mid = 0.5 * (ang.min() + ang.max())
        polys[p] = (pts, mid)
    # orientation: rotate so the bisector points up (+y) for even pieces, down for odd ones
    placed = {}
    for p in pieces:
        pts, mid = polys[p]
        rot = (math.pi / 2 - mid) + (math.pi if p % 2 else 0.0)
        c, s = math.cos(rot), math.sin(rot)
        R = np.array([[c, -s], [s, c]])
        q = pts @ R.T
        placed[p] = (R, q)
    # rows of alternating pieces, nested by a 1-D search on a 0.25 mm raster
    per_row = int(math.ceil(len(pieces) / 2))
    rows = [pieces[:per_row], pieces[per_row:]]
    res = 0.25
    gap_mm = 2.0
    layout = {}
    row_y = 0.0
    for row in rows:
        x_cursor = None
        occupied = []
        row_h = 0.0
        for p in row:
            R, q = placed[p]
            q0 = q - q.min(0)
            h = q0[:, 1].max()
            row_h = max(row_h, h)
        for p in row:
            R, q = placed[p]
            lo = q.min(0)
            q0 = q - lo
            poly = _sector_outline(q0)
            if x_cursor is None:
                dx = 0.0
            else:
                dx = _nest(occupied, poly, x_cursor, gap_mm)
            occupied.append(poly + np.array([dx, 0.0]))
            layout[p] = (R, lo, np.array([dx, row_y]))
            x_cursor = max(pp[:, 0].max() for pp in occupied)
        row_y += row_h + gap_mm
    allpts = np.vstack([ (placed[p][1] - layout[p][1]) + layout[p][2] for p in pieces])
    extent = allpts.max(0)
    side = max(extent) + 2 * 1.0
    ppmm = (tex - 2 * LEAF_PAD_PX) / side
    maps = {}
    for p in pieces:
        R, lo, off = layout[p]
        maps[p] = (R, lo, off)

    def uv(p, flat_pt):
        R, lo, off = maps[p]
        m = (R @ np.asarray(flat_pt)) - lo + off
        px = LEAF_PAD_PX + m * ppmm
        return px / tex
    return uv, ppmm, side


def _sector_outline(q0):
    """Outline polygon of a placed piece from its corner cloud (convex hull; the pieces are thin)."""
    pts = np.unique(np.round(q0, 6), axis=0)
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def _poly_overlap(a, b, gap):
    """True if convex polygons a and b are closer than gap (separating axis with a margin)."""
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            e = poly[(i + 1) % n] - poly[i]
            ax = np.array([-e[1], e[0]])
            ax /= np.linalg.norm(ax)
            pa, pb = a @ ax, b @ ax
            if pa.max() + gap <= pb.min() or pb.max() + gap <= pa.min():
                return False
    return True


def _nest(occupied, poly, x_cursor, gap):
    lo, hi = x_cursor - poly[:, 0].max() - 50.0, x_cursor + gap
    # the smallest shift that clears everything already placed
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if any(_poly_overlap(o, poly + np.array([mid, 0.0]), gap) for o in occupied):
            lo = mid
        else:
            hi = mid
    return hi


def _on_line(a: np.ndarray, b: np.ndarray, R: float) -> np.ndarray:
    """The point on the line a -> b whose horizontal radius is R (Newton; the fold lines are near radial)."""
    d = b - a
    u = (R - float(np.linalg.norm(a[:2]))) / max(float(np.linalg.norm(d[:2])), 1e-9)
    for _ in range(6):
        p = a + u * d
        r = float(np.linalg.norm(p[:2]))
        dr = float(p[:2] @ d[:2]) / max(r, 1e-12)
        u += (R - r) / dr
    return a + u * d


def leaf_edge_radius(spec: FanSpec, t, outer: bool):
    """Horizontal radius of the leaf's edge at fraction t across a face (0 = the leaf line's mountain, 1 = the
    valley): the inner edge is RS 7's clean arc; the outer edge a sinusoid, bump at the mountain."""
    if not outer:
        return spec.r_in + 0.0 * np.asarray(t, np.float64)
    sc = 0.5 * spec.scallop_L * spec.L
    return spec.r_out + sc * np.cos(math.pi * np.asarray(t, np.float64))


class FaceFrame:
    """One rigid leaf face at bind: its fold lines (the leaf line = mountain at t = 0, the mid-gap fold = valley at
    t = 1), its plane, and the affine map from the plane to the flat (developed) leaf."""

    def __init__(self, spec: FanSpec, it: dict):
        q = np.asarray(it["quad"], np.float64)
        kinds = it["kinds"]
        rib_c = [c for c in range(4) if kinds[c] == "rib"]
        mid_c = [c for c in range(4) if kinds[c] == "mid"]
        # inner corner = the smaller horizontal radius on each line
        rk = sorted(rib_c, key=lambda c: np.linalg.norm(q[c][:2]))
        mk = sorted(mid_c, key=lambda c: np.linalg.norm(q[c][:2]))
        self.A = (q[rk[0]], q[rk[1]])          # the leaf line (inner, outer)
        self.B = (q[mk[0]], q[mk[1]])          # the mid-gap fold (inner, outer)
        self.spec = spec
        self.n = _face_normal(q)
        e1 = self.A[1] - self.A[0]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(self.n, e1)
        self.o, self.e1, self.e2 = q[0], e1, e2
        X = np.stack([(q - self.o) @ e1, (q - self.o) @ e2], 1)
        Y = np.asarray(it["flat"], np.float64)
        M, *_ = np.linalg.lstsq(np.hstack([X, np.ones((4, 1))]), Y, rcond=None)
        self.M = M
        # the ends of both fold lines at the leaf's edge radii (moved ALONG the lines: they stay fold vertices)
        self.Ai = _on_line(self.A[0], self.A[1], float(leaf_edge_radius(spec, 0.0, False)))
        self.Ao = _on_line(self.A[0], self.A[1], float(leaf_edge_radius(spec, 0.0, True)))
        self.Bi = _on_line(self.B[0], self.B[1], float(leaf_edge_radius(spec, 1.0, False)))
        self.Bo = _on_line(self.B[0], self.B[1], float(leaf_edge_radius(spec, 1.0, True)))
        # the development of the fold-line ends, exactly as leaf_corners (so two faces sharing a fold line give its
        # vertices the same UV): fold k lies at angle k x beta, a point at its distance from the line's axis point
        beta = spec.face_angle_deg * D2R
        j = it["j"]
        rib_i, mid_i = j // 2 + (j % 2), j // 2
        kA, kB = 2 * rib_i, 2 * mid_i + 1
        zB = 0.5 * (spec.leaf_line_z(mid_i) + spec.leaf_line_z(mid_i + 1))

        def dev(p, k, axis_z):
            d = float(np.linalg.norm(p - np.array([0.0, 0.0, axis_z])))
            return d * np.array([math.cos(k * beta), math.sin(k * beta)])
        zA = float(self.A[0][2])
        self._dev = {(0.0, False): dev(self.Ai, kA, zA), (0.0, True): dev(self.Ao, kA, zA),
                     (1.0, False): dev(self.Bi, kB, zB), (1.0, True): dev(self.Bo, kB, zB)}

    def edge_point(self, t: float, outer: bool) -> np.ndarray:
        a, b = (self.Ao, self.Bo) if outer else (self.Ai, self.Bi)
        if t <= 0.0:
            return a.copy()
        if t >= 1.0:
            return b.copy()
        c = a + t * (b - a)
        R = float(leaf_edge_radius(self.spec, t, outer))
        for _ in range(3):
            rh = np.array([c[0], c[1], 0.0]) / max(float(np.linalg.norm(c[:2])), 1e-12)
            d = rh - (rh @ self.n) * self.n
            d /= np.linalg.norm(d)
            r = float(np.linalg.norm(c[:2]))
            c = c + d * (R - r) / max(float(d[:2] @ rh[:2]), 1e-9)
        return c

    def flat(self, p: np.ndarray) -> np.ndarray:
        x = np.array([(p - self.o) @ self.e1, (p - self.o) @ self.e2, 1.0])
        return x @ self.M

    def flat_t(self, t: float, outer: bool) -> np.ndarray:
        """The flat (developed) position of the edge point at t: the face's affine map, corrected so both fold-line
        ends take the exact development (shared by the neighbouring face)."""
        p = self.edge_point(t, outer)
        a = self.edge_point(0.0, outer)
        b = self.edge_point(1.0, outer)
        ra = self._dev[(0.0, outer)] - self.flat(a)
        rb = self._dev[(1.0, outer)] - self.flat(b)
        return self.flat(p) + (1.0 - t) * ra + t * rb

    def width(self, outer: bool) -> float:
        a, b = (self.Ao, self.Bo) if outer else (self.Ai, self.Bi)
        line = self.A[1] - self.A[0]
        line /= np.linalg.norm(line)
        w = b - a
        return float(np.linalg.norm(w - (w @ line) * line))


def _rotate(v: np.ndarray, k: np.ndarray, ang: float) -> np.ndarray:
    return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * (k @ v) * (1 - math.cos(ang))


def build_leaf(mb: FanMesh, spec: FanSpec, tpl: FF.LeafTemplate, lod: int = 0):
    items = leaf_corners(spec, tpl)
    uvf, ppmm, side = leaf_uv_layout(spec, items, spec.texture_size)
    slot = SLOTS["leaf"]
    faces = [it for it in items if it["kind"] == "face"]
    frames = [FaceFrame(spec, f) for f in faces]
    nf = len(frames)
    up = np.array([0.0, 0.0, 1.0])
    for it in items:
        if it["kind"] != "face":
            continue
        j = it["j"]
        fr = frames[j]
        n = fr.n
        # the ridge (the leaf line's mountain): the bisector with the face across it (the flap's +Z at line 25;
        # under the front guard, at line 0, the fan plane's +Z)
        if j % 2 == 0:
            other = frames[j - 1].n if j >= 1 else up
        else:
            other = frames[j + 1].n if j + 1 < nf else up
        n_r = n + other
        n_r /= np.linalg.norm(n_r)
        k = np.cross(n_r, n)
        th = math.asin(min(1.0, float(np.linalg.norm(k))))
        k = k / max(float(np.linalg.norm(k)), 1e-12)

        def nrm(t, n_r=n_r, k=k, th=th):
            # t = 0: halfway to the ridge bisector; from LEAF_RIDGE_T on: the face normal (flat facet)
            u = min(1.0, t / LEAF_RIDGE_T)
            return _rotate(n_r, k, th * (0.5 + 0.5 * u))
        part, grp, bone = "leaf", f"leaf_{j:02d}", it["bone"]
        piece = it["piece"]
        ts = LEAF_STRIPS[lod]
        inner = [fr.edge_point(t, False) for t in ts]
        outer = [fr.edge_point(t, True) for t in ts]
        for a in range(len(ts) - 1):
            P = [inner[a], outer[a], outer[a + 1], inner[a + 1]]
            T = [ts[a], ts[a], ts[a + 1], ts[a + 1]]
            fl = [fr.flat_t(ts[a], False), fr.flat_t(ts[a], True), fr.flat_t(ts[a + 1], True), fr.flat_t(ts[a + 1], False)]
            uv = [uvf(piece, f) for f in fl]
            cn = [nrm(t) for t in T]
            for (x, y, z) in ((0, 1, 2), (0, 2, 3)):
                mb.tri([P[x], P[y], P[z]], [uv[x], uv[y], uv[z]], [cn[x], cn[y], cn[z]], bone, slot, part, grp,
                       layer="front", locs=[fl[x], fl[y], fl[z]], kind="leaf")
        # the back layer: 0 at both fold lines, LEAF_BACK_OFFSET_MM from LEAF_BACK_TAPER_MM in
        ti = min(0.45, LEAF_BACK_TAPER_MM / fr.width(False))
        to = min(0.45, LEAF_BACK_TAPER_MM / fr.width(True))
        tbi, tbo = (0.0, ti, 1.0 - ti, 1.0), (0.0, to, 1.0 - to, 1.0)
        bi = [fr.edge_point(t, False) for t in tbi]
        bo = [fr.edge_point(t, True) for t in tbo]
        fbi = [fr.flat_t(t, False) for t in tbi]
        fbo = [fr.flat_t(t, True) for t in tbo]
        off = [0.0, LEAF_BACK_OFFSET_MM, LEAF_BACK_OFFSET_MM, 0.0]
        bi = [p - n * o for p, o in zip(bi, off)]
        bo = [p - n * o for p, o in zip(bo, off)]
        for a in range(3):
            P = [bi[a], bo[a], bo[a + 1], bi[a + 1]]
            fl = [fbi[a], fbo[a], fbo[a + 1], fbi[a + 1]]
            uv = [uvf(piece, f) for f in fl]
            for (x, y, z) in ((0, 2, 1), (0, 3, 2)):
                mb.tri([P[x], P[y], P[z]], [uv[x], uv[y], uv[z]], [-n, -n, -n], bone, slot, part, grp,
                       layer="back", locs=[fl[x], fl[y], fl[z]], kind="leaf")
    for it in items:
        if it["kind"] == "face":
            continue
        q = it["quad"]
        uvs = [uvf(it["piece"], it["flat"][c]) for c in range(4)]
        n = np.array([0.0, 0.0, 1.0])
        fl = it["flat"]
        part, grp, bone = "flaps", f"flap_{it['name']}", it["bone"]
        for (a, b, c) in ((0, 1, 2), (0, 2, 3)):
            mb.tri([q[a], q[b], q[c]], [uvs[a], uvs[b], uvs[c]], [n] * 3, bone, slot, part, grp,
                   layer="front", locs=[fl[a], fl[b], fl[c]], kind="leaf")
        back = q - n * LEAF_BACK_OFFSET_MM
        for (a, b, c) in ((0, 1, 2), (0, 2, 3)):
            mb.tri([back[a], back[c], back[b]], [uvs[a], uvs[c], uvs[b]], [-n] * 3, bone, slot, part,
                   grp, layer="back", locs=[fl[a], fl[c], fl[b]], kind="leaf")
    return {"leaf_uv_side_mm": round(side, 3), "leaf_ppmm": round(ppmm, 4), "leaf_strips": len(LEAF_STRIPS[lod]) - 1}


# =========================================================================== rivet (lathe)
def rivet_profile(spec: FanSpec, lod: int):
    """Closed (r, z) loop of the hollow eyelet: LOD0 = heads + barrel through the stack; LOD1/2 = two
    separate head rings on the guard faces."""
    zt = 0.5 * spec.stack_mm
    zb = -zt
    rh, ro, p = spec.rivet_hole_r, spec.rivet_head_r, spec.rivet_proud
    rbar = 0.5 * spec.rivet_shaft_d_mm
    lift = 0.01
    rec = RIVET_RECESS_FLOOR_MM
    head_f = [(rh, zt + 0.55 * p), (rh + 0.35, zt + 0.95 * p), (0.5 * (rh + ro) + 0.3, zt + p),
              (ro - 0.35, zt + 0.8 * p), (ro, zt + 0.35 * p), (ro - 0.12, zt + lift)]
    if lod >= 2:
        head_f = [(rh, zt + 0.6 * p), (0.5 * (rh + ro), zt + p), (ro, zt + 0.4 * p), (ro - 0.1, zt + lift)]
    if lod == 0:
        # each head's hollow is a blind recess: its floor RIVET_RECESS_FLOOR_MM under the stack face (the axis
        # points close the lathe; the segment between them along the axis is degenerate and dropped)
        loop = [(0.0, zt - rec), (rh, zt - rec)] + head_f + [(rbar, zt + lift)]
        loop += [(rbar, zb - lift)]
        head_b = [(r, -z) for (r, z) in head_f[::-1]]
        loop += head_b + [(rh, zb + rec), (0.0, zb + rec)]
        return [np.array(loop)]
    front = head_f + [(rh + 0.02, zt + lift)]
    back = [(r, -z) for (r, z) in front[::-1]]
    return [np.array(front), np.array(back)]


RIVET_RECESS_FLOOR_MM = 0.5


def build_rivet(mb: FanMesh, spec: FanSpec, plan: LodPlan):
    slot = SLOTS["rivet"]
    seg = plan.rivet_seg
    loops = rivet_profile(spec, plan.lod)
    vtot = 0
    for li, prof in enumerate(loops):
        # make the loop CCW in (r, z) so outward normals come out consistently
        m = len(prof)
        per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([prof, prof[:1]]), axis=0), axis=1))])
        # profile normals (outward in r-z), sharp at corners: use per-edge normals
        area = 0.5 * np.sum(prof[:, 0] * np.roll(prof[:, 1], -1) - np.roll(prof[:, 0], -1) * prof[:, 1])
        for k in range(m):
            a, b = prof[k], prof[(k + 1) % m]
            e = b - a
            nrz = np.array([e[1], -e[0]]) if area > 0 else np.array([-e[1], e[0]])
            nrz /= np.linalg.norm(nrz)
            for s in range(seg):
                t0, t1 = 2 * math.pi * s / seg, 2 * math.pi * (s + 1) / seg
                def P(rz, t):
                    return (rz[0] * math.cos(t), rz[0] * math.sin(t), rz[1])
                def N(t):
                    return np.array([nrz[0] * math.cos(t), nrz[0] * math.sin(t), nrz[1]])
                u0, u1 = s / seg, (s + 1) / seg
                v0, v1 = per[k] / per[-1], per[k + 1] / per[-1]
                vv = lambda u, v: np.array([u, (v + li) / len(loops)])
                A, B, C, D = P(a, t0), P(a, t1), P(b, t1), P(b, t0)
                kd = "recess" if (a[0] <= spec.rivet_hole_r + 1e-6 and b[0] <= spec.rivet_hole_r + 1e-6) else ""
                lc = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
                mb.tri([A, B, C], [vv(u0, v0), vv(u1, v0), vv(u1, v1)], [N(t0), N(t1), N(t1)], "pivot", slot, "rivet",
                       f"rivet_{li}", locs=[lc[0], lc[1], lc[2]], kind=kd)
                mb.tri([A, C, D], [vv(u0, v0), vv(u1, v1), vv(u0, v1)], [N(t0), N(t1), N(t0)], "pivot", slot, "rivet",
                       f"rivet_{li}", locs=[lc[0], lc[2], lc[3]], kind=kd)


# =========================================================================== sticks atlas
@dataclass
class StickIsland:
    key: str
    lo: np.ndarray
    hi: np.ndarray
    offset: np.ndarray = field(default_factory=lambda: np.zeros(2))
    flip: bool = False


def pack_shelves(sizes: List[Tuple[str, float, float]], pad_mm: float, width_mm: float):
    """Shelf packer: (key, w, h) -> {key: (x, y)} and total height."""
    order = sorted(sizes, key=lambda s: -s[2])
    pos, x, y, row_h = {}, pad_mm, pad_mm, 0.0
    for key, w, h in order:
        if x + w + pad_mm > width_mm:
            x = pad_mm
            y += row_h + pad_mm
            row_h = 0.0
        pos[key] = (x, y)
        x += w + pad_mm
        row_h = max(row_h, h)
    return pos, y + row_h + pad_mm


# =========================================================================== the whole LOD
def build_lod(spec: FanSpec, lod: int, tpl: FF.LeafTemplate, stick_atlas=None):
    """Return (FanMesh, info).  ``stick_atlas`` from LOD0 is reused so every LOD samples the same maps."""
    plan = LOD_PLANS[lod]
    mb = FanMesh(["pivot"] + [f"stick_{i:02d}" for i in range(spec.n_sticks)]
                 + [f"leaf_{j:02d}" for j in range(2 * (spec.n_sticks - 1))])
    widen = rib1_widening(spec)
    widen24 = rib24_widening(spec)
    outlines = {}
    for i in range(spec.n_sticks):
        if i == 0:
            outlines[i] = guard_outline(spec, "front", plan)
        elif i == spec.n_sticks - 1:
            outlines[i] = guard_outline(spec, "rear", plan)
        else:
            outlines[i] = rib_outline(spec, i, plan, widen if i == 1 else None,
                                      widen24 if i == spec.n_sticks - 2 else None)
    # the stick atlas: islands per stick (top, bottom) and a wall strip, sized from LOD0's outlines
    if stick_atlas is None:
        sizes = []
        for i, poly in outlines.items():
            lo, hi = poly.min(0), poly.max(0)
            w, h = hi[0] - lo[0], hi[1] - lo[1]
            sizes += [(f"s{i}_top", w, h), (f"s{i}_bot", w, h)]
            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
            z0, z1 = spec.stick_z(i)
            nch = int(math.ceil(per * 1.06 / WALL_CHUNK_MM))
            for c in range(nch):
                sizes.append((f"s{i}_wall{c}", per * 1.06 / nch + 3.0, (z1 - z0) + 0.2))
            sizes.append((f"s{i}_hole", 8 * 0.5 + 1.0, (z1 - z0) + 0.2))
        sp = spacer_outline(spec, plan)
        lo_, hi_ = sp.min(0), sp.max(0)
        z0s, z1s = spacer_z(spec)
        sp_per = float(np.sum(np.linalg.norm(np.diff(np.vstack([sp, sp[:1]]), axis=0), axis=1)))
        sizes += [("sp_top", hi_[0] - lo_[0], hi_[1] - lo_[1]), ("sp_bot", hi_[0] - lo_[0], hi_[1] - lo_[1]),
                  ("sp_wall0", sp_per * 1.06 + 3.0, (z1s - z0s) + 0.2), ("sp_hole", 8 * 0.5 + 1.0, (z1s - z0s) + 0.2)]
        for i in range(spec.n_sticks - 1):
            pp = prong_outline(spec, i, 0)
            lo_p, hi_p = pp.min(0), pp.max(0)
            z0p, z1p = prong_z(spec, i)
            per_p = float(np.sum(np.linalg.norm(np.diff(np.vstack([pp, pp[:1]]), axis=0), axis=1)))
            sizes += [(f"p{i}_top", hi_p[0] - lo_p[0], hi_p[1] - lo_p[1]), (f"p{i}_bot", hi_p[0] - lo_p[0], hi_p[1] - lo_p[1]),
                      (f"p{i}_wall0", per_p * 1.06 + 3.0, (z1p - z0p) + 0.2)]
        stick_atlas = _fit_atlas(sizes, spec.texture_size, 8)
        stick_atlas["prong_lo"] = {i: prong_outline(spec, i, 0).min(0) for i in range(spec.n_sticks - 1)}
        stick_atlas["prong_per0"] = {i: float(np.sum(np.linalg.norm(np.diff(np.vstack([prong_outline(spec, i, 0),
                                                                                        prong_outline(spec, i, 0)[:1]]),
                                                                              axis=0), axis=1)))
                                     for i in range(spec.n_sticks - 1)}
        stick_atlas["sp_lo"] = lo_
        stick_atlas["sp_per0"] = sp_per
        stick_atlas["lo"] = {i: outlines[i].min(0) for i in outlines}
        stick_atlas["lo"]["sp"] = stick_atlas["sp_lo"]
        stick_atlas["sp_wall_scale"] = {}
        stick_atlas["chunks"] = {i: sum(1 for k in stick_atlas["pos"] if k.startswith(f"s{i}_wall")) for i in outlines}
        stick_atlas["wall_len"] = {i: float(np.sum(np.linalg.norm(np.diff(np.vstack([outlines[i], outlines[i][:1]]),
                                                                            axis=0), axis=1))) for i in outlines}
    at = stick_atlas
    _sp = spacer_outline(spec, plan)
    at["sp_wall_scale"][lod] = at["sp_per0"] / float(np.sum(np.linalg.norm(np.diff(np.vstack([_sp, _sp[:1]]), axis=0),
                                                                             axis=1)))
    s_px = at["ppmm"]
    tex = spec.texture_size

    def to_uv(key, x, y):
        ox, oy = at["pos"][key]
        return np.array([(ox + x) * s_px / tex, (oy + y) * s_px / tex])
    for i, poly in outlines.items():
        z0, z1 = spec.stick_z(i)
        deg = spec.stick_axis_deg(i, 1.0)
        lo = at["lo"][i]
        ktop, kbot, kwall = f"s{i}_top", f"s{i}_bot", f"s{i}_wall"
        uv_top = (lambda q, kt=ktop, lo=lo: to_uv(kt, q[0] - lo[0], q[1] - lo[1]))
        uv_bot = (lambda q, kb=kbot, lo=lo: to_uv(kb, q[0] - lo[0], q[1] - lo[1]))
        uv_wall = (lambda ch, perim, zz, i=i, z0=z0: to_uv(f"s{i}_wall{ch}", 0.5 + perim, 0.1 + (zz - z0)))
        uv_hole = (lambda perim, zz, i=i, z0=z0: to_uv(f"s{i}_hole", 0.5 + perim, 0.1 + (zz - z0)))
        chamfer = spec.guard_edge_round_mm if (plan.guard_chamfer and i in (0, spec.n_sticks - 1)) else 0.0
        hole_seg = plan.hole_seg
        hole_r = (0.5 * spec.rivet_shaft_d_mm + 0.05) / math.cos(math.pi / max(hole_seg, 3))
        nch = at["chunks"][i]
        if lod == 0:
            _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                     uv_top, uv_bot, uv_wall, n_chunks=nch, uv_hole=uv_hole)
        else:
            # coarse LODs: the whole wall squeezed into LOD0's first wall island (no extra cut vertices)
            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
            _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                     uv_top, uv_bot, uv_wall, n_chunks=1, uv_hole=uv_hole,
                     wall_scale=(at["wall_len"][i] / nch) / per)
    # the spacer under the front guard (its own atlas islands)
    sp = spacer_outline(spec, plan)
    z0s, z1s = spacer_z(spec)
    lo_sp = at["lo"]["sp"]
    _extrude(mb, sp, (0.5 * spec.rivet_shaft_d_mm + 0.05) / math.cos(math.pi / max(plan.hole_seg, 3)), plan.hole_seg,
             z0s, z1s, 0.0, "stick_00", "stick_00", 0.0,
             lambda q: to_uv("sp_top", q[0] - lo_sp[0], q[1] - lo_sp[1]),
             lambda q: to_uv("sp_bot", q[0] - lo_sp[0], q[1] - lo_sp[1]),
             lambda ch, perim, zz: to_uv("sp_wall0", 0.5 + perim, 0.1 + (zz - z0s)), n_chunks=1,
             uv_hole=lambda perim, zz: to_uv("sp_hole", 0.5 + perim, 0.1 + (zz - z0s)),
             wall_scale=at["sp_wall_scale"][lod])
    # round 3: the leaf-zone prongs (their own atlas islands; kinds prong_top / prong_bottom for the painter)
    for i in range(spec.n_sticks - 1):
        pp = prong_outline(spec, i, lod)
        z0p, z1p = prong_z(spec, i)
        lo_p = at["prong_lo"][i]
        per = float(np.sum(np.linalg.norm(np.diff(np.vstack([pp, pp[:1]]), axis=0), axis=1)))
        _extrude(mb, pp, 0.0, 0, z0p, z1p, spec.stick_axis_deg(i, 1.0), f"stick_{i:02d}", f"stick_{i:02d}", 0.0,
                 lambda q, i=i, lo=lo_p: to_uv(f"p{i}_top", q[0] - lo[0], q[1] - lo[1]),
                 lambda q, i=i, lo=lo_p: to_uv(f"p{i}_bot", q[0] - lo[0], q[1] - lo[1]),
                 lambda ch, perim, zz, i=i, z0=z0p: to_uv(f"p{i}_wall0", 0.5 + perim, 0.1 + (zz - z0)), n_chunks=1,
                 wall_scale=at["prong_per0"][i] / per, kinds=("prong_top", "prong_bottom", "prong_wall"), layer="prong")
    # the prong's skin: rigid with stick i along its - edge, with stick i+1 along its + edge, blended by angle between
    # (so it shortens with its gap as the fan closes and, closed, lies 0.9 - 1.2 mm beside its leaf line, inside the
    # guards: a rigid prong would stand ~9 mm proud of the closed stack).  Its + edge keeps its place over the next
    # leaf line and its - edge its place beside its own, which is all the fold argument needs (FanSpec.prong_*)

    leaf_info = build_leaf(mb, spec, tpl, lod)
    build_rivet(mb, spec, plan)
    prong_w = _prong_weights(spec, mb)
    if prong_w:
        mb.W = [prong_w.get(v) or [(mb.bone_names[b], 1.0)] for v, b in enumerate(mb.B)]
    info = {"lod": lod, "triangles": mb.triangles(), "vertices": len(mb.P), "parts": mb.part_triangles(),
            **leaf_info, "stick_ppmm": round(s_px, 4)}
    return mb, info, stick_atlas


def _fit_atlas(sizes, tex, pad_px):
    lo, hi = 1.0, 40.0
    best = None
    for _ in range(40):
        s = 0.5 * (lo + hi)
        pad = pad_px / s
        pos, H = pack_shelves(sizes, pad, tex / s)
        if H <= tex / s:
            lo, best = s, (s, pos, H)
        else:
            hi = s
    s, pos, H = best
    return {"ppmm": s, "pos": pos, "fill_height_mm": H}


__all__ = ["FanMesh", "build_lod", "LOD_PLANS", "prong_outline", "prong_z", "skin", "prong_edge_angles", "leaf_faces", "front_guard_edges", "guard_outline", "rib_outline",
           "SLOTS", "LEAF_BACK_OFFSET_MM", "leaf_corners", "leaf_uv_layout"]
