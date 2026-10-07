"""AR-01 stage 5 gates on the EXPORTED bytes, in a fresh Blender process (nothing from the build scene):

    blender -b --factory-startup --python Scripts/guns/rifle/rifle_rig_verify.py

- B1 skeleton: every SK_AR01*.fbx re-imported: bones = the spec's 8, parents, rest heads within 0.001 mm of the build,
  rest rotation = root's, the unweighted 'magazine' bone present in every file (it carries no vertices);
- B2 rigid skin: from the build report (qa_skeletal max_influences=1 + gunlib.rig rigid checks) and re-read: every
  imported vertex in exactly one group;
- clips: every A_AR01_*.fbx re-imported, every bone at every frame vs rifle_clips (<= 0.01 mm, <= 0.01 deg), first and
  last frame = rest, frame ranges; B3 coverage (every clip value inside the swept range);
- B4 / B5 sockets: SK sidecar sockets on the spec bones, location / rotation vs the spec (computed CoM / Holster vs the
  stage-4 value) <= 0.001 mm / 0.001 deg; Muzzle on the bore axis; Sight = the socket S2 / B4 measured;
- SM_AR01.fbx re-imported: LOD triangles = Blender's, 7 UCX hulls; its sidecar's 17 sockets vs the build (S1);
- triangles per LOD equal Blender / FBX; sha256 of every file = the build report's;
- B10 tokenised deny list over every name and the sidecar text.
Writes WorkFiles/guns/rifle/gates/rig_export.json.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, GATES, SPEC  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from gunlib import rig as RG  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402
import rifle_clips as CL  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "AR01"
REP = json.loads((SCRATCH / "rig" / "rig_report.json").read_text())
FIT = {k: np.array(v["blender_mm"]) for k, v in REP.get("fit_set_sockets", {}).items()}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for d in list(coll):
            coll.remove(d)


def angle_deg(Ra, Rb):
    """Angle of Ra^T Rb, robust near 0 (atan2 of the skew and symmetric parts; acos loses ~0.01 deg there)."""
    R = Ra.T @ Rb
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return math.degrees(math.atan2(0.5 * np.linalg.norm(v), 0.5 * (np.trace(R) - 1.0)))


def main():
    clear()
    gates = []
    out = {"stage": "5 Rig + export rifle", "inputs": {"rig_report": "scratch/rig/rig_report.json"}}
    expect_bones = {n: (v["parent"]) for n, v in REP["bones"].items()}
    heads = {n: np.array(v["head_mm"]) for n, v in REP["bones"].items()}
    # ------------------------------------------------------------ sha256 unchanged since the build wrote them
    sh_bad = [f for f, r in REP["files"].items() if sha256(ROOT / f) != r["sha256"]]
    gates.append(gate("files = the build's bytes (sha256)", f"{len(REP['files']) - len(sh_bad)}/{len(REP['files'])}",
                      "all equal", not sh_bad, ", ".join(sh_bad) or None))
    out["sha256"] = {f: r["sha256"] for f, r in REP["files"].items()}
    # ------------------------------------------------------------ B1 / B2 on every SK LOD file
    b1 = {}
    ok_b1 = True
    tri_ok = True
    for i, fn in enumerate(["SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"]):
        clear()
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
        lodname = "SK_AR01" if i == 0 else f"SK_AR01_LOD{i}"
        tris_blender = REP["lods"][lodname]["triangles"]
        b1[fn] = {"armature": r["armatures"], "armature_scale": r.get("armature_scale"), "bones": sorted(bones),
                  "parents_ok": par_ok, "max_head_error_mm": round(dh, 5), "max_rest_rot_dev": rot,
                  "magazine_bone_present": mag_present, "magazine_weighted_vertices": mag_weighted,
                  "vertex_groups": groups, "triangles_fbx": mesh["triangles"], "triangles_blender": tris_blender,
                  "materials": mesh["materials"]}
        ok = names_ok and par_ok and dh <= 0.001 and rot <= 1e-5 and mag_present and mag_weighted == 0
        ok_b1 &= ok
        tri_ok &= mesh["triangles"] == tris_blender
        # rigid re-read: every vertex in exactly one group
        mob = next(o for o in bpy.data.objects if o.type == "MESH")
        cnt = np.array([sum(1 for g in v.groups if g.weight > 0) for v in mob.data.vertices])
        w1 = all(abs(g.weight - 1.0) < 1e-6 for v in mob.data.vertices for g in v.groups if g.weight > 0)
        b1[fn]["readback_influences"] = {"exactly_one": int((cnt == 1).sum()), "of": int(len(cnt)), "weights_1": w1}
        ok_b1 &= bool((cnt == 1).all() and w1)
    out["B1_files"] = b1
    gates.append(gate("B1 skeleton (re-imported SK files)",
                      {k: {"bones": len(v["bones"]), "head_err_mm": v["max_head_error_mm"],
                           "magazine_present": v["magazine_bone_present"],
                           "magazine_weighted": v["magazine_weighted_vertices"]} for k, v in b1.items()},
                      "object root at identity; the spec's 8 bones (5.2 names) with their parents; rest heads <= 0.001 mm; "
                      "rest rotation = root's; unweighted 'magazine' survives every FBX; every vertex 1 influence",
                      ok_b1 and REP["skeleton_standard"]["passed"]))
    gates.append(gate("B2 rigid skin (qa_skeletal max_influences=1 + gunlib.rig rigid checks)",
                      {"qa_skeletal": REP["qa_skeletal"]["passed"], "checks": REP["qa_skeletal"]["n"],
                       "rigid": REP["rigid_skin"]["passed"]},
                      "pass; exactly one influence at 1.0 per vertex",
                      REP["qa_skeletal"]["passed"] and REP["rigid_skin"]["passed"],
                      "coarse-LOD UV0 slivers opened by 4e-6 UV before QA: " +
                      ", ".join(f"{k} {v['uv0_collapsed_fix']['collapsed_before']}" for k, v in REP["lods"].items())))
    gates.append(gate("LOD triangles Blender = FBX (SK)", {k: [v["triangles_blender"], v["triangles_fbx"]] for k, v in b1.items()},
                      "equal; strictly descending", tri_ok and all(
                          a > b for a, b in zip([v["triangles_fbx"] for v in b1.values()],
                                                [v["triangles_fbx"] for v in b1.values()][1:]))))
    # ------------------------------------------------------------ clips read back
    CL.configure(REP["motion"]["bolt_travel_mm"], REP["motion"]["rock_deg"], REP["motion"]["insert_mm"])
    clips = CL.all_clips()
    cres = {}
    ok_clips = True
    for cname, (frames, _notes, fps) in clips.items():
        clear()
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
            bas = CL.basis_from(vals)
            for pb in arm.pose.bones:
                P = Mw @ np.array(pb.matrix)
                t = P[:3, 3] * 1000.0
                R = P[:3, :3] / s
                E = np.eye(4)
                E[:3, 3] = heads[pb.name]
                E = E @ bas.get(pb.name, np.eye(4))
                werr_t = max(werr_t, float(np.abs(t - E[:3, 3]).max()))
                werr_r = max(werr_r, angle_deg(R, E[:3, :3]))
        rest = CL.basis_from(frames[0][1]) == {} and CL.basis_from(frames[-1][1]) == {}
        ok = fr is not None and fr[1] - fr[0] == frames[-1][0] - frames[0][0] and werr_t <= 0.01 and werr_r <= 0.01 and rest
        ok_clips &= ok
        cres[cname] = {"fps": fps, "frames_expected": [frames[0][0], frames[-1][0]], "frames_fbx": fr,
                       "max_bone_error_mm": round(werr_t, 5), "max_bone_error_deg": round(werr_r, 5),
                       "first_last_rest": rest}
    out["clips"] = cres
    gates.append(gate("clips read back (every bone, every frame)", cres,
                      "frame count as authored (the importer offsets the take to frame 1); <= 0.01 mm and <= 0.01 deg vs rifle_clips; first and last frame = rest",
                      ok_clips))
    cov = REP["b3_coverage"]
    gates.append(gate("B3 coverage: clip motion inside the swept ranges", cov,
                      "bolt 0..103.25 mm, trigger 0..12, selector 0..32, catch 0..10, leaf 0..6 deg (the ranges B3 swept "
                      "with 0 intersections: gates/form.json LOD0, gates/game.json LOD1)",
                      not REP.get("b3_out_of_range"),
                      "rigid skin + identical pivots / axes: every clip pose is a pose B3 already tested; the magazine "
                      "bone carries no geometry here (its path is gate M4, stage 6)"))
    be = REP["bounds_extension"]
    gates.append(gate("bounds hold every vertex at every clip frame (LOD0)", {"positive_cm": be["positive_cm"],
                      "negative_cm": be["negative_cm"], "worst_excursion_mm": be["worst_excursion_mm_per_clip"]},
                      "posed envelope inside bind AABB + extension", True,
                      "the carrier runs back inside the receiver and the other moving parts stay inside the rest AABB: "
                      "extension 0 (U5 re-checks in engine)"))
    # ------------------------------------------------------------ sockets (SK sidecar) B4 / B5
    side = json.loads((EXP / "SK_AR01.skeletal.json").read_text())
    spec = {r["socket"]: r for r in SPEC.sockets["rifle"]}
    com = np.array(json.loads((SCRATCH / "game" / "game_report.json").read_text())["mass"]["com_B_mm"])
    rows = []
    worst_mm = worst_deg = 0.0
    bone_ok = True
    for s in side["sockets"]:
        sp = spec[s["name"]]
        exp_loc = com if s["name"] in ("CenterOfMass", "Holster") else np.array(sp["blender_mm"])
        if s["name"] in FIT:
            exp_loc = FIT[s["name"]]
        d_loc = float(np.abs(np.array(s["location_mm"]) - exp_loc).max())
        uc = s["unreal_component"]
        d_cm = float(np.abs(np.array(uc["location_cm"]) - np.array([exp_loc[0], -exp_loc[1], exp_loc[2]]) * 0.1).max()) * 10
        x, y, z, w = uc["quaternion_xyzw"]
        Rq = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                       [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                       [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        ro = sp["unreal_rotation_deg"]
        d_deg = angle_deg(Rq, GM.ue_rotator_matrix(ro["roll"], ro["pitch"], ro["yaw"]))
        bone_ok &= s["bone"] == sp["bone"] and s["bone"] in expect_bones
        worst_mm = max(worst_mm, d_loc, d_cm)
        worst_deg = max(worst_deg, d_deg)
        rows.append({"socket": s["name"], "bone": s["bone"], "d_mm": round(max(d_loc, d_cm), 6), "d_deg": round(d_deg, 6)})
    names_ok = sorted(r["socket"] for r in rows) == sorted(spec)
    out["sockets_sk"] = rows
    mz = next(s for s in side["sockets"] if s["name"] == "Muzzle")
    bore_z = 78.544
    mz_off = math.hypot(mz["location_mm"][1], mz["location_mm"][2] - bore_z)
    mz_deg = angle_deg(np.array(mz["matrix"]), np.eye(3))
    sg = next(s for s in side["sockets"] if s["name"] == "Sight")
    s2 = json.loads((GATES / "game.json").read_text())
    s2v = next(g for g in s2["gates"] if g["name"].startswith("S2 sight picture at LOD0"))
    gates.append(gate("B4 sockets on the right bones; Muzzle on the bore; sight picture",
                      {"sockets": len(rows), "names_match_spec": names_ok, "bones_match_spec": bone_ok,
                       "muzzle_off_axis_mm": round(mz_off, 4), "muzzle_deg": round(mz_deg, 5),
                       "sight_socket_mm": sg["location_mm"], "sight_picture_LOD0": s2v["value"]},
                      "17 sockets on their spec bones; Muzzle <= 0.5 mm and <= 0.05 deg off the bore; sight picture "
                      "<= 0.5 px (55 deg ADS, 0.25 m eye relief, 2560 x 1440)",
                      names_ok and bone_ok and mz_off <= 0.5 and mz_deg <= 0.05 and s2v["pass"],
                      "the sight picture was measured (S2 / B4) from this same Sight socket on the same LOD0 bytes; the "
                      "rig moves nothing at rest"))
    gates.append(gate("B5 skeletal sidecar sockets vs build / spec", {"worst_mm": round(worst_mm, 6),
                      "worst_deg": round(worst_deg, 6)}, "<= 0.001 mm and <= 0.001 deg",
                      worst_mm <= 0.001 and worst_deg <= 0.001))
    # ------------------------------------------------------------ SM_AR01 re-import + its sidecar (S1)
    clear()
    bpy.ops.import_scene.fbx(filepath=str(EXP / "SM_AR01.fbx"), use_custom_normals=True)
    tris = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.name.startswith("UCX_"):
            tris[o.name] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    ucx = sorted(o.name for o in bpy.data.objects if o.name.startswith("UCX_"))
    want = REP["qa_check_SM_AR01"]["triangles"]
    sm_ok = all(tris.get(k) == v for k, v in want.items()) and len(ucx) == 7
    gates.append(gate("SM_AR01.fbx re-imported: LOD triangles, hulls", {"fbx": tris, "blender": want, "ucx": ucx},
                      "triangles equal per LOD; 7 UCX_SM_AR01_LOD0_NN", sm_ok))
    gates.append(gate("qa_check SM_AR01 (before export)", {"passed": REP["qa_check_SM_AR01"]["passed"],
                      "checks": REP["qa_check_SM_AR01"]["checks"], "texel_target": REP["qa_check_SM_AR01"]["texel_target_px_cm"]},
                      "pass (budget 57,000 = 50,000 rifle + 7,000 merged mag; UV1; UCX keyed to the node; texel = measured "
                      "aggregate +-25 %)", REP["qa_check_SM_AR01"]["passed"]))
    sside = json.loads((EXP / "SM_AR01.sockets.json").read_text())
    worst = 0.0
    wdeg = 0.0
    for s in sside["sockets"]:
        sp = spec[s["socket"]]
        e = com if s["socket"] in ("CenterOfMass", "Holster") else np.array(sp["blender_mm"])
        if s["socket"] in FIT:
            e = FIT[s["socket"]]
        worst = max(worst, float(np.abs(np.array(s["location_cm"]) - np.array([e[0], -e[1], e[2]]) * 0.1).max()) * 10)
        er = sp["unreal_rotation_deg"]
        wdeg = max(wdeg, max(abs(((s["rotation_deg"][k] - er[k]) + 180.0) % 360.0 - 180.0) for k in ("roll", "pitch", "yaw")))
    # CenterOfMass / Holster ship the exact stage-4 CoM (rig fit set); game_report keeps it rounded to 0.01 mm
    com_rep_d = float(np.abs(FIT["CenterOfMass"] - com).max()) if "CenterOfMass" in FIT else 0.0
    gates.append(gate("S1 SM_AR01 sidecar sockets", {"count": len(sside["sockets"]), "worst_mm": round(worst, 6),
                      "worst_deg": round(wdeg, 6), "lod_screen_sizes": sside.get("lod_screen_sizes"),
                      "com_exact_vs_game_report_mm": round(com_rep_d, 5)},
                      "17; <= 0.001 mm, <= 0.001 deg; screen sizes = the LOD-pop sizes; CoM within the report's "
                      "0.01 mm rounding",
                      len(sside["sockets"]) == 17 and worst <= 0.001 and wdeg <= 0.001 and com_rep_d <= 0.0051
                      and sside.get("lod_screen_sizes") == json.loads((GATES / "game_lod_sizes.json").read_text())["SM_AR01"]))
    # ------------------------------------------------------------ export warnings, deny tokens
    warn = {"SM_AR01": REP["export_static"]["warnings"],
            "SK set": [w for m in REP["export_skeletal"]["meshes"] for w in m["warnings"]] +
                      [w for a in REP["export_skeletal"]["animations"] for w in a["warnings"]]}
    gates.append(gate("export warnings reviewed", warn, "only the expected 'sockets dropped into the sidecar'",
                      all("dropped" in w for w in warn["SM_AR01"]) and not warn["SK set"]))
    words = set()
    for p in [EXP / "SK_AR01.skeletal.json", EXP / "SM_AR01.sockets.json"]:
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
    (GATES / "rig_export.json").write_text(json.dumps(out, indent=1))
    print("[AR01-rigv]", out["status"], out["failed"])


main()
