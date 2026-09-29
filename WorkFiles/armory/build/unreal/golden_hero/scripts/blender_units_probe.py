"""Measure Cycles' radiometric scale, so the Unreal light/emissive conversion is computed, not assumed.

A white (albedo 1) diffuse plane under a sun of strength 1 facing it, and an emission plane of strength 1, rendered with
the Standard view transform at exposure 0; the linear pixel values are printed (the ratio sets how Blender emission
strength maps onto light units). Run: blender -b --factory-startup --python blender_units_probe.py
"""
import json
import bpy
import numpy as np
from pathlib import Path

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\blender_units_probe.json")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
res = {}
for mode in ("sun", "emit", "point", "area"):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_plane_add(size=20)
    pl = bpy.context.object
    m = bpy.data.materials.new("m")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    if mode == "emit":
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Strength"].default_value = 1.0
    pl.data.materials.append(m)
    if mode == "sun":
        ld = bpy.data.lights.new("s", "SUN"); ld.energy = 1.0; ld.angle = 0.0
        lo = bpy.data.objects.new("s", ld); sc.collection.objects.link(lo)
    elif mode == "point":   # 1 W point 1 m above the plane: irradiance under it
        ld = bpy.data.lights.new("p", "POINT"); ld.energy = 1.0; ld.shadow_soft_size = 0.0
        lo = bpy.data.objects.new("p", ld); sc.collection.objects.link(lo); lo.location = (0, 0, 1)
    elif mode == "area":    # 1 W, 0.1 x 0.1 m area light 1 m above, facing down
        ld = bpy.data.lights.new("a", "AREA"); ld.energy = 1.0; ld.shape = "SQUARE"; ld.size = 0.1
        lo = bpy.data.objects.new("a", ld); sc.collection.objects.link(lo); lo.location = (0, 0, 1)
    cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 0.2
    co = bpy.data.objects.new("c", cd); sc.collection.objects.link(co); co.location = (0, 0, 5)
    sc.camera = co
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.0
    sc.world = w
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = 16
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "OPEN_EXR"
    p = str(OUT.parent / f"probe_{mode}.exr")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p)
    px = np.array(img.pixels[:]).reshape(-1, 4)
    res[mode] = float(px[:, :3].mean())
res["note"] = ("linear radiance of a white Lambertian plane: sun strength 1 (W/m2), emission strength 1, "
               "1 W point at 1 m, 1 W 0.1 m square area light at 1 m (on axis)")
OUT.write_text(json.dumps(res, indent=1))
print("PROBE", json.dumps(res))
