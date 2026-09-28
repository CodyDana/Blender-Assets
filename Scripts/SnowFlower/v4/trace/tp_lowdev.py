import bpy, numpy as np
from mathutils.bvhtree import BVHTree
W = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
with bpy.data.libraries.load(W + "/tp_low.blend") as (s, d): d.objects = ["SM_SnowFlower_Throat_TP_LOD0"]
low = d.objects[0]; hp = bpy.data.objects["TP_Throat_HIGH"]
dg = bpy.context.evaluated_depsgraph_get()
bh = BVHTree.FromObject(hp, dg)
sd = []
for p in low.data.polygons:
    c = p.center; n = p.normal
    loc, nn, idx, dist = bh.find_nearest(c)
    s = (loc - c).dot(n)
    sd.append(s * 1000)
sd = np.array(sd)
print("LOW face centre -> HIGH signed dist mm (+ = HIGH outside LOW): pct 1,5,25,50,75,95,99", np.percentile(sd, [1, 5, 25, 50, 75, 95, 99]).round(2))
# how many faces have a HIGH normal facing opposite
dots = []; areas = []
for p in low.data.polygons:
    loc, nn, idx, dist = bh.find_nearest(p.center)
    dots.append(p.normal.dot(nn)); areas.append(p.area)
dots = np.array(dots); areas = np.array(areas)
print("LOW vs HIGH normal agreement: area frac dot<0:", round(areas[dots < 0].sum() / areas.sum(), 3), " dot<0.5:", round(areas[dots < 0.5].sum() / areas.sum(), 3))
hn = np.array([p.normal[:] for p in hp.data.polygons[:200000]])
# HIGH orientation sanity: rays from far outside toward the centre should hit front faces
import mathutils
bad = 0; tot = 0
for az in np.linspace(0, 2*np.pi, 72, endpoint=False):
    for z in np.linspace(-0.180, -0.095, 30):
        o = mathutils.Vector((0.3*np.cos(az), 0.3*np.sin(az), z)); dv = (mathutils.Vector((0, 0, z)) - o).normalized()
        loc, nrm, idx, dist = bh.ray_cast(o, dv)
        if loc is not None:
            tot += 1; bad += nrm.dot(dv) > 0
print("HIGH outside-ray hits facing away (inverted):", bad, "/", tot)
