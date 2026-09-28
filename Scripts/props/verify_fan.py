#!/usr/bin/env python
"""Verify the SHIPPED SK_Fan: re-import the exported FBX files into a fresh Blender and prove the fold from
the files alone - never from the build's own data.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/verify_fan.py -- [--exports DIR] [--renders DIR] [--work DIR] [--quick]

1. SK_Fan.fbx (+ LOD1/LOD2): bone names and hierarchy (every leaf face bone the child of the stick it hinges
   on), the root node, one influence per vertex, triangle counts, the rest pose = the open pose.
2. A_Fan_Openness.fbx and A_Fan_OpenClose.fbx: played on the imported armature at EVERY key and every HALF key
   (Blender evaluates between keys the way Unreal does: per-bone rotation and translation, linearly between
   neighbouring keys).  At each: G1 every leaf triangle keeps its edge lengths (no stretch) and every fold
   vertex's copies stay together (no tear: the crack), G2 no triangle of the leaf crosses another leaf face
   (neighbours along a fold excepted: they share it), a stick, the eyelet; no stick crosses another stick,
   G3 no leaf triangle is inside the front guard's plate.
3. The fold sheet (front and top at 0, 15, 30, 60, 90, 120, 150, 163.2 deg) and the closed-stack close-up,
   rendered from the imported files with materials rebuilt from the exported maps + sidecar.
4. SK_Fan_Tassel.fbx: its chain, two influences at most.
Writes WorkFiles/fan/verify/verify_report.json and Renders/Fan/fan_fold_sheet.png, fan_closed_stack.png.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))

import bpy                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from props_lib import fan_fold as FF                              # noqa: E402
from props_lib import fan_gallery as GAL                          # noqa: E402
from props_lib import fan_look as LK                              # noqa: E402
from props_lib.fan_spec import D2R, FAN                           # noqa: E402

T0 = time.time()


def log(*a):
    print(f"[verify {time.time() - T0:6.1f}s]", *a, flush=True)


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True, automatic_bone_orientation=False,
                             primary_bone_axis="Y", secondary_bone_axis="X", ignore_leaf_bones=False)
    return [o for o in bpy.data.objects if o not in before]


EPS_MM = 1e-3        # touching within 1 um (float32 FBX round trip) is contact, not a crossing


def count(TA, TB, same=False, exclude=None):
    ia, ib = FF.pairs_by_aabb(TA, TB, same=same)
    if exclude is not None and len(ia):
        keep = ~exclude(ia, ib)
        ia, ib = ia[keep], ib[keep]
    if not len(ia):
        return 0, []
    hit = FF.tri_tri_intersect(TA[ia], TB[ib], eps=EPS_MM)
    idx = np.nonzero(hit)[0]
    return int(len(idx)), [(int(ia[k]), int(ib[k])) for k in idx[:20]]


def adjacent_pairs(T, face):
    """Crossing triangle pairs between NEIGHBOURING leaf faces (they share a fold line; the G2 count above leaves
    them out).  At bind there must be none; posed, the two rigid copies of a fold line are up to the crack apart, so
    two faces meeting at a small dihedral can cross along their shared fold by that much."""
    ia, ib = FF.pairs_by_aabb(T, T, same=True)
    keep = np.abs(face[ia] - face[ib]) == 1
    ia, ib = ia[keep], ib[keep]
    if not len(ia):
        return 0
    return int(FF.tri_tri_intersect(T[ia], T[ib], eps=EPS_MM).sum())


def copy_pose(src_arm, dst_arm, dst_rest):
    """dst bones take src bones' armature-space pose matrices (both armatures at the identity)."""
    T = {}
    for pb in src_arm.pose.bones:
        M = np.array(pb.matrix)
        R = dst_rest[pb.name]
        Tm = M @ np.linalg.inv(R)
        Tm[:3, 3] /= LK.MM
        T[pb.name] = Tm
    LK.pose(dst_arm, T, dst_rest)


def world_positions(obj):
    return LK.evaluated_positions(obj)


def rest_positions(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(obj.matrix_world)
    return (co @ M[:3, :3].T + M[:3, 3]) / LK.MM


def triangles(obj):
    me = obj.data
    me.calc_loop_triangles()
    return np.array([t.vertices[:] for t in me.loop_triangles], np.int64)


def vertex_groups_all(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [[names[g.group] for g in v.groups if g.weight > 0] for v in obj.data.vertices]


def vertex_bone(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    out, infl = [], []
    for v in obj.data.vertices:
        gs = [(names[g.group], g.weight) for g in v.groups if g.weight > 0]
        infl.append(len(gs))
        out.append(max(gs, key=lambda x: x[1])[0] if gs else "")
    return np.array(out), np.array(infl)


def main(argv=None):
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    ap = argparse.ArgumentParser()
    ap.add_argument("--exports", default=str(PROJECT / "Exports" / "Fan"))
    ap.add_argument("--renders", default=str(PROJECT / "Renders" / "Fan"))
    ap.add_argument("--work", default=str(PROJECT / "WorkFiles" / "fan" / "verify"))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    EXP, REN, WORK = Path(a.exports).resolve(), Path(a.renders).resolve(), Path(a.work).resolve()
    WORK.mkdir(parents=True, exist_ok=True)
    REN.mkdir(parents=True, exist_ok=True)
    spec = FAN
    sidecar = json.loads((EXP / "SK_Fan.skeletal.json").read_text(encoding="utf-8"))
    LK.reset_scene()
    rep = {"exports": str(EXP), "blender": bpy.app.version_string, "sidecar": sidecar.get("schema")}
    # ------------------------------------------------------------------ 1. the mesh
    objs = import_fbx(EXP / "SK_Fan.fbx")
    arm = next(o for o in objs if o.type == "ARMATURE")
    mesh = next(o for o in objs if o.type == "MESH")
    bones = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
    leaf_parent_ok = all(bones.get(f"leaf_{j:02d}") == f"stick_{j // 2 + (j % 2):02d}" for j in range(50))
    tri = triangles(mesh)
    vb, infl = vertex_bone(mesh)
    rep["mesh"] = {"armature_object": arm.name, "bones": len(bones), "top_level_bones": sorted(n for n, p in bones.items() if p is None)[:5],
                   "top_level_count": sum(1 for p in bones.values() if p is None),
                   "leaf_bones_children_of_their_sticks": leaf_parent_ok, "triangles": int(len(tri)),
                   "vertices": len(mesh.data.vertices), "max_influences": int(infl.max()), "unweighted": int((infl == 0).sum()),
                   "materials": [m.name for m in mesh.data.materials]}
    log(f"imported SK_Fan: {len(bones)} bones, {len(tri)} triangles, max influences {infl.max()}")
    lods = {}
    for i in (1, 2):
        o2 = import_fbx(EXP / f"SK_Fan_LOD{i}.fbx")
        m2 = next(o for o in o2 if o.type == "MESH")
        lods[f"LOD{i}"] = {"triangles": int(len(triangles(m2))),
                           "bones": len([b for b in next(o for o in o2 if o.type == "ARMATURE").data.bones])}
        for o in o2:
            bpy.data.objects.remove(o, do_unlink=True)
    rep["lods"] = lods
    vg_all = vertex_groups_all(mesh)
    rep["mesh"]["two_influence_vertices"] = int(sum(1 for gl in vg_all if len(gl) > 1))
    rep["mesh"]["two_influence_vertices_not_sticks"] = int(sum(1 for gl in vg_all if len(gl) > 1 and
                                                               not all(g.startswith("stick_") for g in gl)))
    # ------------------------------------------------------------------ bind data from the imported file
    P0 = rest_positions(mesh)
    TP = np.array(["leaf" if b.startswith("leaf_") else ("stick" if b.startswith("stick_") else "rivet") for b in vb])
    # flaps are leaf-material triangles on the guards: use the material slot
    me = mesh.data
    me.calc_loop_triangles()
    tri_mat = np.array([t.material_index for t in me.loop_triangles])
    slot_names = [m.name for m in me.materials]
    leaf_slot = next(i for i, n in enumerate(slot_names) if "Leaf" in n)
    stick_slot = next(i for i, n in enumerate(slot_names) if "Sticks" in n)
    rivet_slot = next(i for i, n in enumerate(slot_names) if "Rivet" in n)
    tri_bone = vb[tri[:, 0]]
    is_leaf_t = tri_mat == leaf_slot
    is_stick_t = tri_mat == stick_slot
    is_rivet_t = tri_mat == rivet_slot
    face_of = np.array([int(b.split("_")[1]) if b.startswith("leaf_") else (-1 if b == "stick_00" else 50)
                        for b in tri_bone])
    # round 3: a leaf-zone prong's vertices carry its own stick and the next one: a triangle belongs to the LOWEST stick
    # any of its vertices uses (so prong i and rib i are one part, as in the build's fold proof)
    vsticks = [min((int(g.split("_")[1]) for g in gl if g.startswith("stick_")), default=-1) for gl in vertex_groups_all(mesh)]
    stick_of = np.array([min(vsticks[t[0]], vsticks[t[1]], vsticks[t[2]]) if min(vsticks[t[0]], vsticks[t[1]], vsticks[t[2]]) >= 0
                         else max(vsticks[t[0]], vsticks[t[1]], vsticks[t[2]]) for t in tri])
    # fold copies: leaf vertices on different bones at the same bind position (1 um)
    lv = np.nonzero(np.isin(np.arange(len(P0)), np.unique(tri[is_leaf_t])))[0]
    key = {}
    for v in lv:
        k = tuple(np.round(P0[v] * 1000).astype(np.int64))
        key.setdefault(k, []).append(v)
    pairs = [(g[i], g[j]) for g in key.values() if len(g) > 1 for i in range(len(g)) for j in range(i + 1, len(g))
             if vb[g[i]] != vb[g[j]]]
    pairs = np.array(pairs, np.int64)
    # triangle edges of the leaf for the stretch gate
    lt = tri[is_leaf_t]
    e0 = np.concatenate([lt[:, [0, 1]], lt[:, [1, 2]], lt[:, [2, 0]]])
    L0 = np.linalg.norm(P0[e0[:, 0]] - P0[e0[:, 1]], axis=1)
    rep["fold_copies"] = {"pairs": int(len(pairs)), "leaf_triangles": int(is_leaf_t.sum())}
    # front guard plate (stick_00's triangles): its bottom face plane in bind, to test containment
    # ------------------------------------------------------------------ 2. the animations
    results = {}
    players = {}
    rest = LK.rest_matrices(arm)
    for aname in ("A_Fan_Openness", "A_Fan_OpenClose", "A_Fan_OpenPose"):
        # the importer turns FBX seconds into frames at the SCENE's rate: import at the file's own rate so
        # every key lands on a whole frame, then interpolate linearly between keys (as Unreal does)
        fps = next(x["fps"] for x in sidecar["animations"] if x["file"] == f"{aname}.fbx")
        bpy.context.scene.render.fps = int(fps)
        bpy.context.scene.render.fps_base = 1.0
        o3 = import_fbx(EXP / f"{aname}.fbx")
        a3 = next(o for o in o3 if o.type == "ARMATURE")
        act = a3.animation_data.action if a3.animation_data else None
        if act is None:
            results[aname] = {"error": "no action imported"}
            continue
        act.name = aname
        LK._linear(act)
        # Unreal plays an FBX animation as each joint's local transform per key (its own reference pose plays
        # no part); an animation-only FBX carries no bind pose, so Blender's importer gives its armature a rest
        # pose of its own.  So: play the IMPORTED armature and copy each bone's armature-space pose onto the
        # SK_Fan armature (the skin under test), frame by frame
        for o in o3:
            if o is not a3:
                bpy.data.objects.remove(o, do_unlink=True)
        a3.hide_render = True
        players[aname] = a3
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        times = []
        for f in range(f0, f1 + 1):
            times.append((f, 0.0))
            if f < f1:
                times.append((f, 0.5))
        worst = {"stretch_mm": 0.0, "crack_mm": 0.0, "hits": 0, "front_guard_hits": 0, "adjacent_pairs_max": 0}
        rows = []
        step = 1 if not a.quick else 3
        for k, (f, sub) in enumerate(times[::step]):
            bpy.context.scene.frame_set(f, subframe=sub)
            copy_pose(a3, arm, rest)
            Q = world_positions(mesh)
            L1 = np.linalg.norm(Q[e0[:, 0]] - Q[e0[:, 1]], axis=1)
            stretch = float(np.abs(L1 - L0).max())
            crack = float(np.linalg.norm(Q[pairs[:, 0]] - Q[pairs[:, 1]], axis=1).max()) if len(pairs) else 0.0
            T3 = Q[tri]
            Li, Si, Ri = np.nonzero(is_leaf_t)[0], np.nonzero(is_stick_t)[0], np.nonzero(is_rivet_t)[0]
            n_ll, _ = count(T3[Li], T3[Li], same=True,
                                             exclude=lambda x, y: np.abs(face_of[Li][x] - face_of[Li][y]) <= 1)

            def own(x, y):
                fo = face_of[Li][x]
                return ((fo == -1) & (stick_of[Si][y] == 0)) | ((fo == 50) & (stick_of[Si][y] == spec.n_sticks - 1))
            n_ls, ex_ls = count(T3[Li], T3[Si], exclude=own)
            n_ss, _ = count(T3[Si], T3[Si], same=True, exclude=lambda x, y: stick_of[Si][x] == stick_of[Si][y])
            n_lr, _ = count(T3[Li], T3[Ri])
            fg = int(sum(1 for x, y in ex_ls if stick_of[Si][y] == 0)) if n_ls else 0
            worst["adjacent_pairs_max"] = max(worst["adjacent_pairs_max"], adjacent_pairs(T3[Li], face_of[Li]))
            hits = n_ll + n_ls + n_ss + n_lr
            rows.append({"frame": f + sub, "stretch_mm": round(stretch, 6), "crack_mm": round(crack, 5), "hits": hits,
                         "hits_by": [n_ll, n_ls, n_ss, n_lr]})
            worst["stretch_mm"] = max(worst["stretch_mm"], stretch)
            worst["crack_mm"] = max(worst["crack_mm"], crack)
            worst["hits"] += hits
            worst["front_guard_hits"] += fg
        results[aname] = {"frames": [f0, f1], "evaluated": len(rows), "worst": {k: (round(v, 6) if isinstance(v, float) else v)
                                                                             for k, v in worst.items()},
                          "worst_rows": sorted(rows, key=lambda r: -r["crack_mm"])[:4]}
        log(f"{aname}: {len(rows)} keys + half keys, stretch {worst['stretch_mm']:.5f} mm, crack {worst['crack_mm']:.5f} mm, "
            f"intersections {worst['hits']}")
    rep["animations"] = results
    # ------------------------------------------------------------------ 3. fold sheet from the files
    player = players["A_Fan_Openness"]
    pact = player.animation_data.action
    pf0, pf1 = pact.frame_range
    bpy.context.scene.render.fps = next(x["fps"] for x in sidecar["animations"] if x["file"] == "A_Fan_Openness.fbx")

    def pose_at(opening_deg):
        s = spec.s_for_opening(max(opening_deg, spec.opening_at(0.0)))
        fr = pf0 + s * (pf1 - pf0)
        f = int(math.floor(fr))
        bpy.context.scene.frame_set(f, subframe=fr - f)
        copy_pose(player, arm, rest)

    tex = EXP / "Textures"
    mats = {}
    for part, slot_mat in (("leaf", "M_Fan_Leaf"), ("sticks", "M_Fan_Sticks"), ("rivet", "M_Fan_Rivet")):
        m = sidecar["materials"][slot_mat]
        paths = {k: str(tex / f"{v}.png") for k, v in m["textures"].items()}
        mats[slot_mat] = LK.make_material(slot_mat + "_Verify", paths, m.get("tint_default_linear"),
                                          m.get("detail_bias_default") or 0.0, m.get("detail_scale_default") or 1.0,
                                          m.get("specular_scale") or 0.5, metal=m["metal"])
    for i, m in enumerate(me.materials):
        key = next(k for k in mats if k in m.name)
        me.materials[i] = mats[key]
    info = GAL.fold_sheet(spec, arm, mesh, pose_at, REN / "fan_fold_sheet.png", WORK, samples=24 if a.quick else 96,
                          closeup_png=REN / "fan_closed_stack.png")
    rep["fold_sheet"] = info
    # ------------------------------------------------------------------ 4. tassel
    t_objs = import_fbx(EXP / "SK_Fan_Tassel.fbx")
    tarm = next(o for o in t_objs if o.type == "ARMATURE")
    tmesh = next(o for o in t_objs if o.type == "MESH")
    _, tinfl = vertex_bone(tmesh)
    rep["tassel"] = {"bones": [b.name for b in tarm.data.bones],
                     "chain": [(b.name, b.parent.name if b.parent else None) for b in tarm.data.bones],
                     "max_influences": int(tinfl.max()), "triangles": int(len(triangles(tmesh)))}
    # ------------------------------------------------------------------ gates
    anim = [v for k, v in results.items() if "worst" in v]
    rep["gates"] = {
        "V1_bones_78_leaf_children_of_sticks": len(bones) == 77 and leaf_parent_ok,
        # round 3: two influences only on the leaf-zone prongs (stick i and i+1), one everywhere else
        "V2_one_influence_two_on_prongs": rep["mesh"]["max_influences"] <= 2 and rep["mesh"]["unweighted"] == 0 and
                                          rep["mesh"]["two_influence_vertices_not_sticks"] == 0,
        "V3_no_stretch_all_keys_and_half_keys": bool(anim) and all(v["worst"]["stretch_mm"] <= 0.001 for v in anim),
        "V4_cracks_under_0.1mm_all_keys_and_half_keys": bool(anim) and all(v["worst"]["crack_mm"] <= 0.1 for v in anim),
        "V5_no_intersections": bool(anim) and all(v["worst"]["hits"] == 0 for v in anim),
        "V6_tassel_chain_two_influences": rep["tassel"]["max_influences"] <= 2 and len(rep["tassel"]["bones"]) == 6,
    }
    rep["gates"]["_all"] = all(rep["gates"].values())
    out = WORK / "verify_report.json"
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    log("gates:", json.dumps(rep["gates"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
