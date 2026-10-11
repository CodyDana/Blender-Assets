"""SMG01 W3 magazine fit on the SHIPPED bytes (the hook gunlib.drivers.mag_fit calls: cfg.mag_fit["gates"]; inside a
fresh Blender process). SMG_BUILD_PLAN 12.2:

- M6: Mag and MagInsertStart of the exported twin and skeletal sidecars vs the fit (MagInsertStart = Mag - 68.2 mm
  along the magazine's +Z, the same rotation; the skeletal and static sidecars agree; the magazine's own Mag is its
  origin) <= 0.001 mm / 0.001 deg;
- M1: seated, the co-visible LOD pairs (k, k) and (k, k+-1) of the twin (its gun faces) and SM_SMG01_Mag: 0
  intersecting triangles at LOD0-1; LOD2-3 penetration under 1 px at the switch distance (the part of the magazine
  inside the LOD0 well never shows);
- M2-M5, M4b, M5b and F5 on the exported SK_SMG01 LOD0 (the paddle = its 'mag_release' vertex group, posed about its
  pin) and the exported SM_SMG01_Mag LOD0 placed at the exported Mag: gunlib.drivers.magfit_check.straight_gates (the
  form stage's straight-insert set, spring-loaded catch) on the shipped geometry;
- M8 (info): the Reload / ReloadEmpty clips' magazine path stays on the straight axis (no drop inside the well) and the
  posed magazine + paddle meet the gun at no clip frame;
- M10: the twin's merged magazine = SM_SMG01_Mag at every LOD (mag build report);
- the build's own gates: qa_check, LODs, C1, S1, derived sizes, UD1 / UD3 / UD4, B10.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gunlib import gateutil as GU  # noqa: E402
from gunlib import fit as FT  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib.drivers import magfit_check as MC  # noqa: E402


def _sk_lod0(F):
    """The exported SK_SMG01.fbx LOD0 re-imported: (V frame B mm, T gun without the paddle, T paddle)."""
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
    """The fields magfit_check.straight_gates reads, from the shipped bytes (frame M, mm)."""

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
    C = F.C
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
    ok6 = all(v <= 0.001 for k, v in m6.items() if k != "insert_mm")
    gates.append(GU.gate("M6 Mag / MagInsertStart (exported sidecars) vs the fit", m6, "<= 0.001 mm, <= 0.001 deg", ok6,
                         "MagInsertStart lies on the magazine's -Z 68.2 mm below Mag (straight path), same rotation; "
                         "the skeletal and static sidecars agree; the magazine's Mag is its origin"))
    # ------------------------------------------------------------ M1 seated, co-visible pairs
    rtrees = {k: GU.tree(gun[k][0], gun[k][1]) for k in gun}
    rbox = {k: (gun[k][0][np.unique(gun[k][1])].min(0), gun[k][0][np.unique(gun[k][1])].max(0)) for k in gun}
    m1, ok1 = {}, True
    for a, b in F.pairs:
        Q, T = F.place(b, RM, tM)
        n = len(rtrees[a].overlap(GU.tree(Q, T)))
        row = {"intersecting_triangle_pairs": n}
        if n and max(a, b) >= 2:
            Sq = F.samples(Q, T, 0.5)
            raw = F.depth_inside(Sq, rtrees[a], *rbox[a])
            dep = F.depth_inside(F.visible_only(Sq), rtrees[a], *rbox[a])
            k = max(a, b)
            row.update(depth_mm_outside_well=round(dep, 3), depth_px=round(dep * F.px_per_mm(k), 3),
                       at_m=round(F.switch_m[k], 3), raw_depth_mm=round(raw, 3))
            ok1 &= dep * F.px_per_mm(k) < 1.0
        elif n:
            ok1 = False
        m1[f"gun LOD{a} / mag LOD{b}"] = row
    gates.append(GU.gate("M1 seated: intersecting triangles, co-visible LOD pairs (twin bytes + magazine bytes)", m1,
                         "0 at LOD0-1 pairs; LOD2-3 pairs: depth < 1 px at the switch distance outside the LOD0 well", ok1))
    # ------------------------------------------------------------ M2-M5, M4b, M5b, F5 on the shipped LOD0 bytes
    Vg, Tg, Tc = _sk_lod0(F)
    Qm, Tm = F.place(0, RM, tM)
    S = _Scene(Vg, Tg, Tc, Qm, Tm, grip)
    Cs = dict(cfg.magfit)
    Cs["mag_origin_M"] = (tM + grip).tolist()
    Cs["mag_axes_M"] = {"x": RM[:, 0].tolist(), "z": RM[:, 2].tolist()}
    Cs["insert_mm"] = ins
    Cs["well_parts"] = ("gun",)
    sg = MC.straight_gates(S, Cs)
    for g in sg:
        g["name"] = g["name"] + " [shipped bytes]"
    gates += sg
    # ------------------------------------------------------------ M8 (info): the clips' magazine path
    import smg_clips as CL
    m = F.RIG["motion"]
    CL.MAG_Z = np.array(m["mag_axis_B"], float)
    CL.configure(m["bolt_travel_mm"], m["handle_travel_mm"], m["insert_mm"])
    clips = CL.all_clips()
    heads = {n: np.array(v["head_mm"]) for n, v in F.RIG["bones"].items()}
    gtree = GU.tree(S.RV - grip, Tg)
    m8 = {}
    for cname in ("A_SMG01_Reload", "A_SMG01_ReloadEmpty"):
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
    # ------------------------------------------------------------ the build's gates
    mr = F.MAGREP
    lods = [mr["lods"][f"{cfg.mag}_LOD{k}"]["triangles"] for k in range(4)]
    bud = cfg.spec.d["budgets_triangles"]["mag"]
    gates.append(GU.gate("mag qa_check (LOD0-3, before export)", {"passed": mr["qa_check"]["passed"],
                         "triangles": mr["qa_check"]["triangles"], "texel_target": mr["qa_check"]["texel_target_px_cm"],
                         "checks": mr["qa_check"]["checks"]},
                         "pass; budget 5,000; UV1; UCX keyed to the node; texel = measured aggregate +-25 %",
                         mr["qa_check"]["passed"]))
    gates.append(GU.gate("mag LODs strictly descending; LOD0 within budget", lods,
                         f"LOD0 <= {bud['lod0_ceiling']} (target {bud['lod0_target'][0]}-{bud['lod0_target'][1]}); "
                         f"targets ~{bud['lod1']} / ~{bud['lod2']} / {bud['lod3'][0]}-{bud['lod3'][1]} (reported)",
                         lods[0] <= bud["lod0_ceiling"] and lods[0] > lods[1] > lods[2] > lods[3],
                         "the same objects the twin merges (generator LOD1-2, the traced prism at LOD3)"))
    gates.append(GU.gate("C1 mag hull containment", mr["C1"], "0 and 0; 1 hull (spec collision.mag), <= 32 vertices",
                         mr["C1"]["pass"]))
    gates.append(GU.gate("S1 mag sockets (exported sidecar vs build)", {"count": len(mr["S1"]["sockets"]),
                         "worst_mm": mr["S1"]["worst_mm"], "worst_deg": mr["S1"]["worst_deg"],
                         "names_match_spec": mr["S1"]["names_match_spec"]}, "5 = spec names; <= 0.001 mm, <= 0.001 deg",
                         mr["S1"]["pass"]))
    gates.append(GU.gate("mag LOD screen sizes derived from the SK's", mr["lod_screen_sizes"],
                         "size_mag = size_SK x r_mag / r_SK engine", True))
    udok = all(v["ud1_drops"] == 0 and v["min_area_mm2"] >= 0.01 and v["ud3_collapsed_unreal"] == 0
               for v in mr["ud"].values())
    gates.append(GU.gate("UD1 / UD3 on SM_SMG01_Mag LOD0-3", mr["ud"], "0 drops; min area >= 0.01 mm2; 0 collapsed",
                         udok))
    gates.append(GU.gate("UD4 SM_SMG01_Mag authored UV1 (64 / 128 px, 2 px)", {k: v["pass"] for k, v in mr["ud4"].items()},
                         "pass", all(v["pass"] for v in mr["ud4"].values())))
    gates.append(GU.gate("B10 mag names", mr["B10_names"], "no hit", mr["B10_names"]["pass"]))
    tw = mr.get("twin_mag_equal", {"pass": False, "lods": "missing"})
    gates.append(GU.gate("M10 the twin's merged magazine = SM_SMG01_Mag at every LOD", tw["lods"],
                         "equal triangles; vertex sets within 0.001 mm both ways", tw["pass"]))
    out["center_of_mass_mag_mm"] = mr["center_of_mass"]
    return gates
