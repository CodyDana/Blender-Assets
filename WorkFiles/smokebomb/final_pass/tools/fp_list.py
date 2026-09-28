import bpy
for o in bpy.data.objects:
    line = f"{o.name:40s} {o.type:8s}"
    if o.type == 'MESH':
        m = o.data
        line += f" v{len(m.vertices)} f{len(m.polygons)} attrs=" + ",".join(f"{a.name}:{a.domain}" for a in m.attributes)
        line += " uv=" + ",".join(u.name for u in m.uv_layers)
        line += " mats=" + ",".join(s.material.name if s.material else '-' for s in o.material_slots)
    print(line)
for i in bpy.data.images: print("IMG", i.name, i.size[:], i.colorspace_settings.name)
