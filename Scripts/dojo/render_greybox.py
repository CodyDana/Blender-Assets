"""Quick review renders of the grey-box (Assets/Dojo/DojoGreybox.blend, read-only: nothing is saved).

Workbench, flat material colours + cavity + shadow, for every layout.json camera plus an orthographic top view drawn to
the spec plan's frame, so the grey-box can be laid over DOJO_ARENA_TOPDOWN.png by eye. Optional: --cycles for a Cycles
sunset render of the establishing camera (the layout.json sun).

Run: blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/render_greybox.py -- [--cycles]
Out: WorkFiles/dojo/build/renders/*.png
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
OUT = WORK / "renders"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
L = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))
sc = bpy.context.scene


def camera(name, loc, look, hfov=None, ortho=None):
    cam = bpy.data.cameras.new(name)
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    o.location = loc
    d = Vector(look) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho
    else:
        cam.lens = 18.0 / math.tan(math.radians(hfov) / 2.0)
    cam.clip_end = 500.0
    return o


def render(cam, name, w, h):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)


OUT.mkdir(parents=True, exist_ok=True)
for o in bpy.data.objects:   # the 1v1 boundary is invisible in game: keep it out of the review renders too
    if o.name.startswith("SM_DGB_Boundary_1v1__"):
        o.hide_render = True
if "--cycles" in ARGS:
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    s = L["sun"]
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = 4.0
    lt.angle = math.radians(0.6)
    lt.color = (1.0, 0.62, 0.38)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = Vector(s["travel_dir"]).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("Dusk")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.55, 0.42, 0.40, 1.0)
    bg.inputs["Strength"].default_value = 0.35
    sc.world = world
    sc.view_settings.view_transform = "AgX"
    c = next(c for c in L["cameras"] if c["name"] == "CAM_Establishing")
    render(camera("C", c["loc"], c["look_at"], c["hfov_deg"]), "cycles_establishing", *c["out_wh"])
else:
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = True
    sh.show_shadows = True
    sc.display.shadow_focus = 0.2
    sc.display.light_direction = (-0.6, 0.35, 0.72)
    for c in L["cameras"]:
        render(camera(c["name"], c["loc"], c["look_at"], c["hfov_deg"]), "wb_" + c["name"], *c["out_wh"])
    top = camera("Top", (22.0, 18.0, 60.0), (22.0, 18.00001, 0.0), ortho=56.0)
    render(top, "wb_top_ortho", 1600, 1300)
