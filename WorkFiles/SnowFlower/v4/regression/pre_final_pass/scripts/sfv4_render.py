"""Snow Flower v4 renders - always from the SHIPPED game blend with its BAKED maps (image textures).

    blender -b Assets/SnowFlower/SnowFlower_Game_v4.blend --factory-startup --python sfv4_render.py -- --set <set> --out <dir>

Sets:
    refviews   front / side / back orthographic at the sheet's own scale (1.04257 mm per px), sheet-like
               studio light on white -> <out>/ref_<view>.png (+ alpha mask ref_<view>_mask.png)
    details    guard / blade / pommel close-ups framed like the sheet's three detail crops
    gallery    hero 3/4, wireframe, LOD strip
    fbx        the same refviews but from a re-import of the exported FBX (proves the shipped bytes)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_spec as S  # noqa: E402

ROOT = HERE.parents[2]

MMPX = S.MM_PER_PX
SHEET = {  # view: (axis column in the sheet, crop half width px)
    "front": 287.5, "side": 489.0, "back": 681.0}
RENDER_W = 300
RENDER_H = 1287


def gpu():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        sc.cycles.device = "CPU"


def world_studio(bg=(1, 1, 1), bg_strength=1.0, env_top=0.95, env_mid=0.55, env_bot=0.18, env_strength=1.0):
    """Camera sees a flat background; reflections see a top-bright / bottom-dark studio gradient."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new("SF4_Studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bgc = nt.nodes.new("ShaderNodeBackground")
    bgc.inputs["Color"].default_value = (*bg, 1)
    bgc.inputs["Strength"].default_value = bg_strength
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    # Generated on the world = direction; use the Normal-like z via the "Window"? use Generated z (0..1)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (env_bot, env_bot, env_bot * 1.05, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (env_top, env_top, env_top, 1)
    mid = ramp.color_ramp.elements.new(0.55)
    mid.color = (env_mid, env_mid, env_mid * 1.03, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    env = nt.nodes.new("ShaderNodeBackground")
    env.inputs["Strength"].default_value = env_strength * ENV_SCALE
    nt.links.new(ramp.outputs["Color"], env.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs[0], mix.inputs[1])
    nt.links.new(bgc.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


import os
LIGHT_SCALE = float(os.environ.get("SF4_LIGHT_SCALE", "0.25"))
ENV_SCALE = float(os.environ.get("SF4_ENV_SCALE", "1.0"))


def area(name, loc, target, power, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.energy = power * LIGHT_SCALE
    l.size = size
    l.color = color
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def lights_sheet(center_z, size=1.0):
    zc = center_z
    # side-placed softboxes: they rake the relief without mirroring straight back into the dark
    # polished channel (a softbox reflected in a dark metal reads grey, which the sheet's channel is not)
    area("Key", (-1.7, -0.7, zc + 1.1), (0, 0, zc), 300, 1.4 * size, (1.0, 0.98, 0.95))
    area("Fill", (1.7, -0.5, zc + 0.3), (0, 0, zc), 120, 1.4 * size, (0.9, 0.95, 1.0))
    area("Rim", (0.3, 1.6, zc + 0.6), (0, 0, zc), 140, 1.4 * size)
    area("Top", (0.0, 0.2, zc + 1.9), (0, 0, zc), 90, 1.0 * size)


def cam_ortho(view, z_center_mm, x_center_mm, scale_m, w, h):
    sc = bpy.context.scene
    cam = bpy.data.objects.new("SF4_Cam", bpy.data.cameras.new("SF4_Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale_m
    cam.data.clip_start = 0.01
    cam.data.clip_end = 20
    zc = z_center_mm / 1000.0
    xc = x_center_mm / 1000.0
    # every sheet view: pommel at the TOP of the image (camera rolled 180 deg)
    if view == "front":      # camera on -Y looking +Y, image-left = +X
        cam.location = (xc, -5, zc)
        cam.rotation_euler = Euler((math.pi / 2, 0, 0))
    elif view == "back":     # camera on +Y looking -Y, image-left = -X
        cam.location = (xc, 5, zc)
        cam.rotation_euler = Euler((math.pi / 2, 0, math.pi))
    elif view == "side":     # camera on +X (spine side) looking -X, image-left = +Y
        cam.location = (5, xc, zc)
        cam.rotation_euler = Euler((math.pi / 2, 0, math.pi / 2))
    cam.rotation_euler.rotate_axis("Z", math.pi)
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    return cam


def cam_persp(loc, target, lens=85, roll=0.0, w=1600, h=1600, name="SF4_CamP"):
    sc = bpy.context.scene
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    cam.location = loc
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    if roll:
        cam.rotation_euler.rotate_axis("Z", roll)
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    return cam


def base_settings(samples=64, transparent=False):
    sc = bpy.context.scene
    gpu()
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except Exception:  # noqa: BLE001
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"


def show_only_lod(level):
    for o in bpy.data.objects:
        if o.type == "MESH":
            is_lod = o.name.startswith("SM_SnowFlower_LOD")
            o.hide_render = (not is_lod) or (o.name != f"SM_SnowFlower_LOD{level}")
        if o.name.startswith("UCX_"):
            o.hide_render = True


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------- sets

def set_refviews(out: Path, prefix="ref"):
    base_settings(96, transparent=True)
    show_only_lod(0)
    zc = ((RENDER_H - 1) / 2.0 - 10.0) * MMPX + S.Z_POMMEL_TOP
    world_studio(bg=(1, 1, 1), env_top=0.9, env_mid=0.22, env_bot=0.03, env_strength=1.0)
    lights_sheet(zc / 1000.0)
    for view in ("front", "side", "back"):
        # render grid == sheet grid: pixel row r <-> z = (r - 10) * MMPX + Z_POMMEL_TOP, same px size
        scale = RENDER_H * MMPX / 1000.0
        cam = cam_ortho(view, zc, 0.0, scale, RENDER_W, RENDER_H)
        render(out / f"{prefix}_{view}.png")
        bpy.data.objects.remove(cam)


def set_details(out: Path):
    base_settings(128)
    show_only_lod(0)
    world_studio(bg=(1, 1, 1), env_top=1.3, env_mid=0.45, env_bot=0.08)
    g = S.GUARD_BLOSSOM_Z / 1000.0
    lights_sheet(g, size=0.45)
    # guard: sheet crop sees the guard from the front, a little toward the pommel, axis leaning ~12 deg
    cam = cam_persp((0.06, -0.40, g - 0.10), (0.0, 0.0, g + 0.025), lens=85, roll=math.radians(-168), w=1100, h=1400)
    render(out / "detail_guard.png")
    bpy.data.objects.remove(cam)
    # blade: diagonal close-up of the upper blade (first blossom cluster)
    z = 0.26
    cam = cam_persp((0.05, -0.33, z + 0.05), (-0.004, 0.0, z), lens=85, roll=math.radians(-125), w=1600, h=1000)
    render(out / "detail_blade.png")
    bpy.data.objects.remove(cam)
    # pommel: from above the end face at ~40 deg, like the sheet's pommel crop
    zp = S.Z_POMMEL_TOP / 1000.0
    # the end face points DOWN the sword axis (-Z), into the dark floor of the studio gradient: give it
    # its own softboxes (the sheet's pommel crop is lit toward the end face)
    area("PommelKey", (-0.35, -0.30, zp - 0.45), (0, 0, zp), 60, 0.35, (1.0, 0.98, 0.95))
    area("PommelFill", (0.40, -0.10, zp - 0.30), (0, 0, zp), 25, 0.35, (0.9, 0.95, 1.0))
    cam = cam_persp((0.03, -0.12, zp - 0.15), (0.0, 0.0, zp + 0.010), lens=85, roll=math.radians(175), w=1200, h=1100)
    render(out / "detail_pommel.png")
    bpy.data.objects.remove(cam)


def set_gallery(out: Path):
    base_settings(128)
    world_studio(bg=(0.16, 0.17, 0.19), env_top=0.9, env_mid=0.22, env_bot=0.03)
    show_only_lod(0)
    zc = 0.42
    lights_sheet(zc)
    cam = cam_persp((1.05, -1.95, 0.80), (0.02, 0.0, zc), lens=50, roll=math.radians(-62), w=2400, h=1350)
    render(out / "hero.png")
    # wireframe over the hero pose
    for o in bpy.data.objects:
        if o.name == "SM_SnowFlower_LOD0":
            wm = o.modifiers.new("wire", "WIREFRAME")
            wm.thickness = 0.00018
            wm.use_replace = False
            wm.material_offset = 5
            mw = bpy.data.materials.new("SF4_Wire")
            mw.use_nodes = True
            bs = next(n for n in mw.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bs.inputs["Base Color"].default_value = (0.9, 0.55, 0.1, 1)
            bs.inputs["Emission Color"].default_value = (0.9, 0.55, 0.1, 1)
            bs.inputs["Emission Strength"].default_value = 1.5
            while len(o.data.materials) < 5:
                o.data.materials.append(o.data.materials[0])
            o.data.materials.append(mw)
    render(out / "wire.png")
    for o in bpy.data.objects:
        if o.name == "SM_SnowFlower_LOD0":
            o.modifiers.remove(o.modifiers["wire"])
            while len(o.data.materials) > 2:
                o.data.materials.pop()
    bpy.data.objects.remove(cam)
    # LOD strip: the three LODs side by side, front view
    lods = [bpy.data.objects[f"SM_SnowFlower_LOD{i}"] for i in range(3)]
    saved = [o.matrix_world.copy() for o in lods]
    for i, o in enumerate(lods):
        o.hide_render = False
        o.matrix_world = Matrix.Translation((-(i - 1) * 0.16, 0, 0)) @ saved[i]
    cam = cam_ortho("front", 420.0, 0.0, 1.36, 1200, 1600)
    render(out / "lod_strip.png")
    for o, m in zip(lods, saved):
        o.matrix_world = m


def load_shipped_fbx():
    """Fresh scene with ONLY the exported FBX (the shipped bytes) and the shipped PNGs bound by slot name."""
    import sfv4_look as LK
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fbx = ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    tex = ROOT / "Exports" / "SnowFlower" / "v4" / "Textures"
    mats = {}
    for stem, slot in (("T_SnowFlower_Steel", "M_SnowFlower_Steel"), ("T_SnowFlower_Wrap", "M_SnowFlower_Wrap")):
        mats[slot] = LK.make_game_material(slot + "_shipped", tex / f"{stem}_BC.png", tex / f"{stem}_ORM.png", tex / f"{stem}_N.png")
    for o in bpy.data.objects:
        if o.type == "MESH":
            for i, sl in enumerate(o.material_slots):
                name = sl.material.name.split(".")[0] if sl.material else ""
                if name in mats:
                    o.material_slots[i].material = mats[name]
            # the FBX importer names the LOD meshes after their nodes
    return fbx


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if not out.is_absolute():
        out = (ROOT / out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.set == "refviews":
        set_refviews(out)
    elif a.set == "details":
        set_details(out)
    elif a.set == "gallery":
        set_gallery(out)
    elif a.set == "fbx":
        load_shipped_fbx()
        set_refviews(out, prefix="fbx")
    print("SF4_RENDER_DONE", a.set)


if __name__ == "__main__":
    main()
