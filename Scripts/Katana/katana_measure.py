"""Measure the EXPORTED katana (re-import of Exports/Katana/SM_Katana.fbx) against katana_spec.json, and write the saya
interface (the envelope the saya must fit), both from the shipped bytes.

    blender -b --factory-startup --python Scripts/Katana/katana_measure.py

Writes WorkFiles/katana/katana_measured.json and WorkFiles/katana/katana_interface.json.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import katana_spec as K  # noqa: E402

ROOT = HERE.parents[1]
FBX = ROOT / "Exports" / "Katana" / "SM_Katana.fbx"
SIDECAR = ROOT / "Exports" / "Katana" / "SM_Katana.sockets.json"
OUTM = ROOT / "WorkFiles" / "katana" / "katana_measured.json"
OUTI = ROOT / "WorkFiles" / "katana" / "katana_interface.json"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    out = {}
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.name.startswith("UCX_"):
            continue
        me = o.data
        M = o.matrix_world
        V = np.array([(M @ v.co)[:] for v in me.vertices]) * 1000.0
        mi = np.zeros(len(me.polygons), int)
        me.polygons.foreach_get("material_index", mi)
        slots = [m.name.split(".")[0] if m else "" for m in me.materials]
        tris = []
        tmat = []
        for p in me.polygons:
            vs = list(p.vertices)
            for k in range(1, len(vs) - 1):
                tris.append((vs[0], vs[k], vs[k + 1]))
                tmat.append(slots[p.material_index])
        lv = 0 if "LOD0" in o.name else (1 if "LOD1" in o.name else 2)
        out[lv] = {"V": V, "T": np.array(tris), "tmat": np.array(tmat), "name": o.name}
    hulls = [o for o in bpy.context.scene.objects if o.name.startswith("UCX_")]
    return out, hulls


def verts_of(d, slot):
    sel = np.unique(d["T"][d["tmat"] == slot].ravel())
    return d["V"][sel]


def blade_su(P):
    a = np.arctan2(P[:, 2] - K.CZ, K.CX - P[:, 0])
    s = a * K.R
    u = np.hypot(P[:, 0] - K.CX, P[:, 2] - K.CZ) - K.R
    return s, u


def fit_circle(x, z):
    A = np.c_[x, z, np.ones(len(x))]
    b = -(x * x + z * z)
    c = np.linalg.lstsq(A, b, rcond=None)[0]
    cx, cz = -c[0] / 2, -c[1] / 2
    r = math.sqrt(cx * cx + cz * cz - c[2])
    return cx, cz, r


def main():
    lods, hulls = load()
    d0 = lods[0]
    res = {"fbx": str(FBX), "fbx_sha256": sha256(FBX), "sidecar_sha256": sha256(SIDECAR)}
    Bl = verts_of(d0, "M_Katana_Blade")
    blade = Bl[Bl[:, 2] > 57.9]
    s, u = blade_su(blade)
    # mune line = vertices on the mid plane at the arc (u ~ 0)
    mune = blade[(np.abs(blade[:, 1]) < 1e-3) & (np.abs(u) < 0.05)]
    cxf, czf, rf = fit_circle(mune[:, 0], mune[:, 2])
    tip = blade[np.argmax(s)]
    mm = blade[(np.abs(s) < 0.05) & (np.abs(u) < 0.05)][0]
    chord = tip - mm
    nag = float(np.linalg.norm(chord[[0, 2]]))
    cn = chord[[0, 2]] / nag
    rel = mune[:, [0, 2]] - mm[[0, 2]]
    sori = float(np.abs(rel[:, 0] * cn[1] - rel[:, 1] * cn[0]).max())

    def ring(st, tol=0.05):
        sel = np.abs(s - st) < tol
        return blade[sel], u[sel]
    r0, u0 = ring(0.0)
    ry, uy = ring(K.S_Y)
    # yokote from the geometry: the station where the thickness taper breaks
    st_all = np.unique(np.round(s, 3))
    st_all = st_all[(st_all > 300.0) & (st_all < s.max() - 12.0)]
    kk = []
    for st in st_all:
        sel = np.abs(s - st) < 0.01
        kk.append((st, blade[sel][:, 1].max() - blade[sel][:, 1].min()))
    kk = np.array(kk)
    slope = np.diff(kk[:, 1]) / np.diff(kk[:, 0])
    brk = int(np.argmax(np.abs(np.diff(slope)))) + 1
    s_yok = float(kk[brk, 0])
    res["blade"] = {
        "mune_arc_fit": {"centre_xz": [round(cxf, 2), round(czf, 2)], "radius": round(rf, 2),
                         "spec": {"centre_xz": [K.CX, K.CZ], "radius": K.R}},
        "tip_xz": [round(float(tip[0]), 3), round(float(tip[2]), 3)], "spec_tip_xz": K.B["tip_xz"],
        "mune_machi_xz": [round(float(mm[0]), 3), round(float(mm[2]), 3)],
        "nagasa_chord": round(nag, 3), "spec_nagasa": K.B["nagasa_chord"],
        "sori": round(sori, 3), "spec_sori": K.B["sori"],
        "motohaba": round(float(u0.max() - u0.min()), 3), "spec_motohaba": K.B["motohaba"],
        "sakihaba_at_yokote": round(float(uy.max() - uy.min()), 3), "spec_sakihaba": K.B["sakihaba_at_yokote"],
        "motokasane": round(float(r0[:, 1].max() - r0[:, 1].min()), 3), "spec_motokasane": K.B["motokasane"],
        "sakikasane": round(float(ry[:, 1].max() - ry[:, 1].min()), 3), "spec_sakikasane": K.B["sakikasane_at_yokote"],
        "yokote_station_measured": round(s_yok, 3), "spec_yokote_station": K.S_Y,
        "kissaki_on_mune_arc": round(float(s.max() - s_yok), 3), "spec_kissaki": K.B["kissaki"]["length_on_mune_arc"],
        "shinogi_ratio_at_machi": None,
    }
    # shinogi position at the machi: the vertex with |y| = k/2 on the omote
    om = r0[r0[:, 1] < -1e-3]
    if len(om):
        sj_v = om[np.argmin(om[:, 1])]
        res["blade"]["shinogi_ratio_at_machi"] = round(float(blade_su(sj_v[None])[1][0] / (u0.max() - u0.min())), 4)
    Fi = verts_of(d0, "M_Katana_Fittings")
    hab = Fi[(Fi[:, 2] >= 57.999) & (np.abs(Fi[:, 1]) <= 6.01) & (np.abs(Fi[:, 0]) <= 17.51)]
    res["habaki"] = {"z": [round(float(hab[:, 2].min()), 3), round(float(hab[:, 2].max()), 3)],
                     "length": round(float(hab[:, 2].max() - hab[:, 2].min()), 3), "spec_length": K.SP["habaki"]["length"],
                     "x": [round(float(hab[:, 0].min()), 3), round(float(hab[:, 0].max()), 3)],
                     "y_half": round(float(np.abs(hab[:, 1]).max()), 3)}
    ts = Bl[(Bl[:, 2] > 51.0) & (Bl[:, 2] < 57.0)]
    res["tsuba"] = {"diameter": round(float(2 * np.hypot(ts[:, 0], ts[:, 1]).max()), 3), "spec": K.SP["tsuba"]["diameter"],
                    "z": [round(float(ts[:, 2].min()), 3), round(float(ts[:, 2].max()), 3)]}
    fu = Bl[(Bl[:, 2] > 36.5) & (Bl[:, 2] < 50.5)]
    allV = d0["V"]
    zmin = float(allV[:, 2].min())
    zk = float(Bl[:, 2].min())          # the iron kashira's end crown (finaliser: no ito band over it any more)
    res["tsuka"] = {"fuchi_top_z": round(float(fu[:, 2].max()), 3), "kashira_end_z": round(zk, 3),
                    "length": round(float(fu[:, 2].max() - zk), 3), "spec": K.SP["tsuka"]["length_fuchi_top_to_kashira_end"],
                    "ito_band_over_end_z": round(zmin, 3)}
    res["overall"] = {"along_z_tip_to_kashira": round(float(allV[:, 2].max() - zk), 3), "spec": K.SP["overall"]["length_along_Z"],
                      "along_z_incl_band": round(float(allV[:, 2].max() - zmin), 3)}
    # ---------------------------------------------------------------- ito
    G = d0["T"][d0["tmat"] == "M_Katana_Grip"]
    V = d0["V"]
    cen = V[G].mean(axis=1)

    def above_core(P):
        out = np.zeros(len(P))
        for i, p in enumerate(P):
            cx, a, b = K.core_axes(p[2])
            al = math.atan2(p[1], p[0] - cx)
            x, y, nx, ny = K.se_radial(a, b, K.NT, al)
            out[i] = math.hypot(p[0] - cx, p[1]) - math.hypot(x, y)
        return out
    h_c = above_core(cen)
    in_tsuka = (cen[:, 2] < 37.0) & (cen[:, 2] > -204.0)
    cords = G[(h_c > 0.25) & in_tsuka & ~((np.abs(cen[:, 2] - K.SP["mekugi"]["z"]) < 4) & (np.abs(cen[:, 0]) < 4))]
    cv = V[np.unique(cords.ravel())]
    peaks = {}
    for face, sg in (("omote", -1), ("ura", 1)):
        zs = np.arange(-203.0, 36.0, 0.25)
        prof = np.full(len(zs), np.nan)
        sel = cv[(np.sign(cv[:, 1]) == sg)]
        for i, z in enumerate(zs):
            cx = K.core_axes(z)[0]
            m = sel[(np.abs(sel[:, 2] - z) < 0.6) & (np.abs(sel[:, 0] - cx) < 2.5)]
            if len(m):
                prof[i] = np.abs(m[:, 1]).max() - K.core_axes(z)[2]
        pk = []
        ok = ~np.isnan(prof)
        i = 0
        while i < len(zs):
            if not ok[i]:
                i += 1
                continue
            j = i
            while j < len(zs) and ok[j]:
                j += 1
            seg = prof[i:j]
            if j - i >= 2 and np.nanmax(seg) > 1.0:      # finaliser: cords 1.25 thick (was 1.4), crossings ~1.8
                pk.append((float(zs[i + int(np.nanargmax(seg))]), float(np.nanmax(seg))))
            i = j
        # one crossing = one group of samples within 12 mm (the cords leave the centre column between them)
        groups = []
        for z_, h_ in sorted(pk, reverse=True):
            if groups and groups[-1][-1][0] - z_ < 12.0:
                groups[-1].append((z_, h_))
            else:
                groups.append([(z_, h_)])
        pk = [float(np.mean([g[0] for g in grp])) for grp in groups]
        res.setdefault("ito_crossing_height_above_core", {})[face] = [round(max(g[1] for g in grp), 2) for grp in groups]
        spec = K.OMOTE_X if face == "omote" else K.URA_X
        # finaliser: the wrap now starts (ura) and ends (omote) with a half crossing tucked at the fuchi / kashira lip;
        # those are reported apart from the spec's 9 visible crossings per face
        lip = [p for p in pk if p > K.Z_FB - 3.5 or p < K.Z_KT + 3.5]
        pk = [p for p in pk if p not in lip]
        peaks[face] = {"count": len(pk), "z": [round(p, 2) for p in pk], "spec_z": spec,
                       "lip_half_crossings_z": [round(p, 2) for p in lip],
                       "max_abs_err": round(float(max(min(abs(p - q) for q in pk) for p in spec)), 3) if pk else None}
    pitches = np.diff(sorted(peaks["omote"]["z"]))
    res["ito"] = {"crossings": peaks, "pitch_mean": round(float(np.abs(pitches).mean()), 3) if len(pitches) else None,
                  "spec_pitch": K.PITCH}
    # diamond opening (omote, 4th diamond): side-view coverage of the cord triangles facing -Y
    za, zb = K.OMOTE_X[3], K.OMOTE_X[4]
    zc = 0.5 * (za + zb)
    cxm, am, bm = K.core_axes(zc)
    tri = V[cords]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    tri = tri[(tri[:, :, 1].mean(axis=1) < 0)]
    res_mm = 0.05
    xs = np.arange(cxm - am - 2.5, cxm + am + 2.5, res_mm)
    zz = np.arange(zb - 3, za + 3, res_mm)
    X, Z = np.meshgrid(xs, zz)
    cov = np.zeros(X.shape, bool)
    for t in tri:
        (ax, az), (bx, bz), (cx2, cz2) = t[:, [0, 2]]
        if max(az, bz, cz2) < zz[0] or min(az, bz, cz2) > zz[-1]:
            continue
        d = (bz - cz2) * (ax - cx2) + (cx2 - bx) * (az - cz2)
        if abs(d) < 1e-12:
            continue
        x0, x1 = np.searchsorted(xs, min(ax, bx, cx2)), np.searchsorted(xs, max(ax, bx, cx2))
        z0, z1 = np.searchsorted(zz, min(az, bz, cz2)), np.searchsorted(zz, max(az, bz, cz2))
        Xs, Zs = X[z0:z1 + 1, x0:x1 + 1], Z[z0:z1 + 1, x0:x1 + 1]
        l1 = ((bz - cz2) * (Xs - cx2) + (cx2 - bx) * (Zs - cz2)) / d
        l2 = ((cz2 - az) * (Xs - cx2) + (ax - cx2) * (Zs - cz2)) / d
        cov[z0:z1 + 1, x0:x1 + 1] |= (l1 >= 0) & (l2 >= 0) & (1 - l1 - l2 >= 0)
    ic = np.argmin(np.abs(xs - cxm))
    free_z = zz[~cov[:, ic]]
    free_z = free_z[(free_z > zb) & (free_z < za)]
    iz = np.argmin(np.abs(zz - zc))
    free_x = xs[~cov[iz, :]]
    inside_core = np.abs(free_x - cxm) <= am
    free_x_in = free_x[inside_core]
    lat_white = 0.94
    free_x_white = free_x_in[np.abs(free_x_in - cxm) <= lat_white * am]
    res["ito"]["diamond_4_omote"] = {
        "along_mm": round(float(free_z.max() - free_z.min()), 2) if len(free_z) else 0.0,
        "across_open_mm": round(float(free_x_in.max() - free_x_in.min()), 2) if len(free_x_in) else 0.0,
        "across_white_mm": round(float(free_x_white.max() - free_x_white.min()), 2) if len(free_x_white) else 0.0,
        "spec_along": K.SP["design_sheet_measured"]["diamond_along_mm"],
        "spec_across": K.SP["design_sheet_measured"]["diamond_across_mm"],
        "note": "side-view (from -Y) projection of the cord triangles; 'open' = no cord over the core within the core's "
                "depth; 'white' = the part painted as same (lateral |l| <= 0.94; beyond it the core under the edge "
                "folds is painted cord-dark)"}
    # edge scallop: height of the ha-edge silhouette above the core's ha edge, over the middle of the tsuka
    zs = np.arange(-180, 10, 0.25)
    hs = []
    for z in zs:
        cx, a, b = K.core_axes(z)
        m = cv[(np.abs(cv[:, 2] - z) < 0.15) & (cv[:, 0] < cx - a + 3.0)]
        hs.append(max(0.0, (cx - a) - m[:, 0].min()) if len(m) else 0.0)
    hs = np.array(hs)
    res["ito"]["edge_scallop_ha_mm"] = round(float(np.percentile(hs, 95) - np.percentile(hs, 5)), 3)
    res["ito"]["edge_silhouette_above_core_mm"] = [round(float(hs.min()), 3), round(float(hs.max()), 3)]
    # ---------------------------------------------------------------- LODs, hulls, sidecar
    res["lod_triangles"] = [int(len(lods[i]["T"])) for i in sorted(lods)]
    res["hulls"] = sorted(h.name for h in hulls)
    side = json.load(open(SIDECAR))
    res["sidecar"] = side
    json.dump(res, open(OUTM, "w"), indent=1)
    # ---------------------------------------------------------------- saya interface
    env = []
    for lv in sorted(lods):
        Bv = verts_of(lods[lv], "M_Katana_Blade")
        Bv = Bv[Bv[:, 2] > 57.9]
        sB, uB = blade_su(Bv)
        rows = []
        for st in np.arange(0.0, K.S_TIP + 0.01, 2.0):
            sel = (sB >= st - 1.0) & (sB < st + 1.0)
            if not sel.any():
                continue
            rows.append([round(float(st), 1), round(float(uB[sel].min()), 3), round(float(uB[sel].max()), 3),
                         round(float(Bv[sel][:, 1].min()), 3), round(float(Bv[sel][:, 1].max()), 3)])
        env.append({"lod": lv, "stations_s_umin_umax_ymin_ymax": rows,
                    "between_stations": "every LOD's blade is lofted between these rings (linear sections along the arc); "
                                        "use the rings plus the edges between them, or sample the exported mesh",
                    "tip_s": round(float(sB.max()), 3)})
    habs = []
    for lv in sorted(lods):
        F = verts_of(lods[lv], "M_Katana_Fittings")
        H = F[(F[:, 2] >= 57.999) & (np.abs(F[:, 1]) <= 6.01) & (np.abs(F[:, 0]) <= 17.51)]
        habs.append({"lod": lv, "x": [round(float(H[:, 0].min()), 3), round(float(H[:, 0].max()), 3)],
                     "y": [round(float(H[:, 1].min()), 3), round(float(H[:, 1].max()), 3)],
                     "z": [round(float(H[:, 2].min()), 3), round(float(H[:, 2].max()), 3)]})
    Sp = K.SP
    seppa_all = verts_of(d0, "M_Katana_Fittings")
    sb = seppa_all[(seppa_all[:, 2] >= 56.4) & (seppa_all[:, 2] <= 58.01) & ((np.abs(seppa_all[:, 0]) > 17.6) | (np.abs(seppa_all[:, 1]) > 6.1))]
    iface = {
        "what": "Envelope of the shipped SM_Katana that SM_Katana_Saya must fit (measured on the exported FBX bytes)",
        "fbx": str(FBX), "fbx_sha256": res["fbx_sha256"], "sidecar_sha256": res["sidecar_sha256"],
        "frame": "sword frame, mm: origin = Grip socket, +Z along the tsuka axis toward the blade, +X mune, -Y omote",
        "mune_arc": {"radius": K.R, "centre_xz": [K.CX, K.CZ], "machi_z": K.Z_M,
                     "fit_on_export": res["blade"]["mune_arc_fit"],
                     "note": "the blade's mune is one circular arc tangent to +Z at the mune-machi; s = R * atan2(z - CZ, CX - x), "
                             "u = |(x, z) - C| - R (u > 0 toward the edge); sections never grow toward the tip"},
        "blade_envelope_per_lod": env,
        "habaki": {"spec": Sp["habaki"], "measured_per_lod": habs,
                   "rule": "saya habaki pocket = habaki + 0.1 all round (spec saya.cavity.habaki_pocket), swept along the draw arc"},
        "seppa_blade_side": {"spec": Sp["seppa"], "face_z_toward_koiguchi": Sp["seppa"]["z_blade_side"][1],
                             "measured_outline_x": [round(float(sb[:, 0].min()), 3), round(float(sb[:, 0].max()), 3)] if len(sb) else None,
                             "measured_outline_y": [round(float(sb[:, 1].min()), 3), round(float(sb[:, 1].max()), 3)] if len(sb) else None,
                             "seat": "koiguchi face at z = 58.0 + 0.3 (spec sheathed.seat)"},
        "tsuba": {"spec": Sp["tsuba"], "measured": res["tsuba"]},
        "sockets_from_sidecar": side,
        "sheathed": Sp["sheathed"],
        "cavity_rule": Sp["saya"]["cavity"],
        "lod_triangles": res["lod_triangles"],
    }
    json.dump(iface, open(OUTI, "w"), indent=1)
    print("KAT_MEASURE", json.dumps({k: v for k, v in res.items() if k != "sidecar"})[:4000], flush=True)


main()
