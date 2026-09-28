# Import the SNAPSHOTTED FBX (inputs/, not Assets/) in a factory-startup scene, project LOD0 to XY,
# rasterise the plan silhouette into a mm-grid mask, and save it + stats.
import bpy, numpy as np, json, math, os, sys
IN="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/inputs/SM_Shuriken_EightPoint.fbx"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/reconcile"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=IN)
objs=[o for o in bpy.data.objects if o.type=='MESH']
print('mesh objects:', [(o.name, len(o.data.vertices)) for o in objs])
lod0=[o for o in objs if 'LOD0' in o.name and not o.name.startswith('UCX')]
if not lod0: lod0=[max([o for o in objs if not o.name.startswith('UCX')], key=lambda o: len(o.data.vertices))]
ob=lod0[0]; print('using', ob.name)
dg=bpy.context.evaluated_depsgraph_get(); ev=ob.evaluated_get(dg); me=ev.to_mesh()
me.calc_loop_triangles()
M=np.array(ob.matrix_world)
V=np.array([ (M@np.array([*v.co,1.0]))[:3] for v in me.vertices ])
ext=V.max(0)-V.min(0); print('world extent (scene units):', ext)
# figure out which axis is the plate normal (smallest extent)
ax=int(np.argmin(ext)); keep=[i for i in range(3) if i!=ax]
P=V[:,keep]
# units -> mm: across should be 100 mm
across=max(P[:,0].max()-P[:,0].min(), P[:,1].max()-P[:,1].min())
scale=100.0/across; print('thin axis', ax, 'across', across, '-> mm scale', scale)
P=(P-P.mean(0))*scale
# rasterise triangles: grid 0.05 mm over +-52 mm
res=0.05; N=int(round(104/res))+1
xs=-52+np.arange(N)*res
mask=np.zeros((N,N),bool)
tris=np.array([t.vertices[:] for t in me.loop_triangles])
for tri in tris:
    a,b,c=P[tri]
    mn=np.floor((np.minimum(np.minimum(a,b),c)+52)/res).astype(int); mx=np.ceil((np.maximum(np.maximum(a,b),c)+52)/res).astype(int)
    mn=np.clip(mn,0,N-1); mx=np.clip(mx,0,N-1)
    if (mx-mn).min()<0: continue
    gx,gy=np.meshgrid(xs[mn[0]:mx[0]+1], xs[mn[1]:mx[1]+1], indexing='xy')
    v0=c-a; v1=b-a; v2x=gx-a[0]; v2y=gy-a[1]
    d00=v0@v0; d01=v0@v1; d11=v1@v1; den=d00*d11-d01*d01
    if abs(den)<1e-14: continue
    d20=v2x*v0[0]+v2y*v0[1]; d21=v2x*v1[0]+v2y*v1[1]
    u=(d11*d20-d01*d21)/den; v=(d00*d21-d01*d20)/den
    ins=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
    mask[mn[1]:mx[1]+1, mn[0]:mx[0]+1] |= ins
# centre, radial profile, arm orientation
yy,xx=np.nonzero(mask); X=xs[xx]; Y=xs[yy]
R=np.hypot(X,Y); th=np.degrees(np.arctan2(Y,X))%360
bins=np.arange(0,360.01,0.25); rmax=np.zeros(len(bins)-1)
idx=np.digitize(th,bins)-1
np.maximum.at(rmax, idx, R)
kmax=np.argsort(rmax)[::-1]
tipang=[]
for i in kmax:
    a=bins[i]+0.125
    if all(min(abs(a-t)%360,360-abs(a-t)%360)>20 for t in tipang): tipang.append(a)
    if len(tipang)==8: break
tipang=sorted(tipang); print('built tip polar angles (deg, y-up):', np.round(tipang,2), ' max r', rmax.max())
# min radius between arms (hub arc) and hole
inner=np.zeros(len(bins)-1)+99; outer_hole=np.zeros(len(bins)-1)
rmin_out=[]
for a0 in tipang:
    a=(a0+22.5)%360; i=int(a/0.25); rmin_out.append(rmax[i])
print('built outline radius midway between arms (hub arc):', np.round(rmin_out,3))
# hole: largest empty radius at centre
c=N//2; r=0
while not mask[c, c+r]: r+=1
print('hole radius along +x ~', r*res, 'mm')
np.save(OUT+"/built_mask_mm.npy", mask)
json.dump(dict(res_mm=res, origin_mm=-52.0, N=N, tip_polar_deg=list(map(float,tipang)), tip_r_mm=float(rmax.max()),
               hub_arc_r_mm=list(map(float,rmin_out)), hole_r_mm=float(r*res), object=ob.name,
               area_mm2=float(mask.sum()*res*res)), open(OUT+"/built_outline.json","w"), indent=1)
print('plan area (mm2, incl. hole subtraction):', mask.sum()*res*res)
