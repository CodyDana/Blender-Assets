import bpy, numpy as np, json, os, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/inputs/SM_Shuriken_FourPoint.fbx")
for o in bpy.data.objects: print("OBJ",o.name,o.type)
objs=[o for o in bpy.data.objects if o.type=='MESH' and 'LOD0' in o.name and not o.name.startswith('UCX')]
if not objs: objs=[o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('UCX')]
o=objs[0]; print("USING",o.name)
me=o.data
V=np.empty(len(me.vertices)*3,np.float64); me.vertices.foreach_get("co",V); V=V.reshape(-1,3)
M=np.array(o.matrix_world)
Vw=(V@M[:3,:3].T)+M[:3,3]
print("bbox", Vw.min(0), Vw.max(0))
E=np.empty(len(me.edges)*2,np.int64); me.edges.foreach_get("vertices",E); E=E.reshape(-1,2)
# silhouette in XY: boundary of the projected shape. Use the set of edges whose two adjacent faces
# have opposite-sign Z normals OR that lie on the outer rim. Simpler: build the 2D outline from
# faces projected to XY via a union -- instead take the alpha/convex-free approach:
# collect edges belonging to exactly one "top-facing" face when projected
polys=[list(p.vertices) for p in me.polygons]
nrm=np.empty(len(me.polygons)*3,np.float64); me.polygons.foreach_get("normal",nrm); nrm=nrm.reshape(-1,3)
nw=nrm@M[:3,:3].T
from collections import defaultdict
cnt=defaultdict(int)
for pi,p in enumerate(polys):
    if nw[pi][2] <= 1e-6: continue           # keep upward-facing faces only
    for i in range(len(p)):
        a,b=p[i],p[(i+1)%len(p)]
        cnt[(min(a,b),max(a,b))]+=1
bnd=[k for k,v in cnt.items() if v==1]
print("boundary edges of the up-facing face set:",len(bnd))
np.save("built_verts.npy",Vw); np.save("built_bnd.npy",np.array(bnd))
