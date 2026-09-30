"""Hall + roof system review renders (Cycles, headless, denoised) from Assets/Dojo/DojoHall.blend (read-only: nothing
is saved). Context pieces (kit 1, ground, props) take their TEXTURED meshes from their own kits' source blends (read
only), matched by piece name and checked by bounding box; the hall uses the shared material library.

--what sheet    model-sheet views of the hall alone (with the roof AC units, as the sheet shows them): front / side / top
                ortho (views.json records px per m and the ground row so the silhouettes are exactly 1.8 m), a 2 m bay
                close-up, a 3/4 view
--what roof     roof-detail panels a1..f2 matching dojo_roof_details_ref.png (tile field + eave, eave corner, ridge +
                ridge end, hip roll, hip corner, gable end, verge of a plain gable roof (roof_kit.gable_roof on a demo
                plaster box: the API the outbuildings will use), gutter + downpipe)
--what close    key close-ups: route-4 eave landing over the cistern, route-5 AC zone + upper eave step, the downpipe
                corner, the central stair + step band, the gable end and verge overhang; fix round f1: the raised
                centre eave + lit frieze, the side chidori-hafu, the ridge end + diagonal ridge, the upper eave soffit
                (capped rafters, frieze board), a door head (the closed nageshi / kamoi), the veranda deck at the wall
--what context  sunset: the establishing view (dojo1_reference2's framing) and a 3/4 context shot in the compound
Run: blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/render_hall.py -- --what sheet
     [--samples 128] [--scale 1.0] [--tag r0]
Out: WorkFiles/dojo/build/hall/renders/<tag>/
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "roof"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "hall"))
WORK = ROOT / "WorkFiles" / "dojo" / "build"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


WHAT = arg("--what", "sheet")
SAMPLES = int(arg("--samples", "128"))
SCALE = float(arg("--scale", "1.0"))
TAG = arg("--tag", "r0")
ONLY = arg("--only", "")
OUT = (WORK / "hall" / "renders" / TAG).resolve()
OUT.mkdir(parents=True, exist_ok=True)
LH = json.loads((WORK / "hall" / "layout_hall.json").read_text(encoding="utf-8"))
LC_PATH = WORK / "hall" / "layout_hall_checks.json"
LC = json.loads(LC_PATH.read_text(encoding="utf-8")) if LC_PATH.exists() else None
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
HALL = {n for n in KIT if n.startswith("SM_DKH_")}
VIEWS = {}
SOURCES = ["DojoKit1.blend", "DojoGround.blend", "CourtyardStone.blend", "TrainingProps.blend", "ModernProps.blend",
           "Taiko.blend", "DojoGreybox.blend"]


# ------------------------------------------------------------------------------------------------ setup
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


# user 2026-09-28 (round 3): DROP the invented lamps: no street lamps inside the courtyard (only outside on the street
# side, where the references show them) and no short lanterns inside the gate (an unplaced spare). The context renders
# leave them out whatever the showcase layout still holds.
DROPPED = ("SM_DKP_Stone_LanternShort",)


def dropped_instance(o):
    p = piece_of(o)
    if p in DROPPED:
        return True
    return p.startswith("SM_DKP_Modern_StreetLamp") and o.matrix_world.translation.y > -1.0   # inside the wall line


def show(pred):
    """Render only the Assembly instances whose piece passes pred (the 1v1 boundary never; the dropped lamps never)."""
    for o in assembly():
        p = piece_of(o)
        o.hide_render = not pred(p) or p.startswith("SM_DGB_Boundary") or dropped_instance(o)


def textured_context():
    """Swap the context instances' meshes (FBX imports in the showcase: flat materials) for the source kits' textured
    meshes where the piece exists there with the same bounds (1 cm)."""
    need = {piece_of(o) for o in assembly()} - HALL
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
    return got


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


def persp_cam(name, loc, look, lens=50.0, shift_x=0.0, shift_y=0.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.05
    cam.clip_end = 800.0
    cam.shift_x = shift_x
    cam.shift_y = shift_y
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


def ortho_view(name, centre, forward, width_m, w, h, meta=None):
    cam = ortho_cam("CAM_" + name, centre, forward, width_m)
    for c in CATCHERS:
        c.hide_render = True
    render(cam, name, w, h)
    for c in CATCHERS:
        c.hide_render = False
    VIEWS[name] = {"ppm": w * SCALE / width_m, "w": int(w * SCALE), "h": int(h * SCALE), "centre": list(centre),
                   "forward": list(forward), **(meta or {})}


CATCHERS = []


def shadow_catcher(cx, cy, size=120.0):
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
    ko.rotation_euler = Vector((0.40, 0.84, -0.38)).to_track_quat("-Z", "Y").to_euler()   # low key: lights under the eaves
    fl = bpy.data.lights.new("Fill", "SUN")            # a soft, low fill from the viewer's side (the sheets' even light)
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


def sunset_world(exposure=0.6):
    L = LC or {}
    s = L.get("sun", {"elev_deg": 13.0, "azimuth_deg_from_x": 160.0})
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


def lamp_lights():
    """Point lights at the context lamps (layout lights), so lanterns and lamps glow as in the showcase."""
    if not LC:
        return
    for i, lt in enumerate(LC.get("lights", [])):
        loc = lt.get("loc") or lt.get("location")
        if not loc:
            continue
        nm = lt.get("name", "")
        if any(d[3:] in nm for d in DROPPED) or ("StreetLamp" in nm and loc[1] > -1.0):
            continue
        d = bpy.data.lights.new(f"Lamp{i}", "POINT")
        d.energy = 25.0
        d.color = (1.0, 0.68, 0.38)
        d.shadow_soft_size = 0.05
        o = bpy.data.objects.new(f"Lamp{i}", d)
        coll("Lights").objects.link(o)
        o.location = loc


def hall_only(extra=()):
    show(lambda p: p in HALL or p in extra)


# ------------------------------------------------------------------------------------------------ SHEET
def render_sheet():
    sheet_look()
    textured_context()
    hall_only(("SM_DKP_Modern_ACUnit_Roof",))
    shadow_catcher(22.0, 28.0)
    # front elevation (from the courtyard, looking north): 26 m wide
    ortho_view("hall_front", (22.0, 20.0, 4.8), (0, 1, 0), 26.0, 2600, 1300)
    # side elevation (from the west, looking east)
    ortho_view("hall_side", (10.0, 28.0, 4.8), (1, 0, 0), 16.0, 1600, 1300)
    # top view
    cam = ortho_cam("CAM_top", (22.0, 27.8, 10.0), (0, 0, -1), 26.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.location = (22.0, 27.8, 60.0)
    for c in CATCHERS:
        c.hide_render = True
    render(cam, "hall_top", 2000, 1600)
    VIEWS["hall_top"] = {"ppm": 2000 * SCALE / 26.0, "w": int(2000 * SCALE), "h": int(1600 * SCALE),
                         "centre": [22.0, 27.8, 0.0], "forward": [0, 0, -1]}
    for c in CATCHERS:
        c.hide_render = False
    # bay close-up: the door bay at X 19-21 with the veranda post, boards, the step and the stair edge (the sheet's
    # bottom-middle panel)
    for c in CATCHERS:
        c.hide_render = True
    cam = persp_cam("CAM_bay", (19.4, 17.6, 1.55), (20.0, 23.6, 1.6), lens=40)
    render(cam, "hall_bay", 1000, 1800)
    # 3/4 from the front right, above (as the sheet's bottom-right view)
    cam = persp_cam("CAM_34", (38.5, 7.5, 16.0), (21.5, 27.5, 3.2), lens=42)
    render(cam, "hall_34", 1600, 1100)
    # round 3: reference 2's elevated framing under the neutral studio light (the hall alone), for the upper roof form
    render(persp_cam("ref2_studio", (22.0, -7.5, 9.2), (22.0, 23.5, 1.2), lens=30), "context_ref2_studio", 1448, 1086)


# ------------------------------------------------------------------------------------------------ ROOF DETAILS
def demo_gable():
    """roof_kit.gable_roof on a demo plaster box (the verge panel e; the API the storehouse / residence will use),
    placed far from the hall (x 60..66, y 0..5)."""
    import roof_kit as RK
    import kit_mesh as BH
    import dojo_materials as djm
    x0, x1, y0, y1 = 60.0, 66.0, 0.0, 5.0
    r = RK.gable_roof(x0, x1, y0 - 0.6, y1 + 0.6, 3.0, gable_style="plaster", verge_ov=0.0, blocking_run=0.6)
    p = BH.Piece("DEMO_GableRoof", "roof", "Demo", "demo")
    p.g = r["roof"]
    p.wear = False
    c = coll("Demo")
    o, _ = BH.geo_to_object(p, c)
    body = BH.Piece("DEMO_GableBody", "building", "Demo", "demo")
    g = body.g
    BH.cbox(g, x0 + 0.1, x1 - 0.1, y0, y1, 0.0, 2.75, BH.PL, ch=0.01)
    import kit1_geo as K
    for xg in (x0 + 0.1, x1 - 0.1):
        zb = 2.75
        K.prism(g, [Vector((xg, y0, zb)), Vector((xg, y1, zb)), Vector((xg, (y0 + y1) / 2, zb + 2.5 * math.tan(
            math.radians(25.0))))], (1 if xg > 62 else -1, 0, 0), 0.08, BH.PL)
        # a small vent window high on the gable (the sheet's panel e)
        yc = (y0 + y1) / 2
        f = 1 if xg > 62 else -1
        BH.cbox(g, min(xg, xg + f * 0.05), max(xg, xg + f * 0.05), yc - 0.26, yc + 0.26, 3.05, 3.75, BH.TD, ch=0.01)
        BH.cbox(g, min(xg + f * 0.05, xg + f * 0.07), max(xg + f * 0.05, xg + f * 0.07), yc - 0.19, yc + 0.19, 3.12,
                3.68, BH.TD, ch=0.004)
    for (xa, xb) in ((x0 + 0.1, x0 + 0.34), (x1 - 0.34, x1 - 0.1)):
        for (ya, yb) in ((y0 - 0.02, y0 + 0.22), (y1 - 0.22, y1 + 0.02)):
            BH.cbox(g, xa - 0.02, xb + 0.02, ya, yb, 0.0, 2.76, BH.TD, ch=0.01)
    BH.cbox(g, x0 - 0.02, x1 + 0.02, y0 - 0.06, y1 + 0.06, 2.60, 2.78, BH.TD, ch=0.01)
    ob, _ = BH.geo_to_object(body, c)
    for obj in (o, ob):
        for poly in obj.data.polygons:
            pass
        djm.box_uv(obj, "PlasterCream", faces=[pl.index for pl in obj.data.polygons
                                                if obj.data.materials[pl.material_index].name == BH.PL])
    c.hide_render = False
    return (x0, x1, y0, y1)


def render_roof():
    sheet_look(film=False)
    textured_context()
    hall_only(("SM_DKP_Modern_ACUnit_Roof",))
    x0, x1, y0, y1 = demo_gable()
    W, H = 900, 600
    # a1 tile field + eave, straight on (the lower roof front, between the AC units)
    render(persp_cam("a1", (21.0, 18.9, 3.55), (21.0, 22.2, 3.25), lens=55), "roof_a1_tilefield", W, H)
    # a2 eave corner from below-side (the lower roof's front-west corner)
    render(persp_cam("a2", (9.1, 20.1, 2.05), (10.9, 21.9, 3.0), lens=35), "roof_a2_eavecorner", W, H)
    # b1 ridge + ridge end, near side-on (upper ridge, west end)
    render(persp_cam("b1", (15.1, 26.2, 8.75), (14.2, 29.0, 8.55), lens=40), "roof_b1_ridge", W, H)
    # b2 ridge end 3/4
    render(persp_cam("b2", (12.0, 26.4, 9.4), (13.5, 29.0, 8.7), lens=45), "roof_b2_ridgeend", W, H)
    # c1 hip roll from above (upper roof, south-west hip)
    render(persp_cam("c1", (12.0, 21.2, 8.2), (13.3, 24.3, 6.0), lens=40), "roof_c1_hip", W, H)
    # c2 hip corner 3/4 with the upswept eave (upper roof SW corner)
    render(persp_cam("c2", (8.8, 20.0, 7.2), (12.2, 23.2, 5.7), lens=40), "roof_c2_hipcorner", W, H)
    # d1 gable end straight on (the west gable of the upper roof)
    render(persp_cam("d1", (6.4, 29.0, 7.2), (14.0, 29.0, 7.15), lens=40), "roof_d1_gable", W, H)
    # d2 gable 3/4 from below
    render(persp_cam("d2", (7.8, 24.6, 6.3), (13.8, 29.8, 7.3), lens=36), "roof_d2_gable34", W, H)
    # e1 verge of the plain gable roof (demo), straight on
    yc = (y0 + y1) / 2
    render(persp_cam("e1", (x1 + 6.5, yc - 1.8, 3.9), (x1, yc - 1.4, 3.55), lens=40), "roof_e1_verge", W, H)
    # e2 verge 3/4
    render(persp_cam("e2", (x1 + 3.4, y0 - 2.6, 5.2), (x1 - 0.4, yc - 0.6, 3.8), lens=38), "roof_e2_verge34", W, H)
    # f1 gutter + downpipe, front (the hall's front-west corner)
    render(persp_cam("f1", (11.6, 18.4, 2.2), (11.3, 21.8, 2.3), lens=40), "roof_f1_gutter", W, H)
    # f2 gutter 3/4
    render(persp_cam("f2", (8.6, 20.2, 2.6), (10.8, 22.2, 2.2), lens=36), "roof_f2_gutter34", W, H)


# ------------------------------------------------------------------------------------------------ CLOSE-UPS
def render_close():
    sheet_look(film=False)
    textured_context()
    show(lambda p: p in HALL or p.startswith("SM_DKP_Stone_Cistern") or p.startswith("SM_DKP_Modern_ACUnit_Roof")
         or p.startswith("SM_DKP_Stone_Lantern") or p.startswith("SM_DKG_"))
    W, H = 1200, 800
    render(persp_cam("cl_pad", (11.2, 16.8, 2.4), (13.7, 20.6, 2.3), lens=32), "close_eave_landing_route4", W, H)
    render(persp_cam("cl_ac", (18.9, 18.9, 6.4), (15.6, 22.7, 4.7), lens=34), "close_ac_zone_route5", W, H)
    render(persp_cam("cl_pipe", (9.2, 19.8, 1.6), (11.0, 22.2, 1.4), lens=30), "close_downpipe_corner", W, H)
    render(persp_cam("cl_stair", (25.6, 17.8, 1.3), (22.0, 22.0, 0.4), lens=30), "close_stair_band", W, H)
    render(persp_cam("cl_gable", (6.8, 22.2, 4.1), (13.6, 29.0, 6.6), lens=30), "close_gable_verge", W, H)
    render(persp_cam("cl_side", (8.4, 24.4, 1.4), (11.6, 29.4, 1.2), lens=28), "close_veranda_side", W, H)
    render(persp_cam("cl_recess", (19.2, 19.6, 5.7), (21.0, 24.0, 5.25), lens=30), "close_recess_frieze", W, H)
    render(persp_cam("cl_chidori", (5.6, 22.8, 4.9), (11.4, 27.0, 4.05), lens=34), "close_chidori_side", W, H)
    render(persp_cam("cl_ridge", (11.6, 21.4, 10.4), (15.2, 27.6, 7.7), lens=32), "close_ridge_diagonal", W, H)
    render(persp_cam("cl_soffit", (18.6, 22.0, 4.75), (19.6, 24.2, 5.75), lens=24), "close_upper_soffit", W, H)
    render(persp_cam("cl_head", (17.6, 22.55, 2.05), (18.4, 24.0, 2.55), lens=24), "close_door_head", W, H)
    render(persp_cam("cl_deck", (12.1, 22.35, 1.55), (12.9, 24.3, 0.45), lens=24), "close_deck_wall", W, H)
    render(persp_cam("cl_corner", (15.2, 20.6, 7.6), (17.3, 23.6, 5.75), lens=30), "close_recess_corner", W, H)


# ------------------------------------------------------------------------------------------------ CONTEXT
def render_context():
    setup_cycles()
    sunset_world(0.6)
    textured_context()
    show(lambda p: True)
    lamp_lights()
    cams = {c["name"]: c for c in (LC or {}).get("cameras", [])}
    e = cams.get("CAM_Establishing", {"loc": [22.0, -1.6, 2.85], "look_at": [22.0, 30.0, -1.2], "hfov_deg": 74.0})
    lens = 18.0 / math.tan(math.radians(e["hfov_deg"]) / 2)
    render(persp_cam("ctx_est", e["loc"], e["look_at"], lens=lens), "context_establishing_ref2", 1448, 1086)
    render(persp_cam("ctx_court", (22.0, 6.0, 1.7), (22.0, 30.0, 3.6), lens=24), "context_from_courtyard", 1448, 1086)
    # reference 2's composition (hall upper middle, the sand fields in front): from above the gate, 9 m up
    render(persp_cam("ctx_ref2_high", (22.0, -7.5, 9.2), (22.0, 23.5, 1.2), lens=30), "context_ref2_elevated", 1448,
           1086)
    render(persp_cam("ctx_34", (37.5, 9.0, 8.5), (22.0, 27.0, 3.5), lens=28), "context_34_sunset", 1600, 1000)


if WHAT == "sheet":
    render_sheet()
elif WHAT == "roof":
    render_roof()
elif WHAT == "close":
    render_close()
elif WHAT == "context":
    render_context()
vp = OUT / "views.json"
old = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
old.update(VIEWS)
vp.write_text(json.dumps(old, indent=1), encoding="utf-8")
