"""Saya FIT VERIFICATION + MEASUREMENT on the EXPORTED FBX bytes of BOTH assets (adapted from the Snow Flower
shv4_verify.py, read-only; the draw is an arc about the exported DrawPivot instead of a straight slide).

    blender -b --factory-startup --python Scripts/Katana/saya_verify.py

The katana is placed by the saya's Holster socket AS SHIPPED (read back from SM_Katana_Saya.sockets.json: Unreal
location + rotator converted back to the Blender frame), never from the build's own numbers. For every pairing of saya
LOD j and katana LOD k (9 pairs):
    F1 intersections          no katana triangle intersects any saya triangle (BVH overlap), seated
    F2 blade clearance        min distance from every blade vertex inside the mouth to the saya surface   >= 0.3 mm
    F3 habaki clearance       min distance from every habaki vertex to the saya surface                    0.1 - 0.5 mm
    F4 hilt clearance         seppa / tsuba / tsuka (everything outside the mouth but the habaki)          >= 0.2 mm
    F5 enclosure              rays +-X, +-Y from blade vertices: first hit is a cavity wall facing them   0 failures
    F6 arc draw               the katana rotated about the EXPORTED DrawPivot in 10 mm arc steps (0.156 deg) until the
                              tip is 10 mm out of the mouth: 0 intersections at every step
F7 visible seat gap (front and edge-on silhouettes of the katana's Fittings slot over the koiguchi, every LOD) <= 2 mm,
F8 walls on the exported meshes, F9 sidecar sockets vs the spec, F10 katana sha256, F11 tip to cavity end,
F12 (info) a straight slide along the Mouth socket's -Z (expected to collide: a curved blade draws along its arc).
Also measures the exported saya against katana_spec.json -> WorkFiles/katana/saya_measured.json.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "Scripts"))
import saya_spec as S  # noqa: E402
import saya_fit as SF  # noqa: E402

SAYA_FBX = ROOT / "Exports" / "Katana" / f"{S.NAME}.fbx"
SAYA_SIDECAR = ROOT / "Exports" / "Katana" / f"{S.NAME}.sockets.json"
OUT_VERIFY = ROOT / "WorkFiles" / "katana" / "saya_fit_verify.json"
OUT_MEAS = ROOT / "WorkFiles" / "katana" / "saya_measured.json"


def log(*a):
    print("[SAYA-VERIFY]", *a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ue_socket_to_blender_matrix(rec):
    """Copied from shv4_verify: Unreal socket (cm, rotator) -> intended Blender placement 4x4 (mm)."""
    from pipeline.helpers import UE_MIRROR
    loc = rec["location_cm"]
    r = rec["rotation_deg"]
    roll, pitch, yaw = (math.radians(r[k]) for k in ("roll", "pitch", "yaw"))
    basis = (Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(-pitch, 3, "Y") @ Matrix.Rotation(roll, 3, "X"))
    rot = UE_MIRROR @ basis @ UE_MIRROR
    M = rot.to_4x4()
    M.translation = Vector((loc[0] * 10.0, -loc[1] * 10.0, loc[2] * 10.0))
    return M


def bvh(V, T):
    return BVHTree.FromPolygons([Vector(p) for p in V], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def xf(M, P):
    Mn = np.array(M)
    return (np.c_[P, np.ones(len(P))] @ Mn.T)[:, :3]


def to_sword(P_saya):
    P = np.array(P_saya, float)
    P[:, 2] += S.Z_OFF
    return P


def raster_max_z(P2, T, x0, x1, z0, z1, px=0.1):
    nu = int(round((x1 - x0) / px))
    nz = int(round((z1 - z0) / px))
    img = np.zeros((nz, nu), bool)
    us = x0 + (np.arange(nu) + 0.5) * px
    zs = z0 + (np.arange(nz) + 0.5) * px
    for tri in T:
        a, b, c = P2[tri]
        lo = np.minimum(np.minimum(a, b), c)
        hi = np.maximum(np.maximum(a, b), c)
        if hi[0] < x0 or lo[0] > x1 or hi[1] < z0 or lo[1] > z1:
            continue
        i0, i1 = max(int((lo[0] - x0) / px) - 1, 0), min(int((hi[0] - x0) / px) + 2, nu)
        j0, j1 = max(int((lo[1] - z0) / px) - 1, 0), min(int((hi[1] - z0) / px) + 2, nz)
        if i1 <= i0 or j1 <= j0:
            continue
        X, Z = np.meshgrid(us[i0:i1], zs[j0:j1])
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Z - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Z - c[1])) / d
        img[j0:j1, i0:i1] |= (l1 >= -1e-6) & (l2 >= -1e-6) & (1 - l1 - l2 >= -1e-6)
    out = np.full(nu, -np.inf)
    for i in range(nu):
        col = np.nonzero(img[:, i])[0]
        if len(col):
            out[i] = zs[col.max()]
    return us, out


def rotate_about(P, piv, theta):
    """Rotate points (saya frame) in the X-Z plane about the pivot so that their arc station s decreases by
    R * theta (the blade leaves the saya)."""
    u = piv[0] - P[:, 0]
    v = P[:, 2] - piv[2]
    c, s_ = math.cos(theta), math.sin(theta)
    u2 = u * c + v * s_
    v2 = -u * s_ + v * c
    out = P.copy()
    out[:, 0] = piv[0] - u2
    out[:, 2] = piv[2] + v2
    return out


def main():
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SAYA_FBX))
    saya = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.name.startswith("UCX_"):
            for lv in (0, 1, 2):
                if o.name.startswith(f"{S.NAME}_LOD{lv}"):
                    me = o.data
                    me.calc_loop_triangles()
                    V = xf(o.matrix_world, np.array([v.co[:] for v in me.vertices]) * 1.0) * 1000.0
                    T = np.array([lt.vertices[:] for lt in me.loop_triangles], int)
                    slots = [m.name.split(".")[0] if m else "" for m in me.materials]
                    tslot = np.array([slots[lt.material_index] for lt in me.loop_triangles])
                    saya[lv] = {"V": V, "T": T, "tslot": tslot, "name": o.name}
    ucx = [o for o in bpy.data.objects if o.name.startswith("UCX_")]
    side = json.loads(SAYA_SIDECAR.read_text(encoding="utf-8"))
    socks = {r["socket"]: r for r in side["sockets"]}
    M = ue_socket_to_blender_matrix(socks["Holster"])
    piv = np.array(ue_socket_to_blender_matrix(socks["DrawPivot"]).translation)
    mouth_M = ue_socket_to_blender_matrix(socks["Mouth"])
    mouth_z = float(mouth_M.translation.z)
    mouth_axis = np.array((mouth_M.to_3x3() @ Vector((0, 0, -1))).normalized())
    kat, _ = SF.load_katana(clear=False)
    res = {"source": "exported saya FBX + Holster/DrawPivot/Mouth from the exported sidecar; exported katana FBX",
           "saya_fbx_sha256": sha256(SAYA_FBX), "katana_fbx_sha256": sha256(S.KATANA_FBX),
           "F10_katana_bytes_equal_shipped": sha256(S.KATANA_FBX) == S.KATANA_FBX_SHA, "pairs": {}}
    # ---- F9 sockets vs spec
    spec_socks = S.sockets_saya_mm()
    f9 = {}
    for nm, loc in spec_socks.items():
        Mx = ue_socket_to_blender_matrix(socks[nm])
        d = float(np.abs(np.array(Mx.translation) - np.array(loc)).max())
        rot_err = float(np.abs(np.array(Mx.to_3x3()) - np.eye(3)).max())
        f9[nm] = {"exported_mm": [round(v, 4) for v in Mx.translation], "spec_mm": list(loc), "max_abs_err_mm": d,
                  "rotation_matrix_err": rot_err}
    res["F9_sockets"] = f9
    res["F9_pass"] = all(v["max_abs_err_mm"] <= 0.001 and v["rotation_matrix_err"] < 1e-6 for v in f9.values())
    # ---- katana arrays in the saya frame, classified
    W = {}
    for lv, d in kat.items():
        P = xf(M, d["V"])
        vs = SF.vertex_slots(d)
        s, rho, y = S.xyz_to_arc(to_sword(P))
        habaki = (vs == "M_Katana_Fittings") & (d["V"][:, 2] > 57.999) & (d["V"][:, 2] < 90.0)
        inside = s > S.S_MO
        blade = (vs == "M_Katana_Blade") & inside
        hilt = ~habaki & ~blade
        fit_T = d["T"][d["tslot"] == "M_Katana_Fittings"]
        W[lv] = {"P": P, "T": d["T"], "habaki": habaki, "blade": blade, "hilt": hilt, "fitT": fit_T}
    trees_s = {lv: bvh(saya[lv]["V"], saya[lv]["T"]) for lv in saya}
    ok = True
    thetas = np.arange(0.0, (S.K.S_TIP + 10.0) / S.R + 1e-12, 10.0 / S.R)
    for js in (0, 1, 2):
        ts = trees_s[js]
        for kw in (0, 1, 2):
            w = W[kw]
            P = w["P"]
            inter = len(ts.overlap(bvh(P, w["T"])))
            dist = lambda sel: [ts.find_nearest(Vector(p))[3] for p in P[sel]]
            db, dh, dt = dist(w["blade"]), dist(w["habaki"]), dist(w["hilt"])
            bad_enc = 0
            Bp = P[w["blade"]]
            for p in Bp[:: max(1, int(len(Bp) / 4000))]:
                for dv in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
                    hit = ts.ray_cast(Vector(p), Vector(dv), 200.0)
                    if hit[0] is None or hit[1].dot(Vector(dv)) >= 0.0:
                        bad_enc += 1
                        break
            # F6 arc draw about the exported DrawPivot
            worst, steps = 0, 0
            for th in thetas:
                n = len(ts.overlap(bvh(rotate_about(P, piv, th), w["T"])))
                worst = max(worst, n)
                steps += 1
            r = {"F1_intersections": inter, "F2_min_clearance_blade_mm": round(float(min(db)), 4),
                 "F3_min_clearance_habaki_mm": round(float(min(dh)), 4),
                 "F4_min_clearance_hilt_mm": round(float(min(dt)), 4), "blade_vertices": int(w["blade"].sum()),
                 "habaki_vertices": int(w["habaki"].sum()), "F5_enclosure_failures": bad_enc,
                 "F6_draw_steps": steps, "F6_draw_step_deg": round(math.degrees(10.0 / S.R), 4),
                 "F6_draw_max_intersections": worst}
            r["pass"] = bool(inter == 0 and r["F2_min_clearance_blade_mm"] >= 0.3
                             and 0.1 <= r["F3_min_clearance_habaki_mm"] <= 0.5
                             and r["F4_min_clearance_hilt_mm"] >= 0.2 and bad_enc == 0 and worst == 0)
            ok &= r["pass"]
            res["pairs"][f"saya_LOD{js}__katana_LOD{kw}"] = r
            log(js, kw, json.dumps(r), f"{time.time() - t0:.0f}s")
    # ---- F12 (info) straight slide along the Mouth socket -Z, LOD0 pair
    ts = trees_s[0]
    P = W[0]["P"]
    worst_s, first_hit = 0, None
    for d_ in np.arange(0.0, 720.0, 10.0):
        n = len(ts.overlap(bvh(P + mouth_axis[None, :] * d_, W[0]["T"])))
        if n and first_hit is None:
            first_hit = float(d_)
        worst_s = max(worst_s, n)
    res["F12_straight_draw_info"] = {"max_intersections": worst_s, "first_collision_after_mm": first_hit,
                                     "note": "expected to collide: the blade is a 17 mm-sori arc; the clean draw is the "
                                             "rotation about DrawPivot (F6), which starts tangent to the Mouth socket's -Z"}
    # ---- F7 visible seat gap: the katana's Fittings slot (seppa + habaki) over the koiguchi, front and edge-on
    res["F7_visible_seat_gap"] = {}
    D0, W0 = S.dims(S.S_MO)
    for kw in (0, 1, 2):
        w = W[kw]
        g = {}
        for view, k, h in (("front_x", 0, None), ("side_y", 1, W0 / 2)):
            if k == 0:
                x0, x1 = 15.5 - (S.RHO_MUNE + D0), 15.5 - S.RHO_MUNE
            else:
                x0, x1 = -h, h
            us, zmax = raster_max_z(w["P"][:, [k, 2]], w["fitT"], x0, x1, mouth_z - 40.0, mouth_z)
            gap = np.where(np.isfinite(zmax), np.maximum(mouth_z - zmax, 0.0), 40.0)
            g[view] = {"max_gap_mm": round(float(gap.max()), 3), "mean_gap_mm": round(float(gap.mean()), 3),
                       "columns": int(len(us)), "koiguchi_span_mm": [round(x0, 2), round(x1, 2)]}
        g["pass"] = bool(g["front_x"]["max_gap_mm"] <= 2.0 and g["side_y"]["max_gap_mm"] <= 2.0)
        ok &= g["pass"]
        res["F7_visible_seat_gap"][f"katana_LOD{kw}"] = g
        log("seat gap", kw, json.dumps(g))
    # ---- F8 walls on the exported meshes (cavity vertices to the analytic outer surface of their section)
    walls = {}
    th = np.linspace(0, 2 * math.pi, 1441)
    for js in (0, 1, 2):
        Vs = to_sword(saya[js]["V"])
        s, rho, y = S.xyz_to_arc(Vs)
        sc = np.clip(s, S.S_MO, S.S_EN)
        tt = (sc - S.S_MO) / (S.S_EN - S.S_MO)
        D = S.SY["depth_x"]["mouth"] + (S.SY["depth_x"]["kojiri_end"] - S.SY["depth_x"]["mouth"]) * tt
        Wd = S.SY["width_y"]["mouth"] + (S.SY["width_y"]["kojiri_end"] - S.SY["width_y"]["mouth"]) * tt
        rc = S.RHO_MUNE + D / 2
        rr = (np.abs((rho - rc) / (D / 2)) ** S.SE_N + np.abs(y / (Wd / 2)) ** S.SE_N) ** (1 / S.SE_N)
        # cavity vertices: well inside the outer section and within the cavity's |y| (the kurikata's sunk base is not)
        cav = (rr < 0.92) & (np.abs(y) < 7.5) & (s >= S.S_MO - 1e-3) & (s <= S.S_CAV_END + 1e-3)
        if js == 0:
            cav0 = cav.copy()
            s_cav0 = s
        best, at_s = np.inf, None
        best_vis, best_body = np.inf, np.inf
        for i in np.nonzero(cav)[0]:
            c, sn = np.cos(th), np.sin(th)
            ox = rc[i] + D[i] / 2 * np.sign(c) * np.abs(c) ** (2 / S.SE_N)
            oy = Wd[i] / 2 * np.sign(sn) * np.abs(sn) ** (2 / S.SE_N)
            d = float(np.min(np.hypot(ox - rho[i], oy - y[i])))
            if d < best:
                best, at_s = d, float(s[i])
            if s[i] <= S.S_POCKET_END + 0.01:
                best_vis = min(best_vis, d)
            else:
                best_body = min(best_body, d)
        walls[f"saya_LOD{js}"] = {"min_wall_mm": round(best, 3), "at_s": round(at_s, 2),
                                  "min_wall_koiguchi_pocket_mm": round(best_vis, 3),
                                  "min_wall_body_mm": round(best_body, 3), "cavity_vertices": int(cav.sum())}
    res["F8_walls"] = walls
    res["F8_pass"] = bool(walls["saya_LOD0"]["min_wall_koiguchi_pocket_mm"] >= 2.3
                          and walls["saya_LOD0"]["min_wall_body_mm"] >= 3.0
                          and all(v["min_wall_mm"] >= 1.5 for v in walls.values()))
    # mouth-face rim (the 0.4 mm outer round eats into the face): narrowest rim width at s_mouth
    V0 = to_sword(saya[0]["V"])
    s0, rho0, y0 = S.xyz_to_arc(V0)
    ring = np.abs(s0 - S.S_MO) < 1e-3
    pts = np.c_[rho0[ring], y0[ring]]
    rr0 = None
    if len(pts):
        D, Wd = S.dims(S.S_MO)
        rc = S.RHO_MUNE + D / 2
        r_ = (np.abs((pts[:, 0] - rc) / (D / 2)) ** S.SE_N + np.abs(pts[:, 1] / (Wd / 2)) ** S.SE_N) ** (1 / S.SE_N)
        inner, outer = pts[r_ < 0.9], pts[r_ >= 0.9]
        rr0 = float(min(np.min(np.hypot(*(outer - p).T)) for p in inner))
    res["mouth_face_rim_min_mm"] = round(rr0, 3) if rr0 is not None else None
    # ---- F11 tip to cavity end (LOD0 pair, along the arc) and cavity end vs spec
    tip_s = float(S.xyz_to_arc(to_sword(W[0]["P"][W[0]["blade"]]))[0].max())
    cav_end = float(s_cav0[cav0].max())
    res["F11_tip_to_cavity_end_mm"] = round(cav_end - tip_s, 3)
    res["F11_pass"] = res["F11_tip_to_cavity_end_mm"] >= 3.0
    res["hulls"] = sorted(o.name for o in ucx)
    res["pass"] = bool(ok and res["F9_pass"] and res["F10_katana_bytes_equal_shipped"] and res["F8_pass"]
                       and res["F11_pass"])
    res["gates"] = {"F1": "0 intersections, 9 pairs", "F2": ">= 0.3 mm", "F3": "0.1 - 0.5 mm", "F4": ">= 0.2 mm",
                    "F5": "0 failures", "F6": "0 intersections at every 10 mm arc step about the exported DrawPivot",
                    "F7": "front and edge-on max <= 2.0 mm", "F8": ">= 2.3 around the habaki pocket and >= 3.0 in the "
                    "body at LOD0, >= 1.5 everywhere at every LOD", "F9": "<= 0.001 mm", "F10": "sha256 equal",
                    "F11": ">= 3 mm (design 10)"}
    OUT_VERIFY.write_text(json.dumps(res, indent=1), encoding="utf-8")
    log("PASS" if res["pass"] else "FAIL", OUT_VERIFY, f"{time.time() - t0:.0f}s")
    measure(saya, res)


def measure(saya, ver):
    """Exported saya against the spec (sword frame, mm)."""
    V = to_sword(saya[0]["V"])
    s, rho, y = S.xyz_to_arc(V)
    out = {"fbx": str(SAYA_FBX), "fbx_sha256": sha256(SAYA_FBX)}
    out["mouth_s"] = round(float(s.min()), 4)
    out["end_s"] = round(float(s.max()), 4)
    out["length_on_mune_arc"] = round(float(s.max() - s.min()), 3)
    out["spec_length_on_mune_arc"] = S.SY["length_on_blade_mune_arc"]

    def section(sv, tol=0.02):
        sel = np.abs(s - sv) < tol
        D, Wd = S.dims(sv)
        rc = S.RHO_MUNE + D / 2
        rr = (np.abs((rho - rc) / (D / 2)) ** S.SE_N + np.abs(y / (Wd / 2)) ** S.SE_N) ** (1 / S.SE_N)
        sel &= rr > 0.95
        return float(rho[sel].max() - rho[sel].min()), float(y[sel].max() - y[sel].min()), float(rho[sel].min())
    s_after_round = S.S_MO + S.MOUTH_ROUND
    d0, w0, m0 = section(s_after_round)
    d1, w1, m1 = section(S.S_EN - S.KOJIRI_ROUND)
    out["mouth_depth_x_width"] = [round(d0, 3), round(w0, 3)]
    out["spec_mouth_depth_x_width_at_s"] = [round(v, 3) for v in S.dims(s_after_round)]
    out["kojiri_depth_x_width_at_round_start"] = [round(d1, 3), round(w1, 3)]
    out["spec_kojiri_depth_x_width_at_round_start"] = [round(v, 3) for v in S.dims(S.S_EN - S.KOJIRI_ROUND)]
    out["spec_end_depth_x_width"] = [S.SY["depth_x"]["kojiri_end"], S.SY["width_y"]["kojiri_end"]]
    out["mune_line_rho"] = round(m0, 4)
    out["spec_mune_line_rho"] = S.RHO_MUNE
    # seams (groove rings: 0.2 mm inside the outer surface)
    D, Wd = np.vectorize(lambda v: S.dims(min(max(v, S.S_MO), S.S_EN))[0])(s), np.vectorize(lambda v: S.dims(min(max(v, S.S_MO), S.S_EN))[1])(s)
    rc = S.RHO_MUNE + D / 2
    rr = (np.abs((rho - rc) / (D / 2)) ** S.SE_N + np.abs(y / (Wd / 2)) ** S.SE_N) ** (1 / S.SE_N)
    gr = (rr > 0.97) & (rr < 0.995)
    g1 = s[gr & (s > 5) & (s < 40)]
    g2 = s[gr & (s > 650) & (s < 700)]
    out["koiguchi_seam_groove_s"] = [round(float(g1.min()), 3), round(float(g1.max()), 3)] if len(g1) else None
    out["kojiri_seam_groove_s"] = [round(float(g2.min()), 3), round(float(g2.max()), 3)] if len(g2) else None
    out["koiguchi_length"] = round(float(g1.mean() - s.min()), 3) if len(g1) else None
    out["kojiri_length"] = round(float(s.max() - g2.mean()), 3) if len(g2) else None
    out["spec_koiguchi_kojiri"] = [20.0, 28.0]
    # kurikata: vertices standing proud of the omote face
    proud = (y < 0) & (np.abs(y) > Wd / 2 + 0.3) & (s > 40) & (s < 130)
    if proud.any():
        ks, kr, ky = s[proud], rho[proud], y[proud]
        out["kurikata"] = {"centre_s": round(float((ks.max() + ks.min()) / 2), 3),
                           "from_mouth": round(float((ks.max() + ks.min()) / 2 - s.min()), 3),
                           "along": round(float(ks.max() - ks.min()), 3), "radial": round(float(kr.max() - kr.min()), 3),
                           "proud_of_face": round(float((np.abs(ky) - S.dims(80.3)[1] / 2).max()), 3),
                           "radial_centre_offset_from_section_centre": round(float((kr.max() + kr.min()) / 2 - (S.RHO_MUNE + S.dims(80.3)[0] / 2)), 3),
                           "spec": {"from_mouth": 80.0, "along": 30.0, "radial": 11.0, "proud": 9.0, "offset": 3.0}}
    out["seat_gap_from_fit_verify"] = ver["F7_visible_seat_gap"]
    out["tip_to_cavity_end_mm"] = ver["F11_tip_to_cavity_end_mm"]
    out["walls"] = ver["F8_walls"]
    out["lod_triangles"] = [int(len(saya[k]["T"])) for k in (0, 1, 2)]
    OUT_MEAS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    log("SAYA_MEASURE", json.dumps(out)[:1800])


main()
