"""V4 sheen calibration, Blender half (headless; opens NO .blend, writes nothing but its own outputs).

The kunai wrap's Blender look (kunai_wrap.wrap_preview_material) is a Principled BSDF with Sheen Weight 0.35, Sheen
Roughness 0.35, Sheen Tint (0.62, 0.60, 0.56) over the dark wrap (roughness ORM.G, mean 0.859; Specular IOR Level 0.5).
Unreal has no such sheen layer; M_Fabric_Master maps it onto the Cloth shading model (Fuzz Colour + Cloth amount). To
choose that mapping by measurement, both renderers light the SAME flat-coloured sphere with ONE directional light in two
set-ups (front-side key, and a back rim) and the sheen's effect is compared as the ratio sheen-on / sheen-off per
N.V bin (so absolute light units and exposure cancel).

    blender -b --factory-startup --python sheen_blender_reference.py -- <out_dir>
Writes <out_dir>/blender_sheen_<light>_<on|off>.exr and blender_sheen_reference.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

OUT = Path(sys.argv[sys.argv.index("--") + 1])
OUT.mkdir(parents=True, exist_ok=True)
ALBEDO = (0.037644715 * 0.99352, 0.035002095 * 0.99352, 0.03225276 * 0.99352)   # Colour x Detail Mean (flat)
ROUGH = 0.859
SHEEN = {"weight": 0.35, "roughness": 0.35, "tint": (0.62, 0.60, 0.56)}
# light directions: the direction TOWARDS the light, in a frame where the camera sits on +X looking at the origin
LIGHTS = {"key": (1.0, 1.0, 1.0), "rim": (-1.0, 0.35, 0.6)}
RES = 512


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 256
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "32"
    w = bpy.data.worlds.new("black")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.world = w
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.0)
    sphere = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new("wrap_flat")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*ALBEDO, 1.0)
    bsdf.inputs["Roughness"].default_value = ROUGH
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    bsdf.inputs["Sheen Roughness"].default_value = SHEEN["roughness"]
    bsdf.inputs["Sheen Tint"].default_value = (*SHEEN["tint"], 1.0)
    sphere.data.materials.append(mat)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.0
    sc.collection.objects.link(cam)
    cam.location = (5.0, 0.0, 0.0)
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(90))     # look along -X, Z up
    sc.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.data.angle = 0.0
    sc.collection.objects.link(sun)
    return sc, bsdf, sun


def aim(sun, towards):
    v = np.array(towards, float)
    v /= np.linalg.norm(v)
    # a sun shines along its local -Z: rotate -Z onto -v
    d = -v
    pitch = math.acos(max(-1.0, min(1.0, -d[2])))
    yaw = math.atan2(d[1], d[0]) - math.pi / 2
    sun.rotation_euler = (pitch, 0.0, yaw)
    return v


def render(sc, path):
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    a = np.empty(RES * RES * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(RES, RES, 4)[::-1]


def profile(a):
    """mean luminance per N.V bin (camera on +X: pixel -> normal)."""
    lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    ys, xs = np.mgrid[0:RES, 0:RES]
    u = (xs + 0.5) / RES * 2 - 1
    v = (ys + 0.5) / RES * 2 - 1
    r2 = u * u + v * v
    inside = r2 < 0.995
    nv = np.sqrt(np.clip(1 - r2, 0, 1))
    bins = np.linspace(0, 1, 11)
    out = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = inside & (nv >= lo) & (nv < hi)
        out.append({"nv": [round(lo, 2), round(hi, 2)], "n": int(m.sum()), "lum": float(lum[m].mean()) if m.any() else None})
    return {"mean": float(lum[inside].mean()), "bins": out}


sc, bsdf, sun = setup()
res = {"albedo": ALBEDO, "roughness": ROUGH, "sheen": SHEEN, "lights": LIGHTS, "renders": {}}
for lname, towards in LIGHTS.items():
    aim(sun, towards)
    res.setdefault("sun_rotation", {})[lname] = list(sun.rotation_euler)
    for state, weight in (("off", 0.0), ("on", SHEEN["weight"])):
        bsdf.inputs["Sheen Weight"].default_value = weight
        a = render(sc, OUT / f"blender_sheen_{lname}_{state}.exr")
        res["renders"][f"{lname}_{state}"] = profile(a)
(OUT / "blender_sheen_reference.json").write_text(json.dumps(res, indent=1))
print("SHEEN_REF_DONE")
