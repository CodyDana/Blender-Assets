#!/usr/bin/env python
"""props_lib.smokebomb_render - the REFERENCE-VIEW frame, and the comparison sheets.

The fidelity render is the shipped LOD0 with the shipped (baked) maps, seen the way the
reference product shot sees the ball (REFERENCE_SPEC 2 and 3):

    camera     ORTHOGRAPHIC on -Y looking +Y (Blender's Front view), frame width
               1.351 D, 1254 x 1254, the ball centre 0.4 px right / 1.9 px below centre
    backdrop   uniform stored 0.996, no ground, no shadow: rendered with a transparent
               film and composited onto 0.996 here, so the backdrop is exact
    lights     key  (0.380, 0.899, 0.219) camera frame, az 60 / el 64
               fill (-0.897, 0.070, -0.437), left-rear, az -116 / el +4, 0.67 x the key
               ambient 0.42 x the key
               normalised the spec's way: a white Lambert surface facing the key reads
               1.0.  Measured Cycles units (sbb_calib): a sun of strength E lights a white
               Lambert surface to E / pi; a uniform world of radiance L to L.  So with
               key k, fill f, ambient a and k + a = 1: E_key = pi k, E_fill = pi f, L = a.
               Large soft sources (no terminator): sun angle 40 deg.
    transform  "Standard" (plain sRGB), the file is written from linear EXR here

The side-by-side is [reference | render] at the same size and the same crop.  It is a
comparison sheet: the reference image appears in it, and in nothing that ships.
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

REF_PX = 1254
KEY_DIR_CAM = (0.3796, 0.8988, 0.2192)
#: REFERENCE_SPEC 3's fill, exactly: az -116 / el +4 (round 2 used el +16, inside the
#: tolerance; round 3 renders at the measured value, the same lights the round-2 adversary's
#: independent render used - key and fill suns 40 deg across, ambient 0.42)
FILL_DIR_CAM = (-0.8966, 0.0698, -0.4373)
FILL_OVER_KEY = 0.67
AMBIENT_OVER_KEY = 0.42
BACKDROP_STORED = 0.996
SUN_ANGLE_DEG = 40.0


def light_levels(key_scale: float = 1.0) -> Dict[str, float]:
    k = 1.0 / (1.0 + AMBIENT_OVER_KEY)
    f = FILL_OVER_KEY * k
    a = AMBIENT_OVER_KEY * k
    return {"sun_key": math.pi * k * key_scale, "sun_fill": math.pi * f * key_scale,
            "world": a * key_scale, "k": k, "f": f, "a": a}


def srgb_encode(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb_decode(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def write_png(path, arr: np.ndarray) -> str:
    a = np.clip(np.asarray(arr, np.float64), 0.0, 1.0)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    q = np.rint(a * 255).astype("u1")
    raw = b"".join(b"\x00" + q[y].tobytes() for y in range(h))

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, {1: 0, 3: 2, 4: 6}[c], 0, 0, 0)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    return str(path)


def load_png(path) -> np.ndarray:
    """Stored 0..1, rows top-down, RGB(A) as in the file."""
    import bpy
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1])
    finally:
        bpy.data.images.remove(img)


def setup_reference(diameter_mm: float, res: int = REF_PX, samples: int = 256,
                    key_scale: float = 1.0, denoise: bool = True) -> Dict[str, object]:
    """Scene, camera, lamps and world for the reference view.  Returns the rig."""
    import bpy
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    except Exception:                                      # pragma: no cover
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    coll = bpy.data.collections.new("SB_REFERENCE_RIG")
    scene.collection.children.link(coll)
    cam_d = bpy.data.cameras.new("SB_RefCam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = diameter_mm * 0.001 * SS.ORTHO_D_PER_FRAME
    # the reference's ball centre sits 0.38 px right of and 1.92 px below the frame centre
    cam_d.shift_x = -(SS.REF_CENTRE_PX[0] - REF_PX / 2) / REF_PX
    cam_d.shift_y = (SS.REF_CENTRE_PX[1] - REF_PX / 2) / REF_PX
    cam_d.clip_start = 0.01
    cam_d.clip_end = 2.0
    cam = bpy.data.objects.new("SB_RefCam", cam_d)
    coll.objects.link(cam)
    cam.location = (0.0, -0.6, 0.0)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    scene.camera = cam
    lv = light_levels(key_scale)
    lamps = []
    for name, v, e in (("SB_Key", KEY_DIR_CAM, lv["sun_key"]), ("SB_Fill", FILL_DIR_CAM, lv["sun_fill"])):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = e
        ld.angle = math.radians(SUN_ANGLE_DEG)
        lo = bpy.data.objects.new(name, ld)
        coll.objects.link(lo)
        vb = Vector(SS.cam_to_blender(np.array(v)))
        lo.rotation_euler = vb.to_track_quat("Z", "Y").to_euler()
        lamps.append(lo)
    world = bpy.data.worlds.new("SB_RefWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = lv["world"]
    scene.world = world
    return {"collection": coll, "camera": cam, "lamps": lamps, "world": world, "levels": lv}


def teardown(rig) -> None:
    import bpy
    for o in list(rig["collection"].objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        for lib in (bpy.data.cameras, bpy.data.lights):
            try:
                lib.remove(data)
                break
            except Exception:
                pass
    bpy.data.collections.remove(rig["collection"])
    if rig.get("world") is not None:
        bpy.data.worlds.remove(rig["world"])


def render_reference(path_png, exr_path, rig) -> np.ndarray:
    """Render, composite onto the 0.996 backdrop, write the PNG; return stored RGB."""
    import bpy
    scene = bpy.context.scene
    scene.camera = rig["camera"]
    scene.render.filepath = str(exr_path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(exr_path), check_existing=False)
    try:
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        a = np.ascontiguousarray(buf.reshape(h, w, 4)[::-1]).astype(np.float64)
    finally:
        bpy.data.images.remove(img)
    bg = srgb_decode(np.array(BACKDROP_STORED))
    lin = a[..., :3] + (1.0 - a[..., 3:4]) * bg          # premultiplied alpha over the sweep
    stored = srgb_encode(lin)
    write_png(path_png, stored)
    return stored


def side_by_side(ref_png, render_png, out_png, gap: int = 12, crop: Optional[Tuple[int, int, int, int]] = None):
    """[reference | render], same size, white gap; optional crop (x0, y0, x1, y1)."""
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    if crop is not None:
        x0, y0, x1, y1 = crop
        ref = ref[y0:y1, x0:x1]
        ren = ren[y0:y1, x0:x1]
    h = max(ref.shape[0], ren.shape[0])
    sheet = np.ones((h, ref.shape[1] + gap + ren.shape[1], 3))
    sheet[:ref.shape[0], :ref.shape[1]] = ref
    sheet[:ren.shape[0], ref.shape[1] + gap:] = ren
    write_png(out_png, sheet)
    return str(out_png)


__all__ = ["REF_PX", "KEY_DIR_CAM", "FILL_DIR_CAM", "light_levels", "setup_reference",
           "render_reference", "side_by_side", "teardown", "write_png", "load_png",
           "srgb_encode", "srgb_decode"]
