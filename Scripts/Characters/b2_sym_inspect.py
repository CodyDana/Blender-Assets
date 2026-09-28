"""b2_sym_inspect.py - PRIVATE / DO NOT SHIP. Read-only inspection of the 2B rig blend for the symmetry step.

  blender -b 2B_private_rig.blend -P b2_sym_inspect.py -- <out.json>
"""
import bpy, bmesh, sys, os, json
import numpy as np
from collections import Counter

out = sys.argv[sys.argv.index("--") + 1]
R = {}
R["objects"] = [(o.name, o.type, o.parent.name if o.parent else None, [c.name for c in o.users_collection],
                 o.hide_render, [m.type for m in o.modifiers]) for o in bpy.data.objects]
R["scene_camera"] = bpy.context.scene.camera.name if bpy.context.scene.camera else None
for n in ("SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"):
    o = bpy.data.objects[n]
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    # connected components
    seen = set(); comps = []
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        if v.index in seen:
            continue
        st = [v]; seen.add(v.index); c = []
        while st:
            a = st.pop(); c.append(a.index)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); st.append(b)
        comps.append(c)
    X = np.array([list(v.co) for v in me.vertices])
    mats = [m.name for m in me.materials]
    pm = np.zeros(len(me.polygons), dtype=int); me.polygons.foreach_get("material_index", pm)
    vm = {}
    for p in me.polygons:
        for v in p.vertices:
            vm.setdefault(v, set()).add(mats[p.material_index])
    ci = []
    for c in comps:
        cc = X[c]
        ms = Counter(m for v in c for m in vm.get(v, ()))
        ci.append({"n": len(c), "centroid": [round(x, 4) for x in cc.mean(0)], "min": [round(x, 4) for x in cc.min(0)],
                   "max": [round(x, 4) for x in cc.max(0)], "mats": dict(ms)})
    ci.sort(key=lambda d: -d["n"])
    R[n] = {"verts": len(me.vertices), "faces": len(me.polygons), "components": len(comps), "comp_info": ci[:60],
            "attributes": [(a.name, a.domain, a.data_type) for a in me.attributes], "uv_layers": [u.name for u in me.uv_layers],
            "vgroups": len(o.vertex_groups), "bbox_min": X.min(0).tolist(), "bbox_max": X.max(0).tolist(),
            "face_sizes": dict(Counter(len(p.vertices) for p in me.polygons)), "matrix_world_identity": o.matrix_world == o.matrix_world.Identity(4),
            "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []}
    bm.free()
arm = bpy.data.objects["root"]
R["armature"] = {"matrix_world": [list(r) for r in arm.matrix_world], "bones": {
    b.name: {"head": [round(x, 5) for x in b.head_local], "tail": [round(x, 5) for x in b.tail_local],
             "parent": b.parent.name if b.parent else None,
             "mat": [[round(x, 5) for x in r] for r in b.matrix_local.to_3x3()]} for b in arm.data.bones}}
json.dump(R, open(out, "w"), indent=1)
print("wrote", out)
