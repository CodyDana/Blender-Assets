#!/usr/bin/env python
"""props_lib.flashbang_geom - SM_Flashbang's parts as REAL GEOMETRY, generated per LOD (round 1 + finalise).

FINALISE (2026-09-27, the craft review): one brass can per hole column + dark dividers + dark discs inside (was one
brass tube whose gap ceiling / floor made each hole read as an egg, and the limbs were see-through); 24-point holes;
the base end face's wide rim with 5 blocky inward notches and the foot cut-outs; the fuze's raised front panel with
its slot, a 4 mm top-plate overhang, the housing top face removed (it was hidden and baked an invalid normal); the
lever a CHANNEL with flanges (the hinge cheeks round the knuckle) and one filleted joggle; the pull ring a 2.4 mm wire
through the pin's head (no eyelet), perimeter-equivalent polygons on one centreline at every LOD.

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
    flat: bool = False        # ROUND 2: flat-shaded (every edge of the face is marked sharp): faceted chamfers


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

    def f(self, vids, uvs, island, part, look, hint=None, density=1.0, flat=False):
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
        self.faces.append(Face(tuple(vids), tuple(uvs), island, part, look, flat))
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
    # ROUND 2: the ring lines as real V-grooves (0.7 mm wide, 0.4 mm deep) between the outer rows.  The outer rows
    # stop groove_w short of each line; the inner surface keeps the plain rows (it has no groove).  The outer island's
    # v is the PROFILE length (each groove adds 2 (slant - w)), so the groove walls are not stretched.
    gw, gd = spec.groove_w, spec.groove_d
    lines = sorted(spec.ring_lines_z) if q.grooves else []
    slant = math.hypot(gw, gd)
    if lines:
        rows_o = []
        for (za, zb, zc) in rows:
            rows_o.append((za + (gw if any(abs(za - l) < 1e-6 for l in lines) else 0.0),
                           zb - (gw if any(abs(zb - l) < 1e-6 for l in lines) else 0.0), zc))
    else:
        rows_o = list(rows)

    def vz(z):
        extra = 0.0
        for l in lines:
            if z >= l + gw - 1e-9:
                extra += 2.0 * (slant - gw)
        return z + extra

    def uv_out(th, z):
        return ((th - seam) * math.pi / 180.0 * r_o, vz(z))

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
        for ri, (za_, zb_, zc) in enumerate(rows):
            surfs = [("o", r_o, nu, q.body_cell_v, uv_out, LOOK_PAINT, "body_outer", 1.0)]
            if q.inner_shell:
                surfs.append(("i", r_i, max(1, (q.inner_cell_u if kind == "cell" else
                                                max(1, nu * q.inner_cell_u // q.body_cell_u))),
                              q.inner_cell_v, uv_in, LOOK_INNER, "body_inner", DENSITY["inner"]))
            for surf, r, nuu, nvv, uvf, look, isl, dens in surfs:
                za, zb = (rows_o[ri][0], rows_o[ri][1]) if surf == "o" else (za_, zb_)
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
    # ROUND 2: the V-groove strips (lip -> bottom -> lip) round the full revolve, sharing the rows' edge vertices
    ths_all = []
    for (kind, ta, tb, hc, nu) in cols:
        ths_all.extend(list(np.linspace(ta, tb, nu + 1))[:-1])
    ths_all.append(seam + 360.0)
    for gi, l in enumerate(lines):
        v_lo = vz(l - gw)
        prof = [(r_o, l - gw, v_lo), (r_o - gd, l, v_lo + slant), (r_o, l + gw, v_lo + 2 * slant)]
        for k in range(2):
            (ra, za, va), (rb, zb, vb) = prof[k], prof[k + 1]
            n2 = (zb - za, -(rb - ra))
            for m in range(len(ths_all) - 1):
                t0, t1 = ths_all[m], ths_all[m + 1]

                def gv(r, t, z, _l=l):
                    if abs(r - r_o) < 1e-9:
                        return vert("o", r_o, t, z)
                    tk = seam if abs(t - (seam + 360.0)) < 1e-9 else t
                    return mb.v(_cyl(r, t, z), key=("groove", round(_l, 4), round(tk % 360.0, 6)))
                vids = [gv(ra, t0, za), gv(ra, t1, za), gv(rb, t1, zb), gv(rb, t0, zb)]
                uvs = [((t0 - seam) * math.pi / 180.0 * r_o, va), ((t1 - seam) * math.pi / 180.0 * r_o, va),
                       ((t1 - seam) * math.pi / 180.0 * r_o, vb), ((t0 - seam) * math.pi / 180.0 * r_o, vb)]
                tm = math.radians(0.5 * (t0 + t1))
                mb.f(vids, uvs, "body_outer", "tube", LOOK_PAINT,
                     hint=(n2[0] * math.cos(tm), n2[0] * math.sin(tm), n2[1]))
    info["grooves"] = {"lines_z": lines, "half_width_mm": gw, "depth_mm": gd} if lines else None
    # FINALISE: the inside.  One brass CAN per hole column (a vertical cylinder narrower than the hole, so each hole
    # shows a lit cylinder with dark gaps both sides, as the reference does), dark radial DIVIDERS midway between
    # the columns (they close the line of sight through the gap at the limbs: no background through the body) and
    # dark discs closing the gap top and bottom.  Only the cans' outward arc is modelled (the back is never seen).
    # ROUND 2: each can is a straight tube with, at every row's seam, the lower tube's top edge (a 0.45 mm step in)
    # and the upper part's rounded shoulder flaring back out over 1.2 mm - the reference's p4 seam and shoulder as
    # geometry (round 1 painted a light band there, which read as the dome of a "brass egg").
    # ROUND 2b: ONE concentric brass tube just behind the wall (r inner_tube_r = r_i - 0.6), as the reference shows
    # at 4x (WorkFiles/flashbang/r2/look2/holes_dev2.png): the brass fills every window edge to edge, darker toward
    # the window's sides (a large cylinder's shading, not a gap), with a thin seam line a little above the centre.
    # Round 2's per-hole cans (narrower than the hole, dark gaps both sides) read as "pills" in every view; the
    # round-1 tube sat 3 mm deeper, so its floor and ceiling showed as curved dark edges (the "egg").  The tube closes
    # every line of sight, so the dividers and gap discs are gone.  Its ring angles are dense only behind the holes
    # (tube_segs per hole arc, one or two across each web).  At each row's seam (q.can_shoulder) the tube steps in by
    # can_step over 0.35 mm going up: an up-facing lit ledge under a thin dark line (the painter's seam band).
    holes_th = spec.hole_thetas()
    nh = len(holes_th)
    zb0, zb1 = spec.body_z0, spec.sleeve_z0
    rt = spec.inner_tube_r
    tprof = [(rt, zb0)]
    if q.can_shoulder:
        for zs in sorted(spec.tube_seam_z):
            tprof += [(rt, zs), (rt - spec.can_step, zs + 0.35)]
    tprof.append((rt, zb1))
    ts_ = [0.0]
    for k in range(1, len(tprof)):
        ts_.append(ts_[-1] + math.hypot(tprof[k][0] - tprof[k - 1][0], tprof[k][1] - tprof[k - 1][1]))
    hw = spec.hole_ang_w_deg / 2.0 + 1.0
    t_seam = (holes_th[0] - hw - 5.0)                   # the island seam in a web (never seen)
    tang = []
    for i in range(nh):
        a0, a1 = holes_th[i] - hw, holes_th[i] + hw
        tang += list(np.linspace(a0, a1, q.tube_segs + 1))
        nxt = holes_th[(i + 1) % nh] + (360.0 if i == nh - 1 else 0.0) - hw
        gap = nxt - a1
        if gap > 35.0:
            tang.append(a1 + gap / 2.0)
    tang = sorted(set(round(((t - t_seam) % 360.0) + t_seam, 6) for t in tang))
    tang = [t_seam] + [t for t in tang if t > t_seam + 1e-6] + [t_seam + 360.0]

    def tv(t, j):
        tk = t_seam if abs(t - t_seam - 360.0) < 1e-9 else t
        r, z = tprof[j]
        return mb.v(_cyl(r, t, z), key=("brass", round(tk % 360.0, 6), j))
    for j in range(len(tprof) - 1):
        (ra, za), (rb, zb) = tprof[j], tprof[j + 1]
        n2 = (zb - za, -(rb - ra))
        for m in range(len(tang) - 1):
            t0, t1 = tang[m], tang[m + 1]
            vids = [tv(t0, j), tv(t1, j), tv(t1, j + 1), tv(t0, j + 1)]
            uvs = [((t0 - t_seam) * math.pi / 180.0 * rt, ts_[j]), ((t1 - t_seam) * math.pi / 180.0 * rt, ts_[j]),
                   ((t1 - t_seam) * math.pi / 180.0 * rt, ts_[j + 1]), ((t0 - t_seam) * math.pi / 180.0 * rt, ts_[j + 1])]
            am = math.radians(0.5 * (t0 + t1))
            mb.f(vids, uvs, "brass_tube", "tube", LOOK_BRASS,
                 hint=(n2[0] * math.cos(am), n2[0] * math.sin(am), n2[1]), density=DENSITY["tube"])
    # dark radial dividers in the gap (tube -> wall) at the middle of every web: a ray grazing a limb hole otherwise
    # runs round the gap and out through the next hole (measured: background in the v1 / v2 limb holes)
    webs = []
    for i in range(nh):
        a, b = holes_th[i], holes_th[(i + 1) % nh]
        webs.append((a + ((b - a) % 360.0) / 2.0) % 360.0)
    r_div = (spec.body_r_in - 0.02) if q.inner_shell else (spec.body_r - 0.05)
    r_d0 = rt - spec.can_step - 0.1
    for k, wt in enumerate(webs):
        tvv = np.array([-math.sin(math.radians(wt)), math.cos(math.radians(wt)), 0.0])
        rv = np.array([math.cos(math.radians(wt)), math.sin(math.radians(wt)), 0.0])
        for side in (-1.0, 1.0):
            o = tvv * 0.3 * side
            c = [(r_d0, zb0), (r_div, zb0), (r_div, zb1), (r_d0, zb1)]
            vids = [mb.v(tuple(o + rv * r + np.array([0, 0, z])), key=("div", k, side, round(r, 4), round(z, 4)))
                    for r, z in c]
            wdv = r_div - r_d0 + 3.0
            uvs = [(k * 2 * wdv + (side > 0) * wdv + ((r - r_d0) if side > 0 else (r_div - r)), z) for r, z in c]
            mb.f(vids, uvs, "dividers", "tube", LOOK_INNER, hint=tuple(tvv * side), density=DENSITY["hidden"])
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

    # ROUND 2: the sleeve's top chamfer is FACETED (the reference's "striped" bevel, v2 / v3 / blind pair 8): pairs of
    # segments form one planar facet (the odd ring vertices of the chamfer's two rings sit on the facet's chord plane)
    # and the chamfer faces are flat-shaded
    step = 360.0 / q.revolve_segs
    uniform = all(abs((ths[m + 1] - ths[m]) - step) < 1e-6 for m in range(len(ths) - 1)) and q.revolve_segs % 2 == 0
    facet = q.box_chamfer and uniform
    CH = 2                                              # the chamfer band: rings 2 -> 3

    def pv(k, t, m):
        r, z, surf = prof[k]
        if surf == "o":
            return vert("o", r_o, t, z)
        tk = seam if abs(t - (seam + 360.0)) < 1e-9 else t
        if facet and k in (CH, CH + 1) and m % 2 == 1:
            r = r * math.cos(math.radians(step))
        return mb.v(_cyl(r, t, z), key=("sleeve", k, round(tk % 360.0, 6)))

    for k in range(len(prof) - 1):
        (ra, za, _), (rb, zb, _) = prof[k], prof[k + 1]
        dr, dz = rb - ra, zb - za
        n2 = (dz, -dr)                                  # profile walks with the solid on the LEFT
        for m in range(len(ths) - 1):
            t0, t1 = ths[m], ths[m + 1]
            vids = [pv(k, t0, m), pv(k, t1, m + 1), pv(k + 1, t1, m + 1), pv(k + 1, t0, m)]
            if islands[k] == "sleeve":
                rr = [ra, ra, rb, rb]
                uvs = [((t - seam) * math.pi / 180.0 * rr[i], -(s_acc[k] if i < 2 else s_acc[k + 1]))
                       for i, t in enumerate((t0, t1, t1, t0))]
            else:
                uvs = [(r * math.cos(math.radians(t)), r * math.sin(math.radians(t)))
                       for r, t in ((ra, t0), (ra, t1), (rb, t1), (rb, t0))]
            tm = math.radians(0.5 * (t0 + t1))
            hint = (n2[0] * math.cos(tm), n2[0] * math.sin(tm), n2[1])
            mb.f(vids, uvs, islands[k], "sleeve", looks[k], hint=hint, flat=facet and k == CH)
    info["holes"] = hole_list
    info["sleeve_chamfer_facets"] = (q.revolve_segs // 2) if facet else 0
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
    if q.cap_per_flat >= 2:
        # ROUND 2: the reference's cap reads as 12 FLATS (vertical light / dark bands, v2 / v3 and p3): the vertices
        # sit at each corner round's two tangent points, so every flat is one planar quad strip with a narrow soft
        # corner between flats
        a_in = spec.cap_apothem - spec.cap_corner_r
        tp = math.degrees(math.atan(a_in * math.tan(math.pi / n_flat) / spec.cap_apothem))
        base = [15.0 + 30.0 * k + sg * tp for k in range(n_flat) for sg in (-1.0, 1.0)]
        base.append(seam)                            # the island seam (a flat's centre: planar) closes the ring
    else:
        base = [seam + 360.0 * m / (n_flat * q.cap_per_flat) for m in range(n_flat * q.cap_per_flat)]
    half_w = {}
    notch_edges = []
    notch_hw = math.degrees(spec.notch_w_mm / 2.0 / 16.0)     # angular half width (5 mm at the rim's middle, r 16)
    if q.cap_notches:
        for nd in spec.notch_deg:
            a0, a1 = nd - notch_hw, nd + notch_hw
            notch_edges += [a0, a1]
    ne = [((a - seam) % 360.0) + seam for a in notch_edges]
    base = [a for a in base if all(abs(((a - e + 180.0) % 360.0) - 180.0) > 0.8 for e in ne)]
    angles = sorted(set([round(((a - seam) % 360.0) + seam, 6) for a in base + notch_edges]))
    angles.append(seam + 360.0)

    def in_notch(t):
        if not q.cap_notches:
            return False
        for nd in spec.notch_deg:
            d = (t - nd + 180.0) % 360.0 - 180.0
            if abs(d) < notch_hw - 1e-6:
                return True
        return False

    def rpoly(t):
        return rounded_polygon_radius(t, n_flat, spec.cap_apothem, spec.cap_corner_r, phase)

    # rings: (kind, value, z).  FINALISE: the foot ring sits on the contact plane, and inside a notch it is cut out
    # notch_foot_z up through the outer bottom edge (the side views' rectangular foot cut-outs)
    foot_notch = False          # ROUND 2b: no through-cut at the foot (the recesses below replace it)
    side_rings = [("c", spec.body_r - 0.1, spec.body_z0),            # chamfer top (tucked just inside the body)
                  ("p", 0.0, spec.cap_side_z1), ("p", 0.0, spec.cap_side_z0),
                  ("c", spec.foot_r, 0.0)]
    # ROUND 2b: the foot recesses - arcs whose edges snap to the nearest existing ring angles
    recess = []
    if q.cap_notches and q.cap_end_detail >= 1:
        cand = [a % 360.0 for a in angles[:-1]]
        for nd in spec.notch_deg:
            e0 = min(cand, key=lambda a: abs(((a - (nd - spec.foot_recess_w_deg / 2.0)) + 180.0) % 360.0 - 180.0))
            e1 = min(cand, key=lambda a: abs(((a - (nd + spec.foot_recess_w_deg / 2.0)) + 180.0) % 360.0 - 180.0))
            recess.append((e0, (e1 - e0) % 360.0))

    def in_recess(t):
        return any(1e-6 < (t - e0) % 360.0 < w - 1e-6 for e0, w in recess)

    def ring_r(ring, t):
        kind, val, z = ring
        return rpoly(t) + val if kind == "p" else val

    def ring_z(ring, notch, rec=False):
        if ring is side_rings[2] and rec:
            return spec.cap_side_z0 + spec.foot_recess_h
        return ring[2]

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
            notch_q = in_notch(0.5 * (t0 + t1))
            rec_q = in_recess(0.5 * (t0 + t1))
            c = [(ra_, t0), (ra_, t1), (rb_, t1), (rb_, t0)]
            vids = [V("s%d" % (k if i < 2 else k + 1), ring_r(rg, t), t, ring_z(rg, notch_q, rec_q))
                    for i, (rg, t) in enumerate(c)]
            uvs = [((t - seam) * math.pi / 180.0 * rmean[k if i < 2 else k + 1], -(s_acc[k] if i < 2 else s_acc[k + 1]))
                   for i, (rg, t) in enumerate(c)]
            tm = 0.5 * (t0 + t1)
            pa = np.array(_cyl(ring_r(ra_, tm), tm, ring_z(ra_, notch_q, rec_q)))
            pb = np.array(_cyl(ring_r(rb_, tm), tm, ring_z(rb_, notch_q, rec_q)))
            # outward: perpendicular to the profile, away from the axis / down at the foot
            tang = pb - pa
            rad = np.array([math.cos(math.radians(tm)), math.sin(math.radians(tm)), 0.0])
            hint = rad - tang * np.dot(rad, tang) / max(np.dot(tang, tang), 1e-12)
            if k == len(side_rings) - 2:
                hint = hint + np.array([0, 0, -0.5])
            mb.f(vids, uvs, "cap_side", "cap", LOOK_STEEL, hint=hint)
    # ROUND 2b: the recess end walls - a triangle in the radial plane at each recess edge (the flat's lower edge at
    # z0 and z0 + h, the foot ring at 0), facing into the recess
    if recess:
        wk = 0
        rg = side_rings[2]
        for e0, w in recess:
            for t, into in ((e0, 1.0), (e0 + w, -1.0)):
                vb = V("s2", ring_r(rg, t), t, spec.cap_side_z0)
                va = V("s2", ring_r(rg, t), t, spec.cap_side_z0 + spec.foot_recess_h)
                vf = V("s3", spec.foot_r, t, 0.0)
                tang = np.array([-math.sin(math.radians(t)), math.cos(math.radians(t)), 0.0]) * into
                u0 = wk * 6.0
                ua, ub = (u0, u0 + 3.3) if into > 0 else (u0 + 3.3, u0)
                mb.f([vf, vb, va], [(ub, 0.0), (ua, spec.cap_side_z0), (ua, spec.cap_side_z0 + spec.foot_recess_h)],
                     "cap_foot_walls", "cap", LOOK_STEEL, hint=tang, density=DENSITY["cap_end"])
                wk += 1
    # side walls of the foot cut-outs: a triangle at each notch edge (chamfer ring above, foot at 0 and at the cut)
    if foot_notch:
        wk = 0
        for m in range(len(angles) - 1):
            t = angles[m + 1]
            tn = angles[m + 2] if m + 2 < len(angles) else angles[1] + 360.0
            left = in_notch(0.5 * (angles[m] + t))
            right = in_notch(0.5 * (t + tn))
            if left == right:
                continue
            rg = side_rings[2]
            va = V("s2", ring_r(rg, t), t, rg[2])
            v0 = V("s3", spec.foot_r, t, 0.0)
            v1 = V("s3", spec.foot_r, t, spec.notch_foot_z)
            tang = np.array([-math.sin(math.radians(t)), math.cos(math.radians(t)), 0.0])
            hint = tang if right else -tang                   # faces into the cut-out
            u0 = wk * 6.0
            ua, ub = (u0, u0 + 3.3) if right else (u0 + 3.3, u0)          # never mirrored
            mb.f([v0, v1, va], [(ua, 0.0), (ua, spec.notch_foot_z), (ub, spec.cap_side_z0)],
                 "cap_foot_walls", "cap", LOOK_STEEL, hint=hint, density=DENSITY["cap_end"])
            wk += 1
    # end face: radial bands (r_in, r_out, z_normal, z_notch) from the centre out (spec.end_bands, FINALISE)
    bands = [tuple(b) for b in spec.end_bands]
    ann1 = bands[-1][1]
    if not q.cap_notches:
        bands = [(b[0], b[1], b[2], b[2]) for b in bands]
    if q.cap_end_detail == 1:
        # LOD1: the recessed disc, the groove and the rim without the inner tabs; the foot cut-outs stay (the side)
        g0, g1 = bands[3][0], bands[3][1]            # the groove band's radii
        bands = [(0.0, g0, bands[0][2], bands[0][2]), (g0, g1, bands[3][2], bands[3][2]), bands[4],
                 bands[-1] if foot_notch else (bands[-1][0], bands[-1][1], bands[-1][2], bands[-1][2])]
    if q.cap_end_detail == 0:
        bands = [(0.0, ann1, 0.0, 0.0)]

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


def _ear_clip(poly):
    """Triangulate a simple CCW 2-D polygon (list of (x, y)) -> index triples."""
    idx = list(range(len(poly)))
    P = [np.asarray(p, float) for p in poly]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 1000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[(k - 1) % n], idx[k], idx[(k + 1) % n]
            a, b, c = P[i0], P[i1], P[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = P[j]
                if cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12:
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                break
    tris.append(tuple(idx))
    return tris


def prism(mb: MeshBuilder, poly, axis: str, a0, a1, island, part, look, caps=(True, True), density=1.0):
    """ROUND 2: extrude a 2-D polygon (in the plane of the two OTHER axes, in xyz order) from a0 to a1 along
    ``axis``.  Side faces: one unrolled strip island (u = perimeter, v = the axis coordinate); caps: planar islands."""
    ai = "xyz".index(axis)
    o1, o2 = [o for o in range(3) if o != ai]
    poly = [tuple(map(float, p)) for p in poly]
    area = sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1]
               for k in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    n = len(poly)

    def P(k, a):
        p = [0.0, 0.0, 0.0]
        p[ai], p[o1], p[o2] = a, poly[k][0], poly[k][1]
        return p
    per = [0.0]
    for k in range(n):
        per.append(per[-1] + math.hypot(poly[(k + 1) % n][0] - poly[k][0], poly[(k + 1) % n][1] - poly[k][1]))
    for k in range(n):
        k1 = (k + 1) % n
        vids = [mb.v(P(k, a0), key=(island, "pr", k, 0)), mb.v(P(k1, a0), key=(island, "pr", k1, 0)),
                mb.v(P(k1, a1), key=(island, "pr", k1, 1)), mb.v(P(k, a1), key=(island, "pr", k, 1))]
        uvs = [(per[k], a0), (per[k + 1], a0), (per[k + 1], a1), (per[k], a1)]
        dx, dy = poly[k1][0] - poly[k][0], poly[k1][1] - poly[k][1]
        hint = [0.0, 0.0, 0.0]
        hint[o1], hint[o2] = dy, -dx                  # outward of a CCW polygon
        mb.f(vids, uvs, island, part, look, hint=hint, density=density)
    tris = _ear_clip(poly)
    for which, a, sgn in ((0, a0, -1.0 if a1 > a0 else 1.0), (1, a1, 1.0 if a1 > a0 else -1.0)):
        if not caps[which]:
            continue
        hint = [0.0, 0.0, 0.0]
        hint[ai] = sgn
        for t in tris:
            vids = [mb.v(P(i, a), key=(island, "pr", i, which)) for i in t]
            mb.f(vids, [poly[i] for i in t], f"{island}_cap{which}", part, look, hint=hint, density=density)


def chamfered_rect(x0, x1, y0, y1, c):
    """CCW rectangle with its four corners cut by c = (c(x0,y0), c(x1,y0), c(x1,y1), c(x0,y1))."""
    pts = []
    for (x, y, cc, dx0, dy0, dx1, dy1) in ((x0, y0, c[0], 0, 1, 1, 0), (x1, y0, c[1], -1, 0, 0, 1),
                                           (x1, y1, c[2], 0, -1, -1, 0), (x0, y1, c[3], 1, 0, 0, -1)):
        if cc > 0:
            pts += [(x + dx0 * cc, y + dy0 * cc), (x + dx1 * cc, y + dy1 * cc)]
        else:
            pts.append((x, y))
    return pts


def sphere(mb: MeshBuilder, centre, r, nseg, nring, island, part, look):
    """ROUND 2: a low UV sphere (the spring post's ball)."""
    c = np.asarray(centre, float)

    def P(i, j):
        th = math.pi * j / nring
        ph = 2 * math.pi * i / nseg
        return c + r * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
    for i in range(nseg):
        for j in range(nring):
            cor = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            vids = [mb.v(P(a, b), key=(island, "sph", a % nseg if 0 < b < nring else 0, b)) for a, b in cor]
            uvs = [(a * 2 * math.pi * r / nseg, -b * math.pi * r / nring) for a, b in cor]
            mid = P(i + 0.5, j + 0.5) - c
            mb.f(vids, uvs, island, part, look, hint=mid)


def ring_frame(spec: FlashbangSpec):
    """ROUND 2: the pull ring's frame - top point (the pin eye), in-plane unit vectors u (the wire's direction at the
    top: horizontal, ring_yaw_deg off +X) and zdir (centre -> top, tilted ring_tilt_deg off vertical, the centre
    swinging out to -Y), and the centre.  Shared by the geometry and the painter."""
    px, pz = spec.pin_c
    top = np.array([px, spec.pin_eye_y(), pz])
    a = math.radians(spec.ring_yaw_deg)
    u = np.array([math.cos(a), math.sin(a), 0.0])
    out = np.cross(u, np.array([0.0, 0.0, 1.0]))            # horizontal, outward (-Y for u = +X)
    tau = math.radians(spec.ring_tilt_deg)
    zdir = math.cos(tau) * np.array([0.0, 0.0, 1.0]) - math.sin(tau) * out
    return top, u, zdir, top - spec.ring_major_r * zdir


# =============================================================================== lever (swept plate)
def lever_path(spec: FlashbangSpec, q: LodQuality):
    """Centreline of the lever's web in the XZ plane (y handled by the width functions), from the curl's free end
    over the knuckle and down to the bent tip.  Returns ([(x, z, tx, tz)], marks) with the unit tangent and the
    indices of the curl's end (top) and of the joggle's first / last point.

    FINALISE: the joggle is ONE straight diagonal step with a fillet at each bend (it was a cosine S-crank)."""
    kx, _ky, kz = spec.knuckle_c
    t = spec.lever_t
    rc = spec.knuckle_r + 0.05 + t / 2.0
    xu = kx + rc                                         # upper segment centreline x (= knuckle + clearance)
    xl = spec.lever_lower_x + t / 2.0
    pts = []
    for i in range(q.lever_curl + 1):                    # 165 deg -> 0 deg round the knuckle (clockwise, over the top)
        a = math.radians(165.0 - 165.0 * i / q.lever_curl)
        pts.append((kx + rc * math.cos(a), kz + rc * math.sin(a)))
    top_i = len(pts) - 1
    zj0, zj1 = spec.lever_joggle_z
    nf = 2 if q.lever_curl >= 8 else (1 if q.lever_curl >= 4 else 0)
    zt = spec.lever_tip_z
    zb = zt + spec.lever_tip_bend
    A, B, C, Dd = np.array([xu, kz]), np.array([xu, zj0]), np.array([xl, zj1]), np.array([xl, zb])

    def fillet(P0, P1, P2, r, n):
        d0, d1 = _unit(P1 - P0), _unit(P2 - P1)
        a, b = P1 - d0 * r, P1 + d1 * r
        out = []
        for f in np.linspace(0.0, 1.0, n + 2):
            out.append(tuple((1 - f) ** 2 * a + 2 * (1 - f) * f * P1 + f * f * b))
        return out
    f1 = fillet(A, B, C, 1.4, nf)
    j0 = len(pts)
    pts += f1
    f2 = fillet(B, C, Dd, 1.4, nf)
    pts += f2
    j1 = len(pts) - 1
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
    return out, {"top": top_i, "j0": j0, "j1": j1}


def _lever_section(q: LodQuality, t: float, F: float, yp: float, ym: float):
    """The lever's cross-section in (n, y), n = along the outward normal from the web's centreline.
    FINALISE: a CHANNEL (U) - the web plus two flanges F deep toward the body - at LOD0/1 (8 points, CCW); a solid
    box of the same outline at LOD2 (the silhouette is identical)."""
    h = t / 2.0
    if q.box_chamfer:
        return [(h, ym), (h, yp), (h - F, yp), (h - F, yp - t), (-h, yp - t), (-h, ym + t), (h - F, ym + t),
                (h - F, ym)]
    return [(h, ym), (h, yp), (h - F, yp), (h - F, ym)]


def build_lever(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """The spoon: a CHANNEL swept along lever_path (FINALISE), its width tapering on the upper segment (the -Y edge
    slants, the +Y edge is straight - v4), the lower segment 0.26 D wide, the tip squared with rounded corners.  The
    flanges run the full length, so round the knuckle they become the hinge's cheeks either side of the knuckle."""
    path, marks = lever_path(spec, q)
    t = spec.lever_t
    F = spec.lever_flange
    P = np.array([(p[0], p[1]) for p in path])
    # the UV's v is the arc length of a DENSE reference path (the same at every LOD), read at each sample
    dense, _dm = lever_path(spec, LodQuality(1, 1, 1, 3, 1, 1, 1, 3, 3, 1, False, 3, 3, 3, 3, 3, 3, 96, True, (0, 0)))
    DP = np.array([(p[0], p[1]) for p in dense])
    fine = [DP[0]]
    for i in range(1, len(DP)):
        for f in np.linspace(0, 1, 41)[1:]:
            fine.append(DP[i - 1] + (DP[i] - DP[i - 1]) * f)
    fine = np.array(fine)
    fs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    s = np.array([fs[int(np.argmin(np.linalg.norm(fine - p, axis=1)))] for p in P])
    top_i, j0, j1 = marks["top"], marks["j0"], marks["j1"]
    yp_top, ym_top = 6.4, 6.4 - spec.lever_w_top
    yp_j, ym_j = 6.4, 6.4 - spec.lever_w_joggle
    yp_l, ym_l = spec.lever_w / 2.0, -spec.lever_w / 2.0

    def widths(si):
        if si <= s[top_i]:
            return yp_top, ym_top
        if si <= s[j0]:
            f = (si - s[top_i]) / max(s[j0] - s[top_i], 1e-9)
            return yp_top + (yp_j - yp_top) * f, ym_top + (ym_j - ym_top) * f
        if si <= s[j1]:
            f = (si - s[j0]) / max(s[j1] - s[j0], 1e-9)
            return yp_j + (yp_l - yp_j) * f, ym_j + (ym_l - ym_j) * f
        return yp_l, ym_l

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
        dd = rcn * (1.0 - math.sin(ang))
        ww = rcn * (1.0 - math.cos(ang))
        f = 1.0 - dd / seg
        secs.append((xa + (xe - xa) * f, za + (ze - za) * f, txe, tze, yp_l - ww, ym_l + ww, s[-1] - dd))
    last_w = rcn * 0.92 if nt > 1 else rcn * 0.6
    secs.append((xe, ze, txe, tze, yp_l - last_w, ym_l + last_w, s[-1]))

    def section(x, z, tx, tz, yp, ym):
        n = np.array([-tz, 0.0, tx])                 # +n = the web's OUTER face (away from body / knuckle)
        o = np.array([x, 0.0, z])
        Y = np.array([0.0, 1.0, 0.0])
        sec2 = _lever_section(q, t, F, yp, ym)
        pts = [o + n * a + Y * b for a, b in sec2]
        return pts, n, sec2

    S = [section(*sc[:6]) + (sc[6],) for sc in secs]
    npt = len(S[0][0])
    # outward normal of each 2-D section edge (the polygon is CCW in (n, y): outward = (dy, -dn))
    sec0 = S[0][2]
    area = sum(sec0[k][0] * sec0[(k + 1) % npt][1] - sec0[(k + 1) % npt][0] * sec0[k][1] for k in range(npt))
    sgn = 1.0 if area > 0 else -1.0
    for i in range(len(S) - 1):
        A, na, s2a, sa = S[i]
        B, nb_, s2b, sb = S[i + 1]
        ua = np.concatenate([[0.0], np.cumsum([np.linalg.norm(A[(k + 1) % npt] - A[k]) for k in range(npt)])])
        ub = np.concatenate([[0.0], np.cumsum([np.linalg.norm(B[(k + 1) % npt] - B[k]) for k in range(npt)])])
        nm = _unit(na + nb_)
        for k in range(npt):
            k1 = (k + 1) % npt
            vids = [mb.v(A[k], key=("lever", i, k)), mb.v(A[k1], key=("lever", i, k1)),
                    mb.v(B[k1], key=("lever", i + 1, k1)), mb.v(B[k], key=("lever", i + 1, k))]
            dn = s2a[k1][0] - s2a[k][0]
            dy = s2a[k1][1] - s2a[k][1]
            en, ey = sgn * dy, -sgn * dn
            hint = nm * en + np.array([0.0, 1.0, 0.0]) * ey
            mb.f(vids, [(ua[k], -sa), (ua[k + 1], -sa), (ub[k + 1], -sb), (ub[k], -sb)], "lever", "lever",
                 LOOK_LEVER, hint=hint)
    quads = ((0, 1, 4, 5), (1, 2, 3, 4), (5, 6, 7, 0)) if npt == 8 else ((0, 1, 2, 3),)
    for which, idx in ((0, 0), (1, len(S) - 1)):
        A, n, s2, si = S[idx]
        tng = np.array([path[0][2], 0.0, path[0][3]]) if which == 0 else np.array([path[-1][2], 0.0, path[-1][3]])
        hint = -tng if which == 0 else tng
        vids = [mb.v(A[k], key=("lever", idx, k)) for k in range(npt)]
        uvs = [(float(a), float(b)) for a, b in s2]
        for qd in quads:
            mb.f([vids[i] for i in qd], [uvs[i] for i in qd], f"lever_end{which}", "lever", LOOK_LEVER, hint=hint)
    return {"path_len_mm": round(float(s[-1]), 3), "sections": len(S), "section": "channel" if npt == 8 else "box",
            "flange_mm": F, "sheet_mm": t,
            "tip_z_mm": round(float(ze), 3), "upper_inner_x_mm": round(float(path[top_i][0] - t / 2), 3)}


# =============================================================================== fuze head
def build_fuze(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """ROUND 2: the fuze head rebuilt as a mechanism (the round-1 blind tells: "a plain box with a flat cap, no
    striker, pins, hinge knuckle or ring-pin boss").  Every part is real geometry: the housing (its -X+Y vertical
    edge cut back), a thicker chamfered top plate, the striker plate on the -X face with its hinge knuckle across the
    top, the side lug on +Y (a flag plate on a spacer, rolled top edge, two cross pins with square washers), the
    screw head and a coil end on the -Y face, the hinge block, the lever's knuckle, the pin boss and the spring post
    with its ball.  ``q.head_detail`` drops the smallest parts at the lower LODs."""
    s = spec
    h = s.housing_half
    hd = q.head_detail
    ss = q.small_segs
    # housing: a vertical prism (top covered by the plate, bottom by the plinth: no hidden caps)
    cc = s.housing_corner_c if q.box_chamfer else (0.0, 0.0, 0.0, s.housing_corner_c[3])
    prism(mb, chamfered_rect(-h, h, -h, h, cc), "z", s.housing_z0, s.housing_z1, "housing", "fuze", LOOK_STEEL,
          caps=(False, False))
    chamfer_box(mb, (s.plate_x[0], -s.plate_y, s.housing_z1), (s.plate_x[1], s.plate_y, s.plate_z1), 0.5,
                "plate", "fuze", LOOK_STEEL, chamfer=q.box_chamfer)
    # the striker: a plate on the -X face (hinged at its top knuckle, v2's centre)
    sz0, sz1 = s.striker_z
    chamfer_box(mb, (-h - s.striker_proud, -s.striker_y, sz0), (-h + 0.2, s.striker_y, sz1), 0.35, "striker",
                "fuze", LOOK_STEEL, chamfer=q.box_chamfer, skip=((0, 1), (2, 1)))
    skx, skz = s.striker_knuckle_c
    cylinder(mb, (skx, 0.0, skz), "y", s.striker_knuckle_r, -s.striker_y, s.striker_y, ss, "striker_knuckle", "fuze",
             LOOK_STEEL)
    # the side lug on the +Y face
    y0, y1 = s.lug_y
    prism(mb, s.lug_poly_xz, "y", y0, y1, "lug", "fuze", LOOK_STEEL)
    lx0, lx1, lz0, lz1 = s.lug_standoff
    chamfer_box(mb, (lx0, h - 0.3, lz0), (lx1, y0 + 0.1, lz1), 0.3, "lug_spacer", "fuze", LOOK_STEEL,
                chamfer=q.box_chamfer, skip=((1, -1), (1, 1)))
    ptop = max(p[1] for p in s.lug_poly_xz)
    xs = [p[0] for p in s.lug_poly_xz]
    cylinder(mb, (0.0, 0.5 * (y0 + y1), ptop - 0.2), "x", s.lug_roll_r, min(xs) + 0.4, max(xs), max(6, ss // 3 * 2),
             "lug_roll", "fuze", LOOK_STEEL)
    if hd >= 1:
        yc = 0.5 * (y0 + y1)
        for k, (fx, pzz) in enumerate(s.lug_pins):
            chamfer_box(mb, (fx - 0.8, yc - 1.4, pzz - 1.4), (fx + 0.05, yc + 1.4, pzz + 1.4), 0.2, f"lug_washer{k}",
                        "fuze", LOOK_STEEL, chamfer=q.box_chamfer, skip=((0, 1),))
            cylinder(mb, (0.0, yc, pzz), "x", 0.75, fx - 1.6, fx - 0.75, max(6, ss // 2), f"lug_pin{k}", "fuze",
                     LOOK_STEEL, caps=(True, False))
    # ROUND 2b: the -Y side flag (sheet plate in YZ, flush with the -X face) and its cross pin
    prism(mb, s.flag_poly_yz, "x", s.flag_x[0], s.flag_x[1], "flag", "fuze", LOOK_STEEL)
    if hd >= 1:
        fy, fz, fr = s.flag_pin
        cylinder(mb, (0.0, fy, fz), "x", fr, s.flag_x[0] - 0.7, s.flag_x[1] + 0.7, 6, "flag_pin", "fuze", LOOK_STEEL)
    chamfer_box(mb, (s.block_x[0], s.block_y[0], s.block_z[0]), (s.block_x[1], s.block_y[1], s.block_z[1]), 0.4,
                "block", "fuze", LOOK_STEEL, chamfer=q.box_chamfer)
    # knuckle (hinge barrel)
    kx, ky, kz = s.knuckle_c
    cylinder(mb, (kx, 0.0, kz), "y", s.knuckle_r, ky - s.knuckle_len / 2, ky + s.knuckle_len / 2, ss, "knuckle",
             "fuze", LOOK_STEEL)
    # pin boss (sleeve for the pin) off the block's -Y face; the pin shaft shows between it and the pin's head
    px, pz = s.pin_c
    cylinder(mb, (px, 0.0, pz), "y", s.pin_boss_r, s.block_y[0] + 0.2, s.pin_boss_y1, ss, "pin_boss",
             "fuze", LOOK_STEEL, caps=(False, True))
    # the screw head on the housing's -Y face (v1 / v3 / p1) and the coil end beside it (v3)
    bx, bz = s.small_boss_c
    cylinder(mb, (bx, 0.0, bz), "y", s.small_boss_r, -h + 0.1, -h - 0.7, max(8, ss // 3 * 2), "small_boss", "fuze",
             LOOK_STEEL, caps=(False, True))
    if hd >= 2:
        cx_, cz_ = s.coil_c
        torus(mb, (cx_, -h - 0.25, cz_), (1, 0, 0), (0, 0, 1), 1.0, 0.42, 8, 3, "coil", "fuze", LOOK_STEEL)
    # the spring post and its ball at the hinge block's -Y corner (v1's bright ball, v4's post)
    if hd >= 1:
        ptx, pty = s.post_c
        cylinder(mb, (ptx, pty, 0.0), "z", s.post_r, s.post_z[0], s.post_z[1], max(6, ss // 2), "post", "fuze",
                 LOOK_STEEL, caps=(False, False))
        sphere(mb, (ptx, pty, s.ball_z), s.ball_r, 6, 4 if hd >= 2 else 3, "ball", "fuze", LOOK_STEEL)
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
    y_head0 = ye + s.pin_head_len / 2.0                      # the head's inner end
    # pin shaft: hidden inside the boss, and (ROUND 2) visible between the boss's outer end and the head
    cylinder(mb, (px, 0.0, pz), "y", s.pin_r, s.block_y[1] - 1.0, y_head0 + 0.05, max(6, q.small_segs // 2),
             "pin_shaft", "pin", LOOK_RING, density=DENSITY["shaft"] if y_head0 > s.pin_boss_y1 - 0.5 else 1.0)
    # FINALISE: the pin's head - a short thick cylinder the ring passes THROUGH (no separate split-ring eyelet)
    cylinder(mb, (px, 0.0, pz), "y", s.pin_head_r, y_head0, y_head0 - s.pin_head_len, max(6, q.small_segs),
             "pin_head", "pin", LOOK_RING)
    # the ring: its top passes through the pin head.  FINALISE: every LOD's ring lies on the SAME centreline - the
    # polygon radii are compensated so each LOD's mean radius equals the true one (no pop).  ROUND 2: the pose is
    # fitted to the four views (ring_frame: 10 deg off vertical, the wire 10 deg off +X at the top)
    top, u, zdir, c = ring_frame(s)
    R = s.ring_major_r
    r = s.ring_wire_d / 2.0
    # perimeter-equivalent polygons: an n-gon of circumradius x*pi/(n sin(pi/n)) has the circle's perimeter, so its
    # MEAN projected width (Cauchy) equals the round wire's at any view angle - what a sub-pixel wire's coverage sees
    Rv = R * math.pi / (q.ring_major * math.sin(math.pi / q.ring_major))
    rv = r * math.pi / (q.ring_minor * math.sin(math.pi / q.ring_minor))
    torus(mb, c, u, zdir, Rv, rv, q.ring_major, q.ring_minor, "ring", "ring", LOOK_RING,
          seam_maj=math.radians(90.0 + 180.0 / q.ring_major))
    return {"ring_centre_mm": [round(float(v), 3) for v in c], "pin_head_centre_mm": [px, ye, pz],
            "ring_polygon_radii_mm": [round(Rv, 4), round(rv, 4)]}


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
            "cap_side": (135.0, 315.0), "collar": (135.0, 315.0)}
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
