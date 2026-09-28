"""Character-fit review (read-only): what the ORIGINAL exported FBX files carry that matters for the character / cloth
track: skeleton (bones vs metahuman_base_skel), weights, colour sets / pin data, vertex counts vs the editable cages
(authoring_pin_weights.csv indexing), double shells from the baked SOLIDIFY.

blender -b --factory-startup --python inspect_orig_exports.py -- <out.json>
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.kdtree import KDTree

OUT = sys.argv[sys.argv.index("--") + 1:][0]
EXP = Path("C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak")
MH_BONES = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default/rig/bones.json")
mh = json.loads(MH_BONES.read_text(encoding="utf-8"))
mh_names = set(next(iter(mh.values()))["bones"])
out = {"mh_bone_count": len(mh_names)}


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
        for d in list(block):
            if d.users == 0:
                block.remove(d)


for fname in ("BlackCloak_Skeletal.fbx", "BlackCloak_Skeletal_LOD1.fbx", "BlackCloak_Skeletal_LOD2.fbx", "BlackCloak.fbx"):
    clear()
    bpy.ops.import_scene.fbx(filepath=str(EXP / fname), automatic_bone_orientation=False)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    e = {"objects": [(o.name, o.type) for o in bpy.data.objects][:40], "mesh_count": len(meshes)}
    if arms:
        a = arms[0]
        names = [b.name for b in a.data.bones]
        e["armature"] = {"object": a.name, "bones": len(names), "roots": [b.name for b in a.data.bones if b.parent is None],
                         "in_metahuman": len(set(names) & mh_names), "not_in_metahuman": sorted(set(names) - mh_names)[:40],
                         "sample": names[:25]}
    tot_v = tot_t = 0
    used = {}
    infl_max = 0
    per_mesh = {}
    for m in meshes:
        me = m.data
        tot_v += len(me.vertices)
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        tot_t += tris
        idx = {g.index: g.name for g in m.vertex_groups}
        for v in me.vertices:
            ws = [idx[g.group] for g in v.groups if g.weight > 0]
            infl_max = max(infl_max, len(ws))
            for n in ws:
                used[n] = used.get(n, 0) + 1
        per_mesh[m.name] = {"vertices": len(me.vertices), "tris": tris, "materials": [x.name if x else None for x in me.materials],
                            "colour": [(c.name, c.domain) for c in me.color_attributes], "uv": [u.name for u in me.uv_layers],
                            "groups": len(m.vertex_groups)}
    e.update(total_vertices=tot_v, total_tris=tot_t, bones_weighted=used, max_influences=infl_max, meshes=per_mesh)
    # double-shell test on the largest mesh: fraction of vertices with another vertex within 2 mm along the normal
    if meshes:
        big = max(meshes, key=lambda o: len(o.data.vertices))
        me = big.data
        co = np.array([big.matrix_world @ v.co for v in me.vertices])
        kd = KDTree(len(co))
        for i, c in enumerate(co):
            kd.insert(c, i)
        kd.balance()
        step = max(1, len(co) // 5000)
        near = 0
        dists = []
        for i in range(0, len(co), step):
            res = kd.find_n(co[i], 2)
            d = res[1][2] if len(res) > 1 else 1.0
            dists.append(d)
        dists = np.array(dists)
        e["largest_mesh_nearest_vertex_mm"] = {"mesh": big.name, "sampled": len(dists),
                                               "p10": round(float(np.percentile(dists, 10) * 1000), 2),
                                               "median": round(float(np.median(dists) * 1000), 2),
                                               "share_lt_2mm": round(float(np.mean(dists < 0.002)), 3)}
    out[fname] = e

Path(OUT).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("EXPORTS_DONE")
