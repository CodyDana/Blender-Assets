#!/usr/bin/env python
"""props_lib.fan_tassel - SK_Fan_Tassel: the separate, optional tassel (RS 8, fan2 only).  numpy only.

WHY A BONE CHAIN (not a rigid mesh): it must hang from the pivot under gravity whatever the fan does; a
rigid piece would point wherever the fan points.  Six bones in one chain (tassel_root -> cord_01 ->
cord_02 -> knot -> skirt_01 -> skirt_02), at most two influences per vertex, so Unreal's AnimDynamics
(a Chain with Bound Bone tassel_root and Chain End skirt_02) or a Rigid Body node on the small physics
asset the build writes swings it.  SK_Fan carries no tassel geometry: leaving it off leaves nothing.

FRAME: the attach point (the back rivet head's hollow, SK_Fan's ``Tassel`` socket) is the origin; the
bind pose hangs straight down -Z.  Millimetres.

SHAPE (RS 8, L = 190 mm): a cord 0.010 L thick from the rivet to the knot's top at 0.19 L, a round
bead-like knot 0.047 x 0.046 L, a neck binding 0.017 L long and 0.025 L wide, then a round bundle of
threads 0.373 L long widening 0.029 -> 0.050 -> 0.063 -> 0.083 L with ragged tips over 0.015 L.  The
fullness (round, as wide as it is deep) is DESIGNED.

ROUND 2 (the blind test read round 1's tassel as a smooth cone with a perfect bead): the knot is a cord knot
(a ball with the cord's crossing turns raised on it, as fan2's knotted head), and the skirt is a bundle of
thread LOCKS (TASSEL_LOCKS per LOD: thin tubes from the neck to their own ragged ends, each with its own slight
wander and a splay at the tip) round a hidden core, so its outline and its shading are fibrous; the maps add
the single threads along each lock.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from .fan_spec import FAN, FanSpec
from .fan_geom import FanMesh
from .fan_paint import hash01

BONES = ("tassel_root", "cord_01", "cord_02", "knot", "skirt_01", "skirt_02")
#: per LOD: (locks, sides per lock, rings along a lock, core sides, core rings)
TASSEL_LOCKS = {0: (16, 3, 9, 10, 6), 1: (8, 3, 4, 8, 3), 2: (0, 3, 2, 6, 2)}
#: the knot's raised cord turns: (unit normal of the turn's plane, relative height) - DESIGNED from fan2's knotted
#: head (three crossing turns and a band round its waist)
KNOT_TURNS = (((1.0, 0.0, 0.35), 1.0), ((-0.5, 0.87, 0.35), 1.0), ((-0.5, -0.87, 0.35), 1.0), ((0.0, 0.0, 1.0), 0.8))
KNOT_TURN_HEIGHT_MM = 0.55
KNOT_TURN_WIDTH_MM = 1.3


def stations(spec: FanSpec = FAN) -> Dict[str, float]:
    L, t = spec.L, spec.tassel
    knot_top = -t.rivet_to_knot_L * L
    knot_bot = knot_top - t.knot_len_L * L
    neck_bot = knot_bot - t.neck_len_L * L
    tip = neck_bot - t.skirt_len_L * L
    return {"knot_top": knot_top, "knot_bot": knot_bot, "neck_bot": neck_bot, "tip": tip,
            "cord_r": 0.5 * t.cord_d_L * L, "knot_rx": 0.5 * t.knot_w_L * L, "knot_rz": 0.5 * t.knot_len_L * L,
            "neck_r": 0.5 * t.neck_w_L * L, "ragged": t.ragged_L * L}


def bone_table(spec: FanSpec = FAN) -> List[Tuple[str, Tuple[float, float, float], Tuple[float, float, float], str]]:
    st = stations(spec)
    z = [0.0, -4.0, 0.5 * st["knot_top"] - 2.0, st["knot_top"], st["neck_bot"],
         0.5 * (st["neck_bot"] + st["tip"]), st["tip"]]
    out = []
    for k, name in enumerate(BONES):
        out.append((name, (0.0, 0.0, z[k]), (0.0, 0.0, z[k + 1]), BONES[k - 1] if k else ""))
    return out


def _weights_along(zs: np.ndarray, spec: FanSpec) -> List[List[Tuple[str, float]]]:
    """Two-bone linear blends between neighbouring bone mid-points (the knot and neck rigid)."""
    bt = bone_table(spec)
    mids = [0.5 * (h[2] + t[2]) for _, h, t, _ in bt]
    out = []
    for z in zs:
        st = stations(spec)
        if st["neck_bot"] - 0.01 <= z <= st["knot_top"] + 0.01:
            out.append([("knot", 1.0)])
            continue
        # find neighbouring mids (mids are descending)
        k = 0
        while k < len(mids) - 1 and z < mids[k + 1]:
            k += 1
        if k >= len(mids) - 1:
            out.append([(BONES[-1], 1.0)])
            continue
        if z >= mids[0]:
            out.append([(BONES[0], 1.0)])
            continue
        a, b = mids[k], mids[k + 1]
        u = (a - z) / (a - b)
        pair = [(BONES[k], 1.0 - u), (BONES[k + 1], u)]
        pair = [(n, w) for n, w in pair if w > 1e-4]
        s = sum(w for _, w in pair)
        out.append([(n, w / s) for n, w in pair])
    return out


def skirt_radius(spec: FanSpec, d_below_top: float) -> float:
    prof = spec.tassel.skirt_width_L
    xs = [p[0] * spec.L for p in prof]
    ws = [p[1] * spec.L for p in prof]
    return 0.5 * float(np.interp(d_below_top, xs, ws))


def build_tassel(spec: FanSpec = FAN, lod: int = 0):
    """Returns (FanMesh with per-vertex weights in .W, info).  One material slot (0), paint kinds:
    0 cord, 1 knot, 2 neck, 3 skirt; per-corner local coords (around mm, along mm)."""
    seg_cord = (8, 6, 4)[lod]
    seg_skirt = (16, 10, 6)[lod]
    st = stations(spec)
    mb = FanMesh(list(BONES))
    verts_z: Dict[int, float] = {}

    def ring(zc, r, n, phase=0.0, zjit=None):
        pts = []
        for k in range(n):
            a = 2 * math.pi * (k + phase) / n
            zz = zc + (zjit[k] if zjit is not None else 0.0)
            pts.append(np.array([r * math.cos(a), r * math.sin(a), zz]))
        return pts

    def tube(zs, rs, n, kind, v0=0.0, jit_last=None):
        """rings top -> bottom; outward normals; local (around, along)."""
        rings = [ring(z, r, n, zjit=(jit_last if (jit_last is not None and i == len(zs) - 1) else None))
                 for i, (z, r) in enumerate(zip(zs, rs))]
        along = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(zs)))]) + v0
        for i in range(len(rings) - 1):
            for k in range(n):
                k1 = (k + 1) % n
                a, b = rings[i][k], rings[i][k1]
                c, d = rings[i + 1][k1], rings[i + 1][k]
                circ_i, circ_j = 2 * math.pi * rs[i], 2 * math.pi * rs[i + 1]
                la = (circ_i * k / n, along[i])
                lb = (circ_i * (k + 1) / n, along[i])
                lc = (circ_j * (k + 1) / n, along[i + 1])
                ld = (circ_j * k / n, along[i + 1])
                slope = (rs[i + 1] - rs[i]) / (zs[i + 1] - zs[i]) if abs(zs[i + 1] - zs[i]) > 1e-9 else 0.0

                def nrm(p, sl=slope):
                    r = math.hypot(p[0], p[1])
                    v = np.array([p[0] / r, p[1] / r, -sl])
                    return v / np.linalg.norm(v)
                na, nb, nc, nd = nrm(a), nrm(b), nrm(c), nrm(d)
                for tri, locs, ns in (((a, b, c), (la, lb, lc), (na, nb, nc)), ((a, c, d), (la, lc, ld), (na, nc, nd))):
                    mb.tri(list(tri), [(0, 0)] * 3, list(ns), "tassel_root", 0, "tassel", kind_name[kind],
                           locs=list(locs), kind=str(kind))
        return rings

    kind_name = {0: "cord", 1: "knot", 2: "neck", 3: "skirt"}
    # cord: from the attach point down to the knot's top (tucked 1 mm into the knot)
    cz = np.linspace(0.8, st["knot_top"] - 1.0, (6, 3, 2)[lod])
    tube(list(cz), [st["cord_r"]] * len(cz), seg_cord, 0)
    # cord top cap (inside the hollow rivet: a flat disc)
    top = ring(cz[0], st["cord_r"], seg_cord)
    cap_loc = lambda p: (p[0] + 10.0, p[1] - 6.0)          # the disc laid flat beside the cord's strip
    for k in range(1, seg_cord - 1):
        mb.tri([top[0], top[k + 1], top[k]], [(0, 0)] * 3, [np.array([0, 0, 1.0])] * 3, "tassel_root", 0, "tassel",
               "cordcap", locs=[cap_loc(top[0]), cap_loc(top[k + 1]), cap_loc(top[k])], kind="0")
    # knot: a slightly squashed ball with the cord's crossing turns raised on it (KNOT_TURNS)
    zc = 0.5 * (st["knot_top"] + st["knot_bot"])
    rx, rz = st["knot_rx"], st["knot_rz"]
    knot_lat, knot_lon = ((9, 14), (5, 8), (3, 6))[lod]
    turns = [(np.asarray(nv, np.float64) / np.linalg.norm(nv), h) for nv, h in KNOT_TURNS]

    def knot_pt(th, ph):
        d = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
        bump = 0.0
        if lod < 2:
            for nv, h in turns:
                x = float(d @ nv) * rx / KNOT_TURN_WIDTH_MM
                bump = max(bump, h * math.exp(-x * x))
        rr = 1.0 + (KNOT_TURN_HEIGHT_MM / rx) * (bump - 0.35)
        return np.array([rx * rr * d[0], rx * rr * d[1], zc + rz * rr * d[2]])

    def knot_n(th, ph):
        e = 1e-4
        a = knot_pt(th + e, ph) - knot_pt(th - e, ph)
        b = knot_pt(th, ph + e) - knot_pt(th, ph - e)
        n = np.cross(a, b)
        if np.linalg.norm(n) < 1e-12:
            n = knot_pt(th, ph) - np.array([0.0, 0.0, zc])
        n = n / np.linalg.norm(n)
        if n @ (knot_pt(th, ph) - np.array([0.0, 0.0, zc])) < 0:
            n = -n
        return n
    ths = [math.pi * i / knot_lat for i in range(knot_lat + 1)]
    phs = [2 * math.pi * k / knot_lon for k in range(knot_lon)]
    for i in range(knot_lat):
        for k in range(knot_lon):
            k1 = (k + 1) % knot_lon
            corners = [(i, k), (i, k1), (i + 1, k1), (i + 1, k)]
            P = [knot_pt(ths[a], phs[b]) for a, b in corners]
            N = [knot_n(max(ths[a], 1e-3) if a == 0 else (min(ths[a], math.pi - 1e-3)), phs[b]) for a, b in corners]
            lc = [(2 * math.pi * rx * (k + (0 if b == k else 1)) / knot_lon, math.pi * rz * a / knot_lat) for a, b in corners]
            tris = []
            if i == 0:
                tris = [(0, 2, 3)]
            elif i == knot_lat - 1:
                tris = [(0, 1, 2)]
            else:
                tris = [(0, 1, 2), (0, 2, 3)]
            for (x, y, z) in tris:
                mb.tri([P[x], P[y], P[z]], [(0, 0)] * 3, [N[x], N[y], N[z]], "tassel_root", 0, "tassel", "knot",
                       locs=[lc[x], lc[y], lc[z]], kind="1")
    # neck binding: a short band from inside the knot to the skirt's top
    nz = [st["knot_bot"] + 1.2, st["neck_bot"]]
    tube(nz, [st["neck_r"]] * 2, seg_skirt, 2)
    # skirt: a hidden core (so no daylight shows through the bundle) and the thread LOCKS round it
    n_locks, lock_sides, lock_rings, core_sides, core_rings = TASSEL_LOCKS[lod]
    d_tot = st["neck_bot"] - st["tip"]
    top_z = st["neck_bot"] + 0.6
    core_d = np.linspace(0.0, d_tot - 0.6 * st["ragged"], core_rings + 1)
    core_scale = 0.62 if n_locks else 1.0
    zs = [top_z - d for d in core_d]
    rs = [core_scale * skirt_radius(spec, d) for d in core_d]
    rs[0] = min(rs[0], st["neck_r"] * 0.98)
    core = tube(zs, rs, core_sides, 3)
    last = core[-1]
    tipc = np.array([0.0, 0.0, zs[-1] - (0.0 if n_locks else 0.4 * st["ragged"])])
    circ = 2 * math.pi * rs[-1]
    for k in range(core_sides):
        k1 = (k + 1) % core_sides
        mb.tri([last[k], last[k1], tipc], [(0, 0)] * 3, [np.array([0, 0, -1.0])] * 3, "tassel_root", 0, "tassel",
               "skirt", locs=[(circ * k / core_sides, core_d[-1]), (circ * (k + 1) / core_sides, core_d[-1]),
                              (circ * (k + 0.5) / core_sides, core_d[-1] + rs[-1])], kind="3")
    # the locks: two rings (inner 6, outer the rest) filling the measured width profile
    for li in range(n_locks):
        inner = li < n_locks // 3
        n_ring = n_locks // 3 if inner else n_locks - n_locks // 3
        k_ring = li if inner else li - n_locks // 3
        psi = 2 * math.pi * (k_ring + (0.5 if inner else 0.0) + 0.3 * (hash01(li, seed=91) - 0.5)) / n_ring
        rho = (0.36 if inner else 0.74) + 0.06 * (hash01(li, seed=92) - 0.5)
        # its own length: the ragged ends (RS 8, 0.015 L) and a little longer on the outside of the bundle
        end_d = d_tot - st["ragged"] * (hash01(li, seed=93) ** 0.8)
        ds = np.linspace(0.0, end_d, lock_rings + 1)
        wob_a = 0.35 * (hash01(li, seed=94) - 0.5)
        wob_f = 1.0 + hash01(li, seed=95)
        centres, radii = [], []
        for d in ds:
            u = d / d_tot
            R = skirt_radius(spec, d)
            if d < 1e-9:
                R = min(R, st["neck_r"] * 0.98)
            splay = 1.0 + 0.10 * max(0.0, (u - 0.82) / 0.18) ** 2          # the tips part a little at the end
            ang = psi + wob_a * math.sin(wob_f * math.pi * u) * u
            rr = rho * R * splay
            centres.append(np.array([rr * math.cos(ang), rr * math.sin(ang), top_z - d]))
            radii.append(max(0.25, (0.30 if inner else 0.36) * R * (1.0 - 0.45 * max(0.0, u - 0.9) / 0.1)))
        along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.array(centres), axis=0), axis=1))])
        rings = []
        for c, r, d in zip(centres, radii, ds):
            # the lock's cross-section in the plane across the bundle's axis, turned with its angle
            ring = []
            for q in range(lock_sides):
                a = 2 * math.pi * (q + 0.5 * (li % 2)) / lock_sides
                ring.append(c + np.array([r * math.cos(a), r * math.sin(a), 0.0]))
            rings.append(ring)
        for i in range(len(rings) - 1):
            for q in range(lock_sides):
                q1 = (q + 1) % lock_sides
                a, b = rings[i][q], rings[i][q1]
                c_, d_ = rings[i + 1][q1], rings[i + 1][q]
                circ_i, circ_j = 2 * math.pi * radii[i], 2 * math.pi * radii[i + 1]
                la = (circ_i * q / lock_sides, along[i])
                lb = (circ_i * (q + 1) / lock_sides, along[i])
                lc = (circ_j * (q + 1) / lock_sides, along[i + 1])
                ld = (circ_j * q / lock_sides, along[i + 1])
                ca, cb = centres[i], centres[i + 1]
                nn = lambda pnt, cc: (pnt - cc) / np.linalg.norm(pnt - cc)
                na, nb, nc, nd = nn(a, ca), nn(b, ca), nn(c_, cb), nn(d_, cb)
                for tri, locs, ns in (((a, b, c_), (la, lb, lc), (na, nb, nc)), ((a, c_, d_), (la, lc, ld), (na, nc, nd))):
                    mb.tri(list(tri), [(0, 0)] * 3, list(ns), "tassel_root", 0, "tassel", f"lock_{li:02d}",
                           locs=list(locs), kind="3")
        # the lock's cut end: a point a little beyond the last ring (the thread tips)
        end = rings[-1]
        tip = centres[-1] + np.array([0.0, 0.0, -0.6 * radii[-1]])
        circ = 2 * math.pi * radii[-1]
        for q in range(lock_sides):
            q1 = (q + 1) % lock_sides
            mb.tri([end[q], end[q1], tip], [(0, 0)] * 3, [np.array([0, 0, -1.0])] * 3, "tassel_root", 0, "tassel",
                   f"lock_{li:02d}", locs=[(circ * q / lock_sides, along[-1]), (circ * (q + 1) / lock_sides, along[-1]),
                                           (circ * (q + 0.5) / lock_sides, along[-1] + radii[-1])], kind="3")
    # weights: recompute per vertex from z (the factory assigned tassel_root/knot/skirt_02 as placeholders)
    P = np.asarray(mb.P)
    W = _weights_along(P[:, 2], spec)
    # knot vertices stay on the knot
    mb.W = W
    info = {"lod": lod, "triangles": mb.triangles(), "vertices": len(mb.P), "stations_mm": {k: round(v, 3) for k, v in st.items()},
            "rivet_to_tip_mm": round(-st["tip"], 3), "rivet_to_tip_L": round(-st["tip"] / spec.L, 4)}
    return mb, info


def tassel_uvs(mb: FanMesh, size: int = 1024, pad_px: int = 6):
    """Islands per strand part packed on shelves: cord, knot, neck, skirt, from the per-corner local
    coords (around mm, along mm).  Writes mb.TUV in place and returns px/mm."""
    groups: Dict[str, List[int]] = {}
    for t, g in enumerate(mb.TG):
        groups.setdefault(g, []).append(t)
    boxes = {}
    for g, ts in groups.items():
        L = np.concatenate([mb.TL[t] for t in ts])
        boxes[g] = (L.min(0), L.max(0))
    # shelf pack
    order = sorted(boxes, key=lambda g: -(boxes[g][1][1] - boxes[g][0][1]))
    lo, hi = 1.0, 60.0
    best = None
    for _ in range(40):
        s = 0.5 * (lo + hi)
        pad = pad_px / s
        W = size / s
        x = y = pad
        rh = 0.0
        pos = {}
        ok = True
        for g in order:
            w = boxes[g][1][0] - boxes[g][0][0]
            h = boxes[g][1][1] - boxes[g][0][1]
            if x + w + pad > W:
                x = pad
                y += rh + pad
                rh = 0.0
            if x + w + pad > W:
                ok = False
            pos[g] = (x, y)
            x += w + pad
            rh = max(rh, h)
        if ok and y + rh + pad <= W:
            lo, best = s, (s, pos)
        else:
            hi = s
    s, pos = best
    for t, g in enumerate(mb.TG):
        l0 = boxes[g][0]
        ox, oy = pos[g]
        uv = [((ox + p[0] - l0[0]) * s / size, 1.0 - (oy + p[1] - l0[1]) * s / size) for p in mb.TL[t]]
        mb.TUV[t] = np.asarray(uv)
    return s


__all__ = ["build_tassel", "bone_table", "tassel_uvs", "stations", "BONES"]
