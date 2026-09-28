import bpy, hashlib, json, numpy as np
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
def summarize(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    out = {}
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        d = {"type": o.type, "parent": o.parent.name if o.parent else None,
             "loc": [round(v, 5) for v in o.matrix_world.translation], "scale": [round(v, 4) for v in o.matrix_world.to_scale()]}
        if o.type == 'MESH':
            m = o.data; co = np.empty(len(m.vertices)*3); m.vertices.foreach_get("co", co)
            d["verts"] = len(m.vertices); d["tris"] = sum(len(p.vertices)-2 for p in m.polygons)
            d["geo_hash"] = hashlib.md5(np.round(co, 5).tobytes()).hexdigest()[:10]
            if m.uv_layers:
                uv = np.empty(len(m.loops)*2); m.uv_layers[0].data.foreach_get("uv", uv); d["uv_hash"] = hashlib.md5(np.round(uv, 5).tobytes()).hexdigest()[:10]
                d["uv_range"] = [round(float(uv[0::2].min()), 4), round(float(uv[0::2].max()), 4), round(float(uv[1::2].min()), 4), round(float(uv[1::2].max()), 4)]
            d["bbox_mm"] = [round(float(v), 3) for v in (co.reshape(-1, 3).max(0)-co.reshape(-1, 3).min(0))*1000*o.matrix_world.to_scale()[0]]
            d["mats"] = [s.material.name if s.material else None for s in o.material_slots]
        out[o.name] = d
    return out
a = summarize(ROOT+"Exports/PaperBomb/SM_PaperBomb.fbx")
b = summarize(ROOT+"WorkFiles/paperbomb/paused_2026-09-21/Exports_PaperBomb/SM_PaperBomb.fbx")
print("SHIPPED", json.dumps(a, indent=0))
print("SAME_AS_PAUSED", a == b)
if a != b:
    for k in set(a) | set(b):
        if a.get(k) != b.get(k): print("DIFF", k, a.get(k), b.get(k))
