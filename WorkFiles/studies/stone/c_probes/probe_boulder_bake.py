import bpy
for _o in list(bpy.data.objects): bpy.data.objects.remove(_o)
import bpy, bmesh, json, sys, time, random, math
from mathutils import Vector, noise, geometry
out = {}
try:
    import scipy; out["scipy"]=scipy.__version__
except Exception as e: out["scipy"]="missing"
import numpy; out["numpy"]=numpy.__version__
out["mathutils_geometry"]=[k for k in dir(geometry) if not k.startswith("_")]
sc=bpy.context.scene
rng=random.Random(7)
def lobe(c, r, nplanes, seed):
    bm=bmesh.new()
    pts=[c+Vector((rng.gauss(0,1),rng.gauss(0,1),rng.gauss(0,0.7))).normalized()*r*rng.uniform(0.8,1.1) for _ in range(40)]
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    # chip planes
    for i in range(nplanes):
        d=Vector((rng.gauss(0,1),rng.gauss(0,1),rng.gauss(0,1))).normalized()
        if d.z<-0.5: continue
        co=c+d*r*rng.uniform(0.72,0.95)
        geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
        res=bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=d, clear_outer=True)
        # fill hole
        edges=[e for e in res["geom_cut"] if isinstance(e,bmesh.types.BMEdge)]
        if edges:
            try: bmesh.ops.edgeloop_fill(bm, edges=edges)
            except Exception:
                bmesh.ops.contextual_create(bm, geom=edges)
    return bm
t0=time.time()
objs=[]
for i,(c,r) in enumerate([((0,0,0.5),0.6),((0.55,0.1,0.35),0.45),((-0.4,0.3,0.3),0.4)]):
    bm=lobe(Vector(c),r,22,i)
    me=bpy.data.meshes.new(f"L{i}"); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(f"L{i}",me); sc.collection.objects.link(o); objs.append(o)
out["t_lobes"]=round(time.time()-t0,3)
# join
with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
    bpy.ops.object.join()
o=objs[0]
t=time.time()
rm=o.modifiers.new("r","REMESH"); rm.mode='VOXEL'; rm.voxel_size=0.01
with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier="r")
out["voxel_1cm_faces"]=len(o.data.polygons); out["t_voxel"]=round(time.time()-t,2)
# displacement: 3 octaves along normals
t=time.time()
bm=bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
for v in bm.verts:
    p=v.co; n=v.normal
    d=0.03*noise.noise(p*2.0)+0.012*noise.noise(p*6.0+Vector((3,1,2)))+0.004*noise.noise(p*18.0)
    v.co=p+n*d
bm.to_mesh(o.data); bm.free()
out["t_disp"]=round(time.time()-t,2)
out["high_tris"]=sum(len(p.vertices)-2 for p in o.data.polygons)
t=time.time()
lo=o.copy(); lo.data=o.data.copy(); sc.collection.objects.link(lo)
dm=lo.modifiers.new("d","DECIMATE"); dm.ratio=4000/out["high_tris"]
with bpy.context.temp_override(object=lo, active_object=lo): bpy.ops.object.modifier_apply(modifier="d")
out["low_tris"]=sum(len(p.vertices)-2 for p in lo.data.polygons); out["t_decimate"]=round(time.time()-t,2)
# smart UV on low
t=time.time()
bpy.context.view_layer.objects.active=lo
for ob in sc.objects: ob.select_set(False)
lo.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
out["t_uv"]=round(time.time()-t,2)
# ---- bake normal + AO high->low at 1024
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=16
img=bpy.data.images.new("N",1024,1024,alpha=False,float_buffer=True); img.colorspace_settings.name='Non-Color'
mat=bpy.data.materials.new("M"); lo.data.materials.append(mat)
nt=mat.node_tree; tn=nt.nodes.new("ShaderNodeTexImage"); tn.image=img; nt.nodes.active=tn
for ob in sc.objects: ob.select_set(False)
o.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active=lo
t=time.time()
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True, cage_extrusion=0.03, max_ray_distance=0.08, margin=8, margin_type='EXTEND')
out["t_bake_normal_1k"]=round(time.time()-t,2)
import numpy as np
px=np.array(img.pixels[:]).reshape(1024,1024,4)
nx=px[...,0]*2-1; ny=px[...,1]*2-1
curv=np.gradient(nx,axis=1)+np.gradient(ny,axis=0)
out["curv_stats"]=[float(np.percentile(curv,p)) for p in (1,50,99)]
out["normal_mean"]=[float(px[...,c].mean()) for c in range(3)]
img2=bpy.data.images.new("AO",1024,1024,alpha=False); tn.image=img2
t=time.time()
bpy.ops.object.bake(type='AO', use_selected_to_active=True, cage_extrusion=0.03, max_ray_distance=0.08, margin=8, margin_type='EXTEND')
out["t_bake_ao_1k"]=round(time.time()-t,2)
a=np.array(img2.pixels[:]).reshape(1024,1024,4)[...,0]; out["ao_p5_p50"]=[float(np.percentile(a,5)),float(np.percentile(a,50))]
nz=px[...,2]*2-1; out["normal_tilt_gt10deg_frac"]=float((nz<0.985).mean())
img5=bpy.data.images.new("N2",2048,2048,alpha=False,float_buffer=True); img5.colorspace_settings.name='Non-Color'; tn.image=img5
for ob in sc.objects: ob.select_set(False)
o.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active=lo
t=time.time(); sc.cycles.samples=1
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True, cage_extrusion=0.03, margin=16, margin_type='EXTEND')
out["t_bake_normal_2k_1spp"]=round(time.time()-t,2)
img6=bpy.data.images.new("AO4",2048,2048,alpha=False); tn.image=img6; sc.cycles.samples=64
t=time.time()
bpy.ops.object.bake(type='AO', use_selected_to_active=True, cage_extrusion=0.03, margin=16, margin_type='EXTEND')
out["t_bake_ao_2k_64spp"]=round(time.time()-t,2)
a=np.array(img6.pixels[:]).reshape(2048,2048,4)[...,0]; out["ao2k_p5_p50_p95"]=[float(np.percentile(a,q)) for q in (5,50,95)]
json.dump(out, open(sys.argv[-1],"w"), indent=1)
