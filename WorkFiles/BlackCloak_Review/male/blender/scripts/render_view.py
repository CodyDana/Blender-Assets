"""One render of the review scene. args after --:
   tag view(ref|front|q34|side_r|side_l|back) body(0|1) pose(rest|down) mat(game|tiled) mult(res multiple of 417x674) samples
Writes renders/<tag>_raw.png (Cycles, Standard view transform, film transparent + shadow catcher), renders/<tag>.png (over white,
composited in linear), renders/<tag>_mask.png (Workbench: cloak black, torso yellow, arms green, legs red, head/hair blue) and
renders/<tag>.json (camera, lights, calibration, pixel stats)."""
import sys, os, json, bpy, math
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from imgutil import load, save, lum

a = sys.argv[sys.argv.index("--") + 1:]
tag, view, body_on, pose, mat, mult, samples = a[0], a[1], a[2] == "1", a[3], a[4], int(a[5]), int(a[6])
OUT = D + "renders/"
info = {"tag": tag, "view": view, "body": body_on, "pose": pose, "mat": mat, "mult": mult, "samples": samples}
sc = bpy.context.scene
arm = bpy.data.objects["root"]
cl = cloak()

# ---- pose (arms only; the cloak is weighted to spine_03..head, so it does not follow)
if pose == "down":
    info["arm_rotations_deg"] = pose_arms_down(arm)
bpy.context.view_layer.update()
hl = arm.matrix_world @ arm.pose.bones["hand_l"].head; hr = arm.matrix_world @ arm.pose.bones["hand_r"].head
info["hand_l_world"] = list(hl); info["hand_r_world"] = list(hr)

# ---- material variant
if mat == "tiled":
    tm = bpy.data.materials[cl["tiled_material"]]
    for s in cl.material_slots:
        if s.material and s.material.name.startswith("GAME_M_BlackCloak_UV0"):
            s.material = tm
info["wool_material"] = [s.material.name for s in cl.material_slots]

set_visible(True, body_on)

# ---- camera
fit = json.load(open(D + "logs/camfit_male_refine3_constrained.json"))
best = fit["top"][0]; tgt = Vector(fit["target"]); Hh = fit["height_m"]
if view == "ref":
    f, yaw, pitch = best[1], best[2], best[3]
else:
    f, pitch = 85.0, 0.0
    yaw = {"front": 0.0, "q34": -40.0, "q34_other": 40.0, "side_r": -90.0, "side_l": 90.0, "back": 180.0}.get(view, 0.0)
dist = (Hh / 2 * 1.08) / (12 / f)
if view != "ref" and body_on:
    tgt = Vector((tgt.x, tgt.y, 0.93)); dist = (1.90 / 2 * 1.06) / (12 / f)
if view.startswith("macro"):
    # close-range fabric look (in-game close camera distance): mantle below the clasp, and the long front panel
    f, yaw, pitch = 50.0, -18.0, 2.0
    tgt = Vector({"macro_mantle": (0.02, -0.22, 1.22), "macro_panel": (0.05, -0.30, 0.80)}[view]); dist = 0.75
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, idx, obj, mtx = sc.ray_cast(dg, Vector((tgt.x, -3.0, tgt.z)), Vector((0, 1, 0)))
    info["macro_hit"] = [hit, list(loc), obj.name if obj else None]
    if hit: tgt = loc
cam = make_camera(tgt, yaw, pitch, f, dist)
info["camera"] = {"focal_mm": f, "sensor_h_mm": 24, "yaw": yaw, "pitch": pitch, "dist_m": dist, "target": list(tgt), "loc": list(cam.location)}
W, H = REF_W * mult, REF_H * mult
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100

# ---- studio: floor shadow catcher, soft product lights
floor_me = bpy.data.meshes.new("REV_Floor")
import bmesh
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6); bm.to_mesh(floor_me); bm.free()
floor = bpy.data.objects.new("REV_Floor", floor_me); sc.collection.objects.link(floor)
floor.location = (0, 0, 0.0); floor.is_shadow_catcher = True
w = bpy.data.worlds.new("REV_World"); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (1, 1, 1, 1)
AMB = 4.0; bg.inputs[1].default_value = AMB
lights = []
def area(name, loc, size, power, aim):
    l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size = size[0]; l.size_y = size[1]; l.energy = power
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); lights.append(o); return o
c = Vector((0, 0, 1.0))
# the key/fill ride with the camera yaw so every view gets the same product lighting
yr = math.radians(yaw)
def rot(v):
    return Vector((v.x * math.cos(yr) - v.y * math.sin(yr), v.x * math.sin(yr) + v.y * math.cos(yr), v.z))
area("REV_Key", c + rot(Vector((-1.6, -3.0, 1.4))), (3.0, 3.0), 1000, c)
area("REV_Fill", c + rot(Vector((1.9, -2.8, 0.5))), (3.0, 3.0), 350, c)
area("REV_Top", c + Vector((0, 0, 3.0)), (2.5, 2.5), 400, Vector((0, 0, 0)))

sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = (d.type == "OPTIX")
    sc.cycles.device = "GPU"; info["device"] = "OPTIX"
except Exception as e:
    info["device"] = "CPU (%s)" % e
sc.cycles.use_denoising = True
try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception: pass
sc.cycles.max_bounces = 8
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "16"

# ---- calibration: a white Lambertian card at chest height facing the camera must read ~0.90 linear
hidden = {}
for o in sc.objects:
    if o.type == "MESH":
        hidden[o.name] = o.hide_render; o.hide_render = True
card_me = bpy.data.meshes.new("REV_Card"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.3); bm.to_mesh(card_me); bm.free()
card = bpy.data.objects.new("REV_Card", card_me); sc.collection.objects.link(card)
cm = bpy.data.materials.new("REV_White"); cm.use_nodes = True
cb = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED"); cb.inputs["Base Color"].default_value = (1, 1, 1, 1)
cb.inputs["Roughness"].default_value = 1.0; cb.inputs["Specular IOR Level"].default_value = 0.0
card.data.materials.append(cm)
card.location = c + rot(Vector((0, -0.3, 0.25))); card.rotation_euler = (cam.location - card.location).to_track_quat("Z", "Y").to_euler()
sc.render.resolution_x, sc.render.resolution_y = 64, 104
sc.cycles.samples = 64
tmp = OUT + "_cal_%s.png" % tag
sc.view_settings.exposure = -4.0
sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
sc.view_settings.exposure = 0.0
from bpy_extras.object_utils import world_to_camera_view
pc = world_to_camera_view(sc, cam, card.location); cx, cy = int(pc.x * 64), int((1 - pc.y) * 104)
im = load(tmp); cen = im[cy - 2:cy + 3, cx - 2:cx + 3, :3]
info["cal_card_px"] = [cx, cy, float(im[cy, cx, 3])]
cal = float(np.mean(srgb_to_lin(cen))) * 16.0
os.remove(tmp)
k = 0.90 / max(cal, 1e-4)
if view.startswith("macro"):  # the chest card is off-frame for a macro camera: reuse the reference-camera calibration (same yaw)
    k = json.load(open(OUT + "a_ref_cloak_game.json"))["calibration"]["scale"]
for o in lights: o.data.energy *= k
bg.inputs[1].default_value = AMB * k
info["calibration"] = {"white_card_linear_before": cal, "scale": k, "energies_W": {o.name: o.data.energy for o in lights}, "world_strength": AMB * k}
bpy.data.objects.remove(card, do_unlink=True)
for n, hr_ in hidden.items(): bpy.data.objects[n].hide_render = hr_
sc.render.resolution_x, sc.render.resolution_y = W, H

# ---- beauty
sc.cycles.samples = samples
raw = OUT + tag + "_raw.png"; sc.render.filepath = raw
import time; t0 = time.time(); bpy.ops.render.render(write_still=True); info["render_s"] = time.time() - t0
im = load(raw)
rgb = srgb_to_lin(im[..., :3]); al = im[..., 3:4]
comp = lin_to_srgb(rgb * al + (1 - al))
save(comp, OUT + tag + ".png")

# ---- workbench region mask with the same camera
floor.hide_render = True
for o in lights: o.hide_render = True
body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]
if body_on:
    me = body.data
    ca = me.color_attributes.new("REV_Region", "BYTE_COLOR", "POINT")
    names = {g.index: g.name for g in body.vertex_groups}
    for v in me.vertices:
        g = max(v.groups, key=lambda gg: gg.weight, default=None)
        n = names.get(g.group, "") if g else ""
        if any(t in n for t in ("thigh", "calf", "foot", "ball", "knee", "ankle", "toe")):
            col = (1, 0, 0, 1)
        elif any(t in n for t in ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky", "elbow", "wrist")):
            col = (0, 1, 0, 1)
        elif any(t in n for t in ("neck", "head")):
            col = (0, 0, 1, 1)
        else:
            col = (1, 1, 0, 1)
        ca.data[v.index].color = col
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.find("REV_Region")
for o in body_objs():
    if o is not body:
        o.color = (0, 0, 1, 1)
cl.color = (0, 0, 0, 1)
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "OBJECT"
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.color_depth = "8"
sc.display.render_aa = "OFF"
mpath = OUT + tag + "_mask_obj.png"; sc.render.filepath = mpath; bpy.ops.render.render(write_still=True)
if body_on:
    # second pass: body coloured by region (vertex colours), cloak still black
    sc.display.shading.color_type = "VERTEX"
    for s in cl.material_slots: pass
    ca2 = cl.data.color_attributes.new("REV_Black", "BYTE_COLOR", "POINT")
    for i in range(len(cl.data.vertices)): ca2.data[i].color = (0, 0, 0, 1)
    cl.data.color_attributes.active_color = ca2
    for o in body_objs():
        if o is not body:
            ca3 = o.data.color_attributes.new("REV_Blue", "BYTE_COLOR", "POINT")
            for i in range(len(o.data.vertices)): ca3.data[i].color = (0, 0, 1, 1)
            o.data.color_attributes.active_color = ca3
    mpath2 = OUT + tag + "_mask.png"; sc.render.filepath = mpath2; bpy.ops.render.render(write_still=True)
    m = load(mpath2)
    A = m[..., 3] > 0.5; R, G, B = m[..., 0] > 0.5, m[..., 1] > 0.5, m[..., 2] > 0.5
    regions = {"legs_red": A & R & ~G & ~B, "arms_green": A & G & ~R & ~B, "torso_yellow": A & R & G & ~B, "head_blue": A & B & ~R & ~G}
    stats = {}
    for n, mm in regions.items():
        ys, xs = np.nonzero(mm)
        stats[n] = {"px": int(mm.sum()), "px_at_ref_scale": float(mm.sum() / mult / mult),
                    "bbox_xyxy_render_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None}
    info["visible_body_by_region"] = stats
    info["cloak_px"] = int((A & ~R & ~G & ~B).sum())
json.dump(info, open(OUT + tag + ".json", "w"), indent=1, default=str)
print("INFO", json.dumps(info, default=str)[:3000])
