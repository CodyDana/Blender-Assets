"""b2_sym_check_inv.py - PRIVATE / DO NOT SHIP. Independent checker: inventory of a rig blend (read-only, never saves)."""
import bpy
for o in bpy.data.objects:
    s = f"{o.name} {o.type} parent={o.parent.name if o.parent else None} mw_diag={[round(o.matrix_world[i][i],4) for i in range(3)]} loc={tuple(round(x,4) for x in o.matrix_world.translation)}"
    if o.type == 'MESH':
        me = o.data
        s += f" v={len(me.vertices)} f={len(me.polygons)} mats={[m.name if m else None for m in me.materials]} vg={len(o.vertex_groups)} mods={[(m.type, getattr(m,'object',None) and m.object.name) for m in o.modifiers]} attrs={[a.name for a in me.attributes]} custom_normals={me.has_custom_normals} uv={[u.name for u in me.uv_layers]} shapekeys={me.shape_keys and len(me.shape_keys.key_blocks)}"
    if o.type == 'ARMATURE':
        s += f" bones={len(o.data.bones)} names={[b.name for b in o.data.bones]}"
    print("INV", s)
