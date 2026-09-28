import bpy, bmesh, numpy as np, json
from mathutils.bvhtree import BVHTree
o=bpy.data.objects["SM_BlackHat_LOD0"]; me=o.data
bm=bmesh.new(); bm.from_mesh(me)
res={}
for mi,name in ((0,"straw"),(1,"cloth")):
    faces=[f for f in bm.faces if f.material_index==mi]
    fs=set(faces)
    edges=set(e for f in faces for e in f.edges)
    bnd=[e for e in edges if sum(1 for f in e.link_faces if f in fs)==1]
    nm=[e for e in edges if sum(1 for f in e.link_faces if f in fs)>2]
    area=sum(f.calc_area() for f in faces)
    res[name]={"faces":len(faces),"boundary_edges":len(bnd),"nonmanifold_edges":len(nm),"area_m2":area}
    if name=="cloth":
        # thickness: ray from face centre along -normal, first hit distance on cloth
        verts=[v.co.copy() for v in bm.verts]
        polys=[[v.index for v in f.verts] for f in faces]
        bvh=BVHTree.FromPolygons(verts,polys)
        d=[]
        for f in faces:
            c=f.calc_center_median(); n=f.normal
            hit=bvh.ray_cast(c-n*1e-5,-n,0.05)
            if hit[0] is not None: d.append(hit[3])
        d=np.array(d); res[name]["thick_hits"]=len(d); res[name]["thick_mm_q"]=[float(np.quantile(d,p)*1000) for p in (0.05,.25,.5,.75,.95)] if len(d) else None
        zs=[v.co.z for f in faces for v in f.verts]; res[name]["z_min_max"]=[min(zs),max(zs)]
zs=[v.co.z for v in bm.verts]; res["all_z"]=[min(zs),max(zs)]
print("CJM"+json.dumps(res))
