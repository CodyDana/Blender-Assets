#!/usr/bin/env python
"""props_lib.flashbang_geom - SM_Flashbang's parts as REAL GEOMETRY, generated per LOD (round 1).

numpy only (no bpy): every part is built into a ``MeshBuilder`` as vertices (mm), faces, per-corner UV PARAMETERS in
mm on a named UV island, a part tag, a LOOK id (what the painter paints there) and a material slot.  The islands are
packed once (``pack_islands``) over the union of all LODs, so LOD0/1/2 share one atlas.  ``to_blender`` lives in the
build script (bpy).

Nothing here is a height field or a baked outline: the holes are cut through a walled tube with the brass tube
behind, the sleeve step, the chamfers, the base cap's 12 soft flats, its raised notched rim lip and stepped disc, the
collar, the square fuze housing, the top plate and its curled arm, the hinge block and knuckle, the pin boss and eye,
the lever (a swept plate with its curl, joggle and bent tip) and the tilted pull ring are all modelled.

Orientation: every part is built with a HINT (the direction its outward normal must face) and each face is flipped
to agree with it, so the shell is consistently outward.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .flashbang_spec import FLASHBANG, FlashbangSpec, LodQuality

# LOOK ids (the painter's materials) and their FBX slot
LOOK_PAINT, LOOK_STEEL, LOOK_BRASS, LOOK_INNER, LOOK_LEVER, LOOK_RING, LOOK_WALL = 0, 1, 2, 3, 4, 5, 6
LOOK_NAMES = {0: "paint", 1: "steel_dark", 2: "brass", 3: "inner_steel", 4: "lever_steel", 5: "ring_steel",
              6: "hole_wall"}
SLOT_PAINT, SLOT_STEEL = 0, 1
LOOK_SLOT = {0: 0, 6: 0, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1}

# island texel-density factors (1 = the atlas density)
DENSITY = {"inner": 0.35, "tube": 0.6, "floor": 0.3, "shaft": 0.3, "cap_end": 0.8, "hidden": 0.3}


# =============================================================================== builder
@dataclass
class Face:
    v: Tuple[int, ...]
    uv: Tuple[Tuple[float, float], ...]
    island: str
    part: str
    look: int


class MeshBuilder:
    def __init__(self):
        self.verts: List[Tuple[float, float, float]] = []
        self.keys: Dict[tuple, int] = {}
        self.faces: List[Face] = []
        self.island_density: Dict[str, float] = {}

    # -- vertices
    def v(self, p, key=None) -> int:
        if key is not None:
            k = self.keys.get(key)
            if k is not None:
                return k
        self.verts.append((float(p[0]), float(p[1]), float(p[2])))
        i = len(self.verts) - 1
        if key is not None:
            self.keys[key] = i
        return i

    def f(self, vids, uvs, island, part, look, hint=None, density=1.0):
        """Add a face (3 or 4 corners).  ``hint``: a 3-vector the normal must agree with (flips the face if not)."""
        vids = list(vids)
        uvs = [tuple(map(float, u)) for u in uvs]
        if len(set(vids)) < len(vids):
            # collapse repeated corners (a quad with a pole): keep it only as a triangle
            seen, v2, u2 = set(), [], []
            for a, b in zip(vids, uvs):
                if a not in seen:
                    seen.add(a)
                    v2.append(a)
                    u2.append(b)
            vids, uvs = v2, u2
            if len(vids) < 3:
                return
        if hint is not None:
            P = np.array([self.verts[i] for i in vids])
            n = np.cross(P[1] - P[0], P[2] - P[0])
            if len(vids) == 4:
                n = n + np.cross(P[2] - P[0], P[3] - P[0])
            if float(np.dot(n, np.asarray(hint, float))) < 0.0:
                vids = vids[::-1]
                uvs = uvs[::-1]
        self.faces.append(Face(tuple(vids), tuple(uvs), island, part, look))
        self.island_density.setdefault(island, density)

    def tri_count(self) -> int:
        return sum(len(f.v) - 2 for f in self.faces)

    def arrays(self):
        return np.array(self.verts, float)


# =============================================================================== helpers
def _cyl(r, th_deg, z):
    t = math.radians(th_deg)
    return (r * math.cos(t), r * math.sin(t), z)


def rounded_polygon_radius(theta_deg: float, n_flats: int, apothem: float, corner_r: float, phase_deg: float = 0.0):
    """Radius of a rounded regular polygon (flats' normals at phase + k*360/n) at azimuth theta."""
    half = math.pi / n_flats
    t = math.radians(theta_deg - phase_deg) % (2 * math.pi / n_flats) - half   # -half..half from a flat's normal
    a_in = apothem - corner_r                          # the inner polygon (offset by corner_r gives the shape)
    # the inner polygon's corner is at angle +-half, radius a_in/cos(half)
    # ray from the origin at angle t: hits the flat (x = apothem) where |y| <= a_in*tan(half), else the corner circle
    x_flat = apothem
    y_flat = x_flat * math.tan(t)
    if abs(y_flat) <= a_in * math.tan(half) + 1e-12:
        return apothem / math.cos(t)
    cx = a_in                                          # corner circle centre (in the flat's frame)
    cy = math.copysign(a_in * math.tan(half), t)
    # solve |s*(cos t, sin t) - c| = corner_r for the far root
    ct, st = math.cos(t), math.sin(t)
    b = ct * cx + st * cy
    c = cx * cx + cy * cy - corner_r * corner_r
    return b + math.sqrt(max(b * b - c, 0.0))


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


# =============================================================================== the holed tube
def body_columns(spec: FlashbangSpec, q: LodQuality):
    """Column segments round the tube, starting at the seam (the middle of a 30 deg plain web).

    Returns (theta_seam, [(kind, theta_a, theta_b, hole_theta or None, nseg)]) with theta absolute degrees,
    increasing, covering exactly 360 deg."""
    holes = spec.hole_thetas()
    n = len(holes)
    # find a 90 deg gap; the seam is the middle of that gap's web
    gaps = [((holes[(i + 1) % n] - holes[i]) % 360.0, i) for i in range(n)]
    big = [g for g in gaps if g[0] > 75.0]
    gi = big[-1][1] if big else 0
    seam = (holes[gi] + ((holes[(gi + 1) % n] - holes[gi]) % 360.0) / 2.0)
    cols = []
    th = seam
    order = [(gi + 1 + k) % n for k in range(n)]
    for k, hi in enumerate(order):
        hc = holes[hi]
        while hc < th:
            hc += 360.0
        a, b = hc - 30.0, hc + 30.0
        if a > th + 1e-6:
            w = a - th
            cols.append(("web", th, a, None, max(1, int(round(q.body_web_u * w / 30.0)))))
        cols.append(("cell", a, b, hc, q.body_cell_u))
        th = b
    end = seam + 360.0
    if end > th + 1e-6:
        w = end - th
        cols.append(("web", th, end, None, max(1, int(round(q.body_web_u * w / 30.0)))))
    # the first web (seam -> first cell) was not emitted because the loop starts AT the seam, re-check coverage
    total = sum(c[2] - c[1] for c in cols)
    assert abs(total - 360.0) < 1e-6, total
    return seam, cols


def body_rows(spec: FlashbangSpec):
    z = sorted(spec.hole_rows_z)
    edges = [spec.body_z0, spec.ring_lines_z[0], spec.ring_lines_z[1], spec.sleeve_z0]
    return [(edges[i], edges[i + 1], z[i]) for i in range(3)]


def _ellipse_pts(n):
    """Unit ellipse parameters starting at the LEFT point (psi = pi) going CCW."""
    return [math.pi + 2 * math.pi * j / n for j in range(n)]


def _zipper(A, B):
    """Triangulate between closed loops A (outer) and B (inner), each [(psi, vid, uv)], psi increasing CCW,
    both starting near psi = pi.  At each step the angular rule picks which loop advances; if that triangle would
    be folded (non-positive area in the UV parameter plane) the other loop advances instead.  Returns triangles
    as corner lists [(vid, uv), ...] in CCW order."""
    na, nb = len(A), len(B)

    def ps(L, i):
        k, w = divmod(i, len(L))
        return L[w][0] + 2 * math.pi * k

    def area(t):
        (a, b, c) = (np.array(x[1]) for x in t)
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

    tris = []
    i = j = 0
    while i < na or j < nb:
        a0, b0 = A[i % na], B[j % nb]
        ta = tb = None
        if i < na:
            a1 = A[(i + 1) % na]
            ta = [(a0[1], a0[2]), (a1[1], a1[2]), (b0[1], b0[2])]
        if j < nb:
            b1 = B[(j + 1) % nb]
            tb = [(a0[1], a0[2]), (b1[1], b1[2]), (b0[1], b0[2])]
        if ta is None:
            adv_a = False
        elif tb is None:
            adv_a = True
        else:
            adv_a = ps(A, i + 1) <= ps(B, j + 1)
            if adv_a and area(ta) <= 1e-9 < area(tb):
                adv_a = False
            elif not adv_a and area(tb) <= 1e-9 < area(ta):
                adv_a = True
        if adv_a:
            tris.append(ta)
            i += 1
        else:
            tris.append(tb)
            j += 1
    return tris


def build_body(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """The perforated outer tube (outer surface, hole walls, inner surface), its ceiling annulus and floor, the
    brass tube, the sleeve.  Returns info for sockets / reports."""
    r_o, r_i = spec.body_r, spec.body_r_in
    seam, cols = body_columns(spec, q)
    rows = body_rows(spec)
    a_deg = spec.hole_ang_w_deg / 2.0             # hole half angle
    b_mm = spec.hole_h / 2.0
    info = {"seam_deg": seam, "columns": [(c[0], round(c[1], 3), round(c[2], 3), c[3], c[4]) for c in cols]}

    def uv_out(th, z):
        return ((th - seam) * math.pi / 180.0 * r_o, z)

    def uv_in(th, z):
        return ((th - seam) * math.pi / 180.0 * r_i, z)

    def kv(surf, th, z):
        return (surf, round(th % 360.0, 6) if abs(th - seam - 360.0) > 1e-9 else round(seam % 360.0, 6), round(z, 6))

    def vert(surf, r, th, z):
        # the seam's two copies are the SAME vertex (UV is per corner)
        thk = th
        if abs(th - (seam + 360.0)) < 1e-9:
            thk = seam
        return mb.v(_cyl(r, th, z), key=(surf, round(thk % 360.0, 6), round(z, 6)))

    hole_list = []
    for (kind, ta, tb, hc, nu) in cols:
        for (za, zb, zc) in rows:
            surfs = [("o", r_o, nu, q.body_cell_v, uv_out, LOOK_PAINT, "body_outer", 1.0)]
            if q.inner_shell:
                surfs.append(("i", r_i, max(1, (q.inner_cell_u if kind == "cell" else
                                                max(1, nu * q.inner_cell_u // q.body_cell_u))),
                              q.inner_cell_v, uv_in, LOOK_INNER, "body_inner", DENSITY["inner"]))
            for surf, r, nuu, nvv, uvf, look, isl, dens in surfs:
                ths = np.linspace(ta, tb, nuu + 1)
                zs = np.linspace(za, zb, nvv + 1)
                outward = 1.0 if surf == "o" else -1.0
                if kind == "web" or hc is None:
                    for ii in range(nuu):
                        for jj in range(nvv):
                            c = [(ths[ii], zs[jj]), (ths[ii + 1], zs[jj]), (ths[ii + 1], zs[jj + 1]), (ths[ii], zs[jj + 1])]
                            vids = [vert(surf, r, t, z) for t, z in c]
                            tm = math.radians(0.5 * (ths[ii] + ths[ii + 1]))
                            mb.f(vids, [uvf(t, z) for t, z in c], isl, "tube", look,
                                 hint=(outward * math.cos(tm), outward * math.sin(tm), 0.0), density=dens)
                    continue
                # rectangle boundary CCW (theta right, z up), then the hole ellipse; zipper between
                rect = []
                for t in ths[:-1]:
                    rect.append((t, za))
                for z in zs[:-1]:
                    rect.append((tb, z))
                for t in ths[::-1][:-1]:
                    rect.append((t, zb))
                for z in zs[::-1][:-1]:
                    rect.append((ta, z))
                A = []
                for (t, z) in rect:
                    du = (t - hc) / a_deg
                    dv = (z - zc) / b_mm
                    psi = math.atan2(dv, du) % (2 * math.pi)
                    if psi < math.pi - 1e-9:
                        psi += 2 * math.pi
                    A.append((psi, vert(surf, r, t, z), uvf(t, z)))
                A.sort(key=lambda e: e[0])
                B = []
                for psi in _ellipse_pts(q.hole_pts):
                    t = hc + a_deg * math.cos(psi)
                    z = zc + b_mm * math.sin(psi)
                    B.append((psi, vert(surf + "h%.3f_%.3f" % (hc, zc), r, t, z), uvf(t, z)))
                tm = math.radians(hc)
                for tri in _zipper(A, B):
                    mb.f([c[0] for c in tri], [c[1] for c in tri], isl, "tube", look,
                         hint=(outward * math.cos(tm), outward * math.sin(tm), 0.0), density=dens)
                if surf == "o":
                    hole_list.append((hc, zc))
    # hole walls (radial cut through the wall), one island per hole
    per = None
    for k, (hc, zc) in enumerate(hole_list if q.inner_shell else []):
        psis = _ellipse_pts(q.hole_pts)
        pts = [(hc + a_deg * math.cos(p), zc + b_mm * math.sin(p)) for p in psis]
        # ellipse perimeter parameter (arc length at the outer radius), for the UV
        P3 = [np.array(_cyl(r_o, t, z)) for t, z in pts]
        seg = [np.linalg.norm(P3[(j + 1) % len(P3)] - P3[j]) for j in range(len(P3))]
        s = np.concatenate([[0.0], np.cumsum(seg)])
        per = float(s[-1])
        isl = "hole_walls"
        voff = k * (spec.wall_mm + 1.2)
        for j in range(len(pts)):
            j1 = (j + 1) % len(pts)
            (t0, z0), (t1, z1) = pts[j], pts[j1]
            vo0 = mb.v(_cyl(r_o, t0, z0), key=("oh%.3f_%.3f" % (hc, zc), round(t0 % 360.0, 6), round(z0, 6)))
            vo1 = mb.v(_cyl(r_o, t1, z1), key=("oh%.3f_%.3f" % (hc, zc), round(t1 % 360.0, 6), round(z1, 6)))
            vi0 = mb.v(_cyl(r_i, t0, z0), key=("ih%.3f_%.3f" % (hc, zc), round(t0 % 360.0, 6), round(z0, 6)))
            vi1 = mb.v(_cyl(r_i, t1, z1), key=("ih%.3f_%.3f" % (hc, zc), round(t1 % 360.0, 6), round(z1, 6)))
            pm = 0.5 * (np.array(_cyl(r_o, t0, z0)) + np.array(_cyl(r_o, t1, z1)))
            rr = math.hypot(pm[0], pm[1])
            cc = np.array(_cyl(rr, hc, zc))
            hint = cc - pm
            hint[:2] -= np.dot(hint[:2], pm[:2] / rr) * pm[:2] / rr
            mb.f([vo0, vo1, vi1, vi0], [(s[j], voff + spec.wall_mm), (s[j + 1], voff + spec.wall_mm),
                                        (s[j + 1], voff), (s[j], voff)], isl, "tube", LOOK_WALL, hint=hint)
    # ceiling of the gap (under the sleeve) and its floor (the cap top), both coarse and hidden
    nt = q.tube_segs
    for (z, sign, isl) in (((spec.sleeve_z0, -1.0, "gap_ceiling"), (spec.body_z0, 1.0, "gap_floor"))
                           if q.inner_shell else ()):
        for k in range(nt):
            t0, t1 = 360.0 * k / nt, 360.0 * (k + 1) / nt
            ra, rb = spec.inner_tube_r, r_i
            c = [(ra, t0), (rb, t0), (rb, t1), (ra, t1)]
            # the inner ring IS the brass tube's end ring (shared vertices: no coincident pair)
            vids = [mb.v(_cyl(r, t, z), key=(("tube", round(t % 360, 6), round(z, 6)) if r == ra else
                                             (isl, round(r, 4), round(t % 360, 6)))) for r, t in c]
            uvs = [(math.radians(t) * 18.5, r) for r, t in c]
            mb.f(vids, uvs, isl, "tube", LOOK_INNER, hint=(0, 0, sign), density=DENSITY["floor"])
    # brass tube
    rt = spec.inner_tube_r
    for k in range(nt):
        t0, t1 = 360.0 * k / nt, 360.0 * (k + 1) / nt
        c = [(t0, spec.body_z0), (t1, spec.body_z0), (t1, spec.sleeve_z0), (t0, spec.sleeve_z0)]
        vids = [mb.v(_cyl(rt, t, z), key=("tube", round(t % 360, 6), round(z, 6))) for t, z in c]
        uvs = [(math.radians(t) * rt, z) for t, z in c]
        tm = math.radians(0.5 * (t0 + t1))
        mb.f(vids, uvs, "brass_tube", "tube", LOOK_BRASS, hint=(math.cos(tm), math.sin(tm), 0), density=DENSITY["tube"])
    # the sleeve: step (annulus, down), side, top chamfer, top annulus (steel gap) - shares the body's top ring
    ths = []
    for (kind, ta, tb, hc, nu) in cols:
        ths.extend(list(np.linspace(ta, tb, nu + 1))[:-1])
    ths.append(seam + 360.0)
    assert len(ths) - 1 == q.revolve_segs, (len(ths) - 1, q.revolve_segs)
    prof = [(r_o, spec.sleeve_z0, "o"), (spec.sleeve_r, spec.sleeve_z0, None), (spec.sleeve_r, spec.sleeve_z1, None),
            (spec.sleeve_top_r, spec.sleeve_top_z, None), (spec.neck_r, spec.sleeve_top_z, None)]
    looks = [LOOK_PAINT, LOOK_PAINT, LOOK_PAINT, LOOK_STEEL]
    islands = ["sleeve", "sleeve", "sleeve", "sleeve"]
    s_acc = [0.0]
    for k in range(1, len(prof)):
        s_acc.append(s_acc[-1] + math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]))

    def pv(k, t):
        r, z, surf = prof[k]
        if surf == "o":
            return vert("o", r_o, t, z)
        tk = seam if abs(t - (seam + 360.0)) < 1e-9 else t
        return mb.v(_cyl(r, t, z), key=("sleeve", k, round(tk % 360.0, 6)))

    for k in range(len(prof) - 1):
        (ra, za, _), (rb, zb, _) = prof[k], prof[k + 1]
        dr, dz = rb - ra, zb - za
        n2 = (dz, -dr)                                  # profile walks with the solid on the LEFT
        for m in range(len(ths) - 1):
            t0, t1 = ths[m], ths[m + 1]
            vids = [pv(k, t0), pv(k, t1), pv(k + 1, t1), pv(k + 1, t0)]
            if islands[k] == "sleeve":
                rr = [ra, ra, rb, rb]
                uvs = [((t - seam) * math.pi / 180.0 * rr[i], -(s_acc[k] if i < 2 else s_acc[k + 1]))
                       for i, t in enumerate((t0, t1, t1, t0))]
            else:
                uvs = [(r * math.cos(math.radians(t)), r * math.sin(math.radians(t)))
                       for r, t in ((ra, t0), (ra, t1), (rb, t1), (rb, t0))]
            tm = math.radians(0.5 * (t0 + t1))
            hint = (n2[0] * math.cos(tm), n2[0] * math.sin(tm), n2[1])
            mb.f(vids, uvs, islands[k], "sleeve", looks[k], hint=hint)
    info["holes"] = hole_list
    info["hole_wall_perimeter_mm"] = per
    return info


# =============================================================================== revolve (generic, own segs)
def revolve(mb: MeshBuilder, prof, segs, island, part, look_per_band, seam_deg=135.0, key=None, density=1.0,
            polar_islands=()):
    """Revolve a profile [(r, z), ...] walked with the solid on the LEFT.  Bands listed in ``polar_islands`` (by
    index) get a planar (x, y) UV on island ``island + '_disc'``; the rest one unrolled island (u = arc at each
    ring's radius, v = profile length)."""
    key = key or island
    s_acc = [0.0]
    for k in range(1, len(prof)):
        s_acc.append(s_acc[-1] + math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]))
    ths = [seam_deg + 360.0 * m / segs for m in range(segs + 1)]

    def pv(k, t):
        r, z = prof[k]
        tk = seam_deg if abs(t - (seam_deg + 360.0)) < 1e-9 else t
        if r < 1e-9:
            return mb.v((0.0, 0.0, z), key=(key, k, "axis"))
        return mb.v(_cyl(r, t, z), key=(key, k, round(tk % 360.0, 6)))

    for k in range(len(prof) - 1):
        (ra, za), (rb, zb) = prof[k], prof[k + 1]
        dr, dz = rb - ra, zb - za
        n2 = (dz, -dr)
        look = look_per_band[k] if isinstance(look_per_band, (list, tuple)) else look_per_band
        for m in range(segs):
            t0, t1 = ths[m], ths[m + 1]
            vids = [pv(k, t0), pv(k, t1), pv(k + 1, t1), pv(k + 1, t0)]
            if k in polar_islands:
                isl = island + "_disc"
                uvs = [(r * math.cos(math.radians(t)), r * math.sin(math.radians(t)))
                       for r, t in ((ra, t0), (ra, t1), (rb, t1), (rb, t0))]
            else:
                isl = island
                rr = [ra, ra, rb, rb]
                uvs = [((t - seam_deg) * math.pi / 180.0 * max(rr[i], 0.5), -(s_acc[k] if i < 2 else s_acc[k + 1]))
                       for i, t in enumerate((t0, t1, t1, t0))]
            tm = math.radians(0.5 * (t0 + t1))
            mb.f(vids, uvs, isl, part, look, hint=(n2[0] * math.cos(tm), n2[0] * math.sin(tm), n2[1]),
                 density=density)


# =============================================================================== base cap
def build_cap(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """The 12-flat soft-cornered cap with its chamfers and the notched end face (lip, groove, stepped disc)."""
    n_flat = 12
    phase = 15.0                                     # flats' normals at 15 + 30k (a corner faces +X, the lever)
    seam = 135.0
    base = [seam + 360.0 * m / (n_flat * q.cap_per_flat) for m in range(n_flat * q.cap_per_flat)]
    half_w = {}
    notch_edges = []
    if q.cap_notches:
        for nd in spec.notch_deg:
            hw = math.degrees(spec.notch_w_mm / 2.0 / 18.3)
            a0, a1 = nd - hw, nd + hw
            notch_edges += [a0, a1]
    ne = [((a - seam) % 360.0) + seam for a in notch_edges]
    base = [a for a in base if all(abs(((a - e + 180.0) % 360.0) - 180.0) > 0.8 for e in ne)]
    angles = sorted(set([round(((a - seam) % 360.0) + seam, 6) for a in base + notch_edges]))
    angles.append(seam + 360.0)

    def in_notch(t):
        if not q.cap_notches:
            return False
        for nd in spec.notch_deg:
            hw = math.degrees(spec.notch_w_mm / 2.0 / 18.3)
            d = (t - nd + 180.0) % 360.0 - 180.0
            if abs(d) < hw - 1e-6:
                return True
        return False

    def rpoly(t):
        return rounded_polygon_radius(t, n_flat, spec.cap_apothem, spec.cap_corner_r, phase)

    # rings: (kind, value, z)
    side_rings = [("c", spec.body_r - 0.1, spec.body_z0),            # chamfer top (tucked just inside the body)
                  ("p", 0.0, spec.cap_side_z1), ("p", 0.0, spec.cap_side_z0),
                  ("c", spec.foot_r, spec.end_z_annulus)]

    def ring_r(ring, t):
        kind, val, z = ring
        return rpoly(t) + val if kind == "p" else val

    def key_t(t):
        return round(((t - seam) % 360.0) + seam if abs(t - seam - 360.0) > 1e-9 else seam, 6)

    def V(tag, r, t, z):
        return mb.v(_cyl(r, t, z), key=("cap", key_t(t), round(z, 5), round(r, 5)))

    rmean = []
    for ring in side_rings:
        rmean.append(float(np.mean([ring_r(ring, t) for t in np.linspace(0, 360, 721)])))
    s_acc = [0.0]
    for k in range(1, len(side_rings)):
        s_acc.append(s_acc[-1] + math.hypot(rmean[k] - rmean[k - 1], side_rings[k][2] - side_rings[k - 1][2]))
    for k in range(len(side_rings) - 1):
        ra_, rb_ = side_rings[k], side_rings[k + 1]
        for m in range(len(angles) - 1):
            t0, t1 = angles[m], angles[m + 1]
            c = [(ra_, t0), (ra_, t1), (rb_, t1), (rb_, t0)]
            vids = [V("s%d" % (k if i < 2 else k + 1), ring_r(rg, t), t, rg[2])
                    for i, (rg, t) in enumerate(c)]
            uvs = [((t - seam) * math.pi / 180.0 * rmean[k if i < 2 else k + 1], -(s_acc[k] if i < 2 else s_acc[k + 1]))
                   for i, (rg, t) in enumerate(c)]
            tm = 0.5 * (t0 + t1)
            pa = np.array(_cyl(ring_r(ra_, tm), tm, ra_[2]))
            pb = np.array(_cyl(ring_r(rb_, tm), tm, rb_[2]))
            # outward: perpendicular to the profile, away from the axis / down at the foot
            tang = pb - pa
            rad = np.array([math.cos(math.radians(tm)), math.sin(math.radians(tm)), 0.0])
            hint = rad - tang * np.dot(rad, tang) / max(np.dot(tang, tang), 1e-12)
            if k == len(side_rings) - 2:
                hint = hint + np.array([0, 0, -0.5])
            mb.f(vids, uvs, "cap_side", "cap", LOOK_STEEL, hint=hint)
    # end face: radial bands (r_in, r_out, z_normal, z_notch) from the centre out
    ann0, ann1 = spec.end_annulus_r
    lip0, lip1 = spec.end_lip_r
    gr0, gr1 = spec.end_groove_r
    rd = spec.end_disc_r
    step_r = rd - spec.disc_step_depth
    bands = [  # (r0, r1, z_normal, z_in_notch)
        (0.0, step_r, spec.end_z_disc, spec.end_z_disc),
        (step_r, rd, spec.end_z_disc, spec.end_z_groove),
        (gr0, gr1, spec.end_z_groove, spec.end_z_groove),
        (lip0, lip1, spec.end_z_lip, spec.end_z_annulus),
        (ann0, ann1, spec.end_z_annulus, spec.end_z_annulus),
    ]
    if q.cap_end_detail < 2 or not q.cap_notches:
        bands = [(0.0, rd, spec.end_z_disc, spec.end_z_disc)] + bands[2:]
    if q.cap_end_detail == 0:
        bands = [(0.0, ann1, spec.end_z_annulus, spec.end_z_annulus)]

    # polar UV with radius = the NORMAL profile's cumulative length (notch sectors use their own profile)
    def prof_s(notch: bool):
        s = {}
        acc = 0.0
        prev_z = None
        prev_r = 0.0
        for (r0, r1, zn, zk) in bands:
            z = zk if notch else zn
            if prev_z is not None:
                acc += abs(z - prev_z)                  # the wall between bands
            s[(r0, "a")] = acc
            acc += (r1 - r0)
            s[(r1, "b")] = acc
            prev_z = z
            prev_r = r1
        return s

    s_norm, s_notch = prof_s(False), prof_s(True)
    for m in range(len(angles) - 1):
        t0, t1 = angles[m], angles[m + 1]
        tm = 0.5 * (t0 + t1)
        notch = in_notch(tm)
        S = s_notch if notch else s_norm
        prev = None
        for bi, (r0, r1, zn, zk) in enumerate(bands):
            z = zk if notch else zn
            isl = "cap_end"

            def uvp(r, t, which):
                s = S[(r, which)]
                return (s * math.cos(math.radians(t)), s * math.sin(math.radians(t)))
            if r0 < 1e-9:
                vc = mb.v((0.0, 0.0, z), key=("cap", "end_c", round(z, 5)))
                vids = [vc, V("e", r1, t1, z), V("e", r1, t0, z)]
                uvs = [(0.0, 0.0), uvp(r1, t1, "b"), uvp(r1, t0, "b")]
                mb.f(vids, uvs, isl, "cap", LOOK_STEEL, hint=(0, 0, -1), density=DENSITY["cap_end"])
            else:
                vids = [V("e", r0, t0, z), V("e", r1, t0, z), V("e", r1, t1, z), V("e", r0, t1, z)]
                uvs = [uvp(r0, t0, "a"), uvp(r1, t0, "b"), uvp(r1, t1, "b"), uvp(r0, t1, "a")]
                mb.f(vids, uvs, isl, "cap", LOOK_STEEL, hint=(0, 0, -1), density=DENSITY["cap_end"])
            if prev is not None:
                pr1, pz = prev
                if abs(pz - z) > 1e-9:                  # radial wall at r = r0 (== previous r1)
                    va0, va1 = V("e", r0, t0, pz), V("e", r0, t1, pz)
                    vb0, vb1 = V("e", r0, t0, z), V("e", r0, t1, z)
                    sa, sb = S[(r0, "a")] - abs(z - pz), S[(r0, "a")]
                    uvs = [(sa * math.cos(math.radians(t)), sa * math.sin(math.radians(t))) for t in (t0, t1)] + \
                          [(sb * math.cos(math.radians(t)), sb * math.sin(math.radians(t))) for t in (t1, t0)]
                    rad = np.array([math.cos(math.radians(tm)), math.sin(math.radians(tm)), 0.0])
                    # the wall faces outward if the outer band is deeper-in (higher z), else inward
                    hint = rad if z > pz else -rad
                    mb.f([va0, va1, vb1, vb0], uvs, isl, "cap", LOOK_STEEL, hint=hint, density=DENSITY["cap_end"])
            prev = (r1, z)
    # notch side walls (angular walls where a band's height changes between a notch and its neighbour)
    if q.cap_notches:
        wall_k = 0
        for m in range(len(angles) - 1):
            t = angles[m + 1]
            if m + 1 >= len(angles) - 1:
                tn = angles[1] + 360.0
            else:
                tn = angles[m + 2]
            left = in_notch(0.5 * (angles[m] + t))
            right = in_notch(0.5 * (t + tn))
            if left == right:
                continue
            for (r0, r1, zn, zk) in bands:
                if abs(zn - zk) < 1e-9:
                    continue
                zl = zk if left else zn
                zr = zk if right else zn
                va0, va1 = V("e", r0, t, zl), V("e", r1, t, zl)
                vb0, vb1 = V("e", r0, t, zr), V("e", r1, t, zr)
                tang = np.array([-math.sin(math.radians(t)), math.cos(math.radians(t)), 0.0])
                # the wall faces toward the deeper (higher z) side's sector
                hint = tang if zr > zl else -tang          # faces into the recessed (higher z) sector
                u0 = wall_k * 3.2
                ua, ub = (u0, u0 + r1 - r0) if zr > zl else (u0 + r1 - r0, u0)   # never mirrored
                mb.f([va0, va1, vb1, vb0], [(ua, zl), (ub, zl), (ub, zr), (ua, zr)],
                     "cap_notch_walls", "cap", LOOK_STEEL, hint=hint, density=DENSITY["cap_end"])
                wall_k += 1
    return {"angles": len(angles) - 1, "notches": bool(q.cap_notches)}


# =============================================================================== boxes / cylinders / tori
def chamfer_box(mb: MeshBuilder, lo, hi, c, island, part, look, chamfer=True, skip=()):
    """Axis-aligned box with every edge chamfered by ``c`` (26 faces), each face its own island piece."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    ctr = 0.5 * (lo + hi)
    if not chamfer or c <= 0:
        c = 0.0
    # vertices: for each corner sign (sx,sy,sz) three points offset along each axis
    V = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corner = np.array([hi[0] if sx > 0 else lo[0], hi[1] if sy > 0 else lo[1], hi[2] if sz > 0 else lo[2]])
                for ax in range(3):
                    p = corner.copy()
                    # inset the two OTHER axes by c (the point lies on face 'ax')
                    for o in range(3):
                        if o != ax:
                            p[o] -= (sx, sy, sz)[o] * c
                    V[(sx, sy, sz, ax)] = mb.v(p, key=(island, "box", sx, sy, sz, ax if c > 0 else -1))
    kk = 0

    def add(vids, hint, name):
        """Group each face with the main face it most faces (ties: Z first for top/bottom chamfers and corners, then
        X for the vertical chamfers) and project it on that axis: 6 unfolded islands per box, not 26."""
        nonlocal kk
        P = np.array([mb.verts[i] for i in vids])
        h = np.asarray(hint, float)
        m = np.abs(h)
        ax = 2 if m[2] >= m.max() - 1e-9 else (0 if m[0] >= m[1] - 1e-9 else 1)
        sgn = 1 if h[ax] > 0 else -1
        o1, o2 = [o for o in range(3) if o != ax]
        uvs = [(float(p[o1]) * sgn, float(p[o2])) for p in P]
        mb.f(vids, uvs, f"{island}_{'xyz'[ax]}{'p' if sgn > 0 else 'n'}", part, look, hint=hint)
        kk += 1

    # main faces
    for ax in range(3):
        for s in (-1, 1):
            if (ax, s) in skip:
                continue
            o1, o2 = [o for o in range(3) if o != ax]
            quad = []
            for a1, a2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                sg = [0, 0, 0]
                sg[ax], sg[o1], sg[o2] = s, a1, a2
                quad.append(V[(sg[0], sg[1], sg[2], ax)])
            hint = [0, 0, 0]
            hint[ax] = s
            add(quad, hint, f"f{ax}{'p' if s > 0 else 'n'}")
    if c <= 0:
        return
    # edge chamfers
    for ax in range(3):                      # edge runs along ax
        o1, o2 = [o for o in range(3) if o != ax]
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                q = []
                for s in (-1, 1):
                    sg = [0, 0, 0]
                    sg[ax], sg[o1], sg[o2] = s, s1, s2
                    q.append((V[(sg[0], sg[1], sg[2], o1)], V[(sg[0], sg[1], sg[2], o2)]))
                vids = [q[0][0], q[1][0], q[1][1], q[0][1]]
                hint = [0.0, 0.0, 0.0]
                hint[o1], hint[o2] = s1, s2
                add(vids, hint, f"e{ax}{s1}{s2}")
    # corner triangles
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                vids = [V[(sx, sy, sz, 0)], V[(sx, sy, sz, 1)], V[(sx, sy, sz, 2)]]
                add(vids, (sx, sy, sz), f"c{sx}{sy}{sz}")


def cylinder(mb: MeshBuilder, centre, axis: str, r, y0, y1, segs, island, part, look, caps=(True, True), seam=0.0,
             density=1.0):
    """Cylinder along a principal axis ('x', 'y' or 'z') from coordinate y0 to y1 on that axis."""
    ai = "xyz".index(axis)
    o1, o2 = [o for o in range(3) if o != ai]
    c = np.asarray(centre, float)

    def P(t, a):
        p = c.copy()
        p[ai] = a
        p[o1] += r * math.cos(t)
        p[o2] += r * math.sin(t)
        return p

    ts = [seam + 2 * math.pi * m / segs for m in range(segs + 1)]
    for m in range(segs):
        t0, t1 = ts[m], ts[m + 1]
        vids = [mb.v(P(t, a), key=(island, "cyl", round(t % (2 * math.pi), 7), a)) for t, a in
                ((t0, y0), (t1, y0), (t1, y1), (t0, y1))]
        uvs = [((t - seam) * r, a) for t, a in ((t0, y0), (t1, y0), (t1, y1), (t0, y1))]
        hint = np.zeros(3)
        tm = 0.5 * (t0 + t1)
        hint[o1], hint[o2] = math.cos(tm), math.sin(tm)
        mb.f(vids, uvs, island, part, look, hint=hint, density=density)
    for which, a, sgn in ((0, y0, -1.0 if y1 > y0 else 1.0), (1, y1, 1.0 if y1 > y0 else -1.0)):
        if not caps[which]:
            continue
        cc = c.copy()
        cc[ai] = a
        vc = mb.v(cc, key=(island, "cap", which))
        for m in range(segs):
            t0, t1 = ts[m], ts[m + 1]
            vids = [vc, mb.v(P(t0, a), key=(island, "cyl", round(t0 % (2 * math.pi), 7), a)),
                    mb.v(P(t1, a), key=(island, "cyl", round(t1 % (2 * math.pi), 7), a))]
            uvs = [(0.0, 0.0), (r * math.cos(t0), r * math.sin(t0)), (r * math.cos(t1), r * math.sin(t1))]
            hint = np.zeros(3)
            hint[ai] = sgn
            mb.f(vids, uvs, f"{island}_cap{which}", part, look, hint=hint, density=density)


def torus(mb: MeshBuilder, centre, e1, e2, R, r, nmaj, nmin, island, part, look, seam_maj=0.0):
    """Torus: the tube centre line is centre + R (cos a e1 + sin a e2)."""
    c = np.asarray(centre, float)
    e1, e2 = _unit(e1), _unit(e2)
    nrm = _unit(np.cross(e1, e2))

    def P(a, b):
        d = math.cos(a) * e1 + math.sin(a) * e2
        return c + (R + r * math.cos(b)) * d + r * math.sin(b) * nrm

    for i in range(nmaj):
        a0 = seam_maj + 2 * math.pi * i / nmaj
        a1 = seam_maj + 2 * math.pi * (i + 1) / nmaj
        for j in range(nmin):
            b0 = 2 * math.pi * j / nmin
            b1 = 2 * math.pi * (j + 1) / nmin
            cor = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
            vids = [mb.v(P(a, b), key=(island, "tor", i if a == a0 else (i + 1) % nmaj,
                                       j if b == b0 else (j + 1) % nmin)) for a, b in cor]
            uvs = [((a - seam_maj) * R, b * r) for a, b in cor]
            am, bm = 0.5 * (a0 + a1), 0.5 * (b0 + b1)
            d = math.cos(am) * e1 + math.sin(am) * e2
            hint = math.cos(bm) * d + math.sin(bm) * nrm
            mb.f(vids, uvs, island, part, look, hint=hint)


# =============================================================================== lever (swept plate)
def lever_path(spec: FlashbangSpec, q: LodQuality):
    """Centreline of the lever plate in the XZ plane (y handled by the width functions), from the curl's free end
    over the knuckle and down to the bent tip.  Returns [(x, z, tx, tz)] with the unit tangent."""
    kx, _ky, kz = spec.knuckle_c
    t = spec.lever_t
    rc = spec.knuckle_r + 0.05 + t / 2.0
    xu = kx + rc                                         # upper segment centreline x (= knuckle + clearance)
    xl = spec.lever_lower_x + t / 2.0
    pts = []
    for i in range(q.lever_curl + 1):                    # 165 deg -> 0 deg round the knuckle (clockwise, over the top)
        a = math.radians(165.0 - 165.0 * i / q.lever_curl)
        pts.append((kx + rc * math.cos(a), kz + rc * math.sin(a)))
    zj0, zj1 = spec.lever_joggle_z
    pts.append((xu, zj0))
    nj = 4 if q.lever_curl >= 4 else 2
    for i in range(1, nj + 1):                           # smooth S-step out (cosine blend)
        f = i / nj
        w = 0.5 - 0.5 * math.cos(math.pi * f)
        pts.append((xu + (xl - xu) * w, zj0 + (zj1 - zj0) * f))
    zt = spec.lever_tip_z
    zb = zt + spec.lever_tip_bend
    pts.append((xl, zb))
    nb = 2 if q.lever_curl >= 4 else 1
    for i in range(1, nb + 1):
        f = i / nb
        pts.append((xl - spec.lever_tip_in * f * f, zb - (zb - zt) * f))
    out = []
    P = np.array(pts)
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        tng = _unit(b - a)
        out.append((P[i][0], P[i][1], tng[0], tng[1]))
    return out


def build_lever(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """The spoon: a plate swept along lever_path, its width tapering on the upper segment (the -Y edge slants, the
    +Y edge is straight - v4), the lower segment 0.26 D wide, the tip squared with rounded corners.  Section: a
    chamfered rectangle (8 points) at LOD0/1, a plain one at LOD2."""
    path = lever_path(spec, q)
    t = spec.lever_t
    ch = 0.35 if q.box_chamfer else 0.0
    P = np.array([(p[0], p[1]) for p in path])
    # the UV's v is the arc length of a DENSE reference path (the same at every LOD), read at each sample
    dense = lever_path(spec, LodQuality(1, 1, 1, 3, 1, 1, 1, 3, 3, 1, False, 3, 3, 3, 3, 3, 3, 96, True, (0, 0)))
    DP = np.array([(p[0], p[1]) for p in dense])
    # densify the straights / joggle further by linear interpolation
    fine = [DP[0]]
    for i in range(1, len(DP)):
        for f in np.linspace(0, 1, 41)[1:]:
            fine.append(DP[i - 1] + (DP[i] - DP[i - 1]) * f)
    fine = np.array(fine)
    fs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    s = np.array([fs[int(np.argmin(np.linalg.norm(fine - p, axis=1)))] for p in P])
    top_i = q.lever_curl
    zj0 = spec.lever_joggle_z[0]
    j0 = next(i for i in range(top_i + 1, len(path)) if abs(path[i][1] - zj0) < 1e-6)
    nj = 4 if q.lever_curl >= 4 else 2
    j1 = j0 + nj
    yp_top, ym_top = 6.4, 6.4 - spec.lever_w_top
    yp_j, ym_j = 6.4, 6.4 - spec.lever_w_joggle
    yp_l, ym_l = spec.lever_w / 2.0, -spec.lever_w / 2.0

    def widths(si):
        if si <= s[top_i]:
            return yp_top, ym_top
        if si <= s[j0]:
            f = (si - s[top_i]) / (s[j0] - s[top_i])
            return yp_top + (yp_j - yp_top) * f, ym_top + (ym_j - ym_top) * f
        if si <= s[j1]:
            f = (si - s[j0]) / (s[j1] - s[j0])
            return yp_j + (yp_l - yp_j) * f, ym_j + (ym_l - ym_j) * f
        return yp_l, ym_l

    # sections along the path; the last segment gets extra samples that round the tip's two corners
    secs = []
    for i, (x, z, tx, tz) in enumerate(path[:-1]):
        yp, ym = widths(s[i])
        secs.append((x, z, tx, tz, yp, ym, s[i]))
    xe, ze, txe, tze = path[-1]
    xa, za = path[-2][0], path[-2][1]
    seg = math.hypot(xe - xa, ze - za)
    rcn = min(spec.lever_tip_corner_r, seg * 0.9)
    nt = 3 if q.box_chamfer else 1
    for k in range(1, nt + 1):
        ang = math.pi / 2.0 * k / (nt + 1)
        dd = rcn * (1.0 - math.sin(ang))            # distance back from the end
        ww = rcn * (1.0 - math.cos(ang))            # width lost on each side there
        f = 1.0 - dd / seg
        secs.append((xa + (xe - xa) * f, za + (ze - za) * f, txe, tze, yp_l - ww, ym_l + ww, s[-1] - dd))
    last_w = rcn * 0.92 if nt > 1 else rcn * 0.6
    secs.append((xe, ze, txe, tze, yp_l - last_w, ym_l + last_w, s[-1]))

    def section(x, z, tx, tz, yp, ym):
        n = np.array([-tz, 0.0, tx])                 # +n = the plate's OUTER face (away from body / knuckle)
        o = np.array([x, 0.0, z])
        h = t / 2.0
        Y = np.array([0.0, 1.0, 0.0])
        if ch > 0:
            pts = [o + n * h + Y * (ym + ch), o + n * h + Y * (yp - ch), o + n * (h - ch) + Y * yp,
                   o - n * (h - ch) + Y * yp, o - n * h + Y * (yp - ch), o - n * h + Y * (ym + ch),
                   o - n * (h - ch) + Y * ym, o + n * (h - ch) + Y * ym]
        else:
            pts = [o + n * h + Y * ym, o + n * h + Y * yp, o - n * h + Y * yp, o - n * h + Y * ym]
        return pts, n, o + Y * 0.5 * (yp + ym)

    S = [section(*sc[:6]) + (sc[6],) for sc in secs]
    npt = len(S[0][0])
    for i in range(len(S) - 1):
        A, na, ca, sa = S[i]
        B, nb_, cb, sb = S[i + 1]
        ua = np.concatenate([[0.0], np.cumsum([np.linalg.norm(A[(k + 1) % npt] - A[k]) for k in range(npt)])])
        ub = np.concatenate([[0.0], np.cumsum([np.linalg.norm(B[(k + 1) % npt] - B[k]) for k in range(npt)])])
        for k in range(npt):
            k1 = (k + 1) % npt
            vids = [mb.v(A[k], key=("lever", i, k)), mb.v(A[k1], key=("lever", i, k1)),
                    mb.v(B[k1], key=("lever", i + 1, k1)), mb.v(B[k], key=("lever", i + 1, k))]
            mid = 0.25 * (A[k] + A[k1] + B[k] + B[k1])
            hint = mid - 0.5 * (ca + cb)
            mb.f(vids, [(ua[k], -sa), (ua[k + 1], -sa), (ub[k + 1], -sb), (ub[k], -sb)], "lever", "lever",
                 LOOK_LEVER, hint=hint)
    for which, idx in ((0, 0), (1, len(S) - 1)):
        A, n, c, si = S[idx]
        tng = np.array([path[0][2], 0.0, path[0][3]]) if which == 0 else np.array([path[-1][2], 0.0, path[-1][3]])
        hint = -tng if which == 0 else tng
        vids = [mb.v(A[k], key=("lever", idx, k)) for k in range(npt)]
        a_ = _unit(n)
        b_ = np.array([0.0, 1.0, 0.0])
        uvs = [(float(np.dot(p - c, a_)), float(p[1])) for p in A]
        quads = ((0, 1, 2, 3), (0, 3, 4, 7), (4, 5, 6, 7)) if npt == 8 else ((0, 1, 2, 3),)
        for qd in quads:
            mb.f([vids[i] for i in qd], [uvs[i] for i in qd], f"lever_end{which}", "lever", LOOK_LEVER, hint=hint)
    return {"path_len_mm": round(float(s[-1]), 3), "sections": len(S),
            "tip_z_mm": round(float(ze), 3), "upper_inner_x_mm": round(float(path[top_i][0] - t / 2), 3)}


# =============================================================================== fuze head
def build_fuze(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    s = spec
    h = s.housing_half
    chamfer_box(mb, (-h, -h, s.housing_z0), (h, h, s.housing_z1), s.housing_chamfer, "housing", "fuze", LOOK_STEEL,
                chamfer=q.box_chamfer, skip=((2, -1),))
    chamfer_box(mb, (s.plate_x[0], -s.plate_y, s.housing_z1), (s.plate_x[1], s.plate_y, s.plate_z1), 0.45,
                "plate", "fuze", LOOK_STEEL, chamfer=q.box_chamfer)
    chamfer_box(mb, (s.block_x[0], s.block_y[0], s.block_z[0]), (s.block_x[1], s.block_y[1], s.block_z[1]), 0.4,
                "block", "fuze", LOOK_STEEL, chamfer=q.box_chamfer)
    ss = q.small_segs
    # the arm's curl and its cross pin (axis Y) under the plate's free end
    cz = s.plate_z1 - s.arm_curl_r
    cylinder(mb, (s.plate_x[0] + 0.3, 0.0, cz), "y", s.arm_curl_r, -s.arm_curl_len / 2, s.arm_curl_len / 2, ss,
             "arm_curl", "fuze", LOOK_STEEL)
    cylinder(mb, (s.plate_x[0] + 0.3, 0.0, cz), "y", s.arm_pin_r, -s.arm_pin_len / 2, s.arm_pin_len / 2,
             max(6, ss // 2), "arm_pin", "fuze", LOOK_STEEL)
    # knuckle (hinge barrel)
    kx, ky, kz = s.knuckle_c
    cylinder(mb, (kx, 0.0, kz), "y", s.knuckle_r, ky - s.knuckle_len / 2, ky + s.knuckle_len / 2, ss, "knuckle",
             "fuze", LOOK_STEEL)
    # pin boss (sleeve for the pin) off the block's -Y face
    px, pz = s.pin_c
    cylinder(mb, (px, 0.0, pz), "y", s.pin_boss_r, s.block_y[0] + 0.2, s.block_y[0] - s.pin_boss_len, ss, "pin_boss",
             "fuze", LOOK_STEEL, caps=(False, True))
    # the small round boss on the housing's -Y face (v1)
    bx, bz = s.small_boss_c
    cylinder(mb, (bx, 0.0, bz), "y", s.small_boss_r, -h + 0.1, -h - 0.6, max(8, ss // 2), "small_boss", "fuze",
             LOOK_STEEL, caps=(False, True))
    # collar, neck and plinth (revolved, their own segment counts)
    prof = [(s.neck_r, s.sleeve_top_z - 0.05), (s.neck_r, s.collar_z0), (s.collar_r, s.collar_z0),
            (s.collar_r, s.collar_z1 - s.collar_chamfer), (s.collar_r - s.collar_chamfer, s.collar_z1),
            (s.plinth_r, s.collar_z1)]
    # walk with the solid on the LEFT: bottom-up on the outside
    revolve(mb, prof, q.collar_segs, "collar", "fuze", LOOK_STEEL, seam_deg=135.0)
    prof2 = [(s.plinth_r, s.collar_z1 - 0.05), (s.plinth_r, s.plinth_z1), (0.0, s.plinth_z1)]
    revolve(mb, prof2, q.plinth_segs, "plinth", "fuze", LOOK_STEEL, seam_deg=135.0, polar_islands=(1,))


def build_pullring(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    s = spec
    px, pz = s.pin_c
    ye = s.pin_eye_y()
    # pin shaft (hidden inside the boss, slides out when pulled)
    cylinder(mb, (px, 0.0, pz), "y", s.pin_r, s.block_y[1] - 1.0, ye + s.eye_major * 0.6, max(6, q.small_segs // 2),
             "pin_shaft", "pin", LOOK_RING, density=DENSITY["shaft"])
    # the eye: a small torus in the YZ plane (normal X), the ring passes through it along X
    torus(mb, (px, ye, pz), (0, 1, 0), (0, 0, 1), s.eye_major, s.eye_minor, q.eye_major, q.eye_minor, "pin_eye",
          "pin", LOOK_RING)
    # the ring: tilted outward at the bottom so it clears the sleeve; its top passes through the eye
    tau = math.radians(s.ring_tilt_deg)
    zdir = np.array([0.0, math.sin(tau), math.cos(tau)])       # centre -> top
    xdir = np.array([1.0, 0.0, 0.0])
    R = s.ring_major_r
    top = np.array([px, ye, pz])
    c = top - R * zdir
    torus(mb, c, xdir, zdir, R, s.ring_wire_d / 2.0, q.ring_major, q.ring_minor, "ring", "ring", LOOK_RING,
          seam_maj=math.radians(90.0 + 180.0 / q.ring_major))
    return {"ring_centre_mm": [round(float(v), 3) for v in c], "eye_centre_mm": [px, ye, pz]}


# =============================================================================== assembly
def build_lod(spec: FlashbangSpec, lod: int) -> Tuple[MeshBuilder, dict]:
    q = spec.lods[lod]
    mb = MeshBuilder()
    info = {}
    info["body"] = build_body(mb, spec, q)
    info["cap"] = build_cap(mb, spec, q)
    build_fuze(mb, spec, q)
    info["lever"] = build_lever(mb, spec, q)
    info["pullring"] = build_pullring(mb, spec, q)
    # the body's cut: the column boundary nearest the seam + 180 (an exact grid line of every surface)
    bounds = [c[1] % 360.0 for c in info["body"]["columns"]]
    want = (info["body"]["seam_deg"] + 180.0) % 360.0
    cut = min(bounds, key=lambda b: abs((b - want + 180.0) % 360.0 - 180.0))
    info["body"]["island_cut_deg"] = cut
    split_islands(mb, info["body"]["seam_deg"], cut)
    info["triangles"] = mb.tri_count()
    return mb, info


#: long unrolled islands are cut in two so the atlas packs (a 150 mm strip is wider than half the atlas):
#: island -> (seam azimuth, split azimuth); the cut lies on an exact column / segment line
def split_islands(mb: MeshBuilder, body_seam: float, body_cut: float):
    cuts = {"body_outer": (body_seam, body_cut), "body_inner": (body_seam, body_cut), "sleeve": (body_seam, body_cut),
            "cap_side": (135.0, 315.0), "brass_tube": (0.0, 180.0), "collar": (135.0, 315.0)}
    V = np.array(mb.verts)
    for f in mb.faces:
        if f.island in cuts:
            seam, cut = cuts[f.island]
            c = V[list(f.v)].mean(axis=0)
            th = math.degrees(math.atan2(c[1], c[0]))
            a = (th - seam) % 360.0
            b = (cut - seam) % 360.0
            f.island = f.island + ("_a" if a < b else "_b")
        elif f.island == "ring":
            um = float(np.mean([u for u, _ in f.uv]))
            R = um
            f.island = "ring_a" if um < math.pi * FLASHBANG.ring_major_r else "ring_b"
    dens = dict(mb.island_density)
    for k, d in dens.items():
        for suf in ("_a", "_b"):
            mb.island_density.setdefault(k + suf, d)


# =============================================================================== UV packing
@dataclass
class Packing:
    size: int
    ppmm: float
    pad: int
    place: Dict[str, Tuple[float, float, float, float, float]]   # island -> (umin, vmin, x0px, y0px, scale px/mm)
    fill: float

    def uv(self, island, u, v):
        umin, vmin, x0, y0, k = self.place[island]
        return ((x0 + (u - umin) * k) / self.size, (y0 + (v - vmin) * k) / self.size)


def island_boxes(builders: Sequence[MeshBuilder]):
    box = {}
    dens = {}
    for mb in builders:
        for f in mb.faces:
            us = [c[0] for c in f.uv]
            vs = [c[1] for c in f.uv]
            b = box.get(f.island)
            if b is None:
                box[f.island] = [min(us), min(vs), max(us), max(vs)]
            else:
                b[0], b[1] = min(b[0], min(us)), min(b[1], min(vs))
                b[2], b[3] = max(b[2], max(us)), max(b[3], max(vs))
        for k, d in mb.island_density.items():
            dens.setdefault(k, d)
    return box, dens


def _maxrects(rects, W, H):
    """MaxRects, best-short-side-fit, no rotation.  rects: [(name, w, h)] (integers, padding included).
    Returns {name: (x, y)} or None."""
    free = [(0, 0, W, H)]
    out = {}
    for name, w, h in rects:
        best = None
        for (fx, fy, fw, fh) in free:
            if w <= fw and h <= fh:
                ss = min(fw - w, fh - h)
                ls = max(fw - w, fh - h)
                if best is None or (ss, ls) < best[0]:
                    best = ((ss, ls), fx, fy)
        if best is None:
            return None
        _, x, y = best
        out[name] = (x, y)
        nf = []
        for (fx, fy, fw, fh) in free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                nf.append((fx, fy, fw, fh))
                continue
            if x > fx:
                nf.append((fx, fy, x - fx, fh))
            if x + w < fx + fw:
                nf.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy:
                nf.append((fx, fy, fw, y - fy))
            if y + h < fy + fh:
                nf.append((fx, y + h, fw, fy + fh - y - h))
        # prune contained rectangles
        pr = []
        for i, r in enumerate(nf):
            contained = False
            for j, r2 in enumerate(nf):
                if i != j and r[0] >= r2[0] and r[1] >= r2[1] and r[0] + r[2] <= r2[0] + r2[2] and                         r[1] + r[3] <= r2[1] + r2[3] and (r != r2 or i > j):
                    contained = True
                    break
            if not contained:
                pr.append(r)
        free = pr
    return out


def pack_islands(builders: Sequence[MeshBuilder], size: int = 2048, pad: int = 16) -> Packing:
    """MaxRects packing at one texel density (x each island's factor); binary search for the largest density that
    fits.  ``pad`` px between islands (ASSET_GUIDELINES: 16 px at 2K), pad/2 from the atlas edge.  Islands are never
    rotated or mirrored."""
    box, dens = island_boxes(builders)

    def try_pack(ppmm):
        rects = []
        for n, b in box.items():
            k = ppmm * dens[n]
            w = int(math.ceil((b[2] - b[0]) * k)) + pad
            h = int(math.ceil((b[3] - b[1]) * k)) + pad
            rects.append((n, w, h))
        rects.sort(key=lambda r: (-r[2], -r[1]))
        res = _maxrects(rects, size, size)
        if res is None:
            return None
        place = {}
        used = 0.0
        for n, w, h in rects:
            x, y = res[n]
            b = box[n]
            k = ppmm * dens[n]
            place[n] = (b[0], b[1], float(x + pad // 2), float(y + pad // 2), k)
            used += (b[2] - b[0]) * k * (b[3] - b[1]) * k
        return place, used / (size * size)

    lo, hi = 1.0, 30.0
    best = None
    for _ in range(22):
        mid = 0.5 * (lo + hi)
        r = try_pack(mid)
        if r is None:
            hi = mid
        else:
            lo = mid
            best = (mid, r)
    ppmm, (place, fill) = best
    return Packing(size, ppmm, pad, place, fill)


__all__ = ["MeshBuilder", "build_lod", "pack_islands", "Packing", "LOOK_NAMES", "LOOK_SLOT", "SLOT_PAINT",
           "SLOT_STEEL", "rounded_polygon_radius", "lever_path", "body_columns"]
