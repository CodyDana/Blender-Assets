import bpy, json
R = {}
for o in bpy.data.collections['BLACK_CLOAK'].all_objects:
    if o.type != 'MESH': continue
    g = o.vertex_groups.get('CLOTH_Pin'); zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
    d = {'top_z': round(max(zs), 3), 'bottom_z': round(min(zs), 3), 'props': {k: o[k] for k in o.keys() if not k.startswith('_')}}
    if g:
        pz = [(o.matrix_world @ v.co).z for v in o.data.vertices for gg in v.groups if gg.group == g.index and gg.weight > 0.5]
        if pz: d['pinned_z'] = [round(min(pz), 3), round(max(pz), 3)]; d['n_pinned'] = len(pz)
    R[o.name] = d
json.dump(R, open('ve_pins.json', 'w'), indent=1, default=str); print('VE_PIN_DONE')
