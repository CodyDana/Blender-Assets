import bpy, json, math
import numpy as np
from pathlib import Path
OUT=Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/materials")
R={}
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith(('Cloak_','Clasp_')): continue
    me=o.data; uv=me.uv_layers[0].data
    wa=0.0; ua=0.0; umin=[1e9,1e9]; umax=[-1e9,-1e9]
    M=o.matrix_world
    for p in me.polygons:
        vs=[M@me.vertices[i].co for i in p.vertices]; us=[uv[li].uv for li in p.loop_indices]
        for k in range(1,len(vs)-1):
            wa+=((vs[k]-vs[0]).cross(vs[k+1]-vs[0])).length/2
            a=us[k]-us[0]; b=us[k+1]-us[0]; ua+=abs(a.x*b.y-a.y*b.x)/2
        for u in us:
            umin=[min(umin[0],u.x),min(umin[1],u.y)]; umax=[max(umax[0],u.x),max(umax[1],u.y)]
    uv_per_m=math.sqrt(ua/wa) if wa else 0
    R[o.name]={"world_area_m2":wa,"uv_units_per_metre":uv_per_m,"uv_range":[umin,umax],
               "px_per_cm_if_blender_shader_scale":uv_per_m/0.128*2048/100}
(OUT/"mat_uv_density.json").write_text(json.dumps(R,indent=1))
print("UVD_DONE")
