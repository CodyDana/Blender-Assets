#!/usr/bin/env python
"""props_lib.smokebomb_shell - SM_SmokeBomb as ONE CLOSED HEIGHT-FIELD SHELL.

numpy + mathutils (the CDT); no bpy.  Round 2 replaces round 1's layered open sheets
(smokebomb_mesh: one piece per strip, running on under its covers, with open-bottomed skirt
walls) because a stack of open sheets shows its inside: black slots between layers at the
limb, see-through slits on LOD1, and tape ends wherever a piece stopped.  Here the ball is
the visible tape surface and nothing else:

    top(p)    the strip on top at a point of the sphere (highest rank covering it)
    region    a connected area where one strip is on top; its boundary is made of RUNS
    run       a stretch of one strip's edge that is EXPOSED (the strip is on top just inside
              it) with one neighbour (the strip on top just outside it)
    junction  where a run ends: the point where the edge meets the edge of another strip

Every run is sampled ONCE (per LOD) and both regions it separates use exactly those
points, so the shell is watertight by construction.  Each side keeps its own copy of a
boundary vertex, at its own height, and a WALL joins the two copies: the tape's edge is a
real step, and it reaches the silhouette (REFERENCE_SPEC 1 and 5; the kunai lesson).  At a
junction the wall on the lower side is split at the middle copy, so the three walls that
meet there close the surface without a gap.

A region is triangulated in its own strip's chart (s along the tape, w across it) with
Blender's constrained Delaunay triangulation, with interior rows at fixed fractions of the
tape's half-width (so every band carries its crown in the vertices).  UV0 is that chart,
scaled and translated into the region's island: u along the warp everywhere.  A wall is
unfolded onto the island of the strip that owns it.

Nothing here reads the reference image.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

CHART_R_MM = 35.0


# =========================================================================== labels
def top_of(strips: Sequence[SS.Strip], P: np.ndarray) -> np.ndarray:
    """Index of the strip on top at each point (-1 where nothing covers it)."""
    return SS.evaluate_field(strips, P, CHART_R_MM).top


def _edge_points(st: SS.Strip, lam: np.ndarray, side: int, dphi_deg: float = 0.0) -> np.ndarray:
    """Points on strip ``st``'s edge (side +1 = hi, -1 = lo), moved ``dphi_deg`` OUTWARD."""
    lam = np.asarray(lam, np.float64)
    l = ((lam + 180.0) % 360.0) - 180.0
    e = np.interp(l, st._lam, st._hi if side > 0 else st._lo) + side * dphi_deg
    lr, pr = lam * SS.DEG, e * SS.DEG
    cp = np.cos(pr)[..., None]
    return (cp * (np.cos(lr)[..., None] * st.e1 + np.sin(lr)[..., None] * st.e2)
            + np.sin(pr)[..., None] * st.n)


def _edge_d(st: SS.Strip, side: int, P: np.ndarray) -> np.ndarray:
    """Signed distance (mm, + inside) of P to one specific edge of ``st``."""
    e = st.evaluate(P, CHART_R_MM)
    return e["d_hi"] if side > 0 else e["d_lo"]


# =========================================================================== runs
@dataclass
class Junction:
    id: int
    P: np.ndarray                     # unit vector
    edges: Tuple[Tuple[int, int], Tuple[int, int]]


@dataclass
class Run:
    id: int
    strip: int                        # the owner: on top just inside the edge
    side: int                         # +1 hi edge, -1 lo edge
    lam0: float                       # start (deg, unwrapped so lam1 > lam0)
    lam1: float
    nbr: int                          # on top just outside the edge
    j0: int                           # junction at lam0 (-1: none, a closed run)
    j1: int


@dataclass
class RunSet:
    runs: List[Run]
    junctions: List[Junction]
    report: Dict[str, object] = field(default_factory=dict)


#: probe offset across an edge (deg): ~6 um on the 35 mm chart
PROBE_DEG = 1e-4
#: edge sampling for the label scan (deg of lam)
SCAN_DEG = 0.06


def find_runs(strips: Sequence[SS.Strip], scan_deg: float = SCAN_DEG, log=None) -> RunSet:
    """Every exposed stretch of every strip edge, split wherever its neighbour changes."""
    strips = list(strips)
    S = len(strips)
    rank_of = lambda k, P: SS.step_function(strips[k].rank, strips[k].coords(P)[0])
    lam = np.arange(-180.0, 180.0, scan_deg)
    n = len(lam)
    junctions: List[Junction] = []
    jindex: Dict[Tuple, List[int]] = defaultdict(list)

    def junction_at(P, ea, eb):
        key = (min(ea, eb), max(ea, eb))
        for jid in jindex[key]:
            if np.linalg.norm(junctions[jid].P - P) < 2e-6:      # 70 nm on the chart
                return jid
        j = Junction(len(junctions), P.copy(), key)
        junctions.append(j)
        jindex[key].append(j.id)
        return j.id

    def cross_edge(k, side, la, lb, other, oside):
        """Exact point where strip k's edge meets strip ``other``'s ``oside`` edge, lam near
        (la, lb): the label flips on a probe line 6 um inside the edge, so the true crossing
        can sit just outside the scan interval - widen until the sign changes."""
        st, ot = strips[k], strips[other]
        for grow in (0.0, 1.0, 3.0, 8.0):
            a0, b0 = la - grow * scan_deg, lb + grow * scan_deg
            fa = _edge_d(ot, oside, _edge_points(st, np.array([a0]), side))[0]
            fb = _edge_d(ot, oside, _edge_points(st, np.array([b0]), side))[0]
            if fa * fb <= 0:
                break
        else:
            return None
        a, b = a0, b0
        for _ in range(60):
            m = 0.5 * (a + b)
            fm = _edge_d(ot, oside, _edge_points(st, np.array([m]), side))[0]
            if (fm > 0) == (fa > 0):
                a, fa = m, fm
            else:
                b = m
        m = 0.5 * (a + b)
        return m, _edge_points(st, np.array([m]), side)[0]

    def nearest_edge(other, P):
        e = strips[other].evaluate(P[None, :], CHART_R_MM)
        return +1 if abs(e["d_hi"][0]) <= abs(e["d_lo"][0]) else -1

    runs: List[Run] = []
    problems = []
    for k in range(S):
        st = strips[k]
        for side in (+1, -1):
            Pin = _edge_points(st, lam, side, -PROBE_DEG)
            Pout = _edge_points(st, lam, side, +PROBE_DEG)
            tin = top_of(strips, Pin)
            tout = top_of(strips, Pout)
            exposed = tin == k
            if not exposed.any():
                continue
            # state per sample: neighbour where exposed, -9 where covered
            state = np.where(exposed, tout, -9)
            change = np.nonzero(state != np.roll(state, -1))[0]      # between i and i+1
            if len(change) == 0:
                # the whole edge exposed with one neighbour: a closed run, cut at lam 0
                runs.append(Run(len(runs), k, side, -180.0, 180.0, int(state[0]), -1, -1))
                continue
            # transitions -> (lam, junction id)
            marks = []
            for i in change.tolist():
                la = lam[i]
                lb = lam[i] + scan_deg if i + 1 < n else lam[0] + 360.0
                s_a, s_b = int(state[i]), int(state[(i + 1) % n])
                # which edge meets ours here?
                if s_a == -9 or s_b == -9:
                    # a higher strip starts / stops covering our edge
                    Pm = _edge_points(st, np.array([0.5 * (la + lb)]), side, -PROBE_DEG)[0]
                    T = int(tin[i]) if s_a == -9 else int(tin[(i + 1) % n])
                    other = T
                else:
                    # the neighbour changes: the higher of the two ends its edge on ours
                    ra = float(rank_of(s_a, _edge_points(st, np.array([la]), side, PROBE_DEG))[0]) if s_a >= 0 else -1e9
                    rb = float(rank_of(s_b, _edge_points(st, np.array([lb]), side, PROBE_DEG))[0]) if s_b >= 0 else -1e9
                    other = s_a if ra > rb else s_b
                if other < 0:
                    problems.append(("uncovered neighbour", k, side, float(la)))
                    continue
                found = None
                for oside in (nearest_edge(other, _edge_points(st, np.array([0.5 * (la + lb)]), side)[0]),):
                    found = cross_edge(k, side, la, lb, other, oside)
                    if found is None:
                        found = cross_edge(k, side, la, lb, other, -oside)
                        oside = -oside
                    if found is not None:
                        lm, Pj = found
                        jid = junction_at(Pj, (k, side), (other, oside))
                        marks.append((lm, jid, i))
                if found is None:
                    problems.append(("no crossing found", k, side, float(la), other))
            if not marks:
                continue
            # runs between consecutive marks where exposed
            marks.sort()
            for q in range(len(marks)):
                la, ja, ia = marks[q]
                lb, jb, ib = marks[(q + 1) % len(marks)]
                if q + 1 == len(marks):
                    lb += 360.0
                mid_i = (ia + 1) % n
                if state[mid_i] == -9:
                    continue
                runs.append(Run(len(runs), k, side, float(la), float(lb), int(state[mid_i]), ja, jb))
    # ------------------------------------------------------------------ seams
    # A strip that is never fully covered anywhere along its loop could leave a region that
    # winds all the way round it (no chart can hold that).  Such a strip gets a SEAM: a cut
    # straight across it where it is fully exposed, as far round the back as possible.  The
    # seam is a run whose two sides are the same region; it splits the strip's edge runs
    # at its ends, and it never carries a wall.
    cuts = []
    lamc = np.arange(-180.0, 180.0, 1.0)
    for k in range(S):
        st = strips[k]
        lo, hi, _ = st.at(lamc)
        fr = np.linspace(0.08, 0.92, 9)
        ph = lo[:, None] + (hi - lo)[:, None] * fr[None, :]
        lr = np.radians(lamc)[:, None]
        pr = np.radians(ph)
        P = (np.cos(pr)[..., None] * (np.cos(lr)[..., None] * st.e1 + np.sin(lr)[..., None] * st.e2)
             + np.sin(pr)[..., None] * st.n)
        tt = top_of(strips, P.reshape(-1, 3)).reshape(P.shape[:2])
        vis = (tt == k).mean(axis=1)
        if (vis == 0.0).any():
            continue
        full = vis == 1.0
        if not full.any():
            problems.append(("needs a seam but is never fully exposed", k))
            continue
        z = st.centreline_cam(lamc)[:, 2]
        # the fully exposed lam farthest round the back, away from any partial cover
        score = np.where(full, -z, -9.0)
        for dl in (-2, -1, 1, 2):
            score = np.where(np.roll(full, dl), score, score - 5.0)
        lc = float(lamc[int(np.argmax(score))]) + 0.5
        cuts.append((k, lc))
    for k, lc in cuts:
        st = strips[k]
        jl = junction_at(_edge_points(st, np.array([lc]), -1)[0], (k, -1), (k, 0))
        jh = junction_at(_edge_points(st, np.array([lc]), +1)[0], (k, +1), (k, 0))
        # split the edge runs of k that contain lc
        for side, jc in ((-1, jl), (+1, jh)):
            for r in list(runs):
                if r.strip != k or r.side != side:
                    continue
                if r.j0 < 0:
                    runs[r.id] = Run(r.id, k, side, lc, lc + 360.0, r.nbr, jc, jc)
                    break
                x = lc
                while x < r.lam0:
                    x += 360.0
                if r.lam0 < x < r.lam1:
                    runs[r.id] = Run(r.id, k, side, r.lam0, x, r.nbr, r.j0, jc)
                    runs.append(Run(len(runs), k, side, x, r.lam1, r.nbr, jc, r.j1))
                    break
        runs.append(Run(len(runs), k, 0, lc, lc, k, jl, jh))
    runs, merged = _merge_short_runs(strips, runs, junctions)
    rep = {"runs": len(runs), "junctions": len(junctions), "problems": problems[:40],
           "n_problems": len(problems), "seams": [(strips[k].name, round(lc, 2)) for k, lc in cuts],
           "short_runs_merged": merged}
    if log:
        log(f"  shell: {len(runs)} runs, {len(junctions)} junctions, {len(cuts)} seams, "
            f"{merged} short runs merged, {len(problems)} problems")
    return RunSet(runs, junctions, rep)


#: a run shorter than this (mm) is a point where three edges nearly meet: its two junctions
#: are merged into one and the run is dropped (it would be a sub-pixel sliver wall)
MIN_RUN_MM = 0.15


def _merge_short_runs(strips, runs: List[Run], junctions: List[Junction]):
    alias: Dict[int, int] = {}

    def root(j):
        while j in alias:
            j = alias[j]
        return j
    keep = []
    merged = 0
    for r in runs:
        if r.j0 >= 0 and r.side != 0:
            lam = np.linspace(r.lam0, r.lam1, 8)
            P = _edge_points(strips[r.strip], lam, r.side)
            L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()) * CHART_R_MM
            a, b = root(r.j0), root(r.j1)
            if L < MIN_RUN_MM and a != b:
                alias[b] = a
                merged += 1
                continue
        keep.append(r)
    out = []
    for r in keep:
        j0 = root(r.j0) if r.j0 >= 0 else -1
        j1 = root(r.j1) if r.j1 >= 0 else -1
        if r.j0 >= 0 and j0 == j1 and r.side != 0:
            lam = np.linspace(r.lam0, r.lam1, 8)
            P = _edge_points(strips[r.strip], lam, r.side)
            if float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()) * CHART_R_MM < 4 * MIN_RUN_MM:
                merged += 1
                continue
        out.append(Run(len(out), r.strip, r.side, r.lam0, r.lam1, r.nbr, j0, j1))
    return out, merged


__all__ = ["top_of", "Junction", "Run", "RunSet", "find_runs", "CHART_R_MM"]


# =========================================================================== regions
@dataclass
class Region:
    id: int
    strip: int
    #: boundary loops, each a list of (run id, owner_side: bool); owner_side True means
    #: this region is the run's owner (inner side).  Traversal keeps the region on the LEFT
    #: seen from outside the ball (outer loops CCW, holes CW).
    loops: List[List[Tuple[int, bool]]]


def _run_dir(run: Run, owner: bool) -> Tuple[int, int, bool]:
    """(from junction, to junction, lam_increasing) for a traversal with the region left.

    The (s, w) chart of every strip is right-handed about the outward normal, so "left"
    is the same in every chart: the owner of a hi edge (+1) lies at smaller phi, so its
    edge is walked toward DEcreasing lam; a lo edge toward increasing lam.  The neighbour
    walks the other way.  A seam (side 0) is walked lo -> hi by one side, hi -> lo by the
    other; both sides are the same region."""
    if run.side == 0:
        inc = owner
    else:
        inc = (run.side < 0) if owner else (run.side > 0)
    return (run.j0, run.j1, True) if inc else (run.j1, run.j0, False)


def find_regions(runset: RunSet, strips, samples: Dict[int, np.ndarray],
                 log=None) -> Tuple[List[Region], List[str]]:
    n_strips = len(strips)
    by_strip: Dict[int, List[Tuple[int, bool]]] = defaultdict(list)
    for r in runset.runs:
        by_strip[r.strip].append((r.id, True))
        if r.nbr >= 0 and not (r.side == 0 and r.nbr == r.strip):
            by_strip[r.nbr].append((r.id, False))
        elif r.side == 0:
            by_strip[r.strip].append((r.id, False))
    regions: List[Region] = []
    problems: List[str] = []

    def ends(k, item):
        """(start direction, end direction) of a run walked as ``item``, in strip k's chart."""
        run = runset.runs[item[0]]
        Q = samples[run.id]
        _, _, inc = _run_dir(run, item[1])
        if not inc:
            Q = Q[::-1]
        e = strips[k].evaluate(np.stack([Q[0], Q[1], Q[-2], Q[-1]]), CHART_R_MM)
        period = strips[k].length_rad * CHART_R_MM
        ds = lambda a, b: (b - a + 0.5 * period) % period - 0.5 * period
        d0 = np.array([ds(e["s"][0], e["s"][1]), e["w"][1] - e["w"][0]])
        d1 = np.array([ds(e["s"][2], e["s"][3]), e["w"][3] - e["w"][2]])
        return d0, d1

    for k in range(n_strips):
        items = by_strip.get(k, [])
        closed = [(rid, own) for rid, own in items if runset.runs[rid].j0 < 0]
        rest = [(rid, own) for rid, own in items if runset.runs[rid].j0 >= 0]
        out_of: Dict[int, List[Tuple[int, bool]]] = defaultdict(list)
        for rid, own in rest:
            a, b, _ = _run_dir(runset.runs[rid], own)
            out_of[a].append((rid, own))
        used = set()
        loops = [[c] for c in closed]
        for start in rest:
            if start in used:
                continue
            loop = []
            cur = start
            guard = 0
            while cur not in used and guard < 10000:
                used.add(cur)
                loop.append(cur)
                _, b, _ = _run_dir(runset.runs[cur[0]], cur[1])
                nxt = [c for c in out_of.get(b, []) if c not in used and c[0] != cur[0]]
                if not nxt:
                    break
                if len(nxt) > 1:
                    # a face is walked with the region on the left: take the sharpest left turn
                    din = ends(k, cur)[1]
                    best, bang = None, -9.0
                    for c in nxt:
                        dout = ends(k, c)[0]
                        ang = math.atan2(din[0] * dout[1] - din[1] * dout[0], din @ dout)
                        if ang > bang:
                            best, bang = c, ang
                    cur = best
                else:
                    cur = nxt[0]
                guard += 1
            a0, _, _ = _run_dir(runset.runs[loop[0][0]], loop[0][1])
            _, bl, _ = _run_dir(runset.runs[loop[-1][0]], loop[-1][1])
            if a0 != bl:
                problems.append(f"strip {k}: open boundary chain of {len(loop)} runs")
            loops.append(loop)
        for lp in loops:
            regions.append(Region(len(regions), k, [lp]))
    if log:
        log(f"  shell: {len(regions)} boundary loops, {len(problems)} problems")
    return regions, problems


__all__ += ["Region", "find_regions"]


# =========================================================================== heights
def _poly_basis(P: np.ndarray, degree: int) -> np.ndarray:
    """All monomials x^a y^b z^c, a + b + c <= degree, at unit vectors P: on the sphere this
    spans the spherical harmonics up to ``degree`` (a smooth low-order field)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    cols = []
    for a in range(degree + 1):
        for b in range(degree + 1 - a):
            for c in range(degree + 1 - a - b):
                cols.append((x ** a) * (y ** b) * (z ** c))
    return np.stack(cols, axis=1)


@dataclass
class HeightModel:
    """The tape surface's radius (mm) for a strip's sheet at a point.

        h_S(p) = R0(p) - t * Nbar(p) + t * (1 + sum_U cov_U(p)) + crown_S(p) + lift_S(p)

    * sum_U cov_U: the strips lying UNDER S at p (lower rank), each ramped over ``drape``
      across its own edge (a tape bridging a buried edge drapes; it does not step).  So at
      S's own exposed edge the surface steps down by one full tape thickness, whatever the
      depth of the stack: the step the viewer sees at every edge and at the silhouette.
    * Nbar: a smooth, low-order (degree ``nbar_degree``) fit of the number of layers over
      the whole ball.  Subtracting it keeps the OUTLINE round however unevenly the loops
      pile up (REFERENCE_SPEC 1: round within 1.24 % R rms), while every local step stays.
    * R0: the core, with REFERENCE_SPEC 1's low-order sector profile.
    * crown_S: the tape's own arch across its width plus the rolled selvedge bead at its own
      edge, faded out near any edge of a strip lying over it (the tape beneath is pressed
      down into the crevice: REFERENCE_SPEC 5)."""
    core_mm: float = 34.4
    profile: Tuple[float, ...] = (0.0,) * 12
    t_mm: float = 0.38
    drape_mm: float = 4.0
    crown_mm: float = 0.45
    crown_per_hw: float = 0.12
    crown_shape: float = 0.8
    bead_mm: float = 0.10
    bead_w_mm: float = 0.45
    dip_mm: float = 1.6
    nbar_degree: int = 8
    groove_mm: float = 0.12
    groove_w_mm: float = 1.0
    nbar_coef: Optional[np.ndarray] = None
    #: round 3: the outline correction (props_lib.smokebomb_outline), (n, 2) mm
    outline_coef: Optional[np.ndarray] = None
    #: round 3: the tape rolls down to its own edge (a rolled selvedge, not a cut sheet):
    #: the surface is lowered by roll_mm at the edge, easing to 0 at roll_w_mm inside it
    roll_mm: float = 0.0
    roll_w_mm: float = 1.4

    def prepare(self, strips, n: int = 30000) -> "HeightModel":
        """Fit Nbar to the layer count of the finished layout."""
        from .smokebomb_layout import fibonacci_sphere
        P = fibonacci_sphere(n)
        f = SS.evaluate_field(strips, P, CHART_R_MM)
        c = SS.smooth_cover(f.d, self.drape_mm).sum(axis=0)
        A = _poly_basis(P, self.nbar_degree)
        coef, *_ = np.linalg.lstsq(A, c, rcond=None)
        self.nbar_coef = coef
        self.nbar_rms = float(np.sqrt(np.mean((A @ coef - c) ** 2)))
        return self

    def nbar(self, P: np.ndarray) -> np.ndarray:
        if self.nbar_coef is None:
            return np.zeros(P.shape[0])
        return _poly_basis(P, self.nbar_degree) @ self.nbar_coef

    def core(self, P: np.ndarray) -> np.ndarray:
        r = np.full(P.shape[:-1], self.core_mm)
        if any(abs(v) > 0 for v in self.profile):
            th = np.degrees(np.arctan2(P[..., 1], P[..., 0])) % 360.0
            k = SS.periodic_spline([(15.0 + 30.0 * i, v) for i, v in enumerate(self.profile)], th)
            r = r * (1.0 + k)
        if self.outline_coef is not None:
            from .smokebomb_outline import correction
            r = r + correction(P, self.outline_coef)
        return r

    def sheet(self, f: SS.Field, P: np.ndarray, which: np.ndarray) -> np.ndarray:
        N = P.shape[0]
        j = np.arange(N)
        wr = f.rank[which, j]
        under = f.rank < wr[None, :]
        cov = SS.smooth_cover(f.d, self.drape_mm) * under
        cov[which, j] = 0.0
        layers = 1.0 + cov.sum(axis=0)
        higher = f.rank > wr[None, :]
        higher[which, j] = False
        dc = np.where(higher, f.d, -1e3).max(axis=0)
        expose = np.clip(-dc / self.dip_mm, 0.0, 1.0)
        expose = expose * expose * (3.0 - 2.0 * expose)
        hw = np.maximum(f.half_width[which, j], 0.5)
        d = np.clip(f.d[which, j], 0.0, None)
        tt = np.clip(d / hw, 0.0, 1.0)
        arch = np.minimum(self.crown_mm, self.crown_per_hw * hw) * (1.0 - (1.0 - tt) ** 2) ** self.crown_shape
        bead = self.bead_mm * np.exp(-(d / self.bead_w_mm) ** 2)
        lift = f.lift[which, j] * self.t_mm
        # the tape beneath is pressed into a groove along a covering edge
        gq = np.clip(1.0 + dc / self.groove_w_mm, 0.0, 1.0) * (dc < 0.0)
        groove = self.groove_mm * gq * gq
        roll = self.roll_mm * np.clip(1.0 - d / self.roll_w_mm, 0.0, 1.0) ** 2 if self.roll_mm > 0 else 0.0
        return (self.core(P) - self.t_mm * self.nbar(P) + self.t_mm * layers
                + (arch + bead) * expose + lift - groove - roll)


# =========================================================================== one LOD
@dataclass
class ShellParams:
    level: int
    seg_mm: float                   # longest boundary segment
    grid_mm: float                  # interior spacing along the tape
    walls: bool = True
    rows_wide: Tuple[float, ...] = (-0.7, -0.35, 0.0, 0.35, 0.7)
    rows_mid: Tuple[float, ...] = (-0.5, 0.0, 0.5)
    rows_narrow: Tuple[float, ...] = (0.0,)
    clear_frac: float = 0.42        # interior points keep this x grid_mm from the boundary
    min_step_mm: float = 0.06


#: round 4: mark the wall's foot (the edge it shares with the strip beneath) sharp as well
#: as its top, so the tape beneath keeps its own normal right up to the crevice
FOOT_SHARP = True

#: LOD2 is a geodesic resample of the top surface: frequency 5 = 500 triangles
LOD2_FREQUENCY = 5
#: LOD1 likewise at frequency 9 = 1620 triangles (study 6.3: 1,200 - 2,000): a closed shell,
#: the tape steps become slopes (the study's LOD1 rule), no see-through slits
LOD1_FREQUENCY = 10
#: the neighbourhood-mean blend of LOD1 / LOD2 vertex heights (resample_lod)
LOD_AVERAGE_BLEND = 1.0

SHELL_LODS = (
    # round 4: 4.6 / 4.6 mm (round 3: 3.6 / 3.8) - the budget moves from straight runs and
    # flat tape interiors to curved edges (EDGE_TURN_RAD), inside the study's 6,500 ceiling
    ShellParams(0, seg_mm=4.6, grid_mm=4.6),
    ShellParams(1, seg_mm=7.5, grid_mm=8.0, walls=False, rows_wide=(-0.45, 0.45), rows_mid=(0.0,),
                clear_frac=0.5),
)


#: the reference view's LIMB (camera-frame |z| small) is where the outline forms: segments
#: and interior spacing shrink there to this fraction, so the silhouette is a smooth curve
#: with the tape's steps, not a string of chords (adversary round 1: "straight chords of
#: 50-150 px")
LIMB_REFINE = 0.42
LIMB_Z = 0.30


def limb_scale(P: np.ndarray) -> np.ndarray:
    t = np.clip(np.abs(np.asarray(P)[..., 2]) / LIMB_Z, 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    return LIMB_REFINE + (1.0 - LIMB_REFINE) * t


#: round 3: where a strip EDGE crosses the reference view's limb, the wall between two edge
#: samples projects as a slope spread over one segment (1.5 mm, ~2.5 deg of outline), so
#: the outline's steps read as ramps.  The reference's steps are sharp (a jump within
#: 0.5 deg: REFERENCE_SPEC 5).  Edge runs are sampled this much finer again within
#: EDGE_LIMB_Z of the limb (only the runs: the interior grid is unchanged).
EDGE_LIMB_REFINE = 0.3
EDGE_LIMB_Z = 0.10


#: round 4: the largest geodesic turn of a strip edge within one boundary segment (rad);
#: 0 disables the curvature term
EDGE_TURN_RAD = 0.18
EDGE_MIN_SEG_MM = 0.9


def edge_limb_scale(P: np.ndarray) -> np.ndarray:
    t = np.clip(np.abs(np.asarray(P)[..., 2]) / EDGE_LIMB_Z, 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    return limb_scale(P) * (EDGE_LIMB_REFINE + (1.0 - EDGE_LIMB_REFINE) * t)


def _sample_run(st: SS.Strip, run: Run, seg_mm: float, junctions: List[Junction]) -> np.ndarray:
    """Points along the run (unit vectors), junction points exact at both ends."""
    if run.side == 0:
        # a seam: straight across the strip at lam0, lo edge -> hi edge
        lo, hi, _ = st.at(np.array([run.lam0]))
        ph = np.linspace(lo[0], hi[0], 64)
        lr, pr = math.radians(run.lam0), np.radians(ph)[:, None]
        P = np.cos(pr) * (math.cos(lr) * st.e1 + math.sin(lr) * st.e2) + np.sin(pr) * st.n
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1) * CHART_R_MM
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        m = max(1, int(math.ceil(cum[-1] / seg_mm - 1e-9)))
        pt = np.interp(np.linspace(0.0, cum[-1], m + 1), cum, ph)
        pr = np.radians(pt)[:, None]
        Q = np.cos(pr) * (math.cos(lr) * st.e1 + math.sin(lr) * st.e2) + np.sin(pr) * st.n
        Q[0] = junctions[run.j0].P
        Q[-1] = junctions[run.j1].P
        return Q
    lam = np.linspace(run.lam0, run.lam1, max(16, int((run.lam1 - run.lam0) / 0.05)))
    P = _edge_points(st, lam, run.side)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1) * CHART_R_MM
    mid = SS.normalize(0.5 * (P[1:] + P[:-1]))
    cost = seg / (seg_mm * edge_limb_scale(mid))
    if EDGE_TURN_RAD > 0 and len(P) > 2:
        # round 4: curvature-adaptive - a segment may turn the edge (geodesically, in the
        # tape's own surface) by at most EDGE_TURN_RAD, so a bending edge is a smooth curve,
        # not a polygon with visible corners (craft judge r3: "folded paper", Z-kinks)
        t = np.diff(P, axis=0)
        t = t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-15)
        side = np.cross(mid, t)
        turn = np.zeros(len(t))
        turn[1:] = np.abs(np.einsum("ij,ij->i", t[1:] - t[:-1], side[:-1]))
        # smoothed over ~1 mm so a single table node never spikes the density
        k = max(1, int(round(1.0 / max(float(np.median(seg)), 1e-6))))
        if k > 1 and len(turn) > k:
            turn = np.convolve(turn, np.ones(k) / k, mode="same")
        extra = turn / EDGE_TURN_RAD
        # ... and never finer than EDGE_MIN_SEG_MM (no sliver triangles in the chart)
        cost = np.minimum(cost + extra, np.maximum(cost, seg / EDGE_MIN_SEG_MM))
    cum = np.concatenate([[0.0], np.cumsum(cost)])
    L = cum[-1]
    m = max(1, int(math.ceil(L - 1e-9)))
    target = np.linspace(0.0, L, m + 1)
    lt = np.interp(target, cum, lam)
    Q = _edge_points(st, lt, run.side)
    if run.j0 >= 0:
        Q[0] = junctions[run.j0].P
    if run.j1 >= 0:
        Q[-1] = junctions[run.j1].P
    if run.j0 < 0:                    # a closed run: the last point is the first
        Q = Q[:-1]
    return Q


def _unroll(s: np.ndarray, period: float) -> np.ndarray:
    d = np.diff(s)
    d = (d + 0.5 * period) % period - 0.5 * period
    return np.concatenate([[s[0]], s[0] + np.cumsum(d)])


def _poly_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _in_poly(Q, polys):
    inside = np.zeros(len(Q), bool)
    x, y = Q[:, 0], Q[:, 1]
    for P in polys:
        x1, y1 = P[:, 0], P[:, 1]
        x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
        for a, b, c, d in zip(x1, y1, x2, y2):
            cross = (b > y) != (d > y)
            xi = a + (y - b) * (c - a) / np.where(d != b, d - b, 1e-30)
            inside ^= cross & (xi > x)
    return inside


def _dist_to_polys(Q, polys):
    dm = np.full(len(Q), 1e9)
    for P in polys:
        B = np.roll(P, -1, axis=0)
        for a, b in zip(P, B):
            ab = b - a
            L2 = float(ab @ ab)
            t = np.clip(((Q - a) @ ab) / max(L2, 1e-18), 0, 1)
            c = a + t[:, None] * ab
            dm = np.minimum(dm, np.linalg.norm(Q - c, axis=1))
    return dm


@dataclass
class RegionGeom:
    """A region's boundary in its strip's unrolled chart, for one LOD's run sampling."""
    region: Region
    loops_keys: List[List[Tuple]]            # vertex keys per loop
    loops_P: List[np.ndarray]                # unit vectors per loop
    loops_chart: List[np.ndarray]            # (n, 2) unrolled (s, w)
    area_mm2: float = 0.0


def region_geometry(strips, runset: RunSet, regions: List[Region], samples: Dict[int, np.ndarray],
                    problems: List[str]) -> List[RegionGeom]:
    """Chart polygons of every region from the sampled runs (``samples[run_id]``).  Each
    region's loops must already be grouped (outer first, then holes)."""
    out = []
    for reg in regions:
        st = strips[reg.strip]
        period = st.length_rad * CHART_R_MM
        keys_l, P_l, C_l = [], [], []
        anchor = None
        for loop in reg.loops:
            keys, pts = [], []
            for rid, own in loop:
                run = runset.runs[rid]
                Q = samples[rid]
                if run.j0 >= 0:
                    kk = [("J", run.j0)] + [("R", rid, i) for i in range(1, len(Q) - 1)] + [("J", run.j1)]
                else:
                    kk = [("R", rid, i) for i in range(len(Q))]
                _, _, inc = _run_dir(run, own)
                if not inc:
                    Q = Q[::-1]
                    kk = kk[::-1]
                if run.j0 >= 0:
                    Q = Q[:-1]            # the next run starts with this run's last junction
                    kk = kk[:-1]
                keys.extend(kk)
                pts.append(Q)
            P = np.concatenate(pts, axis=0)
            e = st.evaluate(P, CHART_R_MM)
            s = _unroll(e["s"], period)
            if anchor is None:
                anchor = float(np.mean(s))
            else:                         # a hole: shift it next to its outer loop
                s = s + period * round((anchor - float(np.mean(s))) / period)
            C = np.stack([s, e["w"]], axis=1)
            net = (s[-1] + ((s[0] - s[-1] + 0.5 * period) % period - 0.5 * period)) - s[0]
            if abs(net) > 0.5 * period:
                problems.append(f"region {reg.id} (strip {reg.strip}) winds round its strip")
            keys_l.append(keys)
            P_l.append(P)
            C_l.append(C)
        area = _poly_area(C_l[0]) + sum(_poly_area(c) for c in C_l[1:])
        out.append(RegionGeom(reg, keys_l, P_l, C_l, float(area)))
    return out


def group_holes(strips, runset: RunSet, loops: List[Region], samples, problems) -> List[Region]:
    """Single-loop regions -> regions with holes.  A loop that runs clockwise in its strip's
    chart is a hole of the counter-clockwise loop of the same strip that contains it."""
    geo = region_geometry(strips, runset, loops, samples, problems)
    outer = [g for g in geo if g.area_mm2 > 0]
    holes = [g for g in geo if g.area_mm2 <= 0]
    for h in holes:
        st = strips[h.region.strip]
        period = st.length_rad * CHART_R_MM
        host = None
        for g in outer:
            if g.region.strip != h.region.strip:
                continue
            for shift in (0.0, period, -period):
                q = h.loops_chart[0][:1] + np.array([shift, 0.0])
                if _in_poly(q, [g.loops_chart[0]])[0]:
                    host = g
                    break
            if host is not None:
                break
        if host is None:
            problems.append(f"hole loop of strip {h.region.strip} has no host")
            continue
        host.region.loops.append(h.region.loops[0])
    out = []
    for i, g in enumerate(outer):
        out.append(Region(i, g.region.strip, g.region.loops))
    return out


__all__ += ["HeightModel", "ShellParams", "SHELL_LODS", "RegionGeom", "region_geometry", "group_holes"]


# =========================================================================== triangulate
@dataclass
class ShellLod:
    level: int
    verts: np.ndarray               # (V, 3) mm, camera frame
    tris: np.ndarray                # (T, 3)
    tri_region: np.ndarray          # (T,) region id (a wall: its owner's region)
    tri_strip: np.ndarray           # (T,) strip index
    tri_wall: np.ndarray            # (T,) bool
    corner_chart: np.ndarray        # (T, 3, 2) chart (s, w) mm of each corner, in the region's unrolled chart
    sharp: List[Tuple[int, int]]
    region_box: Dict[int, Tuple[float, float, float, float]]   # chart bbox per region (walls included)
    report: Dict[str, object] = field(default_factory=dict)


def _rows(hw: float, across_mm: float) -> np.ndarray:
    n = max(0, int(round(2.0 * hw / across_mm)) - 1)
    return np.linspace(-1.0, 1.0, n + 2)[1:-1]


def _region_owner_map(regions: List[Region]) -> Dict[Tuple[int, bool], int]:
    m = {}
    for reg in regions:
        for loop in reg.loops:
            for rid, own in loop:
                m[(rid, own)] = reg.id
    return m


def build_shell_lod(strips, hm: HeightModel, runset: RunSet, regions: List[Region],
                    params: ShellParams, log=None) -> ShellLod:
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    problems: List[str] = []
    samples = {r.id: _sample_run(strips[r.strip], r, params.seg_mm, runset.junctions) for r in runset.runs}
    geoms = region_geometry(strips, runset, regions, samples, problems)
    side_region = _region_owner_map(regions)
    walls = params.walls

    vP: List[np.ndarray] = []          # unit vector per vertex
    vUsers: List[set] = []             # strips whose sheet the vertex belongs to
    vid: Dict[Tuple, int] = {}
    tris: List[Tuple[int, int, int]] = []
    t_reg: List[int] = []
    t_chart: List[np.ndarray] = []
    t_anchor: List[np.ndarray] = []
    chart_of: Dict[Tuple, np.ndarray] = {}          # (key, region) -> chart (s, w)

    def vertex(key, reg_id, P, strip):
        kk = (key, reg_id) if walls else (key,)
        i = vid.get(kk)
        if i is None:
            i = len(vP)
            vid[kk] = i
            vP.append(np.asarray(P, np.float64))
            vUsers.append({strip})
        else:
            vUsers[i].add(strip)
        return i

    across = params.seg_mm
    for g in geoms:
        reg = g.region
        k = reg.strip
        st = strips[k]
        B = np.concatenate(g.loops_chart, axis=0)
        Bk = [kk for keys in g.loops_keys for kk in keys]
        BP = np.concatenate(g.loops_P, axis=0)
        edges = []
        base = 0
        for C in g.loops_chart:
            n = len(C)
            edges += [(base + q, base + (q + 1) % n) for q in range(n)]
            base += n
        # interior rows at fixed fractions of the tape's half-width
        s0, s1 = float(B[:, 0].min()), float(B[:, 0].max())
        # stations along s at equal COST (denser at the reference view's limb)
        sf = np.linspace(s0, s1, max(8, int((s1 - s0) / 0.2)))
        cf = st.chart_to_cam(sf, np.zeros_like(sf), CHART_R_MM)
        fs = limb_scale(cf)
        cum = np.concatenate([[0.0], np.cumsum(np.diff(sf) / (params.grid_mm * 0.5 * (fs[1:] + fs[:-1])))])
        off = 0.5 * (0.5 + 0.5 * ((k * 0.37) % 1.0))
        tg = np.arange(off, cum[-1], 1.0)
        gs = np.interp(tg, cum, sf)
        Ipts, Ifs = [], []
        if len(gs):
            lamg = st.lam_of_s(gs, CHART_R_MM)
            lo, hi, _c = st.at(lamg)
            hwv = (hi - lo) * 0.5 * SS.DEG * CHART_R_MM
            fg = np.interp(gs, sf, fs)
            for sv, hv, fv in zip(gs, hwv, fg):
                for fr in _rows(hv, across * fv):
                    Ipts.append((sv, fr * hv))
                    Ifs.append(fv)
        Ipts = np.array(Ipts).reshape(-1, 2)
        Ifs = np.array(Ifs)
        if len(Ipts):
            ok = _in_poly(Ipts, g.loops_chart)
            Ipts, Ifs = Ipts[ok], Ifs[ok]
        if len(Ipts):
            ok = _dist_to_polys(Ipts, g.loops_chart) > params.clear_frac * params.grid_mm * Ifs
            Ipts = Ipts[ok]
        allpts = np.concatenate([B, Ipts], axis=0)
        out_v, out_e, out_f, orig_v, orig_e, orig_f = delaunay_2d_cdt(
            [Vector((float(p[0]), float(p[1]))) for p in allpts], edges, [], 0, 1e-7, True)
        V = np.array([(p.x, p.y) for p in out_v])
        src = np.full(len(V), -1)
        for i, ov in enumerate(orig_v):
            if len(ov) >= 1:
                src[i] = ov[0]
            if len(ov) > 1:
                problems.append(f"region {reg.id} (strip {k}): CDT merged input vertices {list(ov)[:4]}")
        T = np.array([f_ for f_ in out_f if len(f_) == 3], np.int64).reshape(-1, 3)
        if len(T) and (src[np.unique(T)] < 0).any():
            problems.append(f"region {reg.id} (strip {k}): CDT added {(src[np.unique(T)] < 0).sum()} vertices")
        if len(T):
            T = T[_in_poly(V[T].mean(axis=1), g.loops_chart)]
        if len(T):
            ca = 0.5 * ((V[T[:, 1], 0] - V[T[:, 0], 0]) * (V[T[:, 2], 1] - V[T[:, 0], 1])
                        - (V[T[:, 2], 0] - V[T[:, 0], 0]) * (V[T[:, 1], 1] - V[T[:, 0], 1]))
            T = T[np.abs(ca) > 1e-9]
        if len(T) == 0:
            problems.append(f"region {reg.id} (strip {k}): no triangles (area {g.area_mm2:.3f} mm2)")
            continue
        nB = len(B)
        ids = np.full(len(V), -1)
        for i in np.unique(T):
            j = src[i]
            if j < 0:
                continue
            if j < nB:
                ids[i] = vertex(Bk[j], reg.id, BP[j], k)
                chart_of[(Bk[j], reg.id)] = B[j]
            else:
                P = st.chart_to_cam(np.array([allpts[j, 0]]), np.array([allpts[j, 1]]), CHART_R_MM)[0]
                ids[i] = vertex(("I", reg.id, int(j)), reg.id, P, k)
        for tri in T:
            if (ids[tri] < 0).any() or (src[tri] < 0).any():
                continue
            tris.append(tuple(int(x) for x in ids[tri]))
            t_reg.append(reg.id)
            t_chart.append(allpts[src[tri]])
            t_anchor.append(allpts[src[tri]])

    # ------------------------------------------------------------------ heights
    P = np.array(vP)
    f = SS.evaluate_field(strips, P, CHART_R_MM)
    H = np.full(len(P), -np.inf)
    for kk in range(len(strips)):
        m = np.array([kk in u for u in vUsers])
        if not m.any():
            continue
        idx = np.nonzero(m)[0]
        fs = SS.Field(f.names, f.d[:, idx], f.rank[:, idx], f.s[:, idx], f.w[:, idx], f.lift[:, idx],
                      f.top[idx], f.covered[:, idx], f.half_width[:, idx])
        h = hm.sheet(fs, P[idx], np.full(len(idx), kk))
        H[idx] = np.maximum(H[idx], h)
    vstrip = np.array([min(u) if len(u) == 1 else -1 for u in vUsers])
    tris_a = np.array(tris, np.int64).reshape(-1, 3)
    chart_a = np.array(t_chart).reshape(-1, 3, 2)
    anchor_a = np.array(t_anchor).reshape(-1, 3, 2)
    reg_a = np.array(t_reg, np.int64)
    wall_a = np.zeros(len(tris_a), bool)
    sharp: List[Tuple[int, int]] = []
    wall_rep = {"segments": 0, "fans": 0, "raised": 0}

    names_of = lambda k: strips[int(k)].name if k >= 0 else "?"
    if walls:
        # ---------------------------------------------------------- the minimum step
        by_key = defaultdict(list)                  # boundary key -> copies
        for (key, rg), i in vid.items():
            if key[0] in ("J", "R"):
                by_key[key].append(i)
        for key, lst in by_key.items():
            if len(lst) < 2:
                continue
            Pk = P[lst[0]][None, :]
            ranks = [float(SS.step_function(strips[vstrip[i]].rank, strips[vstrip[i]].coords(Pk)[0])[0])
                     for i in lst]
            order = [lst[q] for q in np.argsort(ranks, kind="stable")]     # bottom -> top
            for a, b in zip(order[:-1], order[1:]):
                if vstrip[a] == vstrip[b] and vstrip[a] >= 0:
                    # round 4: two copies of one strip's sheet (the two sides of a SEAM)
                    # are the same surface; separating them opened a slit
                    continue
                if H[b] < H[a] + params.min_step_mm:
                    wall_rep.setdefault("raise_mm", []).append(round(float(H[a] + params.min_step_mm - H[b]), 3))
                    wall_rep.setdefault("raise_at", []).append((names_of(vstrip[a]), names_of(vstrip[b]),
                                                                 [round(float(x), 1) for x in SS.cam_to_img(P[a])]))
                    H[b] = H[a] + params.min_step_mm
                    wall_rep["raised"] += 1

        # outward normals of every region's boundary loops (chart, region on the left)
        loop_normal: Dict[Tuple, Tuple[float, float]] = {}
        for g in geoms:
            for keys_l, C_l in zip(g.loops_keys, g.loops_chart):
                n = len(C_l)
                for q in range(n):
                    # the sum of the two adjacent edges' outward normals: outward along the
                    # tip's axis at an acute convex corner, and between the two at a reflex one
                    acc = np.zeros(2)
                    for a, b in ((C_l[(q - 1) % n], C_l[q]), (C_l[q], C_l[(q + 1) % n])):
                        t = b - a
                        L = float(np.hypot(t[0], t[1]))
                        if L > 1e-12:
                            acc += np.array([t[1], -t[0]]) / L
                    L = float(np.hypot(acc[0], acc[1]))
                    if L < 1e-6:
                        continue
                    loop_normal[(keys_l[q], g.region.id)] = (acc[0] / L, acc[1] / L)

        def between(kk, top_i, bot_i):
            if kk[0] != "J":
                return []
            lst = [i for i in by_key[kk] if H[bot_i] + 1e-9 < H[i] < H[top_i] - 1e-9]
            return sorted(lst, key=lambda i: -H[i])

        new_t, new_c, new_r, new_a = [], [], [], []
        for run in runset.runs:
            if run.nbr < 0 or run.side == 0:
                continue
            if run.id in getattr(runset, "dead", set()):
                continue
            r_t = side_region.get((run.id, True))
            r_f = side_region.get((run.id, False))
            if r_t is None or r_f is None:
                problems.append(f"run {run.id}: missing a side region")
                continue
            Q = samples[run.id]
            if run.j0 >= 0:
                keys = [("J", run.j0)] + [("R", run.id, i) for i in range(1, len(Q) - 1)] + [("J", run.j1)]
            else:
                keys = [("R", run.id, i) for i in range(len(Q))] + [("R", run.id, 0)]
            ot = [vid.get((kk, r_t)) for kk in keys]
            of = [vid.get((kk, r_f)) for kk in keys]
            if any(x is None for x in ot) or any(x is None for x in of):
                problems.append(f"run {run.id}: a boundary vertex has no copy")
                continue
            # the TOP side (normally the owner) carries the wall, unfolded outward in its chart
            flag = bool(np.mean(H[ot]) >= np.mean(H[of]))
            ro = r_t if flag else r_f
            o, nb = (ot, of) if flag else (of, ot)
            C = np.array([chart_of[(kk, ro)] for kk in keys])
            # outward unfold direction per vertex from the REGION's own boundary loop (its
            # neighbours in loop order), so two runs of one region that meet at a junction
            # unfold along the same line there and their walls cannot overlap in UV0
            nrm = np.array([loop_normal.get((kk, ro), (0.0, 0.0)) for kk in keys], np.float64)

            def corner(i, pos):
                return C[pos] + nrm[pos] * float(H[o[pos]] - H[i])
            for q in range(len(keys) - 1):
                oa, ob, na, nbv = o[q], o[q + 1], nb[q], nb[q + 1]
                ma = between(keys[q], oa, na)
                mb = between(keys[q + 1], ob, nbv)
                if ma or mb:
                    wall_rep["fans"] += 1
                chain_b = [ob] + mb + [nbv]
                for u, v in zip(chain_b[:-1], chain_b[1:]):
                    new_t.append((oa, u, v))
                    new_c.append([corner(oa, q), corner(u, q + 1), corner(v, q + 1)])
                    new_a.append([C[q], C[q + 1], C[q + 1]])
                    new_r.append(ro)
                chain_a = [oa] + ma + [na]
                for u, v in zip(chain_a[:-1], chain_a[1:]):
                    new_t.append((u, nbv, v))
                    new_c.append([corner(u, q), corner(nbv, q + 1), corner(v, q)])
                    new_a.append([C[q], C[q + 1], C[q]])
                    new_r.append(ro)
                sharp.append((oa, ob))
                if FOOT_SHARP:
                    # round 4: the wall's FOOT is a crease too (craft judge r3: smooth feet
                    # bled the wall's normal onto the strip beneath as a soft grey gradient
                    # instead of a crisp crevice)
                    sharp.append((na, nbv))
                wall_rep["segments"] += 1
        if new_t:
            tris_a = np.concatenate([tris_a, np.array(new_t, np.int64)], axis=0)
            chart_a = np.concatenate([chart_a, np.array(new_c)], axis=0)
            anchor_a = np.concatenate([anchor_a, np.array(new_a)], axis=0)
            reg_a = np.concatenate([reg_a, np.array(new_r, np.int64)])
            wall_a = np.concatenate([wall_a, np.ones(len(new_t), bool)])
    X = P * H[:, None]
    # thin boundary slivers (three boundary points on a slightly concave run) can tilt past
    # vertical where the sheet's height changes along the edge: flip their long edge
    ns = int((~wall_a).sum())
    tris_s, chart_s, anch_s, nflip = _flip_tilted(tris_a[:ns], chart_a[:ns], anchor_a[:ns], reg_a[:ns], X)
    tris_a = np.concatenate([tris_s, tris_a[ns:]], axis=0)
    chart_a = np.concatenate([chart_s, chart_a[ns:]], axis=0)
    anchor_a = np.concatenate([anch_s, anchor_a[ns:]], axis=0)
    wall_rep["tilt_flips"] = nflip
    # one orientation rule for everything: counter-clockwise in the (unfolded) chart is
    # outward, because every chart is right-handed about the outward normal and a wall
    # unfolded outward keeps its outer face up
    cc = chart_a
    ca = 0.5 * ((cc[:, 1, 0] - cc[:, 0, 0]) * (cc[:, 2, 1] - cc[:, 0, 1])
                - (cc[:, 2, 0] - cc[:, 0, 0]) * (cc[:, 1, 1] - cc[:, 0, 1]))
    flip = ca < 0
    tris_a = np.where(flip[:, None], tris_a[:, ::-1], tris_a)
    chart_a = np.where(flip[:, None, None], chart_a[:, ::-1], chart_a)
    anchor_a = np.where(flip[:, None, None], anchor_a[:, ::-1], anchor_a)
    # a check the chart rule cannot fool: surface triangles face away from the centre
    Xt = X[tris_a]
    nrm3 = np.cross(Xt[:, 1] - Xt[:, 0], Xt[:, 2] - Xt[:, 0])
    inward = ((nrm3 * Xt.mean(axis=1)).sum(axis=1) < 0) & ~wall_a
    boxes: Dict[int, Tuple[float, float, float, float]] = {}
    for rg in np.unique(reg_a):
        c = chart_a[reg_a == rg].reshape(-1, 2)
        boxes[int(rg)] = (float(c[:, 0].min()), float(c[:, 0].max()), float(c[:, 1].min()), float(c[:, 1].max()))
    tri_strip = np.array([regions[int(r)].strip for r in reg_a], np.int64)
    rep = {"vertices": int(len(X)), "triangles": int(len(tris_a)), "wall_triangles": int(wall_a.sum()),
           "regions": len(geoms), "inward_surface_triangles": int(inward.sum()),
           "problems": problems[:40], "n_problems": len(problems), **wall_rep}
    if log:
        log(f"  shell LOD{params.level}: {len(X)} verts, {len(tris_a)} tris ({int(wall_a.sum())} wall), "
            f"{int(inward.sum())} inward, {len(problems)} problems")
    out = ShellLod(params.level, X, tris_a, reg_a, tri_strip, wall_a, chart_a, sharp, boxes, rep)
    out.geoms = geoms
    out.corner_anchor = anchor_a
    return out


#: a region smaller than this (mm2) bounded by two runs between the same two junctions is a
#: sliver between two nearly coincident edges: it is removed and its two runs become one
SLIVER_MM2 = 0.3
SLIVER_WIDTH_MM = 0.2


def _collapse_slivers(strips, runset: RunSet, loops: List[Region], samples, problems, log=None):
    fine = {r.id: _sample_run(strips[r.strip], r, 0.2, runset.junctions) for r in runset.runs}
    geo = region_geometry(strips, runset, loops, fine, [])
    dead = set()
    out = []
    subst: Dict[Tuple[int, bool], Tuple[int, bool]] = {}
    for g, lp in zip(geo, loops):
        items = lp.loops[0]
        if len(items) == 2 and len(lp.loops) == 1:
            (a, fa), (b, fb) = items
            ra, rb = runset.runs[a], runset.runs[b]
            C = g.loops_chart[0]
            per = float(np.linalg.norm(np.diff(np.vstack([C, C[:1]]), axis=0), axis=1).sum())
            width = 2.0 * abs(g.area_mm2) / max(per, 1e-9)
            if ({ra.j0, ra.j1} == {rb.j0, rb.j1} and ra.j0 >= 0
                    and (abs(g.area_mm2) < SLIVER_MM2 or width < SLIVER_WIDTH_MM)):
                # the region beyond b takes over the sliver's side of a
                subst[(b, not fb)] = (a, fa)
                dead.add(b)
                continue
        out.append(lp)
    for lp in out:
        lp.loops = [[subst.get(it, it) for it in loop] for loop in lp.loops]
    runset.dead = getattr(runset, "dead", set()) | dead
    if log and dead:
        log(f"  shell: {len(dead)} sliver regions collapsed")
    return out


def _tilt(X, t):
    """cos of the angle between the triangle's normal (chart-CCW order) and the radial."""
    a, b, c = X[t[0]], X[t[1]], X[t[2]]
    n = np.cross(b - a, c - a)
    m = (a + b + c) / 3.0
    return float(n @ m / max(np.linalg.norm(n) * np.linalg.norm(m), 1e-18))


def _ccw(C):
    return (C[1, 0] - C[0, 0]) * (C[2, 1] - C[0, 1]) - (C[2, 0] - C[0, 0]) * (C[1, 1] - C[0, 1])


def _flip_tilted(T, Ch, An, R, X, cos_min: float = 0.35, rounds: int = 80):
    """Edge-flip surface triangles whose normal leans more than ~70 deg from the radial (or
    points inward) with their neighbour across the longest chart edge, when the flip makes
    both triangles counter-clockwise in the chart and better aligned.  Surface triangles
    only; the chart CCW order of every triangle is kept (the orientation rule)."""
    T = T.copy()
    Ch = Ch.copy()
    An = An.copy()
    nflip = 0
    for _ in range(rounds):
        # orient: chart CCW first (as the final pass will)
        edge_of = {}
        for i, t in enumerate(T):
            for k in range(3):
                a, b = int(t[k]), int(t[(k + 1) % 3])
                edge_of.setdefault((min(a, b), max(a, b)), []).append((i, k))
        changed = False
        for i in range(len(T)):
            t = T[i] if _ccw(Ch[i]) > 0 else T[i][::-1]
            if _tilt(X, t) >= cos_min:
                continue
            # the longest chart edge
            L = [np.linalg.norm(Ch[i][(k + 1) % 3] - Ch[i][k]) for k in range(3)]
            k = int(np.argmax(L))
            a, b = int(T[i][k]), int(T[i][(k + 1) % 3])
            c = int(T[i][(k + 2) % 3])
            others = [(j, kk) for j, kk in edge_of.get((min(a, b), max(a, b)), []) if j != i and R[j] == R[i]]
            if len(others) != 1:
                continue
            j, kj = others[0]
            tj = [int(x) for x in T[j]]
            d = [v for v in tj if v not in (a, b)]
            if len(d) != 1:
                continue
            d = d[0]
            # chart points of every vertex involved (both triangles live in the region's chart)
            cp = {int(T[i][q]): Ch[i][q] for q in range(3)}
            cp.update({int(T[j][q]): Ch[j][q] for q in range(3)})
            ap = {int(T[i][q]): An[i][q] for q in range(3)}
            ap.update({int(T[j][q]): An[j][q] for q in range(3)})
            n1, n2 = [c, a, d], [c, d, b]
            C1 = np.array([cp[v] for v in n1])
            C2 = np.array([cp[v] for v in n2])
            if _ccw(C1) < 0:
                n1 = n1[::-1]
                C1 = C1[::-1]
            if _ccw(C2) < 0:
                n2 = n2[::-1]
                C2 = C2[::-1]
            # the flip must not fold the chart: the quad a-c-b-d must be convex (both new
            # triangles on opposite sides of cd with the same orientation as before)
            s_ab_c = _ccw(np.array([cp[a], cp[b], cp[c]]))
            s_ab_d = _ccw(np.array([cp[a], cp[b], cp[d]]))
            s_cd_a = _ccw(np.array([cp[c], cp[d], cp[a]]))
            s_cd_b = _ccw(np.array([cp[c], cp[d], cp[b]]))
            if s_ab_c * s_ab_d >= 0 or s_cd_a * s_cd_b >= 0:
                continue
            old_worst = min(_tilt(X, T[i] if _ccw(Ch[i]) > 0 else T[i][::-1]),
                            _tilt(X, T[j] if _ccw(Ch[j]) > 0 else T[j][::-1]))
            new_worst = min(_tilt(X, np.array(n1)), _tilt(X, np.array(n2)))
            if new_worst <= old_worst:
                continue
            T[i], T[j] = np.array(n1), np.array(n2)
            Ch[i], Ch[j] = C1, C2
            An[i] = np.array([ap[v] for v in n1])
            An[j] = np.array([ap[v] for v in n2])
            nflip += 1
            changed = True
            break
        if not changed:
            break
    return T, Ch, An, nflip


def build_regions(strips, runset: RunSet, log=None) -> Tuple[List[Region], List[str]]:
    samples = {r.id: _sample_run(strips[r.strip], r, 1.5, runset.junctions) for r in runset.runs}
    loops, problems = find_regions(runset, strips, samples, log=log)
    loops = _collapse_slivers(strips, runset, loops, samples, problems, log=log)
    regions = group_holes(strips, runset, loops, samples, problems)
    if log:
        log(f"  shell: {len(regions)} regions")
    return regions, problems


__all__ += ["ShellLod", "build_shell_lod", "build_regions"]


# =========================================================================== to Blender
def atlas_items(lod0: ShellLod, regions: List[Region]):
    """One atlas island per region: its chart box on LOD0 (walls included)."""
    from types import SimpleNamespace
    items = []
    for rid, box in sorted(lod0.region_box.items()):
        items.append(SimpleNamespace(strip=regions[rid].strip, sub=rid, comp=0, bbox_mm=box))
    return items


def island_key(regions: List[Region], rid: int) -> Tuple[int, int, int]:
    return (int(regions[rid].strip), int(rid), 0)


def _clamp_box(c: np.ndarray, box, e: float = 1e-4) -> np.ndarray:
    s0, s1, w0, w1 = box
    return np.stack([np.clip(c[..., 0], s0 + e, s1 - e), np.clip(c[..., 1], w0 + e, w1 - e)], axis=-1)


def assemble(lod: ShellLod, atlas, regions: List[Region], boxes=None):
    """ShellLod -> smokebomb_geometry.Assembled (metres, Blender frame, UV0 in the atlas).
    ``boxes`` (LOD0's region boxes) clamp a coarser LOD's chart points into their island."""
    from .smokebomb_geometry import Assembled, VertexFactory, MM
    X = SS.cam_to_blender(lod.verts * MM)
    fac = VertexFactory()
    ids = np.array([fac.get(x) for x in X], np.int64)
    T = ids[lod.tris]
    from .smokebomb_geometry import _fit_in_box
    luv = np.zeros(lod.corner_chart.shape)
    lanc = np.zeros(lod.corner_chart.shape)
    anchor = getattr(lod, "corner_anchor", None)
    clamped = 0
    for rid in np.unique(lod.tri_region):
        m = np.nonzero(lod.tri_region == rid)[0]
        key = island_key(regions, int(rid))
        c = lod.corner_chart[m].copy()
        if anchor is not None:
            a = anchor[m]
        else:
            a = np.repeat(c.mean(axis=1, keepdims=True), 3, axis=1)
        if boxes is not None:
            isl = atlas.islands[key]
            box = (isl.s0, isl.s1, isl.w0, isl.w1)
            for q in range(len(c)):
                f_ = _fit_in_box(c[q], box)
                if not np.allclose(f_, c[q]):
                    clamped += 1
                c[q] = f_
            a = np.repeat(c.mean(axis=1, keepdims=True), 3, axis=1)
        luv[m] = atlas.uv(key, c.reshape(-1, 2)).reshape(-1, 3, 2)
        lanc[m] = atlas.uv(key, a.reshape(-1, 2)).reshape(-1, 3, 2)
    movable = lod.tri_wall.copy() if anchor is not None else np.ones(len(luv), bool)
    luv, unt = untangle_uv(luv, lanc, movable)
    ok = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])
    sharp = [(int(ids[a]), int(ids[b])) for a, b in lod.sharp]
    V = np.array(fac.co, np.float64)
    out = Assembled(V, T[ok], luv[ok], lod.tri_strip[ok].copy(), lod.tri_wall[ok].copy(),
                    lod.tri_region[ok].copy(), sharp, np.full(len(V), -1), np.zeros((len(V), 2)))
    out.report = {"vertices": int(len(V)), "triangles": int(ok.sum()), "collapsed_dropped": int((~ok).sum()),
                  "welded_by_position": int(fac.merged), "wall_triangles": int(lod.tri_wall[ok].sum()),
                  "corners_clamped_into_island": clamped, "method": "closed height-field shell",
                  "uv_untangle": unt}
    return out


def _overlap_pairs(tris: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Overlapping UV triangle pairs (the same separating-axis rule as pipeline.qa_check)."""
    import itertools
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    area2 = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    idx = np.nonzero(area2 > 1e-12)[0]
    if len(idx) < 2:
        return np.zeros((0, 2), np.int64)
    t = tris[idx]
    mins, maxs = t.min(axis=1), t.max(axis=1)
    cell = max(float(np.median(maxs - mins)) * 2.0, 1e-4)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    buckets = defaultdict(list)
    for i in range(len(t)):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                buckets[(cx, cy)].append(i)
    pairs = set()
    for mem in buckets.values():
        if len(mem) > 1:
            pairs.update(itertools.combinations(mem, 2))
    if not pairs:
        return np.zeros((0, 2), np.int64)
    pa = np.array(sorted(pairs), np.int64)
    A, B = t[pa[:, 0]], t[pa[:, 1]]
    sep = (np.any(maxs[pa[:, 0]] <= mins[pa[:, 1]] + eps, axis=1)
           | np.any(maxs[pa[:, 1]] <= mins[pa[:, 0]] + eps, axis=1))
    for tri in (A, B):
        for k in range(3):
            e = tri[:, (k + 1) % 3] - tri[:, k]
            ax = np.stack([-e[:, 1], e[:, 0]], axis=-1)
            n = np.linalg.norm(ax, axis=1, keepdims=True)
            ax = ax / np.where(n == 0, 1.0, n)
            pa_ = np.einsum("pij,pj->pi", A, ax)
            pb_ = np.einsum("pij,pj->pi", B, ax)
            sep |= (pa_.max(axis=1) <= pb_.min(axis=1) + eps) | (pb_.max(axis=1) <= pa_.min(axis=1) + eps)
    return idx[pa[~sep]]


def untangle_uv(luv: np.ndarray, anchor: np.ndarray, movable: np.ndarray, rounds: int = 10):
    """Shrink movable UV triangles toward their anchors until no pair overlaps (a wall toward
    the edge it hangs from; a resampled triangle toward its centroid).  Texel density drops a
    little on the shrunk triangles; nothing collapses (at most 2^-rounds)."""
    luv = luv.copy()
    shrunk = np.zeros(len(luv), int)
    for r in range(rounds):
        pairs = _overlap_pairs(luv)
        if len(pairs) == 0:
            break
        sel = np.zeros(len(luv), bool)
        for a, b in pairs:
            if movable[a]:
                sel[a] = True
            if movable[b]:
                sel[b] = True
        if not sel.any():
            break
        luv[sel] = anchor[sel] + (luv[sel] - anchor[sel]) * 0.5
        shrunk[sel] += 1
    final = len(_overlap_pairs(luv))
    return luv, {"triangles_shrunk": int((shrunk > 0).sum()), "max_halvings": int(shrunk.max(initial=0)),
                 "overlapping_pairs_left": final}


def _region_containing(strips, geoms_by_strip, k: int, P: np.ndarray):
    """(region geometry, unrolled chart point) of strip k's region holding point P, or the
    nearest region of k if none holds it."""
    st = strips[k]
    e = st.evaluate(P[None, :], CHART_R_MM)
    period = st.length_rad * CHART_R_MM
    q = np.array([e["s"][0], e["w"][0]])
    best = None
    for g in geoms_by_strip.get(k, []):
        C = g.loops_chart[0]
        for sh in (0.0, period, -period, 2 * period, -2 * period):
            qq = q + np.array([sh, 0.0])
            if _in_poly(qq[None, :], g.loops_chart)[0]:
                return g, qq
            d = float(_dist_to_polys(qq[None, :], g.loops_chart)[0])
            if best is None or d < best[0]:
                best = (d, g, qq)
    if best is None:
        return None, q
    return best[1], best[2]


def resample_lod(strips, hm: HeightModel, lod0: ShellLod, regions: List[Region], freq: int = 5,
                 level: int = 2):
    """LOD2: the top surface resampled on a geodesic sphere (study 6.3: 400 - 800 triangles).
    Each triangle is textured through the LOD0 island of the region on top at its centroid,
    its corners unrolled next to that region's chart and clamped into the island, so it
    reads the same texels as LOD0 and never reaches a neighbouring island."""
    from .smokebomb_mesh import geodesic_sphere
    V, F = geodesic_sphere(freq)
    f = SS.evaluate_field(strips, V, CHART_R_MM)
    top = np.maximum(f.top, 0)
    H = hm.sheet(f, V, top)
    if LOD_AVERAGE_BLEND > 0:
        # round 3: a vertex 3.5 mm from its neighbours samples the stepped tape surface at one
        # point; with round 3's thicker tape (0.65 mm) that point's height missed the steps
        # round it by up to 1.6 mm (budget 1.5).  Each vertex takes a blend of its own height
        # and the MEAN height within a third of the vertex spacing round it (the least-squares
        # surface a coarse mesh can hold)
        spacing = 2.0 * math.asin(0.5 * float(np.linalg.norm(V[F[0, 0]] - V[F[0, 1]])))
        rad = spacing / 3.0
        a = np.cross(V, np.array([0.0, 0.0, 1.0]))
        a[np.linalg.norm(a, axis=1) < 1e-6] = np.array([1.0, 0.0, 0.0])
        a = a / np.linalg.norm(a, axis=1, keepdims=True)
        b = np.cross(V, a)
        acc = H.copy()
        cnt = 1
        for k in range(8):
            ang = 2 * math.pi * k / 8
            for rr_ in (0.5 * rad, rad):
                Q = SS.normalize(V + rr_ * (math.cos(ang) * a + math.sin(ang) * b))
                fq = SS.evaluate_field(strips, Q, CHART_R_MM)
                acc = acc + hm.sheet(fq, Q, np.maximum(fq.top, 0))
                cnt += 1
        H = H + LOD_AVERAGE_BLEND * (acc / cnt - H)
    cen = SS.normalize(V[F].mean(axis=1))
    fc = SS.evaluate_field(strips, cen, CHART_R_MM)
    by_strip: Dict[int, list] = defaultdict(list)
    for g in lod0.geoms:
        by_strip[g.region.strip].append(g)
    tri_region = np.zeros(len(F), np.int64)
    charts = np.zeros((len(F), 3, 2))
    unmirrored = 0
    for ti, tri in enumerate(F):
        k = int(max(fc.top[ti], 0))
        g, qc = _region_containing(strips, by_strip, k, cen[ti])
        if g is None:
            continue
        st = strips[k]
        period = st.length_rad * CHART_R_MM
        e = st.evaluate(V[tri], CHART_R_MM)
        sc = e["s"] + period * np.round((qc[0] - e["s"]) / period)
        # round 3: a corner that lies past the strip's own edge (on its neighbour) would read
        # the island's WALL texels (the tape's dark side, unfolded outward): keep every corner
        # on the tape's face, 0.3 mm inside its edges
        hwc = np.maximum(e["half_width"] - 0.3, 0.05)
        c = np.stack([sc, np.clip(e["w"], -hwc, hwc)], axis=1)
        box = lod0.region_box[g.region.id]
        c = _clamp_box(c, box)
        ar = (c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[2, 0] - c[0, 0]) * (c[1, 1] - c[0, 1])
        if ar < 0:
            c = c[[0, 2, 1]]
            unmirrored += 1
        charts[ti] = c
        tri_region[ti] = g.region.id
    out = ShellLod(level, V * H[:, None], F.astype(np.int64), tri_region,
                   np.array([regions[r].strip for r in tri_region], np.int64),
                   np.zeros(len(F), bool), charts, [], {}, {"method": "geodesic resample",
                                                           "frequency": freq, "triangles_unmirrored": unmirrored})
    return out


__all__ += ["atlas_items", "island_key", "assemble", "resample_lod"]
