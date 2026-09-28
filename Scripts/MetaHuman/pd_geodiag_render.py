"""pd_geodiag_render.py -- Blender (headless) close-up renders of the MetaHuman mesh dumps for the geometry diagnosis.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P Scripts/MetaHuman/pd_geodiag_render.py

Only OBJ dumps are read (numpy loader, no .blend opened, nothing saved except PNGs).
UE dumps are left-handed (X fwd... here: character faces +Y, left = +X, Z up). To get images that match the UE
captures (image-left = -X), vertices are mirrored y -> -y; that mirror also turns the dump's winding outward.
Cameras / lights are given in UE coordinates and converted the same way.
Output: WorkFiles/MetaHuman/player_default/geodiag/renders/*.png
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, apply, kabsch, load_obj  # noqa: E402

NH = 24049
RDIR = OUT / "renders"
RDIR.mkdir(parents=True, exist_ok=True)
ONLY = [s for s in os.environ.get("PD_GEO_VIEWS", "").split(",") if s]

# ------------------------------------------------------------------ scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type in ("OPTIX",)
    scene.cycles.device = "GPU"
except Exception as exc:  # noqa: BLE001
    print("GPU setup failed, CPU:", exc)
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
# optional UE-SkyLight-like world: upper hemisphere grey, lower hemisphere black (UE SkyLight default
# 'Lower Hemisphere Is Solid Color' = black). Switched in/out by rig(); Fac=1 -> lower hemisphere black.
_wn = world.node_tree.nodes
_tc = _wn.new("ShaderNodeTexCoord")
_sx = _wn.new("ShaderNodeSeparateXYZ")
_gt = _wn.new("ShaderNodeMath")
_gt.operation = "GREATER_THAN"
_gt.inputs[1].default_value = 0.0
_mix = _wn.new("ShaderNodeMix")
_mix.data_type = "RGBA"
world.node_tree.links.new(_tc.outputs["Generated"], _sx.inputs[0])
world.node_tree.links.new(_sx.outputs["Z"], _gt.inputs[0])
LHB_MIX = _mix


def ue2bl(p):
    return Vector((p[0], -p[1], p[2]))


def make_mesh(name, V, F, mat):
    V = np.asarray(V, dtype=np.float64).copy()
    V[:, 1] *= -1.0
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3)
    me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.validate()
    me.shade_smooth()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def plain_material(name, rgb, rough=0.45, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    return m


def backface_material(name):
    """front faces grey, back faces (seen from the camera) saturated red -> exposes folds / flipped normals."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    b.inputs["Roughness"].default_value = 0.6
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    red = nt.nodes.new("ShaderNodeEmission")
    red.inputs["Color"].default_value = (1, 0, 0, 1)
    red.inputs["Strength"].default_value = 2.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(b.outputs["BSDF"], mix.inputs[1])
    nt.links.new(red.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


SKIN = plain_material("skin_plain", (0.62, 0.45, 0.37))
BACK = backface_material("backface_red")

# ------------------------------------------------------------------ subjects
M = {k: load_obj(p) for k, p in DUMPS.items()}
F_face = M["kelvin_Face"][1]
FH = F_face[np.all(F_face < NH, axis=1)]
R, t, s = kabsch(M["kelvin_Face"][0][:NH], M["FaceC_Face"][0][:NH], scale=True)
subjects = {
    "FaceC": [(M["FaceC_Face"][0][:NH], FH), M["FaceC_Body"]],
    "ref": [(M["ref_Face"][0][:NH], FH), M["ref_Body"]],
    "Kelvin": [(apply(R, t, s, M["kelvin_Face"][0][:NH]), FH),
               (apply(R, t, s, M["kelvin_Body"][0]), M["kelvin_Body"][1])],
    "source": [M["source"]],
}
objs = {}
for sname, parts in subjects.items():
    objs[sname] = [make_mesh(f"{sname}_{i}", V, F, SKIN) for i, (V, F) in enumerate(parts)]


def show(sname):
    for k, obs in objs.items():
        for o in obs:
            o.hide_render = k != sname


def set_material(mat):
    for obs in objs.values():
        for o in obs:
            o.data.materials[0] = mat


# ------------------------------------------------------------------ lights
LIGHTS = []


def clear_lights():
    for o in LIGHTS:
        bpy.data.objects.remove(o, do_unlink=True)
    LIGHTS.clear()


def sun(direction_ue, strength, color=(1, 1, 1), shadows=True, angle_deg=0.5):
    d = ue2bl(direction_ue).normalized()
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle_deg)
    ld.use_shadow = shadows
    ob = bpy.data.objects.new("sun", ld)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)
    LIGHTS.append(ob)


def ue_dir(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))


def rig(name):
    clear_lights()
    links = world.node_tree.links
    for l in list(bg.inputs["Color"].links):
        links.remove(l)
    scene.cycles.max_bounces = 12
    if name == "ue_lhb_nogi":            # + no bounce light, like the UE captures (r.DynamicGlobalIlluminationMethod 0)
        scene.cycles.max_bounces = 0
        name = "ue_lhb"
    if name == "ue_lhb":
        LHB_MIX.inputs["A"].default_value = (0, 0, 0, 1)
        LHB_MIX.inputs["B"].default_value = (0.18, 0.18, 0.18, 1)
        links.new(_gt.outputs[0], LHB_MIX.inputs["Factor"])
        links.new(LHB_MIX.outputs["Result"], bg.inputs["Color"])
        name = "ue_sky_only_upper"
    allsh = name == "ue_allshadows"      # same rig but fill + rim also cast shadows
    if allsh:
        name = "ue"
    if name in ("ue", "ue_sky_only_upper"):   # pb_conform.py LIGHT_RIG: (pitch, yaw, roll, intensity, color, shadows) + sky 1.5 on 0.18 grey
        sun(ue_dir(-27, -117), 4.0 * 0.55, (1, .95, .9), True)
        sun(ue_dir(-12, -58), 2.0 * 0.55, (.9, .94, 1), allsh)
        sun(ue_dir(-37, 90), 2.0 * 0.55, (1, 1, 1), allsh)
        bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
        bg.inputs["Strength"].default_value = 1.5
    elif name == "ue_norim":               # UE rig without the rim light
        sun(ue_dir(-27, -117), 4.0 * 0.55, (1, .95, .9), True)
        sun(ue_dir(-12, -58), 2.0 * 0.55, (.9, .94, 1), False)
        bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
        bg.inputs["Strength"].default_value = 1.5
    elif name == "frontbelow":   # neutral single light from the front and below (travels up and back)
        sun((0.0, -0.75, 0.66), 3.0, (1, 1, 1), True, 2.0)
        bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
        bg.inputs["Strength"].default_value = 0.6
    elif name == "front":
        sun((0.0, -1.0, -0.15), 3.0, (1, 1, 1), True, 2.0)
        bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
        bg.inputs["Strength"].default_value = 0.6


# ------------------------------------------------------------------ camera
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 1.0
cam_data.clip_end = 5000.0


def aim(loc_ue, look_ue, fov_deg, w, h):
    loc, look = ue2bl(loc_ue), ue2bl(look_ue)
    cam.location = loc
    cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler()
    cam_data.angle = math.radians(fov_deg)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100


FC = (0.0, 5.959721088409424, 173.6)
a = math.radians(35.0)
VIEWS = {
    # exact UE capture cameras (pb_face_design.face_shots): 70 cm, hfov 30, 1000x1200
    "ue34": ((FC[0] + 70 * math.sin(a), FC[1] + 70 * math.cos(a), FC[2]), FC, 30.0, 1000, 1200),
    "uefront": ((FC[0], FC[1] + 70, FC[2]), FC, 30.0, 1000, 1200),
    # jaw close-ups (character-left jaw = +X, the side where the line shows in the 3/4 capture)
    "jaw34": ((26.0, 34.0, 150.0), (4.0, 3.0, 161.0), 26.0, 1000, 800),
    "chin_below": ((0.0, 42.0, 140.0), (0.0, 4.0, 160.5), 30.0, 1000, 800),
    # image-left (-X) ear
    "earR_front": ((-9.0, 40.0, 173.5), (-9.0, -1.0, 173.5), 17.0, 800, 1000),
    "earR_side": ((-45.0, 2.0, 174.0), (-9.0, -1.0, 173.5), 20.0, 800, 1000),
}
JOBS = [
    ("earR_front", "ue_allshadows", "plain", ("FaceC", "Kelvin")),
    ("earR_front", "ue_norim", "plain", ("FaceC",)),
    ("ue34", "ue_lhb_nogi", "plain", ("FaceC", "Kelvin", "ref", "source")),
    ("uefront", "ue_lhb_nogi", "plain", ("FaceC", "Kelvin", "source")),
    ("jaw34", "ue_lhb_nogi", "plain", ("FaceC", "Kelvin", "source")),
    ("ue34", "ue_lhb", "plain", ("FaceC", "Kelvin", "ref", "source")),
    ("uefront", "ue_lhb", "plain", ("FaceC", "Kelvin", "source")),
    ("jaw34", "ue_lhb", "plain", ("FaceC", "Kelvin")),
    # (view, rig, material, subjects)
    ("ue34", "ue", "plain", ("FaceC", "Kelvin", "ref", "source")),
    ("uefront", "ue", "plain", ("FaceC", "Kelvin", "source")),
    ("jaw34", "frontbelow", "plain", ("FaceC", "Kelvin", "ref", "source")),
    ("jaw34", "ue", "plain", ("FaceC", "Kelvin")),
    ("jaw34", "ue", "back", ("FaceC", "Kelvin")),
    ("chin_below", "frontbelow", "plain", ("FaceC", "Kelvin", "source")),
    ("chin_below", "front", "back", ("FaceC", "Kelvin")),
    ("earR_front", "ue", "plain", ("FaceC", "Kelvin", "source")),
    ("earR_side", "front", "plain", ("FaceC", "Kelvin")),
    ("earR_front", "ue", "back", ("FaceC",)),
]
for view, rname, mname, subs in JOBS:
    if ONLY and view not in ONLY:
        continue
    rig(rname)
    set_material(SKIN if mname == "plain" else BACK)
    aim(*VIEWS[view])
    for sname in subs:
        show(sname)
        scene.render.filepath = str(RDIR / f"{view}_{rname}_{mname}_{sname}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", scene.render.filepath)
print("DONE")
