"""Character-fit review (read-only): what the MetaHuman fit changed vs the original sculpt, and cloth readiness of the
original. Run on the COPY of BlackCloak_MH_fit.blend; loads the original's objects from the COPY of Assets/BlackCloak.blend.

blender -b copies/MH_fit_copy.blend --factory-startup --python inspect_blends.py -- <orig copy> <pin csv> <out.json>
Never saves.
"""
import csv
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
ORIG, CSV, OUT = args[0], args[1], args[2]
dg = bpy.context.evaluated_depsgraph_get()


def world_coords(obj, evaluated=False):
    if evaluated:
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.array([obj.matrix_world @ v.co for v in me.vertices])
        polys = [tuple(p.vertices) for p in me.polygons]
        tris = sum(len(p) - 2 for p in polys)
        ev.to_mesh_clear()
        return co, polys, tris
    me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3], [tuple(p.vertices) for p in me.polygons], sum(len(p.vertices) - 2 for p in me.polygons)


def describe(obj):
    d = {"type": obj.type, "collections": [c.name for c in obj.users_collection], "parent": obj.parent.name if obj.parent else None}
    if obj.type != "MESH":
        return d
    me = obj.data
    co, polys, tris = world_coords(obj)
    _eco, _ep, etris = world_coords(obj, evaluated=True)
    mods = []
    for m in obj.modifiers:
        e = {"type": m.type, "name": m.name, "show_render": m.show_render}
        if m.type == "SOLIDIFY":
            e.update(thickness_m=round(m.thickness, 5), offset=m.offset, even=m.use_even_offset, rim=m.use_rim)
        if m.type == "SUBSURF":
            e.update(levels=m.levels, render_levels=m.render_levels)
        if m.type == "ARMATURE":
            e.update(object=m.object.name if m.object else None)
        mods.append(e)
    groups = {}
    for g in obj.vertex_groups:
        groups[g.name] = 0
    idx = {g.index: g.name for g in obj.vertex_groups}
    wsum = {}
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 0:
                groups[idx[g.group]] += 1
    d.update(vertices=len(me.vertices), base_tris=tris, evaluated_tris=etris, modifiers=mods,
             materials=[m.name if m else None for m in me.materials], uv_layers=[u.name for u in me.uv_layers],
             colour_attrs=[(c.name, c.domain, c.data_type) for c in me.color_attributes],
             vertex_groups=groups, z_range_m=[round(float(co[:, 2].min()), 3), round(float(co[:, 2].max()), 3)],
             y_range_m=[round(float(co[:, 1].min()), 3), round(float(co[:, 1].max()), 3)],
             x_range_m=[round(float(co[:, 0].min()), 3), round(float(co[:, 0].max()), 3)],
             custom_props={k: str(obj[k]) for k in obj.keys()})
    return d


out = {"fit_file": bpy.data.filepath}
out["fit_collections"] = {c.name: [o.name for o in c.objects] for c in bpy.data.collections}
out["fit_objects"] = {o.name: describe(o) for o in bpy.data.objects}
out["fit_armatures"] = [o.name for o in bpy.data.objects if o.type == "ARMATURE"]

# ---- load the original sculpt's objects (suffix .orig) ----
with bpy.data.libraries.load(ORIG, link=False) as (src, dst):
    dst.objects = list(src.objects)
    dst.collections = list(src.collections)
orig = {}
for o in dst.objects:
    if o is None:
        continue
    base = o.name
    o.name = "ORIG__" + base.split(".")[0]
    orig[base.split(".")[0]] = o
    bpy.context.scene.collection.objects.link(o)
    o.hide_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
out["orig_collections"] = {c.name: [o.name.replace("ORIG__", "") for o in c.objects] for c in dst.collections if c}
out["orig_objects"] = {k: describe(o) for k, o in orig.items()}

# ---- per-piece displacement fit vs original ----
disp = {}
for name, o in orig.items():
    f = bpy.data.objects.get(name)
    if o.type != "MESH" or f is None or f.type != "MESH":
        continue
    a, _, _ = world_coords(o)
    b, _, _ = world_coords(f)
    if len(a) != len(b):
        disp[name] = {"vertices": [len(a), len(b)], "topology_changed": True}
        continue
    same_topo = [tuple(p.vertices) for p in o.data.polygons] == [tuple(p.vertices) for p in f.data.polygons]
    dd = np.linalg.norm(b - a, axis=1)
    dz = b[:, 2] - a[:, 2]
    disp[name] = {"vertices": len(a), "same_topology": same_topo, "max_cm": round(float(dd.max() * 100), 2),
                  "mean_cm": round(float(dd.mean() * 100), 2), "p95_cm": round(float(np.percentile(dd, 95) * 100), 2),
                  "mean_dz_cm": round(float(dz.mean() * 100), 2)}
out["fit_vs_orig_displacement"] = disp

# ---- pin CSV vs the original's CLOTH_Pin groups ----
rows = {}
with open(CSV, newline="") as fh:
    for r in csv.DictReader(fh):
        rows.setdefault(r["blender_object"], []).append((int(r["blender_vertex"]), float(r["pin_weight"])))
pin = {}
for name, lst in rows.items():
    o = orig.get(name)
    e = {"csv_rows": len(lst), "csv_max_index": max(i for i, _ in lst), "csv_pinned_gt0": sum(1 for _, w in lst if w > 0),
         "csv_weight_eq_1": sum(1 for _, w in lst if w >= 0.999)}
    if o is not None and o.type == "MESH":
        e["base_vertices"] = len(o.data.vertices)
        e["evaluated_vertices"] = len(o.evaluated_get(dg).data.vertices)
        g = o.vertex_groups.get("CLOTH_Pin")
        if g:
            gw = np.zeros(len(o.data.vertices))
            for v in o.data.vertices:
                for gg in v.groups:
                    if gg.group == g.index:
                        gw[v.index] = gg.weight
            cw = np.zeros(len(o.data.vertices))
            for i, w in lst:
                if i < len(cw):
                    cw[i] = w
            e["csv_vs_CLOTH_Pin_max_abs_diff"] = round(float(np.abs(gw - cw).max()), 4)
            co, _, _ = world_coords(o)
            pinned = gw > 0
            e["pinned_z_range_m"] = [round(float(co[pinned, 2].min()), 3), round(float(co[pinned, 2].max()), 3)] if pinned.any() else None
            e["piece_top_z_m"] = round(float(co[:, 2].max()), 3)
    pin[name] = e
out["pin_csv"] = pin

# ---- cloth readiness of the ORIGINAL: overlaps between pieces (base meshes = what cloth would simulate) ----
mesh_orig = {k: o for k, o in orig.items() if o.type == "MESH" and not k.startswith("Clasp_") and "Floor" not in k}
trees, cos = {}, {}
for k, o in mesh_orig.items():
    co, polys, _ = world_coords(o)
    trees[k] = BVHTree.FromPolygons([tuple(c) for c in co], polys)
    cos[k] = co
names = sorted(trees)
pairs = {}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        ov = trees[a].overlap(trees[b])
        if ov:
            pairs[f"{a} x {b}"] = len(ov)
out["orig_piece_pair_intersections_base"] = pairs
selfx = {k: len(trees[k].overlap(trees[k])) for k in names}
out["orig_self_overlap_pairs_note"] = "BVHTree.overlap(self) includes adjacent faces sharing vertices; only a rough indicator"
# near-contact: for every vertex, distance to the nearest OTHER piece
near = {}
for k in names:
    co = cos[k]
    step = max(1, len(co) // 4000)
    sample = co[::step]
    dmin = np.full(len(sample), np.inf)
    for other in names:
        if other == k:
            continue
        for j, p in enumerate(sample):
            hit = trees[other].find_nearest(p, 0.02)
            if hit[0] is not None and hit[3] < dmin[j]:
                dmin[j] = hit[3]
    near[k] = {"sampled": len(sample), "within_2mm": int(np.count_nonzero(dmin < 0.002)),
               "within_5mm": int(np.count_nonzero(dmin < 0.005)), "within_10mm": int(np.count_nonzero(dmin < 0.010)),
               "within_20mm": int(np.count_nonzero(dmin < 0.020))}
out["orig_nearest_other_piece_sampled"] = near

# same intersection test on the FIT's base meshes
ftrees = {}
for k in names:
    f = bpy.data.objects.get(k)
    if f is None:
        continue
    co, polys, _ = world_coords(f)
    ftrees[k] = BVHTree.FromPolygons([tuple(c) for c in co], polys)
fpairs = {}
fn = sorted(ftrees)
for i, a in enumerate(fn):
    for b in fn[i + 1:]:
        ov = ftrees[a].overlap(ftrees[b])
        if ov:
            fpairs[f"{a} x {b}"] = len(ov)
out["fit_piece_pair_intersections_base"] = fpairs

# back coverage of the original: fraction of each piece's area behind the body's coronal plane (y > body centre)
out["orig_back_coverage"] = {}
for k, o in mesh_orig.items():
    co, polys, _ = world_coords(o)
    area_back = area_all = 0.0
    for p in o.data.polygons:
        c = np.array(o.matrix_world @ p.center)
        area_all += p.area
        if c[1] > 0.0:
            area_back += p.area
    out["orig_back_coverage"][k] = round(area_back / area_all, 3) if area_all else None

Path(OUT).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("INSPECT_DONE")
