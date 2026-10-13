"""SR01 W3 magazine fit on the SHIPPED bytes (fresh Blender process; gunlib.drivers.mag_fit with this hook; the SMG's
smg_magfit.py, adapted). SR01_BUILD_PLAN 0 / 4 (straight path MagInsertStart -> Mag along +Z):

    blender -b --factory-startup --python Scripts/guns/sniper/sr_magfit.py

- M7 (driver): SM_SR01.fbx = the rig step's sha256, SM_SR01_Mag.fbx = the mag build's, built from those twin bytes;
- M6: Mag / MagInsertStart of the exported twin and skeletal sidecars (MagInsertStart = Mag - 67.8 mm along Z, the same
  rotation; skeletal = static; the magazine's own Mag is its origin) <= 0.001 mm / 0.001 deg;
- M1: seated, co-visible LOD pairs (k, k), (k, k+-1) of the twin's gun faces and SM_SR01_Mag: 0 intersecting triangles
  at LOD0-1; LOD2-3 penetration outside the LOD0 well under 1 px at the switch distance;
- M2-M5, M4b, M5b on the exported SK_SR01 LOD0 (the paddle = its 'mag_release' vertex group, posed about its pin) and
  the exported SM_SR01_Mag LOD0 at the exported Mag: gunlib.drivers.magfit_check.straight_gates;
- M8 (info): the Reload / ReloadEmpty clips' magazine path stays on the straight axis and meets the gun at no frame;
- M9: the magazine's 5 sockets (exported sidecar vs spec); M10: the twin's merged magazine = SM_SR01_Mag per LOD
  (triangle counts); the mag build's qa_check, LODs, hull, UD1 / UD3, B10.
Writes gates/mag.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from sr_gun import CFG  # noqa: E402
from sr_common import D  # noqa: E402

from gunlib import gateutil as GU  # noqa: E402
from gunlib.drivers import magfit_check as MC  # noqa: E402
from gunlib.drivers import mag_fit as MF  # noqa: E402

MAG = D["sockets"]["mag"]


def _sk_lod0(F):
    import bpy
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(F.EXP / f"{F.cfg.skeletal}.fbx"), use_custom_normals=True,
                             automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before]
    mesh = next(o for o in new if o.type == "MESH")
    V, T = GU.mesh_np(mesh)
    gi = {g.index: g.name for g in mesh.vertex_groups}
    vb = np.array([gi[v.groups[0].group] if v.groups else "" for v in mesh.data.vertices])
    catch = np.all(vb[T] == "mag_release", axis=1)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return V, T[~catch], T[catch]


class _Scene:
    def __init__(self, Vg, Tg, Tc, MV, MT, grip):
        self.rn = ["gun", "mag_release"]
        self.ci = 1
        self.RV = Vg + grip
        self.RT = np.vstack([Tg, Tc])
        self.RL = np.r_[np.zeros(len(Tg), int), np.ones(len(Tc), int)]
        self.rtree = GU.tree(self.RV, self.RT)
        self.cV = self.RV
        self.cT = Tc
        self.MV, self.MT = MV + grip, MT


def stage_gates(F, out):
    cfg = F.cfg
    grip = F.grip
    gates = []
    gun, mag = F.gun, F.mag
    # ------------------------------------------------------------ M6
    RM, tM = F.sock_frame(F.gs["Mag"])
    RI, tI = F.sock_frame(F.gs["MagInsertStart"])
    z = RM[:, 2]
    ins = float(F.RIG["motion"]["insert_mm"])
    fit_I = tM - ins * z
    spec = {r["socket"]: r for r in cfg.gun_sockets()}
    d_spec_mag = float(np.abs(tM - np.array(spec["Mag"]["blender_mm"])).max())
    sk = F.sk
    d_sk = max(float(np.abs(np.array(sk[n]["unreal_component"]["location_cm"]) - np.array(F.gs[n]["location_cm"])).max())
               * 10 for n in ("Mag", "MagInsertStart"))
    mag0 = F.ms["Mag"]
    mag_origin = max(max(abs(v) for v in mag0["location_cm"]) * 10, max(abs(v) for v in mag0["rotation_deg"].values()))
    m6 = {"insertstart_on_axis_mm": round(float(np.abs(fit_I - tI).max()), 6),
          "insert_rot_eq_mag_deg": round(float(np.degrees(np.abs(RI - RM).max())), 6),
          "mag_vs_spec_mm": round(d_spec_mag, 6), "skeletal_vs_static_mm": round(d_sk, 6),
          "mag_own_Mag_origin_mm_or_deg": round(mag_origin, 6), "insert_mm": ins}
    gates.append(GU.gate("M6 Mag / MagInsertStart (exported sidecars) vs the fit", m6, "<= 0.001 mm, <= 0.001 deg",
                         all(v <= 0.001 for k, v in m6.items() if k != "insert_mm"),
                         "MagInsertStart lies 67.8 mm below Mag on Z (straight path), same rotation"))
    # ------------------------------------------------------------ M1 seated, co-visible pairs
    rtrees = {k: GU.tree(gun[k][0], gun[k][1]) for k in gun}
    rbox = {k: (gun[k][0][np.unique(gun[k][1])].min(0), gun[k][0][np.unique(gun[k][1])].max(0)) for k in gun}
    m1, ok1 = {}, True
    for a, b in F.pairs:
        if a not in gun or b not in mag:
            continue
        Q, T = F.place(b, RM, tM)
        n = len(rtrees[a].overlap(GU.tree(Q, T)))
        row = {"intersecting_triangle_pairs": n}
        if n and max(a, b) >= 2:
            Sq = F.samples(Q, T, 0.5)
            dep = F.depth_inside(F.visible_only(Sq), rtrees[a], *rbox[a])
            k = max(a, b)
            row.update(depth_mm_outside_well=round(dep, 3), depth_px=round(dep * F.px_per_mm(k), 3),
                       at_m=round(F.switch_m[k], 3))
            ok1 &= dep * F.px_per_mm(k) < 1.0
        elif n:
            ok1 = False
        m1[f"gun LOD{a} / mag LOD{b}"] = row
    gates.append(GU.gate("M1 seated: intersecting triangles, co-visible LOD pairs (twin bytes + magazine bytes)", m1,
                         "0 at LOD0-1 pairs; LOD2-3 pairs: depth < 1 px at the switch distance outside the LOD0 well", ok1))
    # ------------------------------------------------------------ M2-M5, M4b, M5b on the shipped LOD0 bytes
    Vg, Tg, Tc = _sk_lod0(F)
    Qm, Tm = F.place(0, RM, tM)
    S = _Scene(Vg, Tg, Tc, Qm, Tm, grip)
    Cs = {"path": "straight", "catch": "mag_release", "catch_pivot_M": [408.6, 0.0, -74.0], "catch_axis": [0.0, 1.0, 0.0],
          "release_deg": -4.5, "mag_origin_M": (tM + grip).tolist(),
          "mag_axes_M": {"x": RM[:, 0].tolist(), "z": RM[:, 2].tolist()}, "insert_mm": ins,
          "well_band": [0.0, 44.8], "lip_z": 0.0, "well_parts": ("gun",), "catch_zone_mm": 6.0,
          "half_thickness": 13.25, "half_length": 44.6}
    try:
        sg = MC.straight_gates(S, Cs)
        for g in sg:
            g["name"] = g["name"] + " [shipped bytes]"
        gates += sg
    except Exception as e:  # noqa: BLE001
        gates.append(GU.gate("M2-M5 straight-insert set [shipped bytes]", {"error": repr(e)}, "runs", False))
    # ------------------------------------------------------------ M8 (info): the clips' magazine path
    import sr_clips as CL
    clips = CL.all_clips()
    heads = {n: np.array(v["head_mm"]) for n, v in F.RIG["bones"].items()}
    gtree = GU.tree(S.RV - grip, Tg)
    m8 = {}
    for cname in ("A_SR01_Reload", "A_SR01_ReloadEmpty"):
        frames, _n, _fps = clips[cname]
        off_axis, hits = [], []
        for f, v in frames:
            s, d = v.get("insert", 0.0), v.get("drop", 0.0)
            if d > 1e-6 and s < ins - 1e-6:
                off_axis.append(f)
            bas = CL.basis_from(v)
            Mm = bas.get("magazine", np.eye(4))
            Qf = (Qm - heads["magazine"]) @ Mm[:3, :3].T + Mm[:3, 3] + heads["magazine"]
            Mc = bas.get("mag_release", np.eye(4))
            Vc = (Vg - heads["mag_release"]) @ Mc[:3, :3].T + Mc[:3, 3] + heads["mag_release"]
            mt = GU.tree(Qf, Tm)
            ng = len(gtree.overlap(mt))
            nc = len(GU.tree(Vc, Tc).overlap(mt)) if len(Tc) else 0
            if ng or nc:
                hits.append({"frame": f, "gun_pairs": ng, "paddle_pairs": nc, "insert": round(s, 3),
                             "release": round(v.get("release", 0.0), 3)})
        m8[cname] = {"frames": len(frames), "drop_inside_the_well_frames": off_axis, "intersecting_frames": hits}
    gates.append(GU.gate("M8 (info) the clips' magazine path: straight axis, no clip frame meets the gun", m8,
                         "reported (0 expected)", True))
    # ------------------------------------------------------------ M9 sockets, M10 twin = mag, the build's gates
    mr = F.MAGREP
    worst = 0.0
    for s in MAG:
        e = np.array(s["mag_local_mm"], float)
        got = F.ms[s["socket"]]
        worst = max(worst, float(np.abs(np.array(got["location_cm"]) - np.array([e[0], -e[1], e[2]]) * 0.1).max()) * 10)
    names_ok = sorted(F.ms) == sorted(s["socket"] for s in MAG)
    gates.append(GU.gate("M9 magazine sockets (exported sidecar vs spec sockets.mag)", {"count": len(F.ms),
                         "names_match_spec": names_ok, "worst_mm": round(worst, 6)}, "5; <= 0.001 mm",
                         names_ok and worst <= 0.001))
    tw = {}
    ok10 = True
    for k in range(4):
        n_twin = len(gun[k][2]) if k in gun else None
        n_mag = len(mag[k][1]) if k in mag else None
        tw[f"LOD{k}"] = {"twin_merged_mag_tris": n_twin, "SM_SR01_Mag_tris": n_mag}
        ok10 &= n_twin == n_mag
    gates.append(GU.gate("M10 the twin's merged magazine = SM_SR01_Mag at every LOD", tw, "equal triangles", ok10,
                         "both are joined from the same magazine LOD objects (sr_game / sr_attach)"))
    lods = [mr["lods"][f"LOD{k}"]["triangles"] for k in range(4)]
    gates.append(GU.gate("mag qa_check (LOD0-3, before export)", {"passed": mr["qa_check"]["passed"],
                         "triangles": mr["qa_check"]["triangles"], "checks": mr["qa_check"]["checks"]},
                         "pass; budget 5,000; UV1; UCX keyed to the node", mr["qa_check"]["passed"]))
    gates.append(GU.gate("mag LODs strictly descending; LOD0 within budget", lods,
                         "LOD0 <= 5000 (target 2000-3000: reported)", lods[0] <= 5000 and lods[0] > lods[1] > lods[2] > lods[3]))
    gates.append(GU.gate("mag hull (1, <= 32 vertices)", mr["hulls"], "1 hull", len(mr["hulls"]) == 1))
    udok = all(v["ud1_drops"] == 0 and v["min_area_mm2"] >= 0.01 and v["ud3_zero"] == 0 for v in mr["lods"].values())
    gates.append(GU.gate("UD1 / UD3 on SM_SR01_Mag LOD0-3", {k: {x: v[x] for x in ("ud1_drops", "min_area_mm2", "ud3_zero")}
                                                           for k, v in mr["lods"].items()},
                         "0 drops; min area >= 0.01 mm2; 0 float32 zero-tangent corners", udok))
    gates.append(GU.gate("B10 mag names", mr["deny_tokens"], "no hit", not mr["deny_tokens"]))
    return gates


CFG.mag_fit["gates"] = stage_gates

if __name__ == "__main__":
    MF.main(CFG, [])
