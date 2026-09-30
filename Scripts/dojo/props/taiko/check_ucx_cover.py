"""UCX coverage check (f1): every mesh vertex of each taiko piece must lie inside one of its UCX hulls.
Run: blender -b --factory-startup Assets/Dojo/Taiko.blend --python Scripts/dojo/props/taiko/check_ucx_cover.py
"""
import bpy, json
out={}
for name in ("SM_DKP_Taiko_Drum","SM_DKP_Taiko_Stand","SM_DKP_Taiko_Stick"):
    o=bpy.data.objects[name]
    hulls=[]
    for h in o.children:
        if not h.name.startswith("UCX_"): continue
        me=h.data
        hulls.append([(p.normal.copy(), p.normal.dot(me.vertices[p.vertices[0]].co)) for p in me.polygons])
    worst=0.0; outside=0
    for v in o.data.vertices:
        best=min(max(n.dot(v.co)-d for n,d in hl) for hl in hulls)
        if best>0.001:
            outside+=1
            if name.endswith("Stand"): print("OUT", tuple(round(c,3) for c in v.co), round(best,4))
        worst=max(worst,best)
    out[name]={"hulls":len(hulls),"verts":len(o.data.vertices),"verts_outside_1mm":outside,"max_outside_m":round(worst,4)}
print("UCXCOV",json.dumps(out))
