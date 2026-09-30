"""Covered-corridor review renders (Cycles, headless, denoised) from Assets/Dojo/DojoCorridors.blend (read only:
nothing is saved). The hall pieces come textured from the hall blend (loaded at build); the other context pieces (the
showcase's FBX imports) take their textured meshes from their own kits' source blends (read only) where the bounds match,
as Scripts/dojo/hall/render_hall.py does; the outbuildings are still the grey-box blocks (their kit is being built in
parallel).

--what sheet    model-sheet views like References/Dojo/dojo_corridor_ref.png: the closed side (the E corridor from the
                north: outbuilding left, hall right, as the sheet), the open side (the W corridor from the courtyard),
                the end view (the W corridor from the hall side, the corridor alone), the top view, a 3/4 view;
                views.json records px per m so the 1.8 m silhouettes are exact
--what close    key close-ups: the gable at the hall eave, the roof under the outbuilding verge + downpipe, the rail +
                pedestal + deck edge, the closed wall from the alley, the inside (tie beam, king post, rafters), the
                roof from the outbuilding roof (route 3)
--what context  sunset: the W corridor from the courtyard, and from the gate side above
Run: blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/corridors/render_corridors.py --
     --what sheet [--samples 64] [--scale 1.0] [--tag r0] [--only name,name]
Out: WorkFiles/dojo/build/corridors/renders/<tag>/
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


WHAT = arg("--what", "sheet")
SAMPLES = int(arg("--samples", "64"))
SCALE = float(arg("--scale", "1.0"))
TAG = arg("--tag", "r0")
ONLY = arg("--only", "")
OUT = (WORK / "corridors" / "renders" / TAG).resolve()
OUT.mkdir(parents=True, exist_ok=True)
LC_PATH = WORK / "corridors" / "layout_corridors_checks.json"
LC = json.loads(LC_PATH.read_text(encoding="utf-8")) if LC_PATH.exists() else None
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
CORR = {n for n in KIT if n.startswith("SM_DKC_")}
HALL = {n for n in KIT if n.startswith("SM_DKH_")}
OUTB = {"SM_DGB_Storehouse", "SM_DGB_Storehouse_Roof", "SM_DGB_Residence", "SM_DGB_Residence_Roof"}
VIEWS = {}
SOURCES = ["DojoKit1.blend", "DojoGround.blend", "CourtyardStone.blend", "TrainingProps.blend", "ModernProps.blend",
           "Taiko.blend", "DojoGreybox.blend"]
DROPPED = ("SM_DKP_Stone_LanternShort",)


def setup_cycles():
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.cycles.max_bounces = 8


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


def assembly():
    return list(bpy.data.collections["Assembly"].objects)


def piece_of(o):
    return o.name.split("__")[0]


def dropped_instance(o):
    p = piece_of(o)
    if p in DROPPED:
        return True
    return p.startswith("SM_DKP_Modern_StreetLamp") and o.matrix_world.translation.y > -1.0


def show(pred):
    for o in assembly():
        p = piece_of(o)
        o.hide_render = not pred(p, o) or p.startswith("SM_DGB_Boundary") or dropped_instance(o)


def textured_context():
    need = {piece_of(o) for o in assembly()} - CORR - HALL
    got = {}
    for fn in SOURCES:
        path = ROOT / "Assets" / "Dojo" / fn
        if not path.exists():
            continue
        want = [n for n in need - set(got)]
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            names = set(src.objects)
            dst.objects = [n for n in want if n in names]
        for o in dst.objects:
            if o is None or o.type != "MESH":
                continue
            ref = KIT.get(o.name.split(".")[0])
            if ref is None:
                continue
            bb_src = [min(Vector(c)[i] for c in o.bound_box) for i in range(3)] + \
                     [max(Vector(c)[i] for c in o.bound_box) for i in range(3)]
            bb_ref = [min(Vector(c)[i] for c in ref.bound_box) for i in range(3)] + \
                     [max(Vector(c)[i] for c in ref.bound_box) for i in range(3)]
            if max(abs(u - v) for u, v in zip(bb_src, bb_ref)) < 0.01:
                got[ref.name] = o.data
    n = 0
    for o in assembly():
        p = piece_of(o)
        if p in got:
            o.data = got[p]
            n += 1
    print("TEXTURED CONTEXT", len(got), "pieces", n, "instances", flush=True)


def ortho_cam(name, centre, forward, width_m, up=(0, 0, 1)):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = width_m
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.1
    cam.clip_end = 500.0
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    f = Vector(forward).normalized()
    o.matrix_world = Matrix.Translation(Vector(centre) - f * 80.0) @ f.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return o


def persp_cam(name, loc, look, lens=50.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.05
    cam.clip_end = 800.0
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(cam, name, w, h):
    if ONLY and name not in ONLY.split(","):
        return
    sc.camera = cam
    sc.render.resolution_x = int(w * SCALE)
    sc.render.resolution_y = int(h * SCALE)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath, flush=True)


CATCHERS = []


def shadow_catcher(cx, cy, size=80.0):
    me = bpy.data.meshes.new("Catcher")
    hh = size / 2
    me.from_pydata([(cx - hh, cy - hh, -0.002), (cx + hh, cy - hh, -0.002), (cx + hh, cy + hh, -0.002),
                    (cx - hh, cy + hh, -0.002)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("Catcher", me)
    coll("Sheet").objects.link(o)
    o.is_shadow_catcher = True
    CATCHERS.append(o)
    return o


def ortho_view(name, centre, forward, width_m, w, h, catcher=False):
    cam = ortho_cam("CAM_" + name, centre, forward, width_m)
    for c in CATCHERS:
        c.hide_render = not catcher
    render(cam, name, w, h)
    VIEWS[name] = {"ppm": w * SCALE / width_m, "w": int(w * SCALE), "h": int(h * SCALE), "centre": list(centre),
                   "forward": list(forward)}


def sheet_look(film=True):
    setup_cycles()
    sc.render.film_transparent = film
    world = bpy.data.worlds.new("SheetGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.62, 0.62, 0.62, 1.0)
    bg.inputs["Strength"].default_value = 1.35
    sc.world = world
    lt = bpy.data.lights.new("Key", "SUN")
    lt.energy = 2.6
    lt.angle = math.radians(25.0)
    lt.color = (1.0, 0.98, 0.95)
    ko = bpy.data.objects.new("Key", lt)
    sc.collection.objects.link(ko)
    ko.rotation_euler = Vector((0.40, 0.84, -0.38)).to_track_quat("-Z", "Y").to_euler()
    fl = bpy.data.lights.new("Fill", "SUN")
    fl.energy = 1.3
    fl.angle = math.radians(40.0)
    fo = bpy.data.objects.new("Fill", fl)
    sc.collection.objects.link(fo)
    fo.rotation_euler = Vector((-0.25, 0.96, -0.10)).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.35
    return ko, fo


def aim(light_obj, direction):
    light_obj.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()


def sunset_world(exposure=0.6):
    s = (LC or {}).get("sun", {"elev_deg": 13.0, "azimuth_deg_from_x": 160.0})
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    el, az = math.radians(s["elev_deg"]), math.radians(s["azimuth_deg_from_x"])
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(tc.outputs["Generated"], dot.inputs[0])
    dot.inputs[1].default_value = to_sun
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (1.0, 0.52, 0.26, 1)
    cr.elements[1].position = 0.35
    cr.elements[1].color = (0.30, 0.28, 0.46, 1)
    e = cr.elements.new(0.08)
    e.color = (0.95, 0.55, 0.42, 1)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.0
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    nt.links.new(mx.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 6.0
    glow = nt.nodes.new("ShaderNodeMix")
    glow.data_type = "RGBA"
    glow.blend_type = "ADD"
    nt.links.new(pw.outputs[0], glow.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], glow.inputs["A"])
    glow.inputs["B"].default_value = (1.0, 0.62, 0.30, 1)
    below = nt.nodes.new("ShaderNodeMath")
    below.operation = "LESS_THAN"
    below.inputs[1].default_value = 0.0
    nt.links.new(sep.outputs[2], below.inputs[0])
    gmix = nt.nodes.new("ShaderNodeMix")
    gmix.data_type = "RGBA"
    nt.links.new(below.outputs[0], gmix.inputs["Factor"])
    nt.links.new(glow.outputs["Result"], gmix.inputs["A"])
    gmix.inputs["B"].default_value = (0.12, 0.10, 0.09, 1)
    nt.links.new(gmix.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = 4.2
    lt.angle = math.radians(0.8)
    lt.color = (1.0, 0.63, 0.36)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False


def near_corridors(p, o):
    """The corridors with their neighbours only: the hall, the grey-box outbuildings (no perimeter wall, ground or
    props: the sheet's plain backdrop)."""
    return p in CORR or p in HALL or p in OUTB


def corr_only(p, o):
    return p in CORR


def corr_w_only(p, o):
    """The west corridor alone (the east one stands in front of it in a view from the east)."""
    return p in CORR and o.matrix_world.translation.x < 22.0


# ------------------------------------------------------------------------------------------------ SHEET
def render_sheet():
    key, fill = sheet_look()
    textured_context()
    shadow_catcher(22.0, 31.0)
    show(near_corridors)
    # the closed side: the E corridor from the north (outbuilding left, hall right, as the sheet's top view)
    aim(key, (0.35, -0.80, -0.48))
    aim(fill, (0.25, -0.96, -0.10))
    ortho_view("corr_closed", (34.9, 31.0, 2.45), (0, -1, 0), 11.0, 1100, 560, catcher=True)
    # the open side: the W corridor from the courtyard (outbuilding left, hall right)
    aim(key, (0.40, 0.84, -0.38))
    aim(fill, (-0.25, 0.96, -0.10))
    ortho_view("corr_open", (9.1, 31.0, 2.45), (0, 1, 0), 11.0, 1100, 560, catcher=True)
    # the end view: the W corridor alone from the hall side (looking west: the open side on the left, as the sheet)
    show(corr_w_only)
    aim(key, (-0.75, 0.45, -0.48))
    aim(fill, (-0.96, 0.20, -0.15))
    ortho_view("corr_end", (9.0, 31.0, 2.1), (-1, 0, 0), 4.6, 560, 620, catcher=True)
    # top view (W corridor between the outbuilding roof and the hall's roofs)
    show(near_corridors)
    aim(key, (0.40, 0.84, -0.60))
    cam = ortho_cam("CAM_top", (9.1, 31.0, 0.0), (0, 0, -1), 11.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.location = (9.1, 31.0, 60.0)
    for c in CATCHERS:
        c.hide_render = True
    render(cam, "corr_top", 1100, 560)
    VIEWS["corr_top"] = {"ppm": 1100 * SCALE / 11.0, "w": int(1100 * SCALE), "h": int(560 * SCALE),
                         "centre": [9.1, 31.0, 0.0], "forward": [0, 0, -1]}
    # 3/4 from the courtyard, a little above (the sheet's bottom-right view)
    for c in CATCHERS:
        c.hide_render = False
    aim(key, (0.40, 0.84, -0.38))
    render(persp_cam("CAM_34", (7.4, 24.3, 3.0), (9.3, 31.0, 1.9), lens=26), "corr_34", 1100, 700)


# ------------------------------------------------------------------------------------------------ CLOSE-UPS
def render_close():
    sheet_look(film=False)
    textured_context()
    show(lambda p, o: not p.startswith("SM_DGB_Wall_N") and not p.startswith("SM_DKW_Wall_N"))
    W, H = 1100, 740
    render(persp_cam("cl_gable", (8.6, 28.3, 4.5), (10.35, 31.0, 3.3), lens=28), "close_gable_at_hall_eave", W, H)
    render(persp_cam("cl_junc", (9.4, 27.9, 1.9), (10.3, 29.6, 2.95), lens=24), "close_gable_junction_below", W, H)
    render(persp_cam("cl_outb", (9.3, 27.2, 2.2), (7.35, 30.2, 3.1), lens=26), "close_outbuilding_end_downpipe", W, H)
    render(persp_cam("cl_rail", (9.6, 28.0, 1.05), (8.5, 29.9, 0.55), lens=30), "close_rail_pedestal_deck", W, H)
    render(persp_cam("cl_wall", (9.9, 34.9, 1.6), (8.7, 32.2, 1.55), lens=28), "close_closed_wall_alley", W, H)
    render(persp_cam("cl_in", (7.55, 31.6, 1.6), (10.6, 30.7, 2.5), lens=20), "close_inside_frame", W, H)
    render(persp_cam("cl_roof", (6.0, 28.6, 6.1), (10.4, 31.0, 3.4), lens=30), "close_roof_route3", W, H)


# ------------------------------------------------------------------------------------------------ CONTEXT
def render_context():
    setup_cycles()
    sunset_world(0.6)
    textured_context()
    show(lambda p, o: True)
    render(persp_cam("ctx_court", (4.2, 21.8, 1.75), (9.0, 31.0, 2.3), lens=24), "context_corridor_W_sunset", 1448,
           1000)
    render(persp_cam("ctx_high", (5.8, 19.0, 7.8), (9.2, 31.0, 2.6), lens=30), "context_corridor_W_high_sunset",
           1448, 1000)


if WHAT == "sheet":
    render_sheet()
elif WHAT == "close":
    render_close()
elif WHAT == "context":
    render_context()
vp = OUT / "views.json"
old = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
old.update(VIEWS)
vp.write_text(json.dumps(old, indent=1), encoding="utf-8")
