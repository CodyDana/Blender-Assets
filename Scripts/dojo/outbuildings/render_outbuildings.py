"""Storehouse + residence review renders (Cycles, headless, denoised) from Assets/Dojo/DojoOutbuildings.blend (read-only:
nothing is saved). Rig and helpers follow Scripts/dojo/hall/render_hall.py (studio grey like the sheets; sunset for
context); context pieces take their TEXTURED meshes from their own kits' source blends (read only, matched by name
and bounding box).

--what sheet    per building: front (from the courtyard, south) and side (gable) ortho with views.json px per m and the
                ground row (exact 1.8 m silhouettes in compose), top ortho, a 3/4 view
--what close    key close-ups: store door + canopy, route-2 corner (kit 1's step pier under the south eave), residence
                door + window + meter box, gable vent + verge, ridge end, gutter + downpipe corner, route 3 verge over
                the corridor roof
--what context  sunset: the storehouse and the residence in the compound
Run: blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/outbuildings/render_outbuildings.py
     -- --what sheet [--samples 64] [--scale 1.0] [--tag r0] [--only name,name]
Out: WorkFiles/dojo/build/outbuildings/renders/<tag>/
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
OUT = (WORK / "outbuildings" / "renders" / TAG).resolve()
OUT.mkdir(parents=True, exist_ok=True)
LC_PATH = WORK / "outbuildings" / "layout_outbuildings_checks.json"
LC = json.loads(LC_PATH.read_text(encoding="utf-8")) if LC_PATH.exists() else None
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
OURS = {n for n in KIT if n.startswith("SM_DKO_")}
VIEWS = {}
SOURCES = ["DojoHall.blend", "DojoKit1.blend", "DojoGround.blend", "CourtyardStone.blend", "TrainingProps.blend",
           "ModernProps.blend", "Taiko.blend", "DojoGreybox.blend"]


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


DROPPED = ("SM_DKP_Stone_LanternShort",)


def dropped_instance(o):
    p = piece_of(o)
    if p in DROPPED:
        return True
    return p.startswith("SM_DKP_Modern_StreetLamp") and o.matrix_world.translation.y > -1.0


def show(pred):
    for o in assembly():
        p = piece_of(o)
        o.hide_render = not pred(o) or p.startswith("SM_DGB_Boundary") or dropped_instance(o)


def building_of(o):
    return "store" if o.matrix_world.translation.x < 22.0 else "res"


def textured_context():
    need = {piece_of(o) for o in assembly()} - OURS
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
            if max(abs(u - v) for u, v in zip(bb_src, bb_ref)) < 0.06:   # (round-4 ridge re-exports moved caps a few cm)
                got[ref.name] = o.data
    n = 0
    for o in assembly():
        p = piece_of(o)
        if p in got:
            o.data = got[p]
            n += 1
    print("TEXTURED CONTEXT", len(got), "pieces", n, "instances", flush=True)


def ortho_cam(name, centre, forward, width_m):
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


def ortho_view(name, centre, forward, width_m, w, h):
    cam = ortho_cam("CAM_" + name, centre, forward, width_m)
    for c in CATCHERS:
        c.hide_render = True
    render(cam, name, w, h)
    for c in CATCHERS:
        c.hide_render = False
    VIEWS[name] = {"ppm": w * SCALE / width_m, "w": int(w * SCALE), "h": int(h * SCALE), "centre": list(centre),
                   "forward": list(forward)}


def shadow_catcher(cx, cy, size=60.0):
    me = bpy.data.meshes.new("Catcher")
    hh = size / 2
    me.from_pydata([(cx - hh, cy - hh, -0.002), (cx + hh, cy - hh, -0.002), (cx + hh, cy + hh, -0.002),
                    (cx - hh, cy + hh, -0.002)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("Catcher", me)
    coll("Sheet").objects.link(o)
    o.is_shadow_catcher = True
    CATCHERS.append(o)
    return o


def sheet_look(film=True):
    """The hall's studio grey rig (render_hall.sheet_look): a low key from the front-left, a soft front fill."""
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


def aim(obj, direction):
    obj.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()


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


def ours(bld=None):
    def pred(o):
        return piece_of(o) in OURS and (bld is None or building_of(o) == bld)
    return pred


# ------------------------------------------------------------------------------------------------ SHEET
BLD = {"store": {"cx": 3.3, "side_x": 7.0, "side_dir": (-1, 0, 0), "d34": (1, -1)},
       "res": {"cx": 40.7, "side_x": 37.0, "side_dir": (1, 0, 0), "d34": (-1, -1)}}


def render_sheet():
    key, fill = sheet_look()
    shadow_catcher(22.0, 31.0, 80.0)
    for bld, b in BLD.items():
        show(ours(bld))
        cx = b["cx"]
        # the key light from the viewer's front-left for every view (as the sheets): aim per view
        aim(key, (0.40, 0.84, -0.38))
        aim(fill, (-0.25, 0.96, -0.10))
        ortho_view(f"{bld}_front", (cx, 20.0, 3.0), (0, 1, 0), 11.0, 1650, 1050)
        f = Vector(b["side_dir"])
        # side: the gable facing the hall (store: east gable, seen from the east; residence: west gable, from the west)
        rt = (f.y, -f.x)                                  # the viewer's right in plan
        aim(key, (0.84 * f.x + 0.40 * rt[0], 0.84 * f.y + 0.40 * rt[1], -0.38))
        aim(fill, (0.96 * f.x - 0.25 * rt[0], 0.96 * f.y - 0.25 * rt[1], -0.10))
        ortho_view(f"{bld}_side", (cx - f.x * 12.0, 31.7, 3.0), tuple(f), 11.0, 1650, 1050)
        aim(key, (0.40, 0.84, -0.38))
        aim(fill, (-0.25, 0.96, -0.10))
        cam = ortho_cam(f"CAM_{bld}_top", (cx, 31.7, 10.0), (0, 0, -1), 11.0)
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (cx, 31.7, 60.0)
        for c in CATCHERS:
            c.hide_render = True
        render(cam, f"{bld}_top", 1100, 1100)
        VIEWS[f"{bld}_top"] = {"ppm": 1100 * SCALE / 11.0, "w": int(1100 * SCALE), "h": int(1100 * SCALE),
                               "centre": [cx, 31.7, 0.0], "forward": [0, 0, -1]}
        for c in CATCHERS:
            c.hide_render = False
        dx, dy = b["d34"]
        cam = persp_cam(f"CAM_{bld}_34", (cx + dx * 10.5, 31.7 + dy * 13.5, 10.0), (cx, 31.2, 2.4), lens=40)
        render(cam, f"{bld}_34", 1400, 1100)


# ------------------------------------------------------------------------------------------------ CLOSE-UPS
def render_close():
    key, fill = sheet_look(film=False)
    textured_context()
    near = lambda o: piece_of(o) in OURS or (   # noqa: E731
        (o.matrix_world.translation.y > 20.0 or piece_of(o).startswith("SM_DK_Wall"))
        and not piece_of(o).startswith("SM_DGB_Boundary"))
    show(near)
    W, H = 1200, 800
    render(persp_cam("cl_sdoor", (5.6, 23.2, 1.9), (3.4, 27.9, 2.0), lens=30), "close_store_door_canopy", W, H)
    render(persp_cam("cl_route2", (-3.2, 23.4, 4.6), (-0.3, 27.4, 3.1), lens=30), "close_route2_pier_eave", W, H)
    render(persp_cam("cl_rfront", (41.4, 22.9, 1.9), (40.5, 27.9, 1.7), lens=30), "close_res_door_window_meter", W, H)
    render(persp_cam("cl_gable", (11.6, 29.2, 4.4), (7.0, 31.7, 4.3), lens=32), "close_store_gable_vent_verge", W, H)
    render(persp_cam("cl_rgable", (32.6, 29.0, 4.4), (37.0, 31.7, 4.2), lens=32), "close_res_gable_purlins", W, H)
    render(persp_cam("cl_ridge", (10.2, 27.6, 6.9), (7.4, 31.7, 5.5), lens=36), "close_ridge_end", W, H)
    render(persp_cam("cl_pipe", (9.3, 25.0, 2.2), (6.9, 27.8, 2.4), lens=28), "close_gutter_downpipe_corner", W, H)
    render(persp_cam("cl_route3", (11.8, 26.4, 6.8), (7.8, 31.0, 4.2), lens=30), "close_route3_verge_corridor", W, H)


# ------------------------------------------------------------------------------------------------ CONTEXT
def render_context():
    setup_cycles()
    sunset_world(0.6)
    textured_context()
    show(lambda o: True)
    render(persp_cam("ctx_store", (14.0, 14.5, 2.2), (3.6, 30.5, 3.0), lens=26), "context_store_sunset", 1448, 1000)
    render(persp_cam("ctx_res", (30.0, 14.5, 2.2), (40.4, 30.5, 3.0), lens=26), "context_res_sunset", 1448, 1000)
    render(persp_cam("ctx_ref2_high", (22.0, -7.5, 9.2), (22.0, 23.5, 1.2), lens=30), "context_ref2_elevated", 1448,
           1086)


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
