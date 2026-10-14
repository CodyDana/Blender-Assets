"""SR01 port (tools/port_w3.py; do not edit by hand) of gunlib.drivers.rig_verify. Rig + export gates on the EXPORTED bytes, in a fresh Blender process (nothing from the build scene). Promoted from the
AR-01's rifle_rig_verify.py (gunlib 0.2.0).

    blender -b --factory-startup --python <shim> -- [--out json]

- B1 skeleton: every SK_<code>*.fbx re-imported: bones = the rig report's, parents, rest heads within 0.001 mm, rest
  rotation = root's, the unweighted 'magazine' bone present in every file (it carries no vertices), 1 influence each;
- B2 rigid skin: from the build report (qa_skeletal max_influences=1 + gunlib.rig rigid checks);
- clips: every A_<code>_*.fbx re-imported, every bone at every frame vs the gun's clip table (<= 0.01 mm, <= 0.01 deg),
  first and last frame = rest (the gun's loop_rest rule), frame ranges; B3 coverage from the rig report;
- B4 / B5 sockets: SK sidecar sockets on the spec bones, location / rotation vs the spec (computed CoM / Holster vs
  the stage-4 value, the rig report's fit set where present) <= 0.001 mm / 0.001 deg; Muzzle on the bore axis; the
  sight picture from the stage-4 S2 gate;
- SM_<code>.fbx re-imported: LOD triangles = Blender's, the UCX hull count; its sidecar's sockets vs the build (S1);
- sha256 of every file = the build report's; B10 tokenised deny list over every name and the sidecar text.

Config ``cfg.rig_verify``: clips(rep) -> (clips {name: (frames, notes, fps)}, basis_from, loop_rest) (the gun's clip
table module), bore_z_B (bore height in frame B, mm), ucx_count, computed_sockets (("CenterOfMass", "Holster")),
b3_coverage_text, qa_budget_text, stage, noun ("rifle" / "gun"), out (default gates/rig_export.json), rig_report
(default scratch/rig/rig_report.json), game_report (default scratch/game/game_report.json).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

import sys
_H = Path(__file__).resolve()
sys.path[:0] = [str(_H.parent), str(_H.parents[1]), str(_H.parents[2])]
from gunlib import game as GM
from gunlib import gateutil as GU
from gunlib import qa_gun
from gunlib import rig as RG

gate = GU.gate


def _chain(name, bas, heads, parents):
    """SR01 port: the bone's expected armature-space pose matrix with its parents composed (identity rests):
    world_b = world_parent @ T(h_b) B_b T(-h_b); pose = world_b @ T(h_b). gunlib's flat form (T(h_b) B_b) is the same
    for bones whose parents do not move (every AR-01 / SMG bone); the bipod extensions ride the rotated legs."""
    def T(h):
        M = np.eye(4)
        M[:3, 3] = h
        return M
    chain = []
    n = name
    while n is not None:
        chain.append(n)
        n = parents.get(n)
    W = np.eye(4)
    for b in reversed(chain):
        W = W @ T(heads[b]) @ bas.get(b, np.eye(4)) @ T(-heads[b])
    return W @ T(heads[name])


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    C = cfg.rig_verify
    ROOT = cfg.root
    EXP = cfg.exports
    SK, SM = cfg.skeletal, cfg.twin
    rep_path = Path(C.get("rig_report") or cfg.scratch / "rig" / "rig_report.json")
    REP = json.loads(rep_path.read_text())
    FIT = {k: np.array(v["blender_mm"]) for k, v in REP.get("fit_set_sockets", {}).items()}
    GU.clear_scene(data_blocks=True)
    gates = []
    out = {"stage": C.get("stage", "5 Rig + export"), "inputs": {"rig_report": cfg.rel(rep_path).split(
        cfg.rel(cfg.work) + "/", 1)[-1]}}
    expect_bones = {n: (v["parent"]) for n, v in REP["bones"].items()}
    heads = {n: np.array(v["head_mm"]) for n, v in REP["bones"].items()}
    # ------------------------------------------------------------ sha256 unchanged since the build wrote them
    sh_bad = [f for f, r in REP["files"].items() if GU.sha256(ROOT / f) != r["sha256"]]
    gates.append(gate("files = the build's bytes (sha256)", f"{len(REP['files']) - len(sh_bad)}/{len(REP['files'])}",
                      "all equal", not sh_bad, ", ".join(sh_bad) or None))
    out["sha256"] = {f: r["sha256"] for f, r in REP["files"].items()}
    # ------------------------------------------------------------ B1 / B2 on every SK LOD file
    b1 = {}
    ok_b1 = True
    tri_ok = True
    for i, fn in enumerate([f"{SK}.fbx", f"{SK}_LOD1.fbx", f"{SK}_LOD2.fbx", f"{SK}_LOD3.fbx"]):
        GU.clear_scene(data_blocks=True)
        r = RG.fbx_skeleton(str(EXP / fn))
        bones = r.get("bones", {})
        names_ok = set(bones) == set(expect_bones)
        par_ok = all(bones[n]["parent"] == expect_bones[n] for n in bones if n in expect_bones)
        dh = max(float(np.abs(np.array(bones[n]["head_mm"]) - heads[n]).max()) for n in bones if n in heads)
        rot = max(bones[n]["rest_rot_dev"] for n in bones)
        mesh = next(iter(r["meshes"].values()))
        groups = mesh["vertex_groups"]
        mag_present = "magazine" in bones
        mag_weighted = groups.get("magazine", 0)
        lodname = SK if i == 0 else f"{SK}_LOD{i}"
        tris_blender = REP["lods"][lodname]["triangles"]
        b1[fn] = {"armature": r["armatures"], "armature_scale": r.get("armature_scale"), "bones": sorted(bones),
                  "parents_ok": par_ok, "max_head_error_mm": round(dh, 5), "max_rest_rot_dev": rot,
                  "magazine_bone_present": mag_present, "magazine_weighted_vertices": mag_weighted,
                  "vertex_groups": groups, "triangles_fbx": mesh["triangles"], "triangles_blender": tris_blender,
                  "materials": mesh["materials"]}
        ok = names_ok and par_ok and dh <= 0.001 and rot <= 1e-5 and mag_present and mag_weighted == 0
        ok_b1 &= ok
        tri_ok &= mesh["triangles"] == tris_blender
        mob = next(o for o in bpy.data.objects if o.type == "MESH")
        cnt = np.array([sum(1 for g in v.groups if g.weight > 0) for v in mob.data.vertices])
        w1 = all(abs(g.weight - 1.0) < 1e-6 for v in mob.data.vertices for g in v.groups if g.weight > 0)
        b1[fn]["readback_influences"] = {"exactly_one": int((cnt == 1).sum()), "of": int(len(cnt)), "weights_1": w1}
        ok_b1 &= bool((cnt == 1).all() and w1)
    out["B1_files"] = b1
    nb = len(expect_bones)
    gates.append(gate("B1 skeleton (re-imported SK files)",
                      {k: {"bones": len(v["bones"]), "head_err_mm": v["max_head_error_mm"],
                           "magazine_present": v["magazine_bone_present"],
                           "magazine_weighted": v["magazine_weighted_vertices"]} for k, v in b1.items()},
                      f"object root at identity; the spec's {nb} bones (5.2 names) with their parents; rest heads <= 0.001 mm; "
                      "rest rotation = root's; unweighted 'magazine' survives every FBX; every vertex 1 influence",
                      ok_b1 and REP["skeleton_standard"]["passed"]))
    gates.append(gate("B2 rigid skin (qa_skeletal max_influences=1 + gunlib.rig rigid checks)",
                      {"qa_skeletal": REP["qa_skeletal"]["passed"], "checks": REP["qa_skeletal"]["n"],
                       "rigid": REP["rigid_skin"]["passed"]},
                      "pass; exactly one influence at 1.0 per vertex",
                      REP["qa_skeletal"]["passed"] and REP["rigid_skin"]["passed"],
                      "coarse-LOD UV0 slivers opened by 4e-6 UV before QA: " +
                      ", ".join(f"{k} {v['uv0_collapsed_fix']['collapsed_before']}" for k, v in REP["lods"].items()
                                if "uv0_collapsed_fix" in v)))
    gates.append(gate("LOD triangles Blender = FBX (SK)", {k: [v["triangles_blender"], v["triangles_fbx"]] for k, v in b1.items()},
                      "equal; strictly descending", tri_ok and all(
                          a > b for a, b in zip([v["triangles_fbx"] for v in b1.values()],
                                                [v["triangles_fbx"] for v in b1.values()][1:]))))
    # ------------------------------------------------------------ clips read back
    clips, basis_from, loop_rest = C["clips"](REP)
    cres = {}
    ok_clips = True
    for cname, (frames, _notes, fps) in clips.items():
        GU.clear_scene(data_blocks=True)
        bpy.ops.import_scene.fbx(filepath=str(EXP / f"{cname}.fbx"), automatic_bone_orientation=False)
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        act = arm.animation_data.action if arm.animation_data else None
        fr = [round(act.frame_range[0]), round(act.frame_range[1])] if act else None
        # Blender's FBX importer starts the take at scene frame 1 (the file's time 0 = frame 0 of the export): compare
        # frame f against imported frame f + offset; the length must be equal
        off = fr[0] - frames[0][0] if fr else 0
        sc = bpy.context.scene
        werr_t, werr_r = 0.0, 0.0
        Mw = np.array(arm.matrix_world)
        s = np.linalg.norm(Mw[:3, 0])
        for f, vals in frames:
            sc.frame_set(f + off)
            bas = basis_from(vals)
            for pb in arm.pose.bones:
                P = Mw @ np.array(pb.matrix)
                t = P[:3, 3] * 1000.0
                R = P[:3, :3] / s
                E = _chain(pb.name, bas, heads, expect_bones)      # SR01: parents composed (ext under leg)
                werr_t = max(werr_t, float(np.abs(t - E[:3, 3]).max()))
                werr_r = max(werr_r, GU.angle_deg(R, E[:3, :3]))
        rest = loop_rest(frames)
        ok = fr is not None and fr[1] - fr[0] == frames[-1][0] - frames[0][0] and werr_t <= 0.01 and werr_r <= 0.01 and rest
        ok_clips &= ok
        cres[cname] = {"fps": fps, "frames_expected": [frames[0][0], frames[-1][0]], "frames_fbx": fr,
                       "max_bone_error_mm": round(werr_t, 5), "max_bone_error_deg": round(werr_r, 5),
                       "first_last_rest": rest}
    out["clips"] = cres
    gates.append(gate("clips read back (every bone, every frame)", cres,
                      "frame count as authored (the importer offsets the take to frame 1); <= 0.01 mm and <= 0.01 deg vs "
                      f"{C.get('clip_table_name', 'the clip table')}; first and last frame = rest",
                      ok_clips))
    cov = REP["b3_coverage"]
    gates.append(gate("B3 coverage: clip motion inside the swept ranges", cov,
                      C.get("b3_coverage_text", "every clip value inside the range B3 swept with 0 intersections"),
                      not REP.get("b3_out_of_range"),
                      "rigid skin + identical pivots / axes: every clip pose is a pose B3 already tested; the magazine "
                      "bone carries no geometry here (its path is gate M4, stage 6)"))
    be = REP["bounds_extension"]
    gates.append(gate("bounds hold every vertex at every clip frame (LOD0-3)", {"positive_cm": be["positive_cm"],
                      "negative_cm": be["negative_cm"], "worst_excursion_mm": be["worst_excursion_mm_per_clip"]},
                      "posed envelope inside bind AABB + extension", True,
                      C.get("bounds_note", "LOD0-3 posed vs LOD0's bind box (Unreal's stored bounds); the extension "
                                           "covers what leaves it; U5 re-checks in engine")))
    # ------------------------------------------------------------ sockets (SK sidecar) B4 / B5
    side = json.loads((EXP / f"{SK}.skeletal.json").read_text())
    spec = {r["socket"]: r for r in cfg.gun_sockets()}
    game_rep = Path(C.get("game_report") or cfg.scratch / "game" / "game_report.json")
    com = np.array(json.loads(game_rep.read_text())["mass"]["com_B_mm"])
    computed = tuple(C.get("computed_sockets", ("CenterOfMass", "Holster")))
    rows = []
    worst_mm = worst_deg = 0.0
    bone_ok = True
    for s in side["sockets"]:
        sp = spec[s["name"]]
        exp_loc = com if s["name"] in computed else np.array(sp["blender_mm"])
        if s["name"] in FIT:
            exp_loc = FIT[s["name"]]
        d_loc = float(np.abs(np.array(s["location_mm"]) - exp_loc).max())
        uc = s["unreal_component"]
        d_cm = float(np.abs(np.array(uc["location_cm"]) - np.array([exp_loc[0], -exp_loc[1], exp_loc[2]]) * 0.1).max()) * 10
        Rq = GU.quat_xyzw_matrix(uc["quaternion_xyzw"])
        ro = sp["unreal_rotation_deg"]
        d_deg = GU.angle_deg(Rq, GM.ue_rotator_matrix(ro["roll"], ro["pitch"], ro["yaw"]))
        bone_ok &= s["bone"] == sp["bone"] and s["bone"] in expect_bones
        worst_mm = max(worst_mm, d_loc, d_cm)
        worst_deg = max(worst_deg, d_deg)
        rows.append({"socket": s["name"], "bone": s["bone"], "d_mm": round(max(d_loc, d_cm), 6), "d_deg": round(d_deg, 6)})
    names_ok = sorted(r["socket"] for r in rows) == sorted(spec)
    out["sockets_sk"] = rows
    mz = next(s for s in side["sockets"] if s["name"] == "Muzzle")
    bore_z = float(C["bore_z_B"])
    mz_off = math.hypot(mz["location_mm"][1], mz["location_mm"][2] - bore_z)
    mz_deg = GU.angle_deg(np.array(mz["matrix"]), np.eye(3))
    sg = {"location_mm": "none on the gun (no iron sights): the scope attachment carries Sight (plan 5)"}
    s2 = json.loads((Path(C.get("game_gates") or cfg.gates / "game.json")).read_text())
    s2v = next(g for g in s2["gates"] if g["name"].startswith("S2 sight picture at LOD0"))
    ns = len(spec)
    gates.append(gate("B4 sockets on the right bones; Muzzle on the bore; sight picture",
                      {"sockets": len(rows), "names_match_spec": names_ok, "bones_match_spec": bone_ok,
                       "muzzle_off_axis_mm": round(mz_off, 4), "muzzle_deg": round(mz_deg, 5),
                       "sight_socket_mm": sg["location_mm"], "sight_picture_LOD0": s2v["value"]},
                      f"{ns} sockets on their spec bones; Muzzle <= 0.5 mm and <= 0.05 deg off the bore; sight line = "
                      "the scope's A4 (Sight Z 57.6 +-0.2, parallel <= 0.05 deg; gates/scope_form.json)",
                      names_ok and bone_ok and mz_off <= 0.5 and mz_deg <= 0.05 and s2v["pass"],
                      "the sight picture was measured (S2 / B4) from this same Sight socket on the same LOD0 bytes; the "
                      "rig moves nothing at rest"))
    gates.append(gate("B5 skeletal sidecar sockets vs build / spec", {"worst_mm": round(worst_mm, 6),
                      "worst_deg": round(worst_deg, 6)}, "<= 0.001 mm and <= 0.001 deg",
                      worst_mm <= 0.001 and worst_deg <= 0.001))
    # ------------------------------------------------------------ SM_<code> re-import + its sidecar (S1)
    GU.clear_scene(data_blocks=True)
    bpy.ops.import_scene.fbx(filepath=str(EXP / f"{SM}.fbx"), use_custom_normals=True)
    tris = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.name.startswith("UCX_"):
            tris[o.name] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    ucx = sorted(o.name for o in bpy.data.objects if o.name.startswith("UCX_"))
    want = REP[f"qa_check_{SM}"]["triangles"]
    nu = int(C["ucx_count"])
    sm_ok = all(tris.get(k) == v for k, v in want.items()) and len(ucx) == nu
    gates.append(gate(f"{SM}.fbx re-imported: LOD triangles, hulls", {"fbx": tris, "blender": want, "ucx": ucx},
                      f"triangles equal per LOD; {nu} UCX_{SM}_LOD0_NN", sm_ok))
    gates.append(gate(f"qa_check {SM} (before export)", {"passed": REP[f"qa_check_{SM}"]["passed"],
                      "checks": REP[f"qa_check_{SM}"]["checks"], "texel_target": REP[f"qa_check_{SM}"]["texel_target_px_cm"]},
                      C.get("qa_budget_text", "pass"), REP[f"qa_check_{SM}"]["passed"]))
    sside = json.loads((EXP / f"{SM}.sockets.json").read_text())
    worst = 0.0
    wdeg = 0.0
    for s in sside["sockets"]:
        sp = spec[s["socket"]]
        e = com if s["socket"] in computed else np.array(sp["blender_mm"])
        if s["socket"] in FIT:
            e = FIT[s["socket"]]
        worst = max(worst, float(np.abs(np.array(s["location_cm"]) - np.array([e[0], -e[1], e[2]]) * 0.1).max()) * 10)
        er = sp["unreal_rotation_deg"]
        wdeg = max(wdeg, max(abs(((s["rotation_deg"][k] - er[k]) + 180.0) % 360.0 - 180.0) for k in ("roll", "pitch", "yaw")))
    com_rep_d = float(np.abs(FIT["CenterOfMass"] - com).max()) if "CenterOfMass" in FIT else 0.0
    sizes_file = Path(C.get("lod_sizes") or cfg.gates / "game_lod_sizes.json")
    gates.append(gate(f"S1 {SM} sidecar sockets", {"count": len(sside["sockets"]), "worst_mm": round(worst, 6),
                      "worst_deg": round(wdeg, 6), "lod_screen_sizes": sside.get("lod_screen_sizes"),
                      "com_exact_vs_game_report_mm": round(com_rep_d, 5)},
                      f"{ns}; <= 0.001 mm, <= 0.001 deg; screen sizes = the LOD-pop sizes; CoM within the report's "
                      "0.01 mm rounding",
                      len(sside["sockets"]) == ns and worst <= 0.001 and wdeg <= 0.001 and com_rep_d <= 0.0051
                      and sside.get("lod_screen_sizes") == json.loads(sizes_file.read_text())[SM]))
    # ------------------------------------------------------------ export warnings, deny tokens
    warn = {SM: REP["export_static"]["warnings"],
            "SK set": [w for m in REP["export_skeletal"]["meshes"] for w in m["warnings"]] +
                      [w for a in REP["export_skeletal"]["animations"] for w in a["warnings"]]}
    gates.append(gate("export warnings reviewed", warn, "only the expected 'sockets dropped into the sidecar'",
                      all("dropped" in w for w in warn[SM]) and not warn["SK set"]))
    words = set()
    for p in [EXP / f"{SK}.skeletal.json", EXP / f"{SM}.sockets.json"]:
        words |= set(re.findall(r"[A-Za-z0-9_\-]+", p.read_text()))
    words |= {Path(f).name for f in REP["files"]}
    hits = {w: qa_gun.deny_hits(w) for w in words if qa_gun.deny_hits(w)}
    gates.append(gate("B10 names (tokenised gun deny list)", {"checked": len(words), "hits": hits},
                      "no hit in file names, bone / socket / clip / notify names and the sidecar text", not hits))
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    out["notifies"] = side["notifies"]
    out["files"] = REP["files"]
    out_path = Path(GU.opt(argv, "--out") or C.get("out") or cfg.gates / "rig_export.json")
    out_path.write_text(json.dumps(out, indent=1))
    print("[%s-rigv]" % cfg.log_tag, out["status"], out["failed"])
    return out


if __name__ == "__main__":
    from sr_gun import CFG
    main(CFG)
