"""Read-only inspection of the revision-3 Snow Flower master / game blend.
Usage: blender -b <file.blend> --factory-startup --python inspect_rev3.py -- <out.json>
Never saves the blend.
"""
import bpy, bmesh, sys, json, math
from collections import defaultdict
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]
dg = bpy.context.evaluated_depsgraph_get()
res = {'file': bpy.data.filepath, 'unit_scale': bpy.context.scene.unit_settings.scale_length,
       'objects': [], 'collections': {}, 'images': [], 'materials': []}

def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

gmin = Vector((1e9,)*3); gmax = Vector((-1e9,)*3)
coll_tris = defaultdict(int)
for o in bpy.data.objects:
    d = {'name': o.name, 'type': o.type, 'parent': o.parent.name if o.parent else None,
         'collections': [c.name for c in o.users_collection],
         'loc': list(o.location), 'rot': list(o.rotation_euler), 'scale': list(o.scale),
         'hide_render': o.hide_render, 'props': {k: str(o[k]) for k in o.keys() if not k.startswith('_')}}
    if o.type == 'MESH':
        me = o.evaluated_get(dg).to_mesh()
        d['tris'] = tri_count(me); d['verts'] = len(me.vertices)
        d['uv_layers'] = [u.name for u in me.uv_layers]
        d['materials'] = [s.material.name if s.material else None for s in o.material_slots]
        d['modifiers'] = [m.type for m in o.modifiers]
        ws = [o.matrix_world @ v.co for v in me.vertices]
        if ws:
            mn = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
            mx = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
            d['min'] = list(mn); d['max'] = list(mx)
            if not o.name.startswith('UCX_'):
                gmin = Vector(map(min, gmin, mn)); gmax = Vector(map(max, gmax, mx))
        # world-space area and UV area -> texel density (UV0 by index)
        if me.uv_layers:
            uv = me.uv_layers[0].data
            wa = 0.0; ua = 0.0
            for p in me.polygons:
                idx = list(p.loop_indices)
                pts = [o.matrix_world @ me.vertices[me.loops[i].vertex_index].co for i in idx]
                uvs = [uv[i].uv for i in idx]
                for k in range(1, len(idx) - 1):
                    wa += ((pts[k] - pts[0]).cross(pts[k+1] - pts[0])).length / 2
                    a = uvs[k] - uvs[0]; b = uvs[k+1] - uvs[0]
                    ua += abs(a.x*b.y - a.y*b.x) / 2
            d['world_area_m2'] = wa; d['uv0_area'] = ua
            d['uv0_bounds'] = [min(l.uv.x for l in uv), min(l.uv.y for l in uv), max(l.uv.x for l in uv), max(l.uv.y for l in uv)] if len(uv) else None
        o.evaluated_get(dg).to_mesh_clear()
        for c in d['collections']:
            coll_tris[c] += d['tris']
    res['objects'].append(d)
res['bounds_min'] = list(gmin); res['bounds_max'] = list(gmax)
res['collection_tris'] = dict(coll_tris)
for im in bpy.data.images:
    res['images'].append({'name': im.name, 'size': list(im.size), 'colorspace': im.colorspace_settings.name,
                          'packed': bool(im.packed_file), 'filepath': im.filepath})
for m in bpy.data.materials:
    info = {'name': m.name, 'users': m.users}
    if m.node_tree:
        info['nodes'] = sorted({n.type for n in m.node_tree.nodes})
        info['tex_images'] = [n.image.name for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        info['texcoord_object'] = any(n.type == 'TEX_COORD' and n.outputs['Object'].is_linked for n in m.node_tree.nodes)
    res['materials'].append(info)
json.dump(res, open(out, 'w'), indent=1)
print('WROTE', out)
