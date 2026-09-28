#!/usr/bin/env python
"""props_lib.flashbang_look - SM_Flashbang's preview material (from the BAKED maps only) and the renders in the
reference's style: dark grey studio sweep, soft key from the upper right front, one camera photographing four
copies in a row exactly as the reference's top row does (spec 1: one perspective scene, focal ~2600 px on the
1254 px sheet, horizon at row ~460, camera ~14.8 D from the axes), each copy at its own best yaw.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Matrix, Vector

REF_PX = 1254
FOCAL_PX = 2600.0
HORIZON_ROW = 460.0
CAM_DIST_MM = 652.5
#: the four copies' axis x in the reference (spec 1 table) and their contact rows
VIEW_X_PX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
BG_SRGB = (41, 41, 40)


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


# =============================================================================== scene
def setup_cycles(samples=128, res=(REF_PX, REF_PX), denoise=True):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = (d.type == "OPTIX")
        sc.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.cycles.max_bounces = 8
    sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 4
    return sc


def _mat_diffuse(name, rgb, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.3
    return m


class Rig:
    def __init__(self):
        self.objects: List[bpy.types.Object] = []
        self.camera = None
        self.lights = []

    def teardown(self):
        for o in self.objects:
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except Exception:
                pass
        self.objects.clear()


#: light powers (W) calibrated in round 1 so the backdrop and the paint render at the reference's measured values
#: (background sRGB ~45, paint p50 ~70): the first pass (key 60 W) rendered both ~6.5x too bright in linear light.
#: ROUND 2: the reference's bodies are lit from BOTH sides - a key highlight right of centre and a second, weaker
#: highlight left of centre (luminance profiles across v2 / v3 at five heights, WorkFiles/flashbang/r2/tools/
#: r2_light_cal.py: the left half reads 60-100 in the reference, 20-50 with round 1's 0.25 W fill) - so the fill is
#: raised and moved to the front left, the key lowered to keep the paint p50, the floor darkened to keep the backdrop
KEY_W, FILL_W, RIM_W, WORLD = 9.0, 3.5, 4.0, 0.0002
FLOOR_ALBEDO = 0.024
#: ROUND 2: the lights as data - (name, shape, location m, target m, size, size_y, power W, colour).  None = the
#: round-1 rig (a disk key upper right, a weak fill left, a rim behind).  The reference is lit like a product shot
#: with tall STRIP softboxes: a vertical highlight stripe right of centre on every cylinder (paint, cap, brass tubes
#: behind the holes lit evenly top to bottom) and a weaker stripe left of centre.  Round 1's disk key high up could
#: not put a stripe on a vertical cylinder (paint p90 15-29 levels low) and lit the brass through each hole as an
#: oval (the "brass egg").  Calibrated with WorkFiles/flashbang/r2/tools/r2_light_cal2.py (rig "C"): paint p10/p50/
#: p90 and the body's luminance profile at five heights against the reference, backdrop p50 47 vs 45.
LIGHTS = [
    ("FB_KeyStrip", "RECTANGLE", (0.60, -0.55, 0.20), (0.0, 0.0, 0.08), 0.30, 1.2, 10.0, (1.0, 0.96, 0.90)),
    ("FB_Top", "DISK", (0.55, -0.55, 0.62), (0.0, 0.0, 0.08), 0.55, 0.55, 2.0, (1.0, 0.98, 0.95)),
    ("FB_FillStrip", "RECTANGLE", (-0.60, -0.55, 0.20), (0.0, 0.0, 0.08), 0.30, 1.2, 4.0, (1.0, 0.97, 0.93)),
    ("FB_Rim", "DISK", (-0.25, 0.35, 0.45), (0.0, 0.0, 0.1), 0.35, 0.35, 4.0, (1.0, 0.98, 0.95)),
]


def studio(rig: Rig, centre=(0.0, 0.0), backdrop_y=0.28, floor_albedo=FLOOR_ALBEDO, key_w=KEY_W, fill_w=FILL_W, rim_w=RIM_W,
           world=WORLD, scale=1.0, floor=True, bg_lin=None):
    """Dark sweep (floor + curved back wall), soft key upper-right-front, weak fill left, rim behind."""
    cx, cy = centre
    # floor + sweep as one bent plane
    me = bpy.data.meshes.new("FB_Sweep")
    verts, faces = [], []
    W = 3.0 * scale
    prof = []
    R = 0.25 * scale
    for i in range(0, 13):
        a = math.radians(90.0 * i / 12)
        prof.append((backdrop_y * scale - R + R * math.sin(a), R - R * math.cos(a)))
    prof = [(-2.0 * scale, 0.0)] + prof + [(backdrop_y * scale, 2.5 * scale)]
    for j, (y, z) in enumerate(prof):
        verts += [(cx - W, cy + y, z), (cx + W, cy + y, z)]
        if j:
            k = 2 * j
            faces.append((k - 2, k - 1, k + 1, k))
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    ob = bpy.data.objects.new("FB_Sweep", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(_mat_diffuse("FB_SweepMat", (floor_albedo,) * 3, 0.85))
    rig.objects.append(ob)
    if not floor:
        ob.hide_render = True
    w = bpy.data.worlds.new("FB_World")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (world, world, world * 0.98, 1.0)
    if bg_lin is not None:
        # a camera-only background (no floor): what the camera sees behind the object, not what lights it
        lp = w.node_tree.nodes.new("ShaderNodeLightPath")
        bg2 = w.node_tree.nodes.new("ShaderNodeBackground")
        bg2.inputs["Color"].default_value = (bg_lin, bg_lin, bg_lin * 0.98, 1.0)
        mix = w.node_tree.nodes.new("ShaderNodeMixShader")
        outn = next(n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD")
        w.node_tree.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        w.node_tree.links.new(bg.outputs[0], mix.inputs[1])
        w.node_tree.links.new(bg2.outputs[0], mix.inputs[2])
        w.node_tree.links.new(mix.outputs[0], outn.inputs[0])
    bpy.context.scene.world = w

    def area(name, loc, target, size, power, colour=(1.0, 0.98, 0.95)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "DISK"
        ld.size = size
        ld.energy = power
        ld.color = colour
        lo = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = Vector(loc)
        d = Vector(target) - lo.location
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        rig.objects.append(lo)
        rig.lights.append(lo)
        return lo

    s = scale
    if LIGHTS is None:
        area("FB_Key", (cx + 0.55 * s, cy - 0.55 * s, 0.62 * s), (cx, cy, 0.08 * s), 0.55 * s, key_w * s * s)
        area("FB_Fill", (cx - 0.75 * s, cy - 0.35 * s, 0.25 * s), (cx, cy, 0.08 * s), 0.8 * s, fill_w * s * s,
             (0.95, 0.97, 1.0))
        area("FB_Rim", (cx - 0.25 * s, cy + 0.35 * s, 0.45 * s), (cx, cy, 0.1 * s), 0.35 * s, rim_w * s * s)
        return rig
    for (name, shape, loc, tgt, size, size_y, power, col) in LIGHTS:
        lo = area(name, (cx + loc[0] * s, cy + loc[1] * s, loc[2] * s), (cx + tgt[0] * s, cy + tgt[1] * s, tgt[2] * s),
                  size * s, power * s * s, col)
        if shape == "RECTANGLE":
            lo.data.shape = "RECTANGLE"
            lo.data.size_y = size_y * s
    return rig


def row_camera(rig: Rig, res=REF_PX):
    """The reference top row's camera: focal 2600 px on 1254 px, horizon at row 460, 652.5 mm from the axes,
    height solved so the contact line lands at row ~717."""
    cam = bpy.data.cameras.new("FB_RowCam")
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    cam.lens = FOCAL_PX / res * 36.0
    pitch = math.atan((res / 2.0 - HORIZON_ROW) / FOCAL_PX)          # looking down
    # contact row 717: tan(angle_below - pitch) = (717 - 627) / f
    below = math.atan((717.0 - res / 2.0) / FOCAL_PX) + pitch
    zc = CAM_DIST_MM * math.tan(below) * 0.001
    ob = bpy.data.objects.new("FB_RowCam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0.0, -CAM_DIST_MM * 0.001, zc)
    ob.rotation_euler = (math.radians(90.0) - pitch, 0.0, 0.0)
    bpy.context.scene.camera = ob
    cam.clip_start = 0.01
    cam.clip_end = 10.0
    rig.objects.append(ob)
    rig.camera = ob
    return ob, {"lens_mm": cam.lens, "pitch_deg": math.degrees(pitch), "z_mm": zc * 1000}


def view_lateral_m(view: str, res=REF_PX) -> float:
    return (VIEW_X_PX[view] - res / 2.0) / FOCAL_PX * CAM_DIST_MM * 0.001


def place_row(objs_by_view: Dict[str, Sequence[bpy.types.Object]], yaw_deg: Dict[str, float]):
    """Put each view's copy at its lateral position, rotated so its LOCAL azimuth yaw_deg[view] faces the camera."""
    for v, objs in objs_by_view.items():
        x = view_lateral_m(v)
        cam_az = math.degrees(math.atan2(-CAM_DIST_MM * 0.001, -x))      # object -> camera, world azimuth
        rot = cam_az - yaw_deg[v]
        M = Matrix.Translation((x, 0.0, 0.0)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
        for o in objs:
            o.matrix_world = M


def render(path, samples=None):
    sc = bpy.context.scene
    if samples:
        sc.cycles.samples = samples
    path = Path(path).resolve()                    # never a relative path: Blender resolves it against C:/
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path)


def load_png(path) -> np.ndarray:
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()


def save_png(path, rgb: np.ndarray):
    a = np.asarray(rgb, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, 2)
    h, w = a.shape[:2]
    rgba = np.concatenate([np.clip(a[..., :3], 0, 1), np.ones((h, w, 1), np.float32)], 2)[::-1]
    im = bpy.data.images.new(Path(path).name, w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return str(path)


# =============================================================================== materials
def clay_material(name="FB_Clay", albedo=0.3):
    return _mat_diffuse(name, (albedo, albedo, albedo), 0.55)


def preview_materials(paths: Dict[str, str], paint_name="M_Flashbang_Paint", steel_name="M_Flashbang_Steel"):
    """The two slots' preview graphs, from the shipped maps only: BC (sRGB), ORM (linear: G roughness, B metallic),
    N (DirectX: green flipped back for Blender's OpenGL normal map node).  Both slots read the same atlas; the paint
    slot mirrors M_Fabric_Master with Metal From ORM (the baked colour is the default Colour's result)."""
    def img(key, colourspace):
        im = bpy.data.images.load(paths[key], check_existing=True)
        im.colorspace_settings.name = colourspace
        return im

    bc, orm, nrm = img("BC", "sRGB"), img("ORM", "Non-Color"), img("N", "Non-Color")
    mats = []
    for name in (paint_name, steel_name):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        t_bc = nt.nodes.new("ShaderNodeTexImage")
        t_bc.image = bc
        t_orm = nt.nodes.new("ShaderNodeTexImage")
        t_orm.image = orm
        t_n = nt.nodes.new("ShaderNodeTexImage")
        t_n.image = nrm
        for t in (t_bc, t_orm, t_n):
            t.interpolation = "Cubic"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t_orm.outputs["Color"], sep.inputs["Color"])
        sepn = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t_n.outputs["Color"], sepn.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sepn.outputs["Green"], inv.inputs[1])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sepn.outputs["Red"], comb.inputs["Red"])
        nt.links.new(inv.outputs["Value"], comb.inputs["Green"])
        nt.links.new(sepn.outputs["Blue"], comb.inputs["Blue"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "UVMap"
        nt.links.new(comb.outputs["Color"], nm.inputs["Color"])
        nt.links.new(t_bc.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Specular IOR Level"].default_value = 0.5
        nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
        mats.append(m)
    return mats


__all__ = ["setup_cycles", "studio", "row_camera", "place_row", "render", "load_png", "save_png", "Rig",
           "clay_material", "preview_materials", "view_lateral_m", "srgb_to_lin", "lin_to_srgb", "VIEW_X_PX"]
