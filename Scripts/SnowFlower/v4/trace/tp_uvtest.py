import bpy, math, bmesh
import bpy_extras.mesh_utils as MU
import numpy as np
o = bpy.data.objects["SM_SnowFlower_Throat_TP_LOD0"]
sc = bpy.context.scene
def cov(ob):
    me = ob.data; uv = me.uv_layers[0].data; A = 0
    for p in me.polygons:
        pts = [uv[li].uv for li in p.loop_indices]
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            A += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
    return A
def stretch(ob):
    """ratio spread of sqrt(uv area / 3D area) per face (p10/p90 relative to the median)."""
    me = ob.data; uv = me.uv_layers[0].data; r = []
    for p in me.polygons:
        pts = [uv[li].uv for li in p.loop_indices]
        a, b, c = pts[0], pts[1], pts[2]
        au = abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
        if p.area > 0: r.append(math.sqrt(au / p.area))
    r = np.array(r); m = np.median(r)
    return np.percentile(r / m, [5, 25, 75, 95]).round(2).tolist()
for reps, ang in ((20, 60), (40, 66)):
    prox = o.copy(); prox.data = o.data.copy(); sc.collection.objects.link(prox)
    for ob in sc.objects: ob.select_set(False)
    bpy.context.view_layer.objects.active = prox; prox.select_set(True)
    m = prox.modifiers.new("sm", 'SMOOTH'); m.factor = 1.0; m.iterations = reps
    bpy.ops.object.modifier_apply(modifier="sm")
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    # transfer to the real mesh (same topology)
    src = prox.data.uv_layers[0].data; dst = o.data.uv_layers[0].data
    for i in range(len(src)): dst[i].uv = src[i].uv
    print("reps", reps, "angle", ang, "islands", len(MU.mesh_linked_uv_islands(prox.data)), "cov", round(cov(o), 3), "stretch p5,p25,p75,p95", stretch(o))
    bpy.data.objects.remove(prox)
