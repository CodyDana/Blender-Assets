"""b2_inspect.py - PRIVATE / DO NOT SHIP. Headless read-only inspection of the 2B kimono GLB after import.
Usage: blender -b -P b2_inspect.py
"""
import bpy, bmesh
from mathutils import Vector
from collections import defaultdict

SRC = r"C:/Users/Cody/Desktop/Blender_Projects/References/Characters/2B_kimono_private/source/28.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, o.parent.name if o.parent else None, tuple(round(x, 4) for x in o.location),
          tuple(round(x, 4) for x in o.rotation_euler), tuple(round(x, 4) for x in o.scale))
me_objs = [o for o in bpy.data.objects if o.type == 'MESH']
for o in me_objs:
    me = o.data
    mw = o.matrix_world
    print("MESH", o.name, len(me.vertices), len(me.polygons), "mats", len(me.materials), "uvs", [u.name for u in me.uv_layers])
    per = defaultdict(lambda: [0, [1e9] * 3, [-1e9] * 3, 0])
    co = [mw @ v.co for v in me.vertices]
    for p in me.polygons:
        d = per[p.material_index]
        d[0] += len(p.vertices) - 2
        d[3] += 1
        for vi in p.vertices:
            c = co[vi]
            for k in range(3):
                d[1][k] = min(d[1][k], c[k]); d[2][k] = max(d[2][k], c[k])
    tot = 0
    for mi in sorted(per):
        d = per[mi]
        tot += d[0]
        m = me.materials[mi]
        tex = []
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    tex.append(n.image.name)
            bl = m.blend_method if hasattr(m, 'blend_method') else ''
        print(f"MAT {mi:2d} {m.name if m else None!s:45s} tris {d[0]:7d} faces {d[3]:7d} min {tuple(round(x,4) for x in d[1])} max {tuple(round(x,4) for x in d[2])} tex {tex}")
    print("TOTAL tris", tot)
    # face sizes
    sizes = defaultdict(int)
    for p in me.polygons:
        sizes[len(p.vertices)] += 1
    print("poly sizes", dict(sizes))
for m in bpy.data.materials:
    if m.node_tree:
        print("MATNODES", m.name, [(n.type, n.bl_idname) for n in m.node_tree.nodes], getattr(m, 'surface_render_method', ''))
for im in bpy.data.images:
    print("IMG", im.name, im.size[:], im.packed_file is not None, im.filepath)
