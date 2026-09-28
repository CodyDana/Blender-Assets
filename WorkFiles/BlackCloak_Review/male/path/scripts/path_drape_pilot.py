"""Feasibility pilot for the re-drape option: can Blender 5.2's own cloth solver drape a flat-cut cape on the male fit body
(headless, this machine), how long does it take, and does the result have the non-height-field folds real cloth has?
Runs on a COPY of MH_PlayerDefault_FitBody.blend. Writes a NEW blend + renders + json into male/path/. Never saves the input."""
import bpy, bmesh, sys, json, math, time, os
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.name.endswith("HairCards"):
        bpy.data.objects.remove(o, do_unlink=True)
arm = bpy.data.objects["root"]
body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]
head = bpy.data.objects["FIT_MH_PlayerDefault_Head"]
hair = bpy.data.objects["FIT_MH_PlayerDefault_HairProxy"]

# --- arms down (world-space rotation of each upper arm about its head, like the blender capture's arms-down pose)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
def hand_z():
    bpy.context.view_layer.update()
    return [(arm.matrix_world @ arm.pose.bones[n].head).z for n in ("hand_l", "hand_r")]
for side in ("l", "r"):
    pb = arm.pose.bones["upperarm_" + side]
    base = pb.matrix.copy()
    h = arm.matrix_world @ pb.head
    best = None
    for sgn in (1, -1):
        R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(sgn * 30), 4, "Y") @ Matrix.Translation(-h)
        pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ base
        z = hand_z()[0 if side == "l" else 1]
        if best is None or z < best[0]:
            best = (z, sgn)
    R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(best[1] * 30), 4, "Y") @ Matrix.Translation(-h)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ base
bpy.ops.object.mode_set(mode="OBJECT")
hz = hand_z()

# --- collision bodies: bake the posed body / head / hair proxy to static meshes
def bake(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_world)
    ob = bpy.data.objects.new(o.name + "_COL", me)
    sc.collection.objects.link(ob)
    return ob
cols = [bake(o) for o in (body, head, hair)]
for o in (body, head, hair):
    bpy.data.objects.remove(o, do_unlink=True)
for c in cols:
    c.modifiers.new("Collision", "COLLISION")
    c.collision.thickness_outer = 0.008
    c.collision.cloth_friction = 5.0
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
floor = bpy.context.object; floor.name = "PILOT_Floor"; floor.modifiers.new("Collision", "COLLISION")

# neck centre / radius from the baked body
neck_z = (arm.matrix_world @ arm.data.bones["neck_01"].head_local).z
ring = []
for c in cols[:2]:
    ring += [v.co[:] for v in c.data.vertices if abs(v.co.z - neck_z) < 0.012 and math.hypot(v.co.x, v.co.y - (arm.matrix_world @ arm.data.bones["neck_01"].head_local).y) < 0.12]
print("NECK", neck_z, len(ring))
ring = np.array(ring)
nc = ring[:, :2].mean(0); nr = float(np.percentile(np.linalg.norm(ring[:, :2] - nc, axis=1), 90))

# --- flat pattern: a 330-degree circle-cut cape with a front opening, neck hole r = neck + 2 cm, cut radius 1.30 m
R_OUT, R_IN, SP = 1.68, nr + 0.02, 0.028
bm = bmesh.new()
nr_rings = int((R_OUT - R_IN) / SP)
ang0, ang1 = math.radians(-90 + 15), math.radians(270 - 15)   # opening centred on the front (-Y)
rows = []
for i in range(nr_rings + 1):
    r = R_IN + (R_OUT - R_IN) * i / nr_rings
    nseg = max(12, int((ang1 - ang0) * r / SP))
    rows.append([bm.verts.new((nc[0] + r * math.cos(ang0 + (ang1 - ang0) * k / nseg), nc[1] + r * math.sin(ang0 + (ang1 - ang0) * k / nseg), 0.0)) for k in range(nseg + 1)])
bm.verts.ensure_lookup_table()
# triangulate between consecutive rings with different counts
for a, b in zip(rows, rows[1:]):
    i = j = 0
    while i < len(a) - 1 or j < len(b) - 1:
        if j < len(b) - 1 and (i >= len(a) - 1 or (j + 1) / (len(b) - 1) < (i + 1) / (len(a) - 1)):
            bm.faces.new((a[i], b[j], b[j + 1])); j += 1
        else:
            bm.faces.new((a[i], b[j], a[i + 1])); i += 1
me = bpy.data.meshes.new("PILOT_CapePattern"); bm.to_mesh(me); bm.free()
cape = bpy.data.objects.new("PILOT_Cape", me); sc.collection.objects.link(cape)
# place the flat pattern: neck ring at the neck base, the rest pre-shaped as a shallow cone over the shoulders (so it starts outside the body)
shoulder_z = (arm.matrix_world @ arm.data.bones["clavicle_l"].head_local).z
for v in me.vertices:
    d = math.hypot(v.co.x - nc[0], v.co.y - nc[1])
    v.co.z = neck_z + 0.02 - 0.55 * max(0.0, d - R_IN) * 0.5 + 0.06
    # cone: keep lengths ~ flat (small slope), the solver does the rest
pin = cape.vertex_groups.new(name="PIN")
pin.add([v.index for v in me.vertices if math.hypot(v.co.x - nc[0], v.co.y - nc[1]) < R_IN + 0.5 * SP], 1.0, "REPLACE")
cm = cape.modifiers.new("Cloth", "CLOTH")
s = cm.settings
s.quality = 6; s.mass = 0.45; s.air_damping = 1.0
s.tension_stiffness = 40; s.compression_stiffness = 40; s.shear_stiffness = 20; s.bending_stiffness = 0.8
s.vertex_group_mass = "PIN"; s.pin_stiffness = 1.0
cm.collision_settings.distance_min = 0.006; cm.collision_settings.collision_quality = 3
cm.collision_settings.use_self_collision = True; cm.collision_settings.self_distance_min = 0.004
FR = 200
sc.frame_start = 1; sc.frame_end = FR
cm.point_cache.frame_start = 1; cm.point_cache.frame_end = FR
t1 = time.time()
per = []
for f in range(1, FR + 1):
    ts = time.time(); sc.frame_set(f); per.append(time.time() - ts)
t2 = time.time()
dg = bpy.context.evaluated_depsgraph_get()
res_me = bpy.data.meshes.new_from_object(cape.evaluated_get(dg))
res = bpy.data.objects.new("PILOT_CapeDraped", res_me); sc.collection.objects.link(res); res_me.shade_smooth()
cape.hide_render = True; cape.hide_viewport = True

# --- measure: penetration vs body, fold-over / undercut (the height-field test the ChatGPT panels score 0.000 on), hem to floor
cbm = bmesh.new(); cbm.from_mesh(cols[0].data); tree = BVHTree.FromBMesh(cbm)
inside = 0; deep = 0.0
for v in res_me.vertices:
    hit, n, i, d = tree.find_nearest(v.co, 0.3)
    if hit is not None and (v.co - hit).dot(n) < 0:
        inside += 1; deep = max(deep, d)
rbm = bmesh.new(); rbm.from_mesh(res_me)
area = np.array([f.calc_area() for f in rbm.faces]); nrm = np.array([f.normal[:] for f in rbm.faces]); cen = np.array([f.calc_center_median()[:] for f in rbm.faces])
radv = cen[:, :2] - nc; radv /= np.maximum(np.linalg.norm(radv, axis=1, keepdims=True), 1e-9)
nrd = (nrm[:, :2] * radv).sum(1); maj = np.sign((nrd * area).sum())
undercut = float(area[np.sign(nrd) == -maj].sum() / area.sum())
front = cen[:, 1] < nc[1] - 0.05
ny = nrm[front, 1]; fa = area[front]; mj = np.sign((ny * fa).sum())
fold_front = float(fa[np.sign(ny) == -mj].sum() / fa.sum())
zs = np.array([v.co.z for v in res_me.vertices])
# edge strain vs the flat pattern (draped cloth should stay near its cut lengths)
pat = [v.co.copy() for v in me.vertices]
rest = np.array([(me.vertices[e.vertices[0]].co - me.vertices[e.vertices[1]].co).length for e in me.edges])
# rest pattern coords are the pre-shaped cone; use the flat XY distance as the cut length
flat = np.array([math.hypot(me.vertices[e.vertices[0]].co.x - me.vertices[e.vertices[1]].co.x, me.vertices[e.vertices[0]].co.y - me.vertices[e.vertices[1]].co.y) for e in me.edges])
drp = np.array([(res_me.vertices[e.vertices[0]].co - res_me.vertices[e.vertices[1]].co).length for e in res_me.edges])
strain = drp / np.maximum(flat, 1e-6)

# --- workbench renders front / 3-4 / side
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "OBJECT"
sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 600, 900
for o in bpy.data.objects:
    if o.type == "MESH":
        o.color = (0.8, 0.68, 0.6, 1) if o.name.endswith("_COL") else ((0.9, 0.9, 0.9, 1) if o is floor else (0.16, 0.16, 0.18, 1))
camd = bpy.data.cameras.new("PILOT_Cam"); camd.type = "ORTHO"; camd.ortho_scale = 2.1
cam = bpy.data.objects.new("PILOT_Cam", camd); sc.collection.objects.link(cam); sc.camera = cam
shots = []
for name, yaw in (("front", 0), ("q34", 35), ("side", 90), ("back", 180)):
    a = math.radians(yaw)
    cam.location = (5 * math.sin(a), -5 * math.cos(a), 0.95); cam.rotation_euler = (math.radians(90), 0, a)
    p = os.path.join(OUT, "path_pilot_drape_%s.png" % name); sc.render.filepath = p
    bpy.ops.render.render(write_still=True); shots.append(p)
report = {
    "pattern": {"type": "330-deg circle-cut cape, front opening, flat cut", "R_out_m": R_OUT, "R_in_m": round(R_IN, 3), "spacing_m": SP,
                "verts": len(me.vertices), "tris": len(me.polygons)},
    "arms_down_hand_z_m": [round(z, 3) for z in hz],
    "solver": {"frames": FR, "quality": 6, "self_collision": True, "sim_seconds": round(t2 - t1, 1),
               "sec_per_frame_mean": round(float(np.mean(per)), 3), "sec_per_frame_max": round(float(np.max(per)), 3)},
    "result": {"verts_inside_body": inside, "deepest_cm": round(deep * 100, 2), "z_min_m": round(float(zs.min()), 3), "z_max_m": round(float(zs.max()), 3),
               "radial_undercut_area_frac": round(undercut, 4), "front_foldover_area_frac": round(fold_front, 4),
               "edge_strain_vs_flat_cut_p5_p50_p95": [round(float(np.percentile(strain, q)), 3) for q in (5, 50, 95)]},
    "total_seconds": round(time.time() - t0, 1), "renders": shots,
}
json.dump(report, open(os.path.join(OUT, "path_pilot_drape_report.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "path_pilot_drape.blend"), copy=True)
print("PILOT", json.dumps(report))
