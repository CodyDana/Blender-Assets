"""Character-fit review (read-only): the cloth section of an exported MetaHuman cloak FBX - islands, edge lengths,
triangle quality, initial intersections between islands, PinMask distribution, and how the skinned hem swings.

blender -b --factory-startup --python inspect_sim_section.py -- <fbx> <out.json>
"""
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

FBX, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.import_scene.fbx(filepath=FBX, automatic_bone_orientation=False)
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.name != "Cube")
me = mesh.data
mw = mesh.matrix_world
slots = [m.name.split(".")[0] if m else None for m in me.materials]
print("SLOTS", slots, [o.name for o in bpy.data.objects]); sim_idx = [i for i, s in enumerate(slots) if s and "_Sim" in s][0]

bm = bmesh.new()
bm.from_mesh(me)
bm.transform(mw)
bm.faces.ensure_lookup_table()
sim_faces = [f for f in bm.faces if f.material_index == sim_idx]
sim_verts = {v for f in sim_faces for v in f.verts}
# islands in the sim section
seen, islands = set(), []
for f in sim_faces:
    if f in seen:
        continue
    stack, comp = [f], []
    seen.add(f)
    while stack:
        g = stack.pop()
        comp.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.material_index == sim_idx and h not in seen:
                    seen.add(h)
                    stack.append(h)
    islands.append(comp)
islands.sort(key=len, reverse=True)
edges = {e for f in sim_faces for e in f.edges}
lengths = np.array([e.calc_length() for e in edges])
# triangle quality: ratio of inradius*2 / circumradius-ish -> use min angle
min_angles = []
for f in sim_faces:
    angs = [l.calc_angle() for l in f.loops]
    min_angles.append(min(angs))
min_angles = np.degrees(np.array(min_angles))
# intersections between islands (initial state the solver starts from)
trees = []
for comp in islands:
    vs = sorted({v.index for f in comp for v in f.verts})
    remap = {vi: k for k, vi in enumerate(vs)}
    co = [tuple(bm.verts[vi].co) for vi in vs] if False else None
    bm.verts.ensure_lookup_table()
    co = [tuple(bm.verts[vi].co) for vi in vs]
    polys = [tuple(remap[v.index] for v in f.verts) for f in comp]
    trees.append(BVHTree.FromPolygons(co, polys))
pair_x = {}
for i in range(len(trees)):
    for j in range(i + 1, len(trees)):
        n = len(trees[i].overlap(trees[j]))
        if n:
            pair_x[f"{i}x{j}"] = n
# PinMask on sim verts
col = me.color_attributes.get("PinMask") or (me.color_attributes[0] if me.color_attributes else None)
red = np.zeros(len(me.vertices))
if col is not None:
    if col.domain == "CORNER":
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                red[vi] = max(red[vi], col.data[li].color[0])
    else:
        for i, d in enumerate(col.data):
            red[i] = d.color[0]
sim_list = np.array(sorted(v.index for v in sim_verts))
co_all = np.array([mw @ v.co for v in me.vertices])
z = co_all[sim_list, 2]
out = {
    "fbx": FBX, "slots": slots, "sim_slot": slots[sim_idx],
    "sim_faces": len(sim_faces), "sim_vertices": len(sim_verts), "sim_islands": [len(c) for c in islands],
    "sim_edge_length_cm": {"min": round(float(lengths.min() * 100), 2), "median": round(float(np.median(lengths) * 100), 2),
                           "p95": round(float(np.percentile(lengths, 95) * 100), 2), "max": round(float(lengths.max() * 100), 2)},
    "sim_min_angle_deg": {"p1": round(float(np.percentile(min_angles, 1)), 2), "median": round(float(np.median(min_angles)), 2),
                          "under_10deg": int(np.count_nonzero(min_angles < 10)), "under_5deg": int(np.count_nonzero(min_angles < 5))},
    "sim_island_pair_intersections": pair_x,
    "sim_island_pairs_intersecting": len(pair_x),
    "sim_intersecting_triangle_pairs_total": int(sum(pair_x.values())),
    "pinmask_sim": {"red_gt_0.5": int(np.count_nonzero(red[sim_list] > 0.5)), "red_any": int(np.count_nonzero(red[sim_list] > 0)),
                    "z_of_red_m": [round(float(z[red[sim_list] > 0.5].min()), 3), round(float(z[red[sim_list] > 0.5].max()), 3)] if np.any(red[sim_list] > 0.5) else None},
    "pinmask_all_red": int(np.count_nonzero(red > 0.5)),
    "sim_z_range_m": [round(float(z.min()), 3), round(float(z.max()), 3)],
    "sim_below_136cm_share": round(float(np.mean(z < 1.36)), 3),
}
Path(OUT).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("SIM_DONE")
