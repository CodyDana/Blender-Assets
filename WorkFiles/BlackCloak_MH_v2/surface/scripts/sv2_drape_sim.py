# Simple test drape for the fabric check: a circle-cut cloth (r 1.45 m, ~1.6 cm edges) dropped onto a dress-form stand
# (column + shoulder ellipsoid, 1.46 m tall) over a floor, Blender 5.2 cloth with self-collision (the pilot's settings,
# WorkFiles/BlackCloak_Review/male/path/scripts/path_drape_pilot.py).  UVs are true scale in tiles (u = metres / 0.45).
# Saves surface/sv2_test_drape.blend with the applied result (object SV2_Drape) and the stand (SV2_Stand, hidden).
import bpy, bmesh, math, time, json, sys
import numpy as np
from mathutils import Vector

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/"
FR = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 90
TILE = 0.45
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene

# ---- stand: column + shoulder ellipsoid + head knob, joined, collision
parts = []
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.13, depth=1.30, location=(0, 0, 0.65))
parts.append(bpy.context.object)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0, location=(0, 0, 1.36))
sh = bpy.context.object
sh.scale = (0.24, 0.13, 0.12)
parts.append(sh)
for p in parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.join()
stand = bpy.context.object
stand.name = "SV2_Stand"
bpy.ops.object.shade_smooth()
stand.modifiers.new("C", "COLLISION")
stand.collision.thickness_outer = 0.006
stand.collision.cloth_friction = 5.0
# floor
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
fl = bpy.context.object
fl.name = "SV2_FloorCol"
fl.modifiers.new("C", "COLLISION")
fl.collision.thickness_outer = 0.004
fl.collision.cloth_friction = 8.0

# ---- cloth: circle cut, radius 1.45, collar hole r 0.075, flat start at z 1.50, collar ring (r < 0.105) pinned
R, EDGE = 1.45, 0.016
bm = bmesh.new()
n = int(2 * R / EDGE)
grid = {}
for i in range(n + 1):
    for j in range(n + 1):
        x, y = -R + i * EDGE, -R + j * EDGE
        r = math.hypot(x, y)
        if r <= R and r >= 0.075:
            # small jitter breaks the grid symmetry so folds are not axis-locked
            grid[(i, j)] = bm.verts.new((x + np.random.uniform(-0.002, 0.002), y + np.random.uniform(-0.002, 0.002), 1.50))
for i in range(n):
    for j in range(n):
        q = [grid.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
        if all(q):
            bm.faces.new(q)
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="ALTERNATE")
uvl = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for l in f.loops:
        co = l.vert.co
        l[uvl].uv = (co.x / TILE, co.y / TILE)
me = bpy.data.meshes.new("SV2_Drape")
bm.to_mesh(me)
bm.free()
cl = bpy.data.objects.new("SV2_Drape", me)
sc.collection.objects.link(cl)
pin = cl.vertex_groups.new(name="PIN")
pin.add([v.index for v in me.vertices if math.hypot(v.co.x, v.co.y) < 0.105], 1.0, "REPLACE")
cm = cl.modifiers.new("Cloth", "CLOTH")
s = cm.settings
s.quality = 6
s.mass = 0.45
s.air_damping = 1.0
s.tension_stiffness = 40
s.compression_stiffness = 40
s.shear_stiffness = 20
s.bending_stiffness = 0.8
s.vertex_group_mass = "PIN"
s.pin_stiffness = 1.0
cs = cm.collision_settings
cs.distance_min = 0.006
cs.collision_quality = 3
cs.use_self_collision = True
cs.self_distance_min = 0.004
sc.frame_start = 1
sc.frame_end = FR
cm.point_cache.frame_start = 1
cm.point_cache.frame_end = FR
t0 = time.time()
for f in range(1, FR + 1):
    sc.frame_set(f)
t1 = time.time()
dg = bpy.context.evaluated_depsgraph_get()
ev = cl.evaluated_get(dg)
me2 = bpy.data.meshes.new_from_object(ev)
cl.modifiers.clear()
old = cl.data
cl.data = me2
bpy.data.meshes.remove(old)
cl.data.name = "SV2_Drape"
for p in cl.data.polygons:
    p.use_smooth = True
# thickness: a 4 mm solidify (rolled/visible edge in renders), kept as a modifier
so = cl.modifiers.new("Thick", "SOLIDIFY")
so.thickness = 0.004
so.offset = 0.0
stand.modifiers.clear()
fl.modifiers.clear()
bpy.data.objects.remove(fl, do_unlink=True)
stand.hide_render = True
co = np.array([v.co[:] for v in cl.data.vertices])
rep = {"frames": FR, "sim_s": round(t1 - t0, 1), "verts": len(cl.data.vertices), "tris": len(cl.data.polygons),
       "z_min": float(co[:, 2].min()), "z_max": float(co[:, 2].max()),
       "bbox_x": [float(co[:, 0].min()), float(co[:, 0].max())], "bbox_y": [float(co[:, 1].min()), float(co[:, 1].max())]}
bpy.ops.wm.save_as_mainfile(filepath=OUT + "sv2_test_drape.blend")
json.dump(rep, open(OUT + "logs/sv2_test_drape.json", "w"), indent=1)
print("DRAPE", json.dumps(rep))
