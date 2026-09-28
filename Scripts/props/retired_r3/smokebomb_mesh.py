#!/usr/bin/env python
"""props_lib.smokebomb_mesh - SM_SmokeBomb's surface, built strip by strip.

numpy + mathutils (the CDT); no bpy.  ``build_lod`` returns plain arrays that
``props_lib.smokebomb_geometry`` turns into a Blender mesh.

THE SURFACE
-----------
Every strip S (``smokebomb_strips.Strip``) is meshed in its OWN chart (s, w): s in mm
along the tape, w in mm across it.  The part of S that gets geometry - a PIECE - is

    inside S                                  (S's own two edges)
    and not deeper than MARGIN_MM inside any strip that lies OVER S at that point

so a piece runs on for MARGIN_MM under whatever covers it.  That boundary is extracted
with marching squares on

    F = max(-d_S, max over higher T of (d_T - MARGIN_MM))          F < 0: in the piece

on a fine chart raster, simplified, and triangulated with Blender's constrained
Delaunay triangulation (``mathutils.geometry.delaunay_2d_cdt``), never bmesh.ops.bevel.

Every vertex sits at the tape's HEIGHT (``smokebomb_strips.sheet_layers``): the base
spheroid plus one tape thickness for S itself and one, ramped over DRAPE_MM, for each
strip S lies on.  Along each of S's OWN edges that is exposed, a WALL (skirt) drops from
S's surface to below the surface S lies on, so every overlap is a real step: at the
silhouette the ball's outline steps where an edge crosses the limb, exactly as the
reference's does (REFERENCE_SPEC 1 and 5; the kunai lesson).

The walls are open-bottomed and the pieces overlap under their covers: the shell is a set
of layered sheets, not one closed manifold.  qa_check allows boundary edges and requires
no coincident vertices, and none can occur: every vertex is created through a 1 nm
position-keyed factory, so the only shared positions are the deliberate ones (cuts
across a strip, welded).

UV0
---
Analytic: a vertex's UV is its chart (s, w) scaled to the atlas' px/mm and translated to
its island.  u runs ALONG the tape, so the warp threads lie on texel rows at every LOD.
A wall is unfolded onto its piece's island, beyond the edge it hangs from (the kunai's
lightmap lesson: no sub-texel islands).  All three LODs use the same chart, cuts and
island placement, so a texel means the same point of tape on every LOD.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

MM = 0.001

# --------------------------------------------------------------------------- build-to numbers
#: study 4 (DERIVED, reference 0.26-0.78 mm steps): one tape thickness
TAPE_T_MM = 0.55
#: a tape bridging a buried edge drapes over this width instead of stepping
DRAPE_MM = 1.6
#: only the top layers carry height (study 4): full thickness up to KNEE layers, then this
STACK_KNEE = 4.0
STACK_ABOVE = 0.6
#: a piece runs on this far under whatever covers it (larger than LOD2's chordal error)
MARGIN_MM = 1.2
#: walls drop this far below the surface they stand on (hidden inside it)
SKIRT_MM = 0.30
#: the chart is measured on this radius (smokebomb_layout.CHART_RADIUS_MM)
CHART_R_MM = 35.0
#: a tape is not a flat card: it crowns across its width and rolls down to its edges,
#: which is what makes each band read as a soft cushion in the reference (REFERENCE_SPEC
#: 5: "every over-strip edge reads as a rolled, fuzzy rim").  Geometry carries the crown;
#: the normal map carries the 0.27 mm bead at the very edge.
CROWN_MM = 0.80
CROWN_REACH_MM = 1.5
#: < 1 flattens the arch's top and steepens its shoulders
CROWN_SHAPE = 0.7
CROWN_PER_HALF_WIDTH = 0.30
#: an exposed strip's crown dips to nothing over this distance before a covering edge
DIP_MM = 1.3
#: the rolled selvedge bead at every exposed edge (geometry; the maps add its texture)
BEAD_MM = 0.60
BEAD_W_MM = 0.7


@dataclass
class LodParams:
    level: int
    ds: float           # chart raster step along (mm)
    dw: float           # chart raster step across (mm)
    tol: float          # boundary simplification tolerance (mm)
    edge_seg: float     # longest boundary segment (mm)
    grid_s: float       # interior sample spacing along (mm)
    grid_w: float       # interior sample spacing across (mm)
    walls: bool = True
    rows_wide: Tuple[float, ...] = (-0.72, -0.36, 0.0, 0.36, 0.72)
    rows_mid: Tuple[float, ...] = (-0.6, 0.0, 0.6)
    row_clear_mm: float = 0.9


LODS = (
    # LOD0: 0.10 mm boundary tolerance (1.3 px at the reference framing; the fray lives in
    # the maps), 4.5 mm segments, four arch rows across a wide tape
    LodParams(0, ds=0.30, dw=0.10, tol=0.10, edge_seg=4.5, grid_s=4.5, grid_w=3.6,
              rows_wide=(-0.66, -0.22, 0.22, 0.66), rows_mid=(-0.45, 0.45)),
    # LOD1: study 6.3 - walls removed (the step becomes a slope: 0.27 px at the switch),
    # 8 mm segments, one arch row
    LodParams(1, ds=0.30, dw=0.10, tol=0.20, edge_seg=8.5, grid_s=8.0, grid_w=8.0, walls=False,
              rows_wide=(-0.5, 0.0, 0.5), rows_mid=(0.0,), row_clear_mm=1.6),
)
#: LOD2 is a geodesic RESAMPLE of the same surface (``resample_lod``), frequency 5:
#: 500 triangles, ~7 mm edges (study 6.3: 400 - 800 at 14 - 16 mm; 27 px at the switch)
LOD2_FREQUENCY = 5


# =========================================================================== shape
@dataclass
class Shape:
    """The base surface the tape lies on: a slightly lumpy ball (mm).

    ``profile`` is the outline's relative deviation (fraction of R) at the centres of
    twelve 30 deg IMAGE-angle sectors (15, 45, ... 345 deg), interpolated periodically:
    REFERENCE_SPEC 1's flat upper-right and lower-left and full upper-left, applied as a
    gentle modulation of the core the tape is wound on.
    """
    base_mm: float = 33.2
    profile: Tuple[float, ...] = (0.0,) * 12

    def radius(self, P_cam: np.ndarray) -> np.ndarray:
        P = np.asarray(P_cam, np.float64)
        r = np.full(P.shape[:-1], self.base_mm)
        if any(abs(v) > 0 for v in self.profile):
            th = np.degrees(np.arctan2(P[..., 1], P[..., 0])) % 360.0
            knots = [(15.0 + 30.0 * i, v) for i, v in enumerate(self.profile)]
            k = SS.periodic_spline(knots, th)
            r = r * (1.0 + k)
        return r


# =========================================================================== marching squares
_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0))   # cell corners 0=(i,j) 1=(i,j+1) 2=(i+1,j+1) 3=(i+1,j)


def marching_squares(F: np.ndarray, xs: np.ndarray, ys: np.ndarray):
    """Iso-0 segments of F (rows = y, cols = x), F < 0 inside, on grid coordinates xs, ys.

    Returns (points (K, 2) in (x, y), segments (M, 2) indices into points).  Points are
    keyed by the grid EDGE they lie on, so neighbouring cells share them exactly.
    """
    H, W = F.shape
    inside = F < 0.0
    c0 = inside[:-1, :-1]
    c1 = inside[:-1, 1:]
    c2 = inside[1:, 1:]
    c3 = inside[1:, :-1]
    code = c0.astype(np.int32) | (c1.astype(np.int32) << 1) | (c2.astype(np.int32) << 2) | (c3.astype(np.int32) << 3)
    I, J = np.nonzero((code != 0) & (code != 15))
    pts: Dict[Tuple[int, int, int], int] = {}
    coords: List[Tuple[float, float]] = []
    segs: List[Tuple[int, int]] = []

    def corner(i, j, k):
        return [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)][k]

    def edge_point(i, j, e):
        a, b = _EDGES[e]
        (ia, ja), (ib, jb) = corner(i, j, a), corner(i, j, b)
        # a canonical key: horizontal edge (row, col) or vertical edge
        if ia == ib:
            key = (0, ia, min(ja, jb))
        else:
            key = (1, min(ia, ib), ja)
        idx = pts.get(key)
        if idx is not None:
            return idx
        fa, fb = F[ia, ja], F[ib, jb]
        t = fa / (fa - fb) if fa != fb else 0.5
        t = min(max(t, 0.0), 1.0)
        xa, ya = xs[ja], ys[ia]
        xb, yb = xs[jb], ys[ib]
        # exact grid nodes stay exact (a cut column must give identical points to the
        # sub-charts on both sides of it)
        if t == 0.0:
            coords.append((xa, ya))
        elif t == 1.0:
            coords.append((xb, yb))
        else:
            coords.append((xa + (xb - xa) * t, ya + (yb - ya) * t))
        idx = len(coords) - 1
        pts[key] = idx
        return idx

    # segment table: which cell edges connect, per case (inside = bit set)
    table = {
        1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 6: [(0, 2)], 7: [(3, 2)],
        8: [(2, 3)], 9: [(2, 0)], 11: [(2, 1)], 12: [(1, 3)], 13: [(1, 0)], 14: [(0, 3)],
    }
    for i, j, c in zip(I.tolist(), J.tolist(), code[I, J].tolist()):
        if c in (5, 10):
            centre = 0.25 * (F[i, j] + F[i, j + 1] + F[i + 1, j + 1] + F[i + 1, j])
            if c == 5:
                pairs = [(3, 2), (1, 0)] if centre >= 0 else [(3, 0), (1, 2)]
            else:
                pairs = [(0, 3), (2, 1)] if centre >= 0 else [(0, 1), (2, 3)]
        else:
            pairs = table[c]
        for ea, eb in pairs:
            segs.append((edge_point(i, j, ea), edge_point(i, j, eb)))
    return np.array(coords, np.float64).reshape(-1, 2), np.array(segs, np.int64).reshape(-1, 2)


def chain(segs: np.ndarray) -> List[List[int]]:
    """Chain segments into polylines (closed loops repeat their first index at the end)."""
    nxt: Dict[int, List[int]] = {}
    for a, b in segs.tolist():
        nxt.setdefault(a, []).append(b)
        nxt.setdefault(b, []).append(a)
    seen = set()
    loops = []
    for start in list(nxt.keys()):
        if start in seen:
            continue
        # walk from an endpoint if the chain is open
        cur = start
        path = [cur]
        seen.add(cur)
        prev = None
        while True:
            cand = [n for n in nxt[cur] if n != prev and (n not in seen or (n == path[0] and len(path) > 2))]
            if not cand:
                break
            n = cand[0]
            if n == path[0]:
                path.append(n)
                break
            path.append(n)
            seen.add(n)
            prev, cur = cur, n
        loops.append(path)
    return loops


def rdp(P: np.ndarray, tol: float) -> np.ndarray:
    """Ramer-Douglas-Peucker; returns the indices kept (always both ends)."""
    n = len(P)
    if n < 3:
        return np.arange(n)
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = P[b] - P[a]
        L2 = float(seg @ seg)
        rel = P[a + 1:b] - P[a]
        if L2 < 1e-18:
            d = np.linalg.norm(rel, axis=1)
        else:
            d = np.abs(rel[:, 0] * seg[1] - rel[:, 1] * seg[0]) / math.sqrt(L2)
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack.append((a, m))
            stack.append((m, b))
    return np.nonzero(keep)[0]


# =========================================================================== one strip
@dataclass
class Piece:
    strip: int
    name: str
    sub: int                     # sub-chart index along the strip
    uv_mm: np.ndarray            # (V, 2) chart (s, w) of every vertex, before packing
    verts_cam: np.ndarray        # (V, 3) unit directions
    radius_mm: np.ndarray        # (V,) radius
    tris: np.ndarray             # (T, 3) indices into this piece's vertices
    wall: np.ndarray             # (V,) bool: a wall-bottom vertex
    edge_vert: np.ndarray        # (V,) bool: on an own exposed edge (wall top)
    sharp: List[Tuple[int, int]] = field(default_factory=list)
    bbox_mm: Tuple[float, float, float, float] = (0, 0, 0, 0)
    area_mm2: float = 0.0
    comp: int = 0


def crown_profile(f: SS.Field) -> np.ndarray:
    """(S, N) crown of every strip at every point: a soft arch across the tape, highest on
    its centre line and rolling down to both edges (the reference's bands read as padded
    tubes, lit on one flank and shaded on the other)."""
    hw = np.maximum(f.half_width, 0.5)
    d = np.clip(f.d, 0.0, None)
    t = np.clip(d / hw, 0.0, 1.0)
    # a narrow tape arches less than a wide one
    arch = np.minimum(CROWN_MM, CROWN_PER_HALF_WIDTH * hw) * (1.0 - (1.0 - t) ** 2) ** CROWN_SHAPE
    # the rolled selvedge: the tape's edge is a thicker bead (REFERENCE_SPEC 5, "every
    # over-strip edge reads as a rolled, fuzzy rim"), and it is what lifts the step where
    # an edge crosses the limb to the reference's 4 - 8.5 px
    bead = BEAD_MM * np.exp(-(d / BEAD_W_MM) ** 2) * (f.d > -0.05)
    return arch + bead


class Model:
    """The strips plus the base shape: everything the mesh and the texture ask about."""

    def __init__(self, strips: Sequence[SS.Strip], shape: Shape):
        self.strips = list(strips)
        self.shape = shape
        self.names = [s.name for s in self.strips]

    def field(self, P: np.ndarray) -> SS.Field:
        return SS.evaluate_field(self.strips, P, CHART_R_MM)

    def layers(self, f: SS.Field, which: np.ndarray) -> np.ndarray:
        return SS.sheet_layers(f, which, DRAPE_MM, STACK_KNEE, STACK_ABOVE)

    def height_mm(self, P: np.ndarray, which: np.ndarray, f: Optional[SS.Field] = None) -> np.ndarray:
        """base + one tape thickness per layer (compressed below the top few) + the strip's
        OWN crown, which dips to nothing where a higher strip covers it.

        Crowns are not inherited: a tape pressed under another lies flat, so a deep
        strip's arch can never poke through the strip on it (it10), and the arches do not
        pile up into a lumpy outline (it11).  The dip is also what the reference shows at
        every crossing: the under-strip rolls down INTO the crevice at the upper strip's
        edge (REFERENCE_SPEC 5, the occlusion crevice)."""
        f = f if f is not None else self.field(P)
        N = P.shape[0]
        j = np.arange(N)
        wr = f.rank[which, j]
        higher = f.rank > wr[None, :]
        higher[which, j] = False
        dc = np.where(higher, f.d, -1e3).max(axis=0)
        expose = np.clip(-dc / DIP_MM, 0.0, 1.0)
        expose = expose * expose * (3.0 - 2.0 * expose)
        own = crown_profile(f)[which, j] * expose
        return self.shape.radius(P) + TAPE_T_MM * self.layers(f, which) + own

    def below_mm(self, P: np.ndarray, which: np.ndarray, f: Optional[SS.Field] = None) -> np.ndarray:
        """Height of the surface directly under strip ``which[j]`` at P[j] (base if none)."""
        f = f if f is not None else self.field(P)
        N = P.shape[0]
        j = np.arange(N)
        wr = f.rank[which, j]
        cand = np.where((f.d >= -0.15) & (f.rank < wr[None, :]), f.rank, -np.inf)
        cand[which, j] = -np.inf
        u = np.argmax(cand, axis=0)
        has = np.isfinite(cand.max(axis=0))
        h = self.shape.radius(P).copy()
        if has.any():
            hu = self.height_mm(P[has], u[has], _subfield(f, has))
            h[has] = hu
        return h


def _subfield(f: SS.Field, mask: np.ndarray) -> SS.Field:
    return SS.Field(f.names, f.d[:, mask], f.rank[:, mask], f.s[:, mask], f.w[:, mask],
                    f.lift[:, mask], f.top[mask], f.covered[:, mask],
                    None if f.half_width is None else f.half_width[:, mask])


def strip_chart(model: Model, k: int, lod: LodParams, s_range=None):
    """The chart raster of strip k: s (along) and w (across) grids and F."""
    st = model.strips[k]
    sa, sb = s_range if s_range is not None else st.s_range_mm(CHART_R_MM)
    lam = st._lam
    # the strip's widest extent across, plus room for the margin
    lo, hi, c = st.at(lam)
    half = (hi - lo) * 0.5 * SS.DEG * CHART_R_MM
    wmax = float(half.max()) + 1.0
    s = np.arange(sa, sb + lod.ds * 0.5, lod.ds)
    w = np.arange(-wmax, wmax + lod.dw * 0.5, lod.dw)
    SG, WG = np.meshgrid(s, w)                    # rows = w, cols = s
    P = st.chart_to_cam(SG.ravel(), WG.ravel(), CHART_R_MM)
    return s, w, P


def piece_field(model: Model, k: int, P: np.ndarray, f: Optional[SS.Field] = None):
    """own = -d_S, cut = max over higher T of (d_T - MARGIN); F = max(own, cut)."""
    f = f if f is not None else model.field(P)
    own = -f.d[k]
    r = f.rank[k]
    higher = f.rank > r[None, :]
    higher[k] = False
    cut = np.where(higher, f.d - MARGIN_MM, -1e3).max(axis=0)
    return own, cut, f


__all__ = ["TAPE_T_MM", "DRAPE_MM", "STACK_KNEE", "STACK_ABOVE", "MARGIN_MM", "SKIRT_MM",
           "CHART_R_MM", "LodParams", "LODS", "Shape", "Model", "Piece", "marching_squares",
           "chain", "rdp", "strip_chart", "piece_field"]


# =========================================================================== cuts across a strip
#: a UV island is never longer than this along the tape (the atlas is 2048 px)
MAX_ISLAND_MM = 96.0


@dataclass
class StripPlan:
    """Where one strip is cut into sub-charts: shared by every LOD."""
    k: int
    s0: float                    # chart start (mm); closed strips run s0 .. s0 + length
    length: float
    cuts: List[float]            # interior cut positions (absolute s, mm), sorted
    occupancy: Optional[np.ndarray] = None

    def ranges(self) -> List[Tuple[float, float]]:
        edges = [self.s0] + list(self.cuts) + [self.s0 + self.length]
        return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def plan_strip(model: Model, k: int, lod: LodParams) -> StripPlan:
    """Choose the chart start and the cuts from where the strip actually has geometry."""
    st = model.strips[k]
    sa, sb = st.s_range_mm(CHART_R_MM)
    s, w, P = strip_chart(model, k, lod)
    own, cut, _ = piece_field(model, k, P)
    F = np.maximum(own, cut).reshape(len(w), len(s))
    occ = (F < 0).sum(axis=0) * lod.dw                       # mm of width in the piece
    length = float(sb - sa)
    if st.closed:
        # start the loop where the strip has the least geometry (ideally none); the last
        # column duplicates the first (periodic), so it is left out
        j0 = int(np.argmin(occ[:-1]))
        s0 = float(s[j0])
        order = (np.arange(len(s) - 1) + j0) % (len(s) - 1)
    else:
        j0 = 0
        s0 = float(sa)
        order = np.arange(len(s))
    occ_r = occ[order]
    s_r = s0 + np.arange(len(order)) * lod.ds
    cuts: List[float] = []
    run_start = None
    for i in range(len(occ_r) + 1):
        busy = i < len(occ_r) and occ_r[i] > 0
        if busy and run_start is None:
            run_start = i
        if (not busy) and run_start is not None:
            _split_run(occ_r, s_r, run_start, i, cuts, lod)
            run_start = None
    cuts = sorted(c for c in cuts if s0 < c < s0 + length)
    return StripPlan(k, s0, length, cuts, occ_r)


def _split_run(occ, s, a, b, cuts, lod):
    span = (b - a) * lod.ds
    if span <= MAX_ISLAND_MM:
        return
    n = int(math.ceil(span / MAX_ISLAND_MM))
    for q in range(1, n):
        target = a + int(round((b - a) * q / n))
        lo = max(a + 1, target - int(0.18 * (b - a) / n))
        hi = min(b - 1, target + int(0.18 * (b - a) / n))
        j = lo + int(np.argmin(occ[lo:hi + 1]))
        cuts.append(float(s[j]))


# =========================================================================== meshing
@dataclass
class _Loop:
    pts: np.ndarray       # (n, 2) chart (s, w), closed (last != first)
    cls: np.ndarray       # (n,) 0 own edge, 1 under a cover, 2 cut line


def _classify(pts, own_i, cut_i, s_cuts):
    cls = np.where(own_i >= cut_i, 0, 1)
    for sc in s_cuts:
        cls = np.where(np.abs(pts[:, 0] - sc) < 1e-7, 2, cls)
    return cls


#: a run of boundary shorter than this (mm) between two runs of another class is noise
#: where a strip's own edge and a cover's margin nearly coincide; it is merged
DEBOUNCE_MM = 0.8


def _debounce(P: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Merge short class runs: an 'under cover' (1) run shorter than DEBOUNCE_MM becomes
    own edge (0) - a wall under a cover is hidden, a zig-zag of tiny walls is not - and a
    short own-edge run between two cover runs becomes cover.  Cut lines (2) never move."""
    n = len(C)
    if n < 4:
        return C
    seg = np.linalg.norm(np.roll(P, -1, axis=0) - P, axis=1)
    for _ in range(3):
        change = np.nonzero(C != np.roll(C, 1))[0]
        if len(change) < 2:
            break
        runs = []
        for i, a in enumerate(change):
            b = change[(i + 1) % len(change)]
            idx = np.arange(a, a + ((b - a) % n or n)) % n
            runs.append(idx)
        changed = False
        for idx in runs:
            c = C[idx[0]]
            if c == 2:
                continue
            L = float(seg[idx].sum())
            if L < DEBOUNCE_MM:
                prev_c = C[(idx[0] - 1) % n]
                next_c = C[(idx[-1] + 1) % n]
                if c == 1 and 2 not in (prev_c, next_c):
                    C[idx] = 0
                    changed = True
                elif c == 0 and prev_c == 1 and next_c == 1:
                    C[idx] = 1
                    changed = True
        if not changed:
            break
    return C


def _simplify_loop(loop: _Loop, lod: LodParams) -> _Loop:
    """RDP per run of one class, then subdivide long segments; run ends are kept.

    A vertex's class is the class of the run that STARTS at it, so the segment from a
    vertex to the next one belongs to that vertex's run.
    """
    P, C = loop.pts, loop.cls
    n = len(P)
    change = np.nonzero(C != np.roll(C, 1))[0]
    start = int(change[0]) if len(change) else 0
    P = np.roll(P, -start, axis=0)
    C = np.roll(C, -start)
    runs = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and C[j + 1] == C[i]:
            j += 1
        runs.append((i, j))
        i = j + 1
    out_p, out_c = [], []
    for ri, (a, b) in enumerate(runs):
        nxt = runs[(ri + 1) % len(runs)][0]
        idx = list(range(a, b + 1)) + [nxt]
        seg = P[idx]
        cls = int(C[a])
        if cls == 2:
            keep = np.array([0, len(seg) - 1])              # a cut line is straight
        else:
            keep = rdp(seg, lod.tol if cls == 0 else lod.tol * 2.0)
        kept = seg[keep]
        limit = lod.edge_seg if cls != 1 else lod.edge_seg * 1.6
        for q in range(len(kept) - 1):
            p0, p1 = kept[q], kept[q + 1]
            L = float(np.linalg.norm(p1 - p0))
            m = max(1, int(math.ceil(L / limit - 1e-9)))
            for t in range(m):
                out_p.append(p0 + (p1 - p0) * (t / m))
                out_c.append(cls)
    P2 = np.array(out_p)
    C2 = np.array(out_c)
    d = np.linalg.norm(P2 - np.roll(P2, 1, axis=0), axis=1)
    keep = d > 1e-9
    return _Loop(P2[keep], C2[keep])


def _loop_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _bilinear(F, s, w, qs, qw):
    ds = s[1] - s[0]
    dw = w[1] - w[0]
    fx = np.clip((qs - s[0]) / ds, 0, len(s) - 1.000001)
    fy = np.clip((qw - w[0]) / dw, 0, len(w) - 1.000001)
    j = np.floor(fx).astype(int)
    i = np.floor(fy).astype(int)
    tx = fx - j
    ty = fy - i
    return ((1 - tx) * (1 - ty) * F[i, j] + tx * (1 - ty) * F[i, j + 1]
            + (1 - tx) * ty * F[i + 1, j] + tx * ty * F[i + 1, j + 1])


def _in_loops(Q: np.ndarray, loops) -> np.ndarray:
    """Even-odd inside test of points Q (n, 2) against a component's loops (outer + holes)."""
    inside = np.zeros(len(Q), bool)
    x, y = Q[:, 0], Q[:, 1]
    for lp in loops:
        P = lp.pts
        x1, y1 = P[:, 0], P[:, 1]
        x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
        for a, b, c, d in zip(x1, y1, x2, y2):
            cross = (b > y) != (d > y)
            xi = a + (y - b) * (c - a) / np.where(d != b, d - b, 1e-30)
            inside ^= cross & (xi > x)
    return inside


def _point_in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def mesh_strip(model: Model, plan: StripPlan, lod: LodParams, min_area_mm2: float = 0.4) -> List[Piece]:
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    k = plan.k
    st = model.strips[k]
    lo, hi, _ = st.at(st._lam)
    half = float(((hi - lo) * 0.5 * SS.DEG * CHART_R_MM).max()) + 1.0
    pieces: List[Piece] = []
    for sub, (sa, sb) in enumerate(plan.ranges()):
        # a raster whose columns land EXACTLY on sa and sb (a cut must hit grid nodes,
        # so both sides of it produce the same vertices)
        n_in = max(2, int(round((sb - sa) / lod.ds)))
        ds = (sb - sa) / n_in
        s = sa + ds * np.arange(-2, n_in + 3)
        s[2] = sa
        s[-3] = sb
        w = np.arange(-half, half + lod.dw * 0.5, lod.dw)
        SG, WG = np.meshgrid(s, w)
        P = st.chart_to_cam(SG.ravel(), WG.ravel(), CHART_R_MM)
        own, cut, _f = piece_field(model, k, P)
        own = own.reshape(len(w), len(s))
        cut = cut.reshape(len(w), len(s))
        F = np.maximum(own, cut)
        # the sub-chart walls: exactly zero on the cut columns, positive beyond
        wall = np.maximum(sa - SG, SG - sb)
        F = np.where(wall >= -1e-9, np.maximum(F, np.maximum(wall, 0.0) * 50.0), F)
        F[:, :2] = np.maximum(F[:, :2], 1.0)
        F[:, -2:] = np.maximum(F[:, -2:], 1.0)
        F[:, 2] = np.maximum(F[:, 2], 0.0)
        F[:, -3] = np.maximum(F[:, -3], 0.0)
        F[0, :] = F[-1, :] = 1.0
        pts, segs = marching_squares(F, s, w)
        if len(segs) == 0:
            continue
        own_i = _bilinear(own, s, w, pts[:, 0], pts[:, 1])
        cut_i = _bilinear(cut, s, w, pts[:, 0], pts[:, 1])
        cls_all = _classify(pts, own_i, cut_i, [s[2], s[-3]])
        loops = []
        for path in chain(segs):
            if len(path) < 4 or path[0] != path[-1]:
                continue
            idx = path[:-1]
            lp = _Loop(pts[idx], _debounce(pts[idx], cls_all[idx].copy()))
            loops.append((lp, _loop_area(lp.pts)))
        comps = [(lp, a) for lp, a in loops if abs(a) >= min_area_mm2]
        if not comps:
            continue
        simp = [(_simplify_loop(lp, lod), a) for lp, a in comps]
        simp = [(lp, a) for lp, a in simp if len(lp.pts) >= 3]
        if not simp:
            continue
        depth = []
        for i, (lp, a) in enumerate(simp):
            p0 = lp.pts[0]
            depth.append(sum(1 for j, (lq, b) in enumerate(simp) if j != i and _point_in_poly(p0, lq.pts)))
        outers = [i for i in range(len(simp)) if depth[i] % 2 == 0]
        holes = [i for i in range(len(simp)) if depth[i] % 2 == 1]
        groups = {i: [i] for i in outers}
        for h in holes:
            hp = simp[h][0].pts[0]
            for o in outers:
                if _point_in_poly(hp, simp[o][0].pts):
                    groups[o].append(h)
                    break
        for comp_i, o in enumerate(sorted(outers, key=lambda i: simp[i][0].pts[:, 0].min())):
            piece = _triangulate(model, k, st, sub, comp_i, [simp[i][0] for i in groups[o]],
                                 F, s, w, lod, delaunay_2d_cdt, Vector, abs(simp[o][1]))
            if piece is not None:
                pieces.append(piece)
    return pieces


def _tri_overlap(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> bool:
    """Separating-axis overlap of two 2-D triangles (touching is not overlapping)."""
    for tri in (a, b):
        for k in range(3):
            e = tri[(k + 1) % 3] - tri[k]
            ax = np.array([-e[1], e[0]])
            L = np.linalg.norm(ax)
            if L < 1e-15:
                continue
            ax /= L
            pa, pb = a @ ax, b @ ax
            if pa.max() <= pb.min() + eps or pb.max() <= pa.min() + eps:
                return False
    return True


def _untangle_walls(V, new_uv, origin, T_top, T_wall, base, rounds: int = 6):
    """Shrink the unfold of any wall vertex whose triangles overlap another triangle of
    the same piece in the chart (walls fanning out past a tight corner).  The vertex moves
    back along its own unfold direction (from ``origin``, its top vertex), halving each
    round: the wall's texel density drops a little there, nothing overlaps, and nothing
    collapses."""
    uv_all = np.concatenate([V, new_uv], axis=0)
    tris = np.concatenate([T_top, T_wall], axis=0)
    nt = len(T_top)
    scale = np.ones(len(new_uv))
    for _ in range(rounds):
        X = uv_all[tris]
        lo, hi = X.min(axis=1), X.max(axis=1)
        bad_v = set()
        for wi in range(nt, len(tris)):
            cand = np.nonzero((lo[:, 0] < hi[wi, 0]) & (hi[:, 0] > lo[wi, 0])
                              & (lo[:, 1] < hi[wi, 1]) & (hi[:, 1] > lo[wi, 1]))[0]
            for j in cand:
                if j == wi or len(set(tris[j].tolist()) & set(tris[wi].tolist())) >= 2:
                    continue
                if _tri_overlap(X[wi], X[j]):
                    for v in tris[wi]:
                        if v >= base:
                            bad_v.add(int(v) - base)
        if not bad_v:
            break
        for q in bad_v:
            scale[q] *= 0.5
            uv_all[base + q] = origin[q] + (new_uv[q] - origin[q]) * scale[q]
    return uv_all[base:]


def _triangulate(model, k, st, sub, comp_i, loops, F, s, w, lod, cdt, Vector, area):
    verts: List[Tuple[float, float]] = []
    cls: List[int] = []
    edges: List[Tuple[int, int]] = []
    for lp in loops:
        base = len(verts)
        n = len(lp.pts)
        for q in range(n):
            verts.append((float(lp.pts[q, 0]), float(lp.pts[q, 1])))
            cls.append(int(lp.cls[q]))
        for q in range(n):
            edges.append((base + q, base + (q + 1) % n))
    B = np.array(verts)
    s0, s1 = B[:, 0].min(), B[:, 0].max()
    off = (k * 0.37) % 1.0
    # interior ROWS at fixed fractions of the tape's half-width, so every visible piece -
    # however narrow - carries the band's arch in its vertices
    gs = np.arange(s0 + lod.grid_s * (0.5 + off * 0.5), s1, lod.grid_s)
    if len(gs):
        lo, hi, _c = st.at(st.lam_of_s(gs, CHART_R_MM))
        hwv = (hi - lo) * 0.5 * SS.DEG * CHART_R_MM
        GS, GW = [], []
        for sv, hv in zip(gs, hwv):
            fr = lod.rows_wide if hv > 5.5 else (lod.rows_mid if hv > 2.5 else (0.0,))
            for fv_ in fr:
                GS.append(sv)
                GW.append(fv_ * hv)
        GS, GW = np.array(GS), np.array(GW)
        fv = _bilinear(F, s, w, GS, GW)
        clear = lod.row_clear_mm
        ok = (fv < -clear) & _in_loops(np.stack([GS, GW], axis=1), loops)
        if ok.any():
            cand = np.stack([GS[ok], GW[ok]], axis=1)
            dmin = np.sqrt(((cand[:, None, :] - B[None, :, :]) ** 2).sum(-1)).min(axis=1)
            for p in cand[dmin > clear]:
                verts.append((float(p[0]), float(p[1])))
                cls.append(-1)
    out_v, out_e, out_f, orig_v, orig_e, orig_f = cdt([Vector(v) for v in verts], edges, [], 0, 1e-7, True)
    V = np.array([(p.x, p.y) for p in out_v])
    vcls = np.full(len(V), -1)
    out_of_in = {}
    for i, ov in enumerate(orig_v):
        if ov:
            V[i] = verts[ov[0]]
            vcls[i] = cls[ov[0]]
            for j in ov:
                out_of_in[j] = i
    own_in = [(a, b) for (a, b) in edges if cls[a] == 0]
    T = np.array([f for f in out_f if len(f) == 3], np.int64).reshape(-1, 3)
    if len(T) == 0:
        return None
    cen = V[T].mean(axis=1)
    # the triangle must be in THIS component (a sub-chart can hold several) and in F < 0
    T = T[(_bilinear(F, s, w, cen[:, 0], cen[:, 1]) < 0.0) & _in_loops(cen, loops)]
    if len(T) == 0:
        return None
    # CDT's convex-hull triangles along a straight boundary run are DEGENERATE (three
    # collinear boundary points) and their centroid sits on the boundary, so the F test
    # above can keep them: drop anything with no area in the chart, and make every
    # triangle counter-clockwise in the chart (the outward orientation, see below)
    ca = 0.5 * ((V[T[:, 1], 0] - V[T[:, 0], 0]) * (V[T[:, 2], 1] - V[T[:, 0], 1])
                - (V[T[:, 2], 0] - V[T[:, 0], 0]) * (V[T[:, 1], 1] - V[T[:, 0], 1]))
    T = T[np.abs(ca) > 1e-6]
    ca = ca[np.abs(ca) > 1e-6]
    T = np.where((ca < 0)[:, None], T[:, ::-1], T)
    if len(T) == 0:
        return None
    used = np.unique(T)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    V = V[used]
    vcls = vcls[used]
    T = remap[T]
    own_pairs = set()
    for a, b in own_in:
        oa, ob = out_of_in.get(a), out_of_in.get(b)
        if oa is None or ob is None:
            continue
        ra, rb = int(remap[oa]), int(remap[ob])
        if ra >= 0 and rb >= 0:
            own_pairs.add((min(ra, rb), max(ra, rb)))
    P = st.chart_to_cam(V[:, 0], V[:, 1], CHART_R_MM)
    f = model.field(P)
    rad = model.height_mm(P, np.full(len(V), k), f)
    X = P * rad[:, None]
    nrm = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]])
    flipped = float((nrm * X[T].mean(axis=1)).sum()) < 0
    if flipped:
        T = T[:, ::-1]
    wall_flag = np.zeros(len(V), bool)
    edge_flag = np.zeros(len(V), bool)
    sharp: List[Tuple[int, int]] = []
    uv = V.copy()
    Pall, radall = [P], [rad]
    if lod.walls:
        from collections import defaultdict
        count = defaultdict(int)
        directed = {}
        for tri in T.tolist():
            for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                key = (min(a, b), max(a, b))
                count[key] += 1
                directed[key] = (a, b)
        bedges = [directed[kk] for kk, c in count.items() if c == 1]
        # an exposed OWN edge: its first vertex (in loop order) starts an own-edge run.
        # The loop order is CCW in (s, w) before any flip; the triangle order after the
        # flip decides the direction, so test both ends.
        own_edges = [(a, b) for a, b in bedges if (min(a, b), max(a, b)) in own_pairs]
        if own_edges:
            ev = sorted({v for e in own_edges for v in e})
            onrm = {v: np.zeros(2) for v in ev}
            sgn = -1.0 if flipped else 1.0
            for a, b in own_edges:
                d = V[b] - V[a]
                o = sgn * np.array([d[1], -d[0]])
                L = np.linalg.norm(o)
                if L > 0:
                    onrm[a] += o / L
                    onrm[b] += o / L
            Pe = P[ev]
            fe = model.field(Pe)
            bel = model.below_mm(Pe, np.full(len(ev), k), fe)
            top = rad[ev]
            bottom = np.minimum(bel - SKIRT_MM, top - 0.12)
            base = len(V)
            new_uv = []
            for q, v in enumerate(ev):
                nn = onrm[v]
                L = np.linalg.norm(nn)
                nn = nn / L if L > 0 else nn
                new_uv.append(V[v] + nn * float(top[q] - bottom[q]))
                edge_flag[v] = True
            idx_of = {v: base + q for q, v in enumerate(ev)}
            wall_tris = []
            for a, b in own_edges:
                a2, b2 = idx_of[a], idx_of[b]
                wall_tris.append((b, a, a2))
                wall_tris.append((b, a2, b2))
                sharp.append((a, b))
            new_uv = _untangle_walls(V, np.array(new_uv), V[np.array(ev)], T,
                                     np.array(wall_tris, np.int64), base)
            uv = np.concatenate([uv, new_uv], axis=0)
            Pall.append(Pe)
            radall.append(bottom)
            T = np.concatenate([T, np.array(wall_tris, np.int64)], axis=0)
            wall_flag = np.concatenate([wall_flag, np.ones(len(ev), bool)])
            edge_flag = np.concatenate([edge_flag, np.zeros(len(ev), bool)])
    Pc = np.concatenate(Pall, axis=0)
    rc = np.concatenate(radall, axis=0)
    bb = (float(uv[:, 0].min()), float(uv[:, 0].max()), float(uv[:, 1].min()), float(uv[:, 1].max()))
    return Piece(k, st.name, sub, uv, Pc, rc, T, wall_flag, edge_flag, sharp, bb, area, comp_i)


# =========================================================================== one LOD
@dataclass
class LodMesh:
    level: int
    pieces: List[Piece]
    plans: List[StripPlan]


def build_lod(model: Model, lod: LodParams, plans: Optional[List[StripPlan]] = None,
              log=print) -> LodMesh:
    if plans is None:
        plans = [plan_strip(model, k, lod) for k in range(len(model.strips))]
    pieces: List[Piece] = []
    for plan in plans:
        ps = mesh_strip(model, plan, lod)
        pieces.extend(ps)
        log(f"  LOD{lod.level} {model.strips[plan.k].name:5s} cuts {len(plan.cuts)} "
            f"pieces {len(ps)} tris {sum(len(p.tris) for p in ps)}")
    return LodMesh(lod.level, pieces, plans)


__all__ += ["MAX_ISLAND_MM", "StripPlan", "plan_strip", "mesh_strip", "LodMesh", "build_lod"]


# =========================================================================== LOD2: resample
def geodesic_sphere(freq: int):
    """Unit geodesic sphere: icosahedron faces subdivided ``freq`` times; (V, 3), (F, 3)."""
    t = (1.0 + 5 ** 0.5) / 2.0
    V0 = np.array([(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                   (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)], float)
    V0 /= np.linalg.norm(V0, axis=1, keepdims=True)
    F0 = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
          (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8),
          (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    verts: Dict[Tuple[int, int, int], int] = {}
    co: List[np.ndarray] = []

    def vid(p):
        key = tuple(np.round(p * 1e9).astype(np.int64))
        i = verts.get(key)
        if i is None:
            i = len(co)
            verts[key] = i
            co.append(p)
        return i
    faces = []
    for a, b, c in F0:
        A, B_, C = V0[a], V0[b], V0[c]
        grid = {}
        for i in range(freq + 1):
            for j in range(freq + 1 - i):
                p = (A * (freq - i - j) + B_ * i + C * j) / freq
                p = p / np.linalg.norm(p)
                grid[(i, j)] = vid(p)
        for i in range(freq):
            for j in range(freq - i):
                faces.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
                if j + i + 1 < freq:
                    faces.append((grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]))
    return np.array(co), np.array(faces, np.int64)


@dataclass
class ResampledLod:
    level: int
    verts_cam: np.ndarray        # (V, 3) unit directions
    radius_mm: np.ndarray        # (V,)
    tris: np.ndarray             # (T, 3)
    tri_strip: np.ndarray        # (T,)
    loop_chart: np.ndarray       # (T, 3, 2) chart (s, w) per corner, already in-island
    loop_key: List[Tuple[int, int, int]]


def resample_lod(model: Model, plans: List[StripPlan], island_of, freq: int = 5,
                 level: int = 2) -> ResampledLod:
    """The top surface resampled on a geodesic sphere.  Each triangle takes the strip that
    is on top at its centroid, and every corner is mapped through THAT strip's chart into
    the LOD0 island that holds it (``island_of(strip, s, w) -> (key, clamp_box)``), with
    the chart point clamped to that island, so the LOD reads the same texels as LOD0 and
    never reaches into a neighbouring island.  Positions are the top surface at each
    vertex, so the shell is watertight and the silhouette is LOD0's."""
    V, F = geodesic_sphere(freq)
    f = model.field(V)
    top = np.maximum(f.top, 0)
    rad = model.height_mm(V, top, f)
    cen = SS.normalize(V[F].mean(axis=1))
    fc = model.field(cen)
    tstrip = np.maximum(fc.top, 0)
    charts = np.zeros((len(F), 3, 2))
    keys = []
    for ti, (tri, k) in enumerate(zip(F, tstrip)):
        st = model.strips[k]
        ev = st.evaluate(V[tri], CHART_R_MM)
        evc = st.evaluate(cen[ti:ti + 1], CHART_R_MM)
        plan = plans[k]
        # s on the plan's own unrolled range
        sc = plan.s0 + np.mod(evc["s"][0] - plan.s0, plan.length) if st.closed else evc["s"][0]
        ss_ = ev["s"].copy()
        if st.closed:
            ss_ = sc + ((ss_ - sc + 0.5 * plan.length) % plan.length) - 0.5 * plan.length
        charts[ti, :, 0] = ss_
        charts[ti, :, 1] = ev["w"]
        keys.append(None)
    return ResampledLod(level, V, rad, F, tstrip, charts, keys)


__all__ += ["LOD2_FREQUENCY", "geodesic_sphere", "ResampledLod", "resample_lod"]
