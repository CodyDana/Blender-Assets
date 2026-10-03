"""Smoke bomb texture-trim comparison (test only; touches no shipped file).

Renders the shipped LOD0 with its shipped maps (BaseColor 4096) and again with the BaseColor halved to 2048 (normal and
ORM are already 2048), at first-person hand distance and as a frame-filling close-up, then composes one side-by-side
sheet: left = current, right = trimmed.
    blender -b --factory-startup --python sb_trim_compare.py
"""
import os

import bpy
import numpy as np

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
EXP = ROOT + "/Exports/SmokeBomb"
OUT = ROOT + "/WorkFiles/smokebomb/trim_test"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=EXP + "/SM_SmokeBomb.fbx")
for o in list(sc.objects):
    if o.name != "SM_SmokeBomb_LOD0":
        bpy.data.objects.remove(o, do_unlink=True)
ob = sc.objects["SM_SmokeBomb_LOD0"]
ob.parent = None
ob.location = (0, 0, 0)
ob.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
mn = np.min([ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box], axis=0)
mx = np.max([ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box], axis=0)
centre = (mn + mx) / 2


def load(name, colour):
    im = bpy.data.images.load(EXP + "/Textures/" + name)
    im.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return im


bc_full = load("T_SmokeBomb_BC.png", True)
bc_half = bc_full.copy()
bc_half.name = "BC_2048"
bc_half.scale(2048, 2048)
orm = load("T_SmokeBomb_ORM.png", False)
nrm = load("T_SmokeBomb_N.png", False)

mat = bpy.data.materials.new("SB_Test")
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
nt.links.new(bsdf.outputs[0], out.inputs[0])
t_bc = nt.nodes.new("ShaderNodeTexImage")
t_orm = nt.nodes.new("ShaderNodeTexImage")
t_orm.image = orm
t_n = nt.nodes.new("ShaderNodeTexImage")
t_n.image = nrm
for t in (t_bc, t_orm, t_n):
    t.interpolation = "Cubic"
sep = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(t_orm.outputs[0], sep.inputs[0])
ao_mix = nt.nodes.new("ShaderNodeMix")
ao_mix.data_type = "RGBA"
ao_mix.blend_type = "MULTIPLY"
ao_mix.inputs["Factor"].default_value = 1.0
nt.links.new(t_bc.outputs[0], ao_mix.inputs["A"])
nt.links.new(sep.outputs[0], ao_mix.inputs["B"])
nt.links.new(ao_mix.outputs["Result"], bsdf.inputs["Base Color"])
nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
# DirectX normal map: flip green for Blender (OpenGL)
sepn = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(t_n.outputs[0], sepn.inputs[0])
inv = nt.nodes.new("ShaderNodeMath")
inv.operation = "SUBTRACT"
inv.inputs[0].default_value = 1.0
nt.links.new(sepn.outputs[1], inv.inputs[1])
comb = nt.nodes.new("ShaderNodeCombineColor")
nt.links.new(sepn.outputs[0], comb.inputs[0])
nt.links.new(inv.outputs[0], comb.inputs[1])
nt.links.new(sepn.outputs[2], comb.inputs[2])
nmap = nt.nodes.new("ShaderNodeNormalMap")
nt.links.new(comb.outputs[0], nmap.inputs["Color"])
nt.links.new(nmap.outputs[0], bsdf.inputs["Normal"])
ob.data.materials.clear()
ob.data.materials.append(mat)

world = bpy.data.worlds.new("W")
sc.world = world
world.color = (0.18, 0.18, 0.19)
key = bpy.data.lights.new("Key", "AREA")
key.energy = 40
key.size = 0.5
kobj = bpy.data.objects.new("Key", key)
sc.collection.objects.link(kobj)
kobj.location = (centre[0] - 0.5, centre[1] - 0.6, centre[2] + 0.6)
kobj.rotation_euler = (0.9, 0, -0.7)

cam_d = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam

sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception as e:  # CPU fallback
    print("GPU setup failed:", e)
sc.cycles.samples = 512
sc.cycles.use_denoising = False
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.image_settings.file_format = "PNG"

ball = float(np.max(mx - mn))
shots = {
    # first person: ~35 cm from the eye, 90 deg horizontal field of view
    "hand": (0.35, 90.0),
    # frame-filling close-up: ball about 90 % of the frame height
    "closeup": (None, 30.0),
}
results = {}
for shot, (dist, hfov) in shots.items():
    cam_d.sensor_fit = "HORIZONTAL"
    cam_d.angle = np.radians(hfov)
    if dist is None:
        vfov = 2 * np.arctan(np.tan(np.radians(hfov) / 2) * 1080 / 1920)
        dist = (ball / 0.9) / 2 / np.tan(vfov / 2)
    direction = np.array([0.55, -1.0, 0.35])
    direction /= np.linalg.norm(direction)
    cam.location = tuple(centre + direction * dist)
    look = __import__("mathutils").Vector(tuple(centre - np.array(cam.location)))
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    for label, img in (("current", bc_full), ("trimmed", bc_half)):
        t_bc.image = img
        path = f"{OUT}/sb_{shot}_{label}.png"
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        results[(shot, label)] = path
        print("rendered", path, "dist m", round(dist, 3))


def pixels(path):
    im = bpy.data.images.load(path)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    bpy.data.images.remove(im)
    return a


def crop_ball(a, frac):
    """Square crop around the ball's visible extent, padded by frac."""
    lum = a[..., :3].mean(-1)
    bg = np.median(np.concatenate([lum[:5].ravel(), lum[-5:].ravel()]))
    ys, xs = np.where(np.abs(lum - bg) > 0.02)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    half = int(max(ys.max() - ys.min(), xs.max() - xs.min()) * (0.5 + frac))
    return a[max(cy - half, 0):cy + half, max(cx - half, 0):cx + half]


def fit(a, size):
    """Nearest-neighbour resize to size x size (keeps pixels honest: no smoothing)."""
    h, w = a.shape[:2]
    yi = (np.arange(size) * h / size).astype(int)
    xi = (np.arange(size) * w / size).astype(int)
    return a[yi][:, xi]


tile = 900
rows = []
# row 1: hand distance, the ball's real pixels enlarged (nearest neighbour)
for shot, frac, zoom_part in (("hand", 0.15, None), ("closeup", 0.05, None), ("closeup", 0.0, 0.33)):
    pair = []
    for label in ("current", "trimmed"):
        a = pixels(results[(shot, label)])
        if zoom_part:
            h, w = a.shape[:2]
            s = int(h * zoom_part)
            a = a[h // 2 - s // 2 + int(h * 0.05):h // 2 + s // 2 + int(h * 0.05), w // 2 - s // 2:w // 2 + s // 2]
        else:
            a = crop_ball(a, frac)
        pair.append(fit(a, tile))
    gap = np.ones((tile, 20, 4), np.float32)
    rows.append(np.concatenate([pair[0], gap, pair[1]], axis=1))
vgap = np.ones((20, rows[0].shape[1], 4), np.float32)
sheet = np.concatenate([rows[0], vgap, rows[1], vgap, rows[2]], axis=0)
sheet[..., 3] = 1.0
H, W = sheet.shape[:2]
out_im = bpy.data.images.new("sheet", W, H, alpha=True)
out_im.pixels = sheet.ravel()
out_im.filepath_raw = OUT + "/SmokeBomb_TextureTrim_SideBySide.png"
out_im.file_format = "PNG"
out_im.save()
print("SHEET", out_im.filepath_raw, W, H)
