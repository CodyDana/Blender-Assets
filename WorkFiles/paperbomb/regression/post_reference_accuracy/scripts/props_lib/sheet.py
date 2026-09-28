#!/usr/bin/env python
"""props_lib.sheet - a sheet of paper as geometry: outline, grid, curl, creases, dog-ear, rim.

Deliberately generic, because the folding fan's leaf and the smoke bomb's wrapped label
are the same problem: a thin flat thing with a trimmed outline, a bend or two, and a
print on it.  ``build_sheet`` takes a ``Surface`` (the deformation), a ``Trim`` (the real
cut edge) and three UV functions, and returns a watertight quad-dominant shell - front
skin, back skin, rim ring - with UV0 already written from PAPER coordinates.

WHY PAPER COORDINATES ARE THE UV
--------------------------------
The deformation is built to be an ISOMETRY of the flat sheet.  Along the length the
centre line is integrated at unit speed through the creases, so arc length IS ``v``.
Across the width the curl lays a circular arc of arc length ``|W/2 - u|``.  The dog-ear
turns its flap RIGIDLY about the crease.  So a UV taken straight from ``(u, v)`` has
uniform texel density everywhere and needs no unwrap, no packing solver and no seam
hunt: the only seams are the card's own edge, which is where a real print's seams are.
It also means the LODs need no UV *transfer* - LOD1 and LOD2 evaluate the SAME map at
their own vertices, so their UVs agree with LOD0 exactly rather than to within a
projection tolerance.  ``props_lib.measure.cross_lod_uv_agreement`` proves that.

Curving in two directions at once is never exactly developable, and the residual is
measured rather than assumed: ``uv_stretch`` reports the worst edge-length ratio between
the mesh and its UV and the build gates on it.  The error lives only where the two
curvatures multiply - inside a crease band at the extreme side edge - which is why
``FoldSpec.half_width_mm`` is 3.5 mm and not the study's 0.5 mm fold radius.

THE OUTLINE IS SHARED WITH THE TEXTURE
--------------------------------------
``Trim`` wraps ``props_lib.paperbomb_art.card_outline_mm`` - the same polyline the art
module cuts its card mask to.  Boundary grid nodes are RAY-SNAPPED onto it, so a torn
lobe is in the silhouette and in the texture at the same millimetre, and because UV0 is
the paper coordinate the snap carries its own UV with it.

THE 1 nm VERTEX FACTORY
-----------------------
Every position goes through ``VertexFactory``, keyed on the position rounded to a
nanometre.  Two vertices that should be one ARE one, and a seam can never open because
two code paths computed the same corner to slightly different floats.  Geometry here is
authored, never operated on: no ``bmesh.ops.bevel`` (it silently clamps), no Decimate.

THE CORNER CLIPS AND THE DOG-EAR ARE EXACT MESH DIAGONALS
---------------------------------------------------------
The grid always carries lines at ``c`` and ``W - c`` / ``H - c`` (the 45 deg clip) and at
``2c`` in from the bottom-right corner, and the cells between them are square, so both
45 deg lines fall on cell diagonals at EVERY LOD.  That is why the dog-ear's leg is 2c
(15.2 mm) rather than the study's 12 mm: see ``spec.DogEarSpec``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

MM = 0.001                              # Blender metres per millimetre
KEY = 1e-9                              # the vertex factory's 1 nm key, in metres
FD = 5e-3                               # finite-difference step for the frame, mm
#: boundary points per mm inside the 5 mm nick; four is enough to read as a bite
NICK_REFINE_PER_MM = 0.8


# ===========================================================================
# 1.  The vertex factory
# ===========================================================================

class VertexFactory:
    """Positions in METRES, welded at 1 nm.  Nothing else creates a vertex."""

    def __init__(self) -> None:
        self._index: Dict[Tuple[int, int, int], int] = {}
        self.co: List[Tuple[float, float, float]] = []
        self.uv: List[Tuple[float, float]] = []
        self.paper: List[Tuple[float, float]] = []
        self.side: List[str] = []
        self.welds = 0

    def add(self, co, uv, paper, side: str) -> int:
        key = (int(round(co[0] / KEY)), int(round(co[1] / KEY)), int(round(co[2] / KEY)))
        found = self._index.get(key)
        if found is not None:
            self.welds += 1
            return found
        index = len(self.co)
        self._index[key] = index
        self.co.append((float(co[0]), float(co[1]), float(co[2])))
        self.uv.append((float(uv[0]), float(uv[1])))
        self.paper.append((float(paper[0]), float(paper[1])))
        self.side.append(side)
        return index

    def __len__(self) -> int:
        return len(self.co)


# ===========================================================================
# 2.  The deformation
# ===========================================================================

def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def radius_for_sagitta(half_width: float, sagitta: float) -> float:
    """Solve ``s = R (1 - cos(h/R))`` for R by Newton, from a parabolic first guess."""
    h, s = float(half_width), float(sagitta)
    if s <= 1e-9:
        return 1e9
    r = h * h / (2.0 * s)
    for _ in range(80):
        f = r * (1.0 - math.cos(h / r)) - s
        d = 1.0 - math.cos(h / r) - (h / r) * math.sin(h / r)
        if abs(d) < 1e-16:
            break
        step = f / d
        r -= step
        if abs(step) < 1e-13:
            break
    return r


@dataclass
class Surface:
    """The mid-surface of the sheet: paper ``(u, v)`` in mm -> world position in mm.

    Composed of arc-length-preserving moves, in this order:

    1.  the CENTRE LINE is integrated along ``v`` at unit speed through the creases, so
        ``X(v)`` and ``Z(v)`` come out of ``theta(u, v)``.  The creases WANDER, so the
        integration is per column and cached;
    2.  the CURL lays a circular arc of arc length ``|W/2 - u|`` across the local tangent
        plane, bulging toward +Z - the printed face is CONCAVE, because a sheet curls
        toward the side that dries last (study 6, sourced);
    3.  the DOG-EAR turns its flap rigidly about the crease line ``u + v = const``.

    The frame is taken by central differences on the finished position, so the dog-ear
    and the creases are handled without a second analytic derivation to get wrong.
    """

    width_mm: float
    height_mm: float
    curl_sagitta_mm: float = 2.0
    curl_deepen_sagitta_mm: float = 3.0
    curl_deepen_run_mm: float = 40.0
    #: how much of the curl relaxes at each crease, and over what distance.  See
    #: ``props_lib.spec.CurlSpec.crease_relief``: a cupped sheet cannot be folded across
    #: its cup without strain, and real paper answers that by popping the cup out at the
    #: crease.  The ramp is long on purpose - ``|Tv|^2 = (1 - lift*dtheta/dv)^2 + lift_v^2``,
    #: so relaxing the curl over a couple of millimetres would replace one stretch term
    #: with another exactly as large.
    curl_crease_relief: float = 0.0
    curl_crease_sigma_mm: float = 13.0
    #: a gentle whole-length bow, so the panels between the creases are not rigid planes
    bow_deg: float = 0.0
    bow_cycles: float = 1.6
    #: (v_mm, turn_deg, half_width_mm, wander_mm)
    folds: Sequence[Tuple[float, float, float, float]] = ()
    #: (leg_mm, fold_back_deg, soften_mm) or None
    dog_ear: Optional[Tuple[float, float, float]] = None
    seed: int = 20260919
    step_mm: float = 0.05

    def __post_init__(self) -> None:
        rng = np.random.default_rng([int(self.seed), 0xF01D])
        self._wander_ctrl = [rng.uniform(-0.5, 0.5, 7) for _ in self.folds]
        self._columns: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
        n = int(round(self.height_mm / self.step_mm)) + 1
        self._vs = np.linspace(0.0, self.height_mm, n)
        self._r0 = radius_for_sagitta(self.width_mm * 0.5, self.curl_sagitta_mm)
        self._r1 = radius_for_sagitta(self.width_mm * 0.5, self.curl_deepen_sagitta_mm)

    # ---- creases ---------------------------------------------------------

    def _wander(self, u: float, k: int) -> float:
        ctrl = self._wander_ctrl[k]
        t = min(max(u / self.width_mm, 0.0), 1.0) * (len(ctrl) - 1)
        j = min(int(math.floor(t)), len(ctrl) - 2)
        f = t - j
        f = f * f * (3.0 - 2.0 * f)
        return float(ctrl[j] * (1 - f) + ctrl[j + 1] * f) * self.folds[k][3]

    def _column(self, u: float):
        """(v, X, Z, theta) along the centre line of column ``u``, cached."""
        key = int(round(u * 1e6))
        hit = self._columns.get(key)
        if hit is not None:
            return hit
        v = self._vs
        theta = np.zeros_like(v)
        for k, (vf, turn, half, _w) in enumerate(self.folds):
            vc = vf + self._wander(u, k)
            theta = theta + math.radians(turn) * _smoothstep((v - (vc - half)) / (2.0 * half))
        if self.bow_deg:
            # a slow bow down the length, so no stretch of the card is a rigid plane.
            # Its dtheta/dv is about 0.0025 /mm, which costs well under 1 % of metric.
            phase = 0.7 + 0.25 * math.sin(u / max(self.width_mm, 1e-6) * math.pi)
            theta = theta + math.radians(self.bow_deg) * np.sin(
                2.0 * math.pi * (v / self.height_mm) * self.bow_cycles + phase)
        dx = -np.cos(theta)
        dz = np.sin(theta)
        h = v[1] - v[0]
        x = np.concatenate(([0.0], np.cumsum(0.5 * (dx[1:] + dx[:-1]) * h)))
        z = np.concatenate(([0.0], np.cumsum(0.5 * (dz[1:] + dz[:-1]) * h)))
        vc = self.height_mm * 0.5
        x = x - np.interp(vc, v, x)
        z = z - np.interp(vc, v, z)
        out = (v, x, z, theta)
        self._columns[key] = out
        return out

    def curl_radius(self, v):
        """R(v): the curl tightens over the last ``deepen_run_mm`` at the bottom end."""
        v = np.asarray(v, np.float64)
        t = _smoothstep((v - (self.height_mm - self.curl_deepen_run_mm)) / self.curl_deepen_run_mm)
        k = (1.0 / self._r0) * (1.0 - t) + (1.0 / self._r1) * t      # blend CURVATURE
        if self.curl_crease_relief > 0.0 and self.folds:
            sig = max(self.curl_crease_sigma_mm, 1e-6)
            dip = np.zeros_like(v)
            for vf, _turn, _half, _w in self.folds:
                dip = np.maximum(dip, np.exp(-((v - vf) / sig) ** 2))
            k = k * (1.0 - self.curl_crease_relief * dip)
        return 1.0 / np.maximum(k, 1e-9)

    # ---- positions -------------------------------------------------------

    def _base_position(self, u, v) -> np.ndarray:
        """Centre line + curl, without the dog-ear.  ``u`` may be an array."""
        u = np.atleast_1d(np.asarray(u, np.float64))
        v = np.atleast_1d(np.asarray(v, np.float64))
        u, v = np.broadcast_arrays(u, v)
        out = np.empty(u.shape + (3,), np.float64)
        flat = u.ravel()
        vflat = v.ravel()
        res = out.reshape(-1, 3)
        r = self.curl_radius(vflat)
        s = (self.width_mm * 0.5) - flat
        a = s / r
        y = r * np.sin(a)
        lift = r * (1.0 - np.cos(a))
        for uu in np.unique(flat):
            sel = flat == uu
            vg, xg, zg, tg = self._column(float(uu))
            x0 = np.interp(vflat[sel], vg, xg)
            z0 = np.interp(vflat[sel], vg, zg)
            th = np.interp(vflat[sel], vg, tg)
            res[sel, 0] = x0 + lift[sel] * np.sin(th)
            res[sel, 1] = y[sel]
            res[sel, 2] = z0 + lift[sel] * np.cos(th)
        return out

    def _base_frame(self, u, v):
        p = self._base_position(u, v)
        tu = (self._base_position(np.asarray(u) + FD, v)
              - self._base_position(np.asarray(u) - FD, v)) / (2 * FD)
        tv = (self._base_position(u, np.asarray(v) + FD)
              - self._base_position(u, np.asarray(v) - FD)) / (2 * FD)
        n = -np.cross(tu, tv)
        n = n / np.linalg.norm(n, axis=-1, keepdims=True)
        return p, tu, tv, n

    def position(self, u, v) -> np.ndarray:
        """World position of the MID-SURFACE in millimetres, dog-ear included."""
        u = np.atleast_1d(np.asarray(u, np.float64))
        v = np.atleast_1d(np.asarray(v, np.float64))
        u, v = np.broadcast_arrays(u, v)
        p = self._base_position(u, v)
        if not self.dog_ear:
            return p
        leg, deg, soften = self.dog_ear
        c = self.width_mm + self.height_mm - leg
        d = ((u + v) - c) / math.sqrt(2.0)
        if not np.any(d > 0.0):
            return p
        dd = np.maximum(d, 0.0)
        fu = u - dd / math.sqrt(2.0)
        fv = v - dd / math.sqrt(2.0)
        fp, ftu, ftv, fn = self._base_frame(fu, fv)
        # the in-plane direction of increasing d, unit length
        pdir = ftu / np.linalg.norm(ftu, axis=-1, keepdims=True) \
            + ftv / np.linalg.norm(ftv, axis=-1, keepdims=True)
        pdir = pdir / np.linalg.norm(pdir, axis=-1, keepdims=True)
        # A TRUE CYLINDRICAL BEND, not a rotated ray.
        #
        # The first version placed the flap at ``fp + d * (pdir cos phi - n sin phi)``
        # with phi ramping over the soften distance - a ray of fixed length d swung
        # through a varying angle.  That is not an isometry: the metric along d picks up
        # ``sqrt(1 + (d dphi/dd)^2)``, and for a smoothstep ramp ``d dphi/dd`` is about
        # 1.37 at the middle of the band WHATEVER the soften distance, so the paper
        # stretches by tens of per cent right on the crease and no amount of softening
        # helps.  It only stayed inside the reported numbers because the grid straddles
        # the band.  A real folded corner is a cylinder: the sheet rolls round a radius
        # ``soften / Phi`` and then runs straight.  Arc length is preserved exactly, so
        # the print does not stretch and the fold can be as tight as it likes.
        phi_max = math.radians(deg)
        r = max(soften, 1e-6) / max(abs(phi_max), 1e-9)
        rolled = np.minimum(dd, soften)
        beyond = np.maximum(dd - soften, 0.0)
        phi = np.sign(phi_max) * rolled / r
        along = r * np.sin(np.abs(phi)) + beyond * math.cos(phi_max)
        normal = r * (1.0 - np.cos(phi)) + beyond * math.sin(abs(phi_max))
        turned = (fp + along[..., None] * pdir
                  - np.sign(phi_max) * normal[..., None] * fn)
        return np.where((d > 0.0)[..., None], turned, p)

    def frame(self, u, v):
        """``(P, Tu, Tv, N)`` at paper ``(u, v)``: mm and unit vectors, dog-ear included.

        ``N`` is the outward normal of the PRINTED face.
        """
        u = np.atleast_1d(np.asarray(u, np.float64))
        v = np.atleast_1d(np.asarray(v, np.float64))
        u, v = np.broadcast_arrays(u, v)
        p = self.position(u, v)
        tu = (self.position(u + FD, v) - self.position(u - FD, v)) / (2 * FD)
        tv = (self.position(u, v + FD) - self.position(u, v - FD)) / (2 * FD)
        n = -np.cross(tu, tv)
        ln = np.linalg.norm(n, axis=-1, keepdims=True)
        n = n / np.where(ln > 1e-12, ln, 1.0)
        return p, tu, tv, n

    def skin(self, u, v, half_t: float, side: str) -> np.ndarray:
        """The front (+) or back (-) skin position, millimetres."""
        p, _tu, _tv, n = self.frame(u, v)
        return p + n * (half_t if side == "front" else -half_t)


# ===========================================================================
# 3.  The trimmed outline
# ===========================================================================

def nominal_outline(width: float, height: float, clip: float):
    """The card box with its four 45 deg corner clips, as a closed polyline."""
    w, h, c = width, height, clip
    return np.array([(c, 0.0), (w - c, 0.0), (w, c), (w, h - c),
                     (w - c, h), (c, h), (0.0, h - c), (0.0, c), (c, 0.0)], np.float64)


@dataclass
class Trim:
    """The card's real cut edge as a closed polyline in paper millimetres.

    The authority is ``paperbomb_art.card_outline_mm`` - the same function the texture is
    drawn to.  This class only answers the geometric question the grid needs: where does
    the real edge sit on the ray that leaves the nominal box at this point?
    """

    outline: np.ndarray
    width_mm: float
    height_mm: float

    def __post_init__(self) -> None:
        o = np.asarray(self.outline, np.float64)
        if np.hypot(*(o[0] - o[-1])) > 1e-9:
            o = np.vstack([o, o[0]])
        self.outline = o
        self._a = o[:-1]
        self._seg = o[1:] - o[:-1]

    def snap(self, point, inward, reach_mm: float = 8.0):
        """Move one nominal boundary point onto the real outline along ``-inward``.

        The ray starts ``reach_mm`` OUTSIDE and walks in; the first crossing is the
        silhouette.  Every deviation on this outline goes inward (the art module keeps
        the card inside its 70 x 156 mm box), so the first crossing is the right one and
        a lobe is never skipped.
        """
        d = np.asarray(inward, np.float64)
        d = d / np.linalg.norm(d)
        o = np.asarray(point, np.float64) - d * reach_mm
        a, seg = self._a, self._seg
        den = d[0] * (-seg[:, 1]) - d[1] * (-seg[:, 0])
        ok = np.abs(den) > 1e-12
        if not np.any(ok):
            return np.asarray(point, np.float64)
        rhs = a - o
        t = np.full(len(a), np.inf)
        s = np.zeros(len(a))
        t[ok] = (rhs[ok, 0] * (-seg[ok, 1]) - rhs[ok, 1] * (-seg[ok, 0])) / den[ok]
        s[ok] = (d[0] * rhs[ok, 1] - d[1] * rhs[ok, 0]) / den[ok]
        good = ok & (t > 1e-9) & (s >= -1e-9) & (s <= 1.0 + 1e-9)
        if not np.any(good):
            return np.asarray(point, np.float64)
        return o + d * float(t[good].min())

    def bite_span(self, height: float, clip: float, depth_mm: float = 0.25):
        """Where the bottom edge pulls in: the torn stretch, read off the outline itself."""
        o = self.outline
        w = self.width_mm
        on_bottom = (o[:, 1] > height - 4.0) & (o[:, 0] > clip + 0.5) & (o[:, 0] < w - clip - 0.5)
        bitten = on_bottom & (o[:, 1] < height - depth_mm)
        if not np.any(bitten):
            return (height, height)
        xs = o[bitten, 0]
        return (float(xs.min()) - 0.6, float(xs.max()) + 0.6)


# ===========================================================================
# 4.  The grid
# ===========================================================================

@dataclass
class GridPlan:
    u: List[float]
    v: List[float]
    width: float
    height: float
    clip: float
    dog_ear_leg: Optional[float]

    @property
    def nu(self) -> int:
        return len(self.u) - 1

    @property
    def nv(self) -> int:
        return len(self.v) - 1


def _merge(base: Sequence[float], forced: Sequence[float], lo: float, hi: float,
           min_gap: float) -> List[float]:
    """``forced`` lines survive; a base line within ``min_gap`` of one is dropped.

    Two FORCED lines closer than ``min_gap`` are collapsed to the first as well - a coarse
    LOD can otherwise end up with a 0.6 mm row between, say, a crease shoulder and a
    boundary the shape also wants, which is a sliver in every cell across the card.
    """
    want = sorted(set(round(float(f), 6) for f in forced if lo - 1e-9 <= f <= hi + 1e-9))
    kept_forced: List[float] = []
    for f in want:
        if not kept_forced or f - kept_forced[-1] >= min_gap:
            kept_forced.append(f)
    keep = [round(float(b), 6) for b in base
            if lo - 1e-9 <= b <= hi + 1e-9 and all(abs(b - f) >= min_gap for f in kept_forced)]
    return sorted(set(keep + kept_forced))


def plan_grid(spec, lod) -> GridPlan:
    """Grid lines for one LOD.

    Even spacing, plus the lines the shape must have: the corner clip at ``c`` and
    ``W - c`` / ``H - c`` so each 45 deg clip is one cell's diagonal, the dog-ear's
    ``2c`` lines so the crease is two cells' diagonals, the crease shoulders, and a line
    either side of the nick.
    """
    w, h, c = spec.width_mm, spec.height_mm, spec.corner_clip_mm
    leg = spec.dog_ear.leg_mm

    fu = [c, w - c]
    fv = [c, h - c]
    if lod.dog_ear:
        fu.append(w - leg)                    # = w - 2c: the crease's far end
        fv.append(h - leg)
    if lod.folds:
        for f in spec.folds:
            fv += [f.v_mm - f.half_width_mm, f.v_mm + f.half_width_mm]
    # The nick needs BOUNDARY refinement, not grid lines: the refiner takes whichever
    # right-edge cells overlap it.  Forcing rows there put a 0.6 mm row across the whole
    # card at LOD1, where the nick's line landed beside a crease shoulder.

    base_u = np.linspace(0.0, w, max(3, lod.columns + 1)).tolist()
    base_v = np.linspace(0.0, h, max(3, lod.rows + 1)).tolist()
    u = [0.0] + _merge(base_u, fu, 0.0, w, min_gap=2.0) + [w]
    v = [0.0] + _merge(base_v, fv, 0.0, h, min_gap=2.6) + [h]
    u = sorted(set(round(x, 6) for x in u))
    v = sorted(set(round(x, 6) for x in v))
    return GridPlan(u=u, v=v, width=w, height=h, clip=c,
                    dog_ear_leg=leg if lod.dog_ear else None)


# ===========================================================================
# 5.  Building the shell
# ===========================================================================

@dataclass
class SheetMesh:
    verts: List[Tuple[float, float, float]]
    faces: List[Tuple[int, ...]]
    loop_uv: List[List[Tuple[float, float]]]
    paper: List[Tuple[float, float]]
    sharp_edges: List[Tuple[int, int]]
    groups: Dict[str, List[int]] = field(default_factory=dict)
    report: Dict[str, object] = field(default_factory=dict)

    @property
    def triangles(self) -> int:
        return sum(len(f) - 2 for f in self.faces)


def _inside_nominal(u: float, v: float, w: float, h: float, c: float) -> bool:
    eps = 1e-6
    return (u + v >= c - eps and (w - u) + v >= c - eps
            and u + (h - v) >= c - eps and (w - u) + (h - v) >= c - eps)


def _split_fan(chain: List[object], r0: object, r1: object) -> List[Tuple[object, object, object]]:
    """Triangulate a cell whose boundary edge carries extra points.

    The cell is the polygon ``chain + [r0, r1]`` in positive (paper-space) order, so
    ``r1`` is the far corner next to the chain's START and ``r0`` the one next to its
    END.  Each far corner fans over its own half of the chain and one triangle bridges
    them, so no sliver spans the whole cell.  ``len(chain) + 1`` triangles for a
    ``len(chain) + 2``-gon, which is what a polygon needs.
    """
    k = len(chain) - 1
    if k <= 0:
        return []
    m = k // 2
    tris: List[Tuple[object, object, object]] = [(r1, chain[i], chain[i + 1]) for i in range(m)]
    tris.append((r1, chain[m], r0))
    tris += [(r0, chain[i], chain[i + 1]) for i in range(m, k)]
    return tris


def build_sheet(spec, lod, surface: Surface, trim: Trim, atlas,
                seed: int = 20260919) -> SheetMesh:
    """Front skin, back skin and rim ring for one LOD.

    ``atlas`` is a ``props_lib.atlas.AtlasPlan``: it supplies ``uv_front(u, v)``,
    ``uv_back(u, v)`` and ``uv_rim(s_mm, t, perimeter, strip)``, so the UV is written
    straight from the paper coordinate and no unwrap ever runs.
    """
    uv_front, uv_back = atlas.uv_front, atlas.uv_back
    plan = plan_grid(spec, lod)
    w, h, c = plan.width, plan.height, plan.clip
    half_t = spec.half_thickness_mm
    nu, nv = plan.nu, plan.nv

    tear_lo, tear_hi = trim.bite_span(h, c)
    nick_lo = spec.nick_v_mm - 3.0
    nick_hi = spec.nick_v_mm + 3.0

    # ---- node table, boundary nodes snapped to the real outline ----------
    paper: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for iv, vv in enumerate(plan.v):
        for iu, uu in enumerate(plan.u):
            if not _inside_nominal(uu, vv, w, h, c):
                continue                                   # the four clipped corners
            on_u = iu == 0 or iu == nu
            on_v = iv == 0 or iv == nv
            if on_u or on_v:
                inward = np.array([(1.0 if iu == 0 else -1.0) if on_u else 0.0,
                                   (1.0 if iv == 0 else -1.0) if on_v else 0.0])
                snapped = trim.snap(np.array([uu, vv]), inward)
                paper[(iu, iv)] = (float(snapped[0]), float(snapped[1]))
            else:
                paper[(iu, iv)] = (uu, vv)

    # the four clip corners: the diagonal's two ends are ordinary nodes already.

    # ---- extra boundary points where the edge is torn or nicked ----------
    extras: Dict[Tuple[Tuple[int, int], Tuple[int, int]], List[Tuple[float, float]]] = {}

    def refine(a_key, b_key, a_paper, b_paper, inward, per_mm, span):
        """Insert boundary points on the edge a->b, CONCENTRATED inside ``span``.

        ``span`` is the (lo, hi) of the interesting stretch in the edge's own driving
        coordinate.  Refining the whole edge instead - which is what this did first -
        spent 12 points on a 17 mm LOD1 cell to resolve a 5 mm nick, and cost more
        triangles at LOD1 than the whole LOD2.
        """
        if per_mm <= 0.0:
            return
        a = np.array(a_paper, np.float64)
        b = np.array(b_paper, np.float64)
        length = float(np.linalg.norm(b - a))
        if length < 1e-6:
            return
        axis = 0 if abs(b[0] - a[0]) > abs(b[1] - a[1]) else 1
        lo, hi = min(span), max(span)
        t_lo = (lo - a[axis]) / (b[axis] - a[axis])
        t_hi = (hi - a[axis]) / (b[axis] - a[axis])
        t_lo, t_hi = min(t_lo, t_hi), max(t_lo, t_hi)
        t_lo = min(max(t_lo, 0.0), 1.0)
        t_hi = min(max(t_hi, 0.0), 1.0)
        n = int(round((t_hi - t_lo) * length * per_mm))
        if n < 2:
            return
        ts = []
        if t_lo > 0.03:
            ts.append(t_lo)
        ts += [t_lo + (t_hi - t_lo) * k / n for k in range(1, n)]
        if t_hi < 0.97:
            ts.append(t_hi)
        pts = []
        for t in sorted(set(round(x, 9) for x in ts)):
            if t <= 1e-6 or t >= 1.0 - 1e-6:
                continue
            nominal = a + (b - a) * t
            pts.append(tuple(float(x) for x in trim.snap(nominal, inward)))
        if pts:
            extras[(a_key, b_key)] = pts

    if lod.tear_lobes is None or lod.tear_lobes > 0:
        for iu in range(nu):
            a, b = (iu, nv), (iu + 1, nv)
            if a not in paper or b not in paper:
                continue
            u0, u1 = plan.u[iu], plan.u[iu + 1]
            if u1 <= tear_lo or u0 >= tear_hi:
                continue
            refine(a, b, (u0, h), (u1, h), np.array([0.0, -1.0]),
                   lod.tear_refine_per_mm, (tear_lo, tear_hi))
    if lod.nick:
        for iv in range(nv):
            a, b = (nu, iv), (nu, iv + 1)
            if a not in paper or b not in paper:
                continue
            v0, v1 = plan.v[iv], plan.v[iv + 1]
            if v1 <= nick_lo or v0 >= nick_hi:
                continue
            refine(a, b, (w, v0), (w, v1), np.array([-1.0, 0.0]),
                   NICK_REFINE_PER_MM, (nick_lo, nick_hi))

    # ---- vertices --------------------------------------------------------
    factory = VertexFactory()
    fi: Dict[object, int] = {}
    bi: Dict[object, int] = {}

    def make(key, pu, pv):
        p, _tu, _tv, n = surface.frame(np.array([pu]), np.array([pv]))
        fi[key] = factory.add((p[0] + n[0] * half_t) * MM, uv_front(pu, pv), (pu, pv), "front")
        bi[key] = factory.add((p[0] - n[0] * half_t) * MM, uv_back(pu, pv), (pu, pv), "back")

    for key, (pu, pv) in paper.items():
        make(key, pu, pv)
    for edge, pts in extras.items():
        for i, (pu, pv) in enumerate(pts):
            make((edge, i), pu, pv)

    faces: List[Tuple[int, ...]] = []
    loop_uv: List[List[Tuple[float, float]]] = []
    groups: Dict[str, List[int]] = {"front": [], "back": [], "rim": []}

    def add_face(idx: Sequence[int], uvs: Sequence[Tuple[float, float]], group: str):
        faces.append(tuple(idx))
        loop_uv.append([tuple(x) for x in uvs])
        groups[group].append(len(faces) - 1)

    def skin_pair(loop_keys: Sequence[object]):
        """Emit one paper-space loop as front faces and their mirrored back faces.

        ``loop_keys`` is in POSITIVE paper order (u right, v down: TL, TR, BR, BL), whose
        3D normal comes out -Z at the flat centre - so that winding is the BACK, and the
        front is its reverse.  Worked out once, here, and re-measured by ``verify``.

        THE TWO SKINS ARE TRIANGULATED THE SAME WAY, AND THAT IS NOT COSMETIC.

        A four-sided cell on a curled, creased sheet is not planar, so which diagonal it
        is split along decides where its surface actually lies.  Emitted as quads, the
        front loop is the reverse of the back loop, Blender's tessellator picks each
        one's diagonal from its own vertex order, and on a warped cell the two skins end
        up split the OTHER WAY from each other - at which point two surfaces 0.15 mm
        apart cross.  The shipped build had eight such pairs in LOD0 (sixteen in LOD1,
        nine in LOD2), and the Cycles AO bake found every one of them: a ray leaving the
        front skin hit the back skin immediately, and the whole UV cell came back almost
        black.  That is the source of the hard-edged square patches of speckle a reviewer
        spotted at 4x in ``Renders/PaperBomb/paperbomb_front.png`` - they are UV QUADS,
        which is why their edges are straight and axis-aligned.

        Emitting explicit triangles fixes it at the root: each front triangle is the
        exact normal-offset twin of a back triangle over the same paper coordinates, so
        the two skins are parallel everywhere by construction and cannot intersect
        whatever the sheet does.  The TRIANGLE count is unchanged - a quad was always
        going to be two triangles - so every LOD band, every screen size and the whole
        collision story are untouched.  ``measure.shell_self_intersections`` is the gate.
        """
        keys = list(loop_keys)
        if len(keys) <= 3:
            tris = [keys]
        else:
            # fan from the first key: ONE chosen diagonal, used by both skins
            tris = [[keys[0], keys[i], keys[i + 1]] for i in range(1, len(keys) - 1)]
        for tri in tris:
            b = [bi[k] for k in tri]
            f = [fi[k] for k in reversed(tri)]
            add_face(f, [factory.uv[i] for i in f], "front")
            add_face(b, [factory.uv[i] for i in b], "back")

    # ---- cells -----------------------------------------------------------
    crease_c = (w + h - plan.dog_ear_leg) if plan.dog_ear_leg else None
    crease_cells = 0
    for iv in range(nv):
        for iu in range(nu):
            quad = [(iu, iv), (iu + 1, iv), (iu + 1, iv + 1), (iu, iv + 1)]   # TL TR BR BL
            present = [q for q in quad if q in paper]
            if len(present) < 3:
                continue
            if len(present) == 3:
                skin_pair(present)                     # the clipped corner, in quad order
                continue
            bottom_key = ((iu, nv), (iu + 1, nv))
            right_key = ((nu, iv), (nu, iv + 1))
            if iv == nv - 1 and bottom_key in extras:
                pts = extras[bottom_key]               # stored left -> right
                # the cell's bottom edge runs BR -> BL in positive order, so reverse
                chain = ([quad[2]] + [(bottom_key, i) for i in reversed(range(len(pts)))]
                         + [quad[3]])
                for tri in _split_fan(chain, quad[0], quad[1]):     # r0 = TL, r1 = TR
                    skin_pair(list(tri))
                continue
            if iu == nu - 1 and right_key in extras:
                pts = extras[right_key]                # stored top -> bottom
                # the cell's right edge runs TR -> BR in positive order
                chain = [quad[1]] + [(right_key, i) for i in range(len(pts))] + [quad[2]]
                for tri in _split_fan(chain, quad[3], quad[0]):     # r0 = BL, r1 = TL
                    skin_pair(list(tri))
                continue
            if crease_c is not None and _crease_cell(plan, iu, iv, crease_c):
                # split along the BL-TR anti-diagonal so the dog-ear crease is a real edge
                skin_pair([quad[0], quad[1], quad[3]])
                skin_pair([quad[1], quad[2], quad[3]])
                crease_cells += 1
                continue
            skin_pair(quad)

    # ---- the boundary ring, and the rim ----------------------------------
    ring = _boundary_ring(plan, paper, extras, nu, nv)
    ring_paper = []
    for k in ring:
        if k in paper:
            ring_paper.append(paper[k])
        else:
            edge, i = k
            ring_paper.append(extras[edge][i])

    s = [0.0]
    for i in range(1, len(ring_paper) + 1):
        a = ring_paper[i - 1]
        b = ring_paper[i % len(ring_paper)]
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    perimeter = s[-1]

    # One strip per QUAD, chosen from its start, and the strip's row range taken from its
    # own first and last ring vertex - a quad that straddled a strip boundary would put
    # its two ends 40 px apart in U and sample the gap between them.
    quad_strip = [atlas.rim_strip_index(s[i], perimeter) for i in range(len(ring))]
    bounds: Dict[int, List[float]] = {}
    for i, k in enumerate(quad_strip):
        b = bounds.setdefault(k, [s[i], s[i + 1]])
        b[0] = min(b[0], s[i])
        b[1] = max(b[1], s[i + 1])

    sharp: List[Tuple[int, int]] = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        fa, fb, ba, bb = fi[a], fi[b], bi[a], bi[b]
        strip = quad_strip[i]
        s0, s1 = bounds[strip]
        uvs = [atlas.uv_rim(s[i], 1.0, s0, s1, strip),
               atlas.uv_rim(s[i + 1], 1.0, s0, s1, strip),
               atlas.uv_rim(s[i + 1], 0.0, s0, s1, strip),
               atlas.uv_rim(s[i], 0.0, s0, s1, strip)]
        add_face([fa, fb, bb, ba], uvs, "rim")
        sharp.append((fa, fb))
        sharp.append((ba, bb))

    mesh = SheetMesh(verts=factory.co, faces=faces, loop_uv=loop_uv, paper=factory.paper,
                     sharp_edges=sharp, groups=groups)
    mesh.report = {
        "lod": lod.level,
        "grid_lines": {"u": len(plan.u), "v": len(plan.v)},
        "cells": {"u": nu, "v": nv},
        "boundary_points": len(ring),
        "perimeter_mm": round(perimeter, 3),
        "tear_span_mm": [round(tear_lo, 2), round(tear_hi, 2)],
        "refined_edges": len(extras),
        "extra_boundary_points": sum(len(p) for p in extras.values()),
        "crease_cells_split": crease_cells,
        "welds": factory.welds,
        "vertices": len(factory),
        "triangles": mesh_triangles(faces),
        "faces": {k: len(v) for k, v in groups.items()},
    }
    return mesh


def mesh_triangles(faces) -> int:
    return sum(len(f) - 2 for f in faces)


def _crease_cell(plan: GridPlan, iu: int, iv: int, crease_c: float) -> bool:
    """True when the dog-ear crease ``u + v = crease_c`` is this cell's anti-diagonal."""
    u0, u1 = plan.u[iu], plan.u[iu + 1]
    v0, v1 = plan.v[iv], plan.v[iv + 1]
    return abs((u0 + v1) - crease_c) < 1e-6 and abs((u1 + v0) - crease_c) < 1e-6


def _boundary_ring(plan: GridPlan, paper, extras, nu: int, nv: int) -> List[object]:
    """The closed boundary loop, counter-clockwise in paper space, extras included."""
    ring: List[object] = []

    def push(key):
        if not ring or ring[-1] != key:
            ring.append(key)

    def edge(a, b):
        """Walk a -> b, inserting the refinement points of that edge in walking order.

        ``extras`` is keyed by the edge as the REFINER made it (left to right along the
        bottom, top to bottom down the right side); the ring walks the bottom the other
        way, so the reversed key is looked up too and its points come out reversed.
        """
        push(a)
        pts = extras.get((a, b))
        if pts:
            for i in range(len(pts)):
                push(((a, b), i))
        else:
            pts = extras.get((b, a))
            if pts:
                for i in reversed(range(len(pts))):
                    push(((b, a), i))
        push(b)

    # top edge, left to right
    for iu in range(nu):
        if (iu, 0) in paper and (iu + 1, 0) in paper:
            edge((iu, 0), (iu + 1, 0))
    # the top-right clip
    push((nu - 1, 0))
    push((nu, 1))
    # right edge
    for iv in range(1, nv):
        if (nu, iv) in paper and (nu, iv + 1) in paper:
            edge((nu, iv), (nu, iv + 1))
    push((nu, nv - 1))
    push((nu - 1, nv))
    # bottom edge, right to left
    for iu in range(nu - 1, 0, -1):
        if (iu, nv) in paper and (iu - 1, nv) in paper:
            edge((iu, nv), (iu - 1, nv))
    push((1, nv))
    push((0, nv - 1))
    # left edge, bottom to top
    for iv in range(nv - 1, 1, -1):
        if (0, iv) in paper and (0, iv - 1) in paper:
            edge((0, iv), (0, iv - 1))
    push((0, 1))
    push((1, 0))
    # drop the wrap-around duplicate
    out: List[object] = []
    for k in ring:
        if not out or out[-1] != k:
            out.append(k)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


__all__ = ["MM", "Surface", "Trim", "GridPlan", "SheetMesh", "VertexFactory",
           "build_sheet", "plan_grid", "nominal_outline", "radius_for_sagitta",
           "mesh_triangles"]
