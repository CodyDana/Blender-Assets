import bpy, sys, numpy as np
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
p=sys.argv[sys.argv.index('--')+1]
try:
    bpy.ops.import_scene.fbx(filepath=p)
    print("IMPORTER python")
except Exception as e:
    print("pyimport fail",e); bpy.ops.wm.fbx_import(filepath=p)
tot=0
for o in bpy.data.objects:
    s=""
    if o.type=='MESH':
        m=o.data; m.calc_loop_triangles(); tot+=len(m.loop_triangles)
        uvs=[]
        for u in m.uv_layers:
            a=np.zeros(len(m.loops)*2); u.data.foreach_get('uv',a); a=a.reshape(-1,2)
            uvs.append((u.name,a.min(0).round(2).tolist(),a.max(0).round(2).tolist()))
        s=f"tris={len(m.loop_triangles)} mats={[x.name for x in m.materials]} uv={uvs}"
    print("OBJ",o.name,o.type,[round(x,3) for x in o.dimensions],[round(x,3) for x in o.location],[round(x,3) for x in o.rotation_euler],[round(x,3) for x in o.scale],s)
print("TOTAL",tot)
for m in bpy.data.materials: print("MAT",m.name,[ (n.type, n.image.filepath if getattr(n,'image',None) else '') for n in (m.node_tree.nodes if m.node_tree else [])])
