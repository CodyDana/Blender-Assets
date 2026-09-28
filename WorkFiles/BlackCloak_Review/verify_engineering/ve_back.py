import bpy, json
R = {}
for o in bpy.data.collections['BLACK_CLOAK'].all_objects:
    if o.type != 'MESH' or not o.name.startswith('Cloak_'): continue
    me = o.data; tot = 0; back = 0
    for p in me.polygons:
        c = o.matrix_world @ p.center; tot += p.area
        if c.y > 0: back += p.area
    R[o.name] = round(back / tot, 3)
json.dump(R, open('ve_back.json', 'w'), indent=1); print('VE_BACK_DONE')
