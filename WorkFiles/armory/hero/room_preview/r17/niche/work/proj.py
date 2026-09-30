# project scene parts through the C1 camera (level shift lens) into 1448x1086 pixels
import bpy, sys
from mathutils import Vector
W,H=1448,1086; F=40/36*W; CAM=Vector((6.0,-4.18,3.39)); SH=-0.315
def P(v):
    d=v.y-CAM.y; return (W/2+F*(v.x-CAM.x)/d, H/2-F*(v.z-CAM.z)/d+SH*W)
dg=bpy.context.evaluated_depsgraph_get()
pat=sys.argv[sys.argv.index('--')+1].split(',')
for o in bpy.context.scene.objects:
    if o.type!='MESH' or not any(p in o.name for p in pat): continue
    oe=o.evaluated_get(dg); me=oe.to_mesh(); mw=o.matrix_world
    vs=[mw@v.co for v in me.vertices]
    def bb(vv,tag):
        if not vv: return
        pp=[P(v) for v in vv]; xs=[p[0] for p in pp]; ys=[p[1] for p in pp]
        print(f"{o.name:40s} {tag:10s} x {min(xs):7.1f}-{max(xs):7.1f} y {min(ys):7.1f}-{max(ys):7.1f}  Z {min(v.z for v in vv):.3f}-{max(v.z for v in vv):.3f} X {min(v.x for v in vv):.3f}-{max(v.x for v in vv):.3f}")
    bb(vs,'all')
    if 'Banner' in o.name:
        bb([v for v in vs if v.z<2.80],'lowZ<2.8')
        # material split
        for mi,m in enumerate(o.material_slots):
            vv=set()
            for p in me.polygons:
                if p.material_index==mi: vv.update(p.vertices)
            bb([mw@me.vertices[i].co for i in vv], (m.name or '')[:10])
    oe.to_mesh_clear()
