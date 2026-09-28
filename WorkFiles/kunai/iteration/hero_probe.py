"""Hero-only probe (scratch): open a scratch kunai build, render the pack's hero shot at several yaws / rolls with the
baked preview materials, and print the coat / whole / wrap statistics.  Usage:
    blender -b <k.blend> --factory-startup --python hero_probe.py -- <build_dir> <out_dir> yaw[:roll] ...
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken")
import bpy  # noqa: E402

import build_kunai_plain as K  # noqa: E402
from shuriken_lib import render as R  # noqa: E402
from shuriken_lib.bake import preview_material  # noqa: E402
from shuriken_lib.kunai_wrap import wrap_preview_material  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
build, out = Path(argv[0]), Path(argv[1])
out.mkdir(parents=True, exist_ok=True)
poses = argv[2:]
samples = 96
report = json.loads((build / "kunai_plain_report.json").read_text(encoding="utf-8"))
tex = report["textures"]
lod0 = bpy.data.objects["SM_Kunai_Plain_LOD0"]
others = [o for o in bpy.data.objects if o is not lod0]
steel = preview_material("M_Probe_Steel", tex["maps"], uv_map=tex["uv_map"])
wrapm = wrap_preview_material(tex)
o = K.FORM.geometry.render_outline()
res_x, res_y = 1600, 900
scene = bpy.context.scene
R.setup_render(samples, res_x, res_y)
rig = R.build_preview_rig(o, res_x, res_y)
for ob in others:
    if ob.name.startswith("PREVIEW_"):
        continue
    ob.hide_render = True
lod0.hide_render = False
lod0.data.materials[0] = steel
lod0.data.materials[1] = wrapm
mask_mat = R._wall_mask_material()
results = {}
for pose in poses:
    yaw, _, roll = pose.partition(":")
    yaw, roll = float(yaw), float(roll or 0.0)
    lod0.location = (0.0, 0.0, 0.0)
    lod0.rotation_euler = (math.radians(roll), 0.0, math.radians(yaw))
    bpy.context.view_layer.update()
    cam = rig["cam_persp"]
    cam.location = R._polar(0.30, 29.0, -22.0)
    cam.data.shift_x = cam.data.shift_y = 0.0
    R._aim(cam)
    R.fit_perspective(cam, [lod0], 0.90, 0.86)
    R.centre_perspective(cam, [lod0], res_x, res_y)
    R.place_for_shift(cam, lod0, res_x, res_y)
    R.centre_perspective(cam, [lod0], res_x, res_y, steps=1)
    R.solve_depth_of_field(cam, [lod0], res_x)
    k = cam.location.length / R.HERO_RIG_REFERENCE_M
    saved = []
    for light in rig["hero_lights"]:
        saved.append((light, light.location.copy(), light.data.size, light.data.size_y, light.data.energy))
        light.location = light.location * k
        light.data.size *= k
        light.data.size_y *= k
        light.data.energy *= k * k
    for light in rig["hero_lights"] + rig["top_lights"]:
        light.hide_render = light not in rig["hero_lights"]
    rig["ground"].hide_render = False
    rig["card"].hide_render = False
    rig["band"].hide_render = True
    scene.render.film_transparent = False
    scene.cycles.samples = samples
    name = f"hero_y{yaw:g}_r{roll:g}"
    beauty = Path(R.render_to(out / f"{name}.png", cam))
    rig["ground"].hide_render = True
    rig["card"].hide_render = True
    scene.render.film_transparent = True
    scene.cycles.samples = 8
    vt = scene.view_settings.view_transform
    bpy.context.view_layer.material_override = mask_mat
    scene.view_settings.view_transform = "Standard"
    mask = Path(R.render_to(out / f"{name}_mask.png", cam))
    bpy.context.view_layer.material_override = None
    scene.view_settings.view_transform = vt
    scene.render.film_transparent = False
    for light, loc, size, size_y, energy in saved:
        light.location, light.data.size, light.data.size_y, light.data.energy = loc, size, size_y, energy
    st = R.image_stats(beauty, mask, o.n, wrap=True)
    results[name] = {"coat": st.get("coat_luminance"), "whole": st.get("object_luminance"),
                     "wrap": st.get("wrap_luminance"), "walls": st.get("wall_luminance", {}).get("p50"),
                     "facets": (st.get("facet_luminance") or {}).get("near", {}).get("p50"),
                     "backdrop": st.get("backdrop_points")}
    c = st.get("coat_luminance") or {}
    print(f"PROBE {name}: coat p50 {c.get('p50')} mean {c.get('mean')} frac {c.get('fraction_of_object')}  whole "
          f"{st['object_luminance']['p50']}/{st['object_luminance']['mean']}")
(out / "probe.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
