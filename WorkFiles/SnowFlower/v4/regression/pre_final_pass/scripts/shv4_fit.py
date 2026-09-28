"""Snow Flower sheath - FIT stage: seat the SHIPPED v4 sword (the exact exported FBX bytes, read-only) in the reference
sheath outline and derive the inner cavity from it.

    blender -b --factory-startup --python build_sheath.py -- --stage fit

Placement (sheath frame, mm):  p_S = R_y(phi) @ p_W + t,  t = (t_x, 0, t_z)
    t_z   : the lowest hilt vertex sits GUARD_GAP above the mouth plane (z = Z_MOUTH)
    phi   : a small seat tilt about Y.  The v4 blade is a dao: its spine sweeps 9.4 mm toward +X at the tip while the
            reference body tapers 26 % symmetrically, so a coaxial straight sheath of the reference outline cannot hold
            it (margin -3.3 mm, see SHEATH_REPORT).  Tilting the sword ~0.6 deg in the holster moves the tip toward
            the sheath axis and fits it without changing the reference outline.  The Holster socket carries the tilt.
    t_x   : lateral offset; chosen to centre the guard on the sheath axis when the margin allows.
Cavity: the blade (vertices of ALL THREE sword LODs below the mouth) SWEPT along its own axis out of the mouth - so a
straight draw is clean by construction - plus CLEARANCE, as a support polygon per station (window-conservative).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import shv4_spec as S

OUT = S.ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build" / "fit"


def log(*a):
    print("[SH4-FIT]", *a, flush=True)


# ---------------------------------------------------------------------------------------------- sword vertices

def load_sword_vertices():
    """Import the shipped sword FBX into an empty scene; return {lod: (N,3) mm in the sword frame}."""
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(S.SWORD_FBX))
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith("UCX_"):
            continue
        for lv in (0, 1, 2):
            if o.name.startswith(f"SM_SnowFlower_LOD{lv}"):
                M = np.array(o.matrix_world)
                V = np.array([v.co[:] for v in o.data.vertices])
                V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0
                out[lv] = V
    rep = json.loads(S.SWORD_REPORT.read_text(encoding="utf-8"))
    bb0, bb1 = out[0].min(axis=0), out[0].max(axis=0)
    err = max(np.abs(bb0 - np.array(rep["bbox_min_mm"])).max(), np.abs(bb1 - np.array(rep["bbox_max_mm"])).max())
    if err > 0.05:
        raise RuntimeError(f"sword FBX re-import bbox differs from sword_report.json by {err:.3f} mm")
    log("sword LOD vertices", {k: len(v) for k, v in out.items()}, "bbox check", round(float(err), 4), "mm")
    return out, rep


# ---------------------------------------------------------------------------------------------- geometry helpers

def rot_y(phi):
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def outer_half_at(z):
    """Outer half-width (mm) of the lacquer core, or of the chape where the chape carries the cavity."""
    row = S.row_of(z)
    if row >= S.CHAPE_POCKET_END_ROW:
        return S.chape_half(row)
    return float(S.core_w(row)) / 2


def outer_poly_at(z):
    row = float(S.row_of(z))
    if row >= S.CHAPE_POCKET_END_ROW:
        return S.core_section(2 * S.chape_half(row), S.chape_depth(row))
    return S.core_section(float(S.core_w(row)), float(S.body_d(row)))


def suffix_extremes(zs, vals, zq):
    """For query heights zq: max over points with z >= zq of vals (points sorted by z)."""
    order = np.argsort(zs)
    z_sorted = zs[order]
    v_sorted = vals[order]
    suf = np.maximum.accumulate(v_sorted[::-1], axis=0)[::-1]
    idx = np.searchsorted(z_sorted, zq, side="left")
    out = np.full((len(zq),) + vals.shape[1:], -np.inf)
    ok = idx < len(z_sorted)
    out[ok] = suf[idx[ok]]
    return out


def swept_support(P, dirs, zq, s_xy, swept=True):
    """Support h(n) of the blade point set at heights zq: static = points in a thin slab; swept = every point at or
    below (deeper than) zq, moved up the sword axis to zq.  P (N,3) sheath frame, dirs (M,2), s_xy = axis x,y per z."""
    proj = P[:, :2] @ dirs.T                               # (N, M)
    ns = dirs @ s_xy                                       # (M,)
    if swept:
        vals = proj - P[:, 2:3] * ns[None, :]
        return zq[:, None] * ns[None, :] + suffix_extremes(P[:, 2], vals, zq)
    raise NotImplementedError


def placement(phi, t_x, hilt, blade_all):
    R = rot_y(phi)
    zh = (hilt @ R.T)[:, 2]
    t_z = S.Z_MOUTH - S.GUARD_GAP - zh.max()
    t = np.array([t_x, 0.0, t_z])
    B = blade_all @ R.T + t
    return R, t, B[B[:, 2] > S.Z_MOUTH]


def lateral_margin(phi, t_x, hilt, blade_all, zq=None):
    R, t, B = placement(phi, t_x, hilt, blade_all)
    if zq is None:
        zq = np.arange(S.Z_MOUTH, B[:, 2].max(), 2.0)
    s_xy = np.array([math.tan(phi), 0.0])
    dirs = np.array([[1.0, 0.0], [-1.0, 0.0]])
    h = swept_support(B, dirs, zq, s_xy)
    hi, lo = h[:, 0], -h[:, 1]
    oh = np.array([outer_half_at(z) for z in zq])
    m = np.minimum(oh - (hi + S.CLEARANCE), oh + (lo - S.CLEARANCE)) - S.MIN_WALL
    i = int(np.argmin(m))
    return float(m[i]), float(zq[i]), R, t, B


# ---------------------------------------------------------------------------------------------- cavity polygons

def _clip(poly, n, h):
    out = []
    m = len(poly)
    for k in range(m):
        P, Q = poly[k], poly[(k + 1) % m]
        dp, dq = P @ n - h, Q @ n - h
        if dp <= 0:
            out.append(P)
        if (dp < 0) != (dq < 0) and dp != dq:
            out.append(P + (Q - P) * (dp / (dp - dq)))
    return np.array(out)


def support_polygon(h, dirs, sup, min_edge=0.15):
    """Vertices of the polygon {x : n_i . x <= h_i} with exactly one vertex between every pair of consecutive
    directions (so all stations loft with the same topology).  Lines are first tightened to the exact polygon; a line
    that only touches a corner is then shaved in 0.02 mm steps until its edge is at least ``min_edge`` long (a
    degenerate edge would fail qa).  Returns (vertices, min over directions of h_final - support) = the design
    clearance left after shaving."""
    M = len(dirs)
    h = np.asarray(h, float).copy()

    def X(i, j):
        return np.linalg.solve(np.array([dirs[i], dirs[j]]), np.array([h[i], h[j]]))

    for _ in range(600):
        poly = np.array([[-1e4, -1e4], [1e4, -1e4], [1e4, 1e4], [-1e4, 1e4]], float)
        for i in range(M):
            poly = _clip(poly, dirs[i], h[i])
        h = np.array([float((poly @ dirs[i]).max()) for i in range(M)])
        V = np.array([X(i, (i + 1) % M) for i in range(M)])
        bad = []
        for i in range(M):
            t = np.array([-dirs[i][1], dirs[i][0]])
            if float((V[i] - V[i - 1]) @ t) < min_edge:
                bad.append(i)
        if not bad:
            return V, float(np.min(h - sup))
        for i in bad:
            h[i] -= 0.02
    raise RuntimeError("support polygon did not converge")


def cavity_polygons(B, phi, level, z_end):
    """Stations and M-gon sections (sheath frame) of the cavity at a given LOD."""
    M = S.CAVITY_DIRS[level]
    ang = 2 * math.pi * (np.arange(M) + 0.5) / M
    dirs = np.stack([np.cos(ang), np.sin(ang)], 1)
    s_xy = np.array([math.tan(phi), 0.0])
    z0 = S.Z_MOUTH
    step = S.CAVITY_STEP[level]
    n = max(2, int(math.ceil((z_end - z0) / step)))
    stations = np.linspace(z0, z_end, n + 1)
    zq = np.arange(z0, z_end + 1.0, 0.5)
    zq[-1] = min(zq[-1], z_end)
    H = swept_support(B, dirs, zq, s_xy)                     # (Q, M)
    fin = np.isfinite(H).all(axis=1)
    last = int(np.nonzero(fin)[0].max())
    H[last + 1:] = H[last]                                   # past the tip: keep the tip section (cavity end cap)
    # knot values: start at the exact support, then lift both ends of any segment whose chord dips under the dense
    # support (the loft interpolates the support lines linearly between stations, so the chord must dominate)
    V = np.array([H[np.argmin(np.abs(zq - zs))] for zs in stations])
    for _ in range(3):
        for k in range(n):
            sel = (zq >= stations[k] - 1e-6) & (zq <= stations[k + 1] + 1e-6)
            tt = ((zq[sel] - stations[k]) / (stations[k + 1] - stations[k]))[:, None]
            chord = (1 - tt) * V[k] + tt * V[k + 1]
            viol = np.maximum((H[sel] - chord).max(axis=0), 0.0)
            V[k] += viol
            V[k + 1] += viol
    polys, cuts = [], []
    for k, zs in enumerate(stations):
        sup = V[k]
        Vx, clr = support_polygon(sup + S.CLEARANCE, dirs, sup)
        polys.append(Vx)
        cuts.append(clr)
    return stations, np.array(polys), float(min(cuts)), dirs


def poly_min_wall(inner, outer):
    """Min distance from the inner convex polygon's vertices to the outer convex polygon's edges (positive inside)."""
    O = np.asarray(outer)
    n = len(O)
    best = np.inf
    for p in inner:
        d_in = np.inf
        for i in range(n):
            a, b = O[i], O[(i + 1) % n]
            e = b - a
            nrm = np.array([-e[1], e[0]]) / np.linalg.norm(e)
            # outward normal: the ring runs +X side -> front(-Y) -> -X side, i.e. clockwise seen from +Z
            d = float((a - p) @ nrm)
            d_in = min(d_in, d)
        best = min(best, d_in)
    return best


# ---------------------------------------------------------------------------------------------- stage

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    verts, rep = load_sword_vertices()
    allv = np.vstack([verts[0], verts[1], verts[2]])
    hilt = allv[allv[:, 2] <= 128.6]
    blade_all = allv[allv[:, 2] > 90.0]
    # ---- search the tilt and lateral offset
    table = []
    for phi_deg in np.arange(-1.2, 0.001, 0.05):
        phi = math.radians(phi_deg)
        best = None
        for tx in np.arange(-6.0, 6.001, 0.25):
            m, zl, R, t, B = lateral_margin(phi, tx, hilt, blade_all)
            hilt_off = float((R @ np.array([0.0, 0.0, 128.9]) + t)[0])
            row = (m, tx, zl, hilt_off)
            if best is None or m > best[0] + 1e-9:
                best = row
            table.append({"phi_deg": round(float(phi_deg), 3), "t_x": float(tx), "margin": round(m, 3),
                          "limit_z": round(zl, 1), "hilt_offset_at_mouth": round(hilt_off, 2)})
        log(f"phi {phi_deg:.2f} deg: best margin {best[0]:+.2f} mm (t_x {best[1]:+.2f}, limit z {best[2]:.0f})")
    # rule: the smallest tilt that leaves >= 0.25 mm beyond MIN_WALL + CLEARANCE; within it the most centred guard
    GOAL = 0.25
    ok = [r for r in table if r["margin"] >= GOAL]
    if ok:
        phi_sel = max(r["phi_deg"] for r in ok)          # the smallest |tilt| (tilts are negative)
        cand = [r for r in ok if r["phi_deg"] == phi_sel]
        # take the tilt one step above the minimum when that buys a centred guard (<= 1 mm)
        for step in (0.0, -0.05, -0.1):
            c2 = [r for r in ok if abs(r["phi_deg"] - (phi_sel + step)) < 1e-6 and abs(r["hilt_offset_at_mouth"]) <= 1.0]
            if c2:
                cand = c2
                break
        pick = min(cand, key=lambda r: (abs(r["hilt_offset_at_mouth"]), -r["margin"]))
    else:
        pick = max(table, key=lambda r: r["margin"])
    phi = math.radians(pick["phi_deg"])
    # refine t_x finely around the pick
    best = None
    for tx in np.arange(pick["t_x"] - 0.25, pick["t_x"] + 0.2501, 0.05):
        m, zl, R, t, B = lateral_margin(phi, tx, hilt, blade_all)
        hilt_off = float((R @ np.array([0.0, 0.0, 128.9]) + t)[0])
        key = (m >= GOAL, -abs(hilt_off) if m >= GOAL else m)
        if best is None or key > best[0]:
            best = (key, tx, m, zl, hilt_off)
    _, tx, m, zl, hilt_off = best
    m, zl, R, t, B = lateral_margin(phi, tx, hilt, blade_all)
    log(f"PICK phi {math.degrees(phi):.3f} deg, t = {t.round(3).tolist()}, lateral margin {m:+.3f} mm at z {zl:.0f}, "
        f"hilt offset at the mouth {hilt_off:+.2f} mm")
    # ---- guard / hilt clearance to the mouth plane (all LODs)
    Hs = hilt @ R.T + t
    guard_gap = float(S.Z_MOUTH - Hs[:, 2].max())
    z_tip = float(B[:, 2].max())
    z_end = z_tip + S.CLEARANCE
    # ---- cavity per LOD + walls against the outer polygons
    cav = {}
    walls = {}
    for lv in (0, 1, 2):
        st, polys, clr_min, dirs = cavity_polygons(B, phi, lv, z_end)
        w = []
        for zs, P in zip(st, polys):
            w.append(poly_min_wall(P, outer_poly_at(zs)))
        cav[lv] = (st, polys)
        walls[lv] = {"min_wall_mm": round(float(min(w)), 3), "at_z": round(float(st[int(np.argmin(w))]), 1),
                     "min_design_clearance_mm": round(clr_min, 3), "stations": len(st), "sides": polys.shape[1]}
        np.savez(OUT / f"cavity_L{lv}.npz", stations=st, polys=polys)
        log(f"cavity L{lv}: {len(st)} stations x {polys.shape[1]} sides, min wall {min(w):.2f} mm "
            f"at z {st[int(np.argmin(w))]:.0f}, design clearance >= {clr_min:.3f}")
    # ---- static (sheathed pose) extents for the report / section view
    zq = np.arange(S.Z_MOUTH, z_tip, 2.0)
    stat = []
    for z in zq:
        sl = B[(B[:, 2] >= z - 1.0) & (B[:, 2] < z + 1.0)]
        if len(sl):
            stat.append([float(z), float(sl[:, 0].min()), float(sl[:, 0].max()), float(np.abs(sl[:, 1]).max())])
    # ---- sockets (sheath frame, mm)
    mouth_w = (S.Z_MOUTH - t[2]) / math.cos(phi)
    mouth_pt = R @ np.array([0.0, 0.0, mouth_w]) + t
    sockets = {
        "Holster": {"location_mm": t.round(4).tolist(), "rotation_euler_rad": [0.0, phi, 0.0],
                    "note": "the sword's pivot (its Grip socket) when sheathed; attach the sword here with zero relative "
                            "transform"},
        "Mouth": {"location_mm": mouth_pt.round(4).tolist(), "rotation_euler_rad": [0.0, phi, 0.0],
                  "note": "the sword axis at the mouth plane; DRAW AXIS = this socket's -Z (the blade slides out along "
                          "it; the swept cavity keeps a straight draw clean)"},
    }
    fit = {"phi_deg": math.degrees(phi), "t_mm": t.tolist(), "R": R.tolist(),
           "matrix_S_from_W": np.block([[R, t[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]).tolist(),
           "lateral_margin_beyond_wall_and_clearance_mm": m, "limit_z": zl, "hilt_offset_at_mouth_mm": hilt_off,
           "guard_gap_mm": guard_gap, "z_tip": z_tip, "z_cavity_end": z_end, "tip_row": float(S.row_of(z_tip)),
           "clearance_mm": S.CLEARANCE, "min_wall_goal_mm": S.MIN_WALL, "cavity": walls, "sockets": sockets,
           "sword_fbx_sha256": __import__("hashlib").sha256(S.SWORD_FBX.read_bytes()).hexdigest(),
           "search_table": table, "static_extents": stat,
           "no_tilt_best": max((r for r in table if r["phi_deg"] == 0.0), key=lambda r: r["margin"])}
    (OUT / "fit.json").write_text(json.dumps(fit, indent=1), encoding="utf-8")
    log("fit saved", OUT / "fit.json", f"tip z {z_tip:.1f} (ref row {S.row_of(z_tip):.0f}), guard gap {guard_gap:.3f}")
    return fit
