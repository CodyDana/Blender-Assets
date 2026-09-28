"""Regression: the garment pipeline's BlackCloak against the 2026-09-26 one-off MetaHuman fit (read-only).

    # fit stage: the pipeline work file vs the one-off's fitted sculpt, piece by piece, vertex by vertex
    blender -b <pipeline BlackCloak_MH_garment.blend> --factory-startup --python Scripts/garments/regress_blackcloak.py -- \
        --stage fit --oneoff WorkFiles/BlackCloak_MH/BlackCloak_MH_fit.blend --json <out.json>
    # fbx stage: both exported FBX files imported into one empty scene
    blender -b --factory-startup --python Scripts/garments/regress_blackcloak.py -- \
        --stage fbx --oneoff <SKM_BlackCloak_MH.fbx> --pipeline <SK_BlackCloak_MH.fbx> --json <out.json>

FBX stage compares: bone set and world rest matrices; vertex / triangle counts per material section; positions
(index to index when the counts agree, and nearest-vertex distance both ways, i.e. the Hausdorff distance); skin
weights at matched vertices; bones used; PinMask colours; UVs. Both files go through Blender's FBX importer with the
same settings, so any difference is in the files, not the import.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import kdtree


def coords(obj, world=True):
    array = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", array)
    array = array.reshape(-1, 3)
    if world:
        matrix = np.array(obj.matrix_world)
        array = array @ matrix[:3, :3].T + matrix[:3, 3]
    return array


def stats_mm(delta):
    if not len(delta):
        return {}
    return {"max": round(float(delta.max()) * 1000, 4), "mean": round(float(delta.mean()) * 1000, 5),
            "p99": round(float(np.percentile(delta, 99)) * 1000, 4),
            "over_0.01mm": int(np.count_nonzero(delta > 1e-5)), "over_1mm": int(np.count_nonzero(delta > 1e-3))}


def nearest(a, b):
    tree = kdtree.KDTree(len(b))
    for i, p in enumerate(b):
        tree.insert(p, i)
    tree.balance()
    dist = np.empty(len(a))
    index = np.empty(len(a), dtype=np.int64)
    for i, p in enumerate(a):
        _co, j, d = tree.find(p)
        dist[i], index[i] = d, j
    return dist, index


def stage_fit(oneoff_path):
    pieces = sorted([o for c in ("GARMENT", "GARMENT_SIM") for o in bpy.data.collections[c].objects], key=lambda o: o.name)
    with bpy.data.libraries.load(oneoff_path, link=False) as (source, target):
        target.objects = [name for name in source.objects if name.startswith(("Cloak_", "Clasp_"))]
    theirs = {o.name.rsplit(".", 1)[0]: o for o in target.objects}
    out = {"pieces": {}}
    all_delta = []
    for obj in pieces:
        other = theirs[obj.name]
        a, b = coords(obj), coords(other)
        entry = {"vertices": [len(a), len(b)]}
        if len(a) == len(b):
            delta = np.linalg.norm(a - b, axis=1)
            entry.update(stats_mm(delta))
            all_delta.append(delta)
        out["pieces"][obj.name] = entry
    if all_delta:
        out["all"] = stats_mm(np.concatenate(all_delta))
    return out


def import_one(path, tag):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, global_scale=1.0, automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH")
    return {"armature": arm, "mesh": mesh, "tag": tag}


def weights_of(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0} for v in obj.data.vertices]


def sections(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    per = {}
    for tri in mesh.loop_triangles:
        name = mesh.materials[tri.material_index].name.split(".")[0] if mesh.materials[tri.material_index] else None
        per.setdefault(name, set()).update(tri.vertices)
    tri_counts = {}
    for tri in mesh.loop_triangles:
        name = mesh.materials[tri.material_index].name.split(".")[0]
        tri_counts[name] = tri_counts.get(name, 0) + 1
    return per, tri_counts


def stage_fbx(oneoff, pipeline):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    a = import_one(oneoff, "oneoff")
    b = import_one(pipeline, "pipeline")
    out = {}
    # skeleton
    bones_a = {bone.name: a["armature"].matrix_world @ bone.matrix_local for bone in a["armature"].data.bones}
    bones_b = {bone.name: b["armature"].matrix_world @ bone.matrix_local for bone in b["armature"].data.bones}
    worst_t = worst_r = 0.0
    for name in set(bones_a) & set(bones_b):
        ma, mb = bones_a[name], bones_b[name]
        worst_t = max(worst_t, (ma.translation - mb.translation).length)
        # normalise first: the one-off armature carries a 0.01 object scale, and to_quaternion() of a scaled
        # matrix is not a pure rotation
        qa_, qb = ma.to_3x3().normalized().to_quaternion(), mb.to_3x3().normalized().to_quaternion()
        worst_r = max(worst_r, np.degrees(qa_.rotation_difference(qb).angle))
    out["skeleton"] = {"bones": [len(bones_a), len(bones_b)], "same_names": set(bones_a) == set(bones_b),
                       "armature_objects": [a["armature"].name, b["armature"].name],
                       "max_head_delta_mm": round(worst_t * 1000, 5), "max_rotation_delta_deg": round(worst_r, 5)}
    # mesh
    ma, mb = a["mesh"], b["mesh"]
    ca, cb = coords(ma), coords(mb)
    sa, ta = sections(ma)
    sb, tb = sections(mb)
    out["mesh"] = {"names": [ma.name, mb.name], "vertices": [len(ca), len(cb)],
                   "triangles": [sum(ta.values()), sum(tb.values())],
                   "polygons": [len(ma.data.polygons), len(mb.data.polygons)],
                   "section_triangles": {"oneoff": ta, "pipeline": tb},
                   "slots": [[m.name for m in ma.data.materials], [m.name for m in mb.data.materials]]}
    if len(ca) == len(cb):
        out["mesh"]["index_to_index"] = stats_mm(np.linalg.norm(ca - cb, axis=1))
    d_ab, i_ab = nearest(ca, cb)
    d_ba, _ = nearest(cb, ca)
    out["mesh"]["nearest_oneoff_to_pipeline"] = stats_mm(d_ab)
    out["mesh"]["nearest_pipeline_to_oneoff"] = stats_mm(d_ba)
    out["mesh"]["hausdorff_mm"] = round(max(float(d_ab.max()), float(d_ba.max())) * 1000, 4)
    per_section = {}
    for name in set(sa) & set(sb):
        ia, ib = np.array(sorted(sa[name])), np.array(sorted(sb[name]))
        d1, _ = nearest(ca[ia], cb[ib])
        d2, _ = nearest(cb[ib], ca[ia])
        per_section[name] = {"vertices": [len(ia), len(ib)], "hausdorff_mm": round(max(d1.max(), d2.max()) * 1000, 4),
                             "mean_mm": round(float(np.concatenate([d1, d2]).mean()) * 1000, 5)}
    out["mesh"]["per_section"] = per_section
    far = np.nonzero(d_ab > 1e-5)[0]
    if len(far):
        section_of = {}
        for name, verts in sa.items():
            for v in verts:
                section_of[v] = name
        out["mesh"]["differing_vertices"] = {
            "count": int(len(far)), "sections": sorted({section_of.get(int(i)) for i in far}),
            "bbox_min": [round(float(v), 3) for v in ca[far].min(axis=0)],
            "bbox_max": [round(float(v), 3) for v in ca[far].max(axis=0)]}
    # weights at matched vertices (nearest pipeline vertex for every one-off vertex)
    wa, wb = weights_of(ma), weights_of(mb)
    worst_w = 0.0
    mismatched = 0
    for i, j in enumerate(i_ab):
        if d_ab[i] > 1e-5:
            continue
        keys = set(wa[i]) | set(wb[j])
        diff = max(abs(wa[i].get(k, 0.0) - wb[j].get(k, 0.0)) for k in keys) if keys else 0.0
        worst_w = max(worst_w, diff)
        mismatched += diff > 1e-3
    used_a = {}
    for w in wa:
        for k in w:
            used_a[k] = used_a.get(k, 0) + 1
    used_b = {}
    for w in wb:
        for k in w:
            used_b[k] = used_b.get(k, 0) + 1
    out["weights"] = {"max_abs_diff_at_matched": round(worst_w, 6), "matched_vertices_differing_over_1e-3": mismatched,
                      "bones_used": {"oneoff": used_a, "pipeline": used_b},
                      "max_influences": [max(len(w) for w in wa), max(len(w) for w in wb)]}
    # colours and UVs (corner domain; compare per matched vertex through the first corner of each vertex)
    def first_corner_values(obj, getter):
        values = {}
        for loop in obj.data.loops:
            values.setdefault(loop.vertex_index, getter(loop.index))
        return values
    col_a, col_b = ma.data.color_attributes.get("PinMask"), mb.data.color_attributes.get("PinMask")
    out["pin_mask"] = {"present": [col_a is not None, col_b is not None],
                       "active": [getattr(ma.data.color_attributes.active_color, "name", None),
                                  getattr(mb.data.color_attributes.active_color, "name", None)]}
    if col_a is not None and col_b is not None:
        pa = first_corner_values(ma, lambda i: col_a.data[i].color[0])
        pb = first_corner_values(mb, lambda i: col_b.data[i].color[0])
        diffs = [abs(pa[i] - pb[j]) for i, j in enumerate(i_ab) if d_ab[i] <= 1e-5]
        out["pin_mask"]["max_red_diff_at_matched"] = round(max(diffs), 5) if diffs else None
        out["pin_mask"]["pinned_vertices"] = [sum(1 for v in pa.values() if v > 0.5), sum(1 for v in pb.values() if v > 0.5)]
    uva, uvb = ma.data.uv_layers[0], mb.data.uv_layers[0]
    ua = first_corner_values(ma, lambda i: tuple(uva.data[i].uv))
    ub = first_corner_values(mb, lambda i: tuple(uvb.data[i].uv))
    uv_diff = [max(abs(ua[i][0] - ub[j][0]), abs(ua[i][1] - ub[j][1])) for i, j in enumerate(i_ab) if d_ab[i] <= 1e-5]
    out["uv"] = {"max_diff_at_matched": round(max(uv_diff), 6) if uv_diff else None,
                 "note": "first corner per vertex; a seam vertex may pick a different corner in each file"}
    out["matched_vertices_within_0.01mm"] = int(np.count_nonzero(d_ab <= 1e-5))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("fit", "fbx"), required=True)
    parser.add_argument("--oneoff", required=True)
    parser.add_argument("--pipeline", default=None)
    parser.add_argument("--json", required=True)
    args = parser.parse_args(argv)
    result = stage_fit(args.oneoff) if args.stage == "fit" else stage_fbx(args.oneoff, args.pipeline)
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print("REGRESS_DONE", args.stage, args.json)


if __name__ == "__main__":
    main()
