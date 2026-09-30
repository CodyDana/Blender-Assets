"""Round 4 review renders for the TRAINING SHED and the DRUM PAVILION (Cycles, headless, denoised), from their blends
(read-only: nothing is saved). The context pieces (wall, taiko, crates, ground) take their TEXTURED meshes from their
own kits' source blends (read only, matched by piece name and bounds), as render_hall.py does.

--asset pavilion|shed
--what  sheet    model sheet like the reference: ortho front / side / top + a 3/4 view, grey studio background, a 1.8 m
                 silhouette beside the building (the sheet's own device); the context pieces the sheet shows are kept
                 (the pavilion: the taiko; the shed: the compound wall behind it and its rack)
        close    key close-ups (pavilion: eave corner + bracket, hip end, finial, the route-7 pad over the crate, the
                 plinth stair; shed: post foot + footing, the front band edge over the crate, the top flashing, rack)
        context  a 3/4 view in the compound (studio light) and one sunset view
Run: blender -b --factory-startup Assets/Dojo/DojoPavilion.blend --python Scripts/dojo/shed/render_sp.py --
     --asset pavilion --what sheet [--samples 96] [--tag r0] [--only a,b]
Out: WorkFiles/dojo/build/shed_pavilion/renders/<tag>/<asset>_<view>.png + views_<asset>_<what>.json
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
SPW = WORK / "shed_pavilion"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


ASSET = arg("--asset", "pavilion")
WHAT = arg("--what", "sheet")
SAMPLES = int(arg("--samples", "96"))
TAG = arg("--tag", "r0")
ONLY = arg("--only", "")
OUT = (SPW / "renders" / TAG).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
PREFIX = {"pavilion": "SM_DKV_", "shed": "SM_DKS_"}[ASSET]
OWN = {n for n in KIT if n.startswith(PREFIX)}
VIEWS = {}
SOURCES = ["DojoKit1.blend", "DojoGround.blend", "CourtyardStone.blend", "TrainingProps.blend", "ModernProps.blend",
           "Taiko.blend", "DojoHall.blend", "DojoGreybox.blend"]
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
        o.hide_render = not pred(o) or p.startswith("SM_DGB_Boundary") or dropped_instance(o)


def textured_context():
    need = {piece_of(o) for o in assembly()} - OWN
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
    up = "Y"
    o.matrix_world = Matrix.Translation(Vector(centre) - f * 80.0) @ f.to_track_quat("-Z", up).to_matrix().to_4x4()
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
    name = f"{ASSET}_{name}"
    if ONLY and name not in ONLY.split(","):
        return
    sc.camera = cam
    sc.render.resolution_x = int(w)
    sc.render.resolution_y = int(h)
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


def sheet_look():
    setup_cycles()
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("SheetGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1.0)
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


def set_key(direction, energy=2.6):
    """Point the key light along `direction` (the direction the light travels)."""
    ko = bpy.data.objects["Key"]
    ko.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()
    ko.data.energy = energy


def set_fill(direction, energy=1.3):
    """Point the soft fill along `direction` (the sheets' even light comes from the viewer's side)."""
    fo = bpy.data.objects["Fill"]
    fo.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()
    fo.data.energy = energy


def sunset_world(exposure=0.6):
    s = {"elev_deg": 13.0, "azimuth_deg_from_x": 160.0}
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    el, az = math.radians(s["elev_deg"]), math.radians(s["azimuth_deg_from_x"])
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (1.0, 0.52, 0.26, 1)
    cr.elements[1].position = 0.35
    cr.elements[1].color = (0.30, 0.28, 0.46, 1)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
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


# ------------------------------------------------------------------------------------------------ silhouette
def silhouette(x, y, facing_deg=0.0):
    """A plain 1.8 m standing figure (the sheets' scale device): flat mid-grey, no detail."""
    mat = bpy.data.materials.new("Silhouette")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.09, 0.09, 0.09, 1)
    b.inputs["Roughness"].default_value = 0.9
    parts = []

    def add(obj):
        obj.data.materials.append(mat)
        coll("Sheet").objects.link(obj)
        parts.append(obj)

    def box(name, c, s):
        me = bpy.data.meshes.new(name)
        hx, hy, hz = s
        v = [(c[0] + sx * hx, c[1] + sy * hy, c[2] + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        me.from_pydata(v, [], f)
        add(bpy.data.objects.new(name, me))

    def cyl(name, c, r, h, n=16):
        me = bpy.data.meshes.new(name)
        v = []
        for zz in (c[2] - h / 2, c[2] + h / 2):
            for k in range(n):
                a = 2 * math.pi * k / n
                v.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a) * 0.6, zz))
        f = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        f.append(tuple(range(n - 1, -1, -1)))
        f.append(tuple(range(n, 2 * n)))
        me.from_pydata(v, [], f)
        add(bpy.data.objects.new(name, me))
    cyl("SilLegL", (-0.09, 0, 0.44), 0.075, 0.88)
    cyl("SilLegR", (0.09, 0, 0.44), 0.075, 0.88)
    cyl("SilTorso", (0, 0, 1.19), 0.19, 0.62)
    cyl("SilArmL", (-0.25, 0, 1.13), 0.05, 0.62)
    cyl("SilArmR", (0.25, 0, 1.13), 0.05, 0.62)
    cyl("SilNeck", (0, 0, 1.54), 0.05, 0.10)
    me = bpy.data.meshes.new("SilHead")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.11)
    bm.to_mesh(me)
    bm.free()
    h = bpy.data.objects.new("SilHead", me)
    h.location = (0, 0, 1.69)
    h.scale = (0.85, 0.95, 1.0)
    add(h)
    root = bpy.data.objects.new("Silhouette", None)
    coll("Sheet").objects.link(root)
    for o in parts:
        o.parent = root
    root.location = (x, y, 0.0)
    root.rotation_euler = (0, 0, math.radians(facing_deg))
    return root


# ------------------------------------------------------------------------------------------------ views
def near(o, box):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    x0, x1 = min(p.x for p in bb), max(p.x for p in bb)
    y0, y1 = min(p.y for p in bb), max(p.y for p in bb)
    return x0 < box[1] and x1 > box[0] and y0 < box[3] and y1 > box[2]


def ortho(name, centre, forward, width, w, h):
    cam = ortho_cam("CAM_" + name, centre, forward, width)
    render(cam, name, w, h)
    VIEWS[f"{ASSET}_{name}"] = {"ppm": w / width, "w": w, "h": h, "centre": list(centre), "forward": list(forward)}


def pavilion_sheet():
    sheet_look()
    textured_context()
    keep = ("SM_DKP_Taiko",)
    show(lambda o: piece_of(o).startswith(PREFIX) or piece_of(o).startswith(keep))
    shadow_catcher(41.0, 3.0)
    # the sheet's front = the drum body side-on = from the courtyard (west), looking east
    sil = silhouette(37.0, 6.2, 90.0)
    set_key((0.62, 0.55, -0.56))
    ortho("front_W", (40.8, 3.0, 2.55), (1, 0, 0), 8.6, 1448, 1086)
    # the sheet's side = the drum head = from the north (the stair side), looking south
    sil.location = (44.6, 7.0, 0.0)
    sil.rotation_euler = (0, 0, 0)
    set_key((0.55, -0.62, -0.56))
    ortho("side_N", (41.2, 3.0, 2.55), (0, -1, 0), 8.6, 1448, 1086)
    sil.location = (46.0, 20.0, 0.0)
    cam = ortho_cam("CAM_top", (41.0, 3.0, 20.0), (0, 0, -1), 7.0)
    cam.rotation_euler = (0.0, 0.0, math.radians(180.0))      # the stair (north) at the bottom, as the sheet's top view
    cam.location = (41.0, 3.2, 60.0)
    render(cam, "top", 1000, 1000)
    VIEWS[f"{ASSET}_top"] = {"ppm": 1000 / 7.0, "centre": [41.0, 3.2], "note": "north (the stair) at the bottom"}
    sil.location = (36.6, 6.0, 0.0)
    set_key((0.55, -0.35, -0.75))
    render(persp_cam("CAM_34", (33.6, 11.2, 6.4), (41.0, 3.0, 2.2), lens=40), "34", 1448, 1086)


def pavilion_close():
    sheet_look()
    textured_context()
    show(lambda o: near(o, (30, 50, -3, 12)) and not piece_of(o).startswith("SM_DKP_Modern_StreetLamp"))
    set_key((0.55, 0.45, -0.70))
    render(persp_cam("c_corner", (37.2, -0.2, 2.5), (38.8, 0.9, 3.25), lens=35), "close_eave_corner_SW", 1200, 900)
    render(persp_cam("c_bracket", (38.3, 3.0, 1.9), (39.55, 1.6, 3.2), lens=28), "close_bracket_underside", 1200, 900)
    render(persp_cam("c_finial", (38.0, -0.5, 5.6), (41.0, 3.0, 4.7), lens=70), "close_finial_hips", 1200, 900)
    set_key((0.60, 0.20, -0.77))
    render(persp_cam("c_pad", (34.3, 4.6, 2.4), (38.0, 3.0, 2.6), lens=32), "close_route7_pad_crate", 1200, 900)
    set_key((0.35, -0.55, -0.76))
    render(persp_cam("c_stair", (43.3, 8.6, 1.6), (41.0, 5.2, 0.6), lens=30), "close_plinth_stair_N", 1200, 900)


def pavilion_context():
    sheet_look()
    textured_context()
    show(lambda o: True)
    set_key((0.55, -0.35, -0.75))
    render(persp_cam("ctx_yard", (30.5, 13.5, 4.2), (41.0, 3.0, 2.2), lens=32), "context_from_yard", 1448, 1086)


# ------------------------------------------------------------------------------------------------ shed
def shed_sheet():
    sheet_look()
    set_fill((0.10, -0.97, -0.22), 1.6)       # all shed cameras look from the courtyard (north) side
    textured_context()
    show(lambda o: piece_of(o).startswith(PREFIX) or (near(o, (-1.3, 8.0, -1.3, 0.3)) and "Wall" in piece_of(o)) or
         (near(o, (-1.3, 0.3, -1.3, 8.0)) and "Wall" in piece_of(o)))
    shadow_catcher(3.0, 3.0)
    sil = silhouette(-0.2 + 7.2, 6.4, 0.0)
    set_key((0.40, -0.62, -0.68))
    ortho("front_N", (3.2, 2.5, 1.9), (0, -1, 0), 9.0, 1448, 760)
    sil.location = (0.9, 7.2, 0.0)
    sil.rotation_euler = (0, 0, math.radians(90.0))
    set_key((-0.62, 0.45, -0.64))
    ortho("side_E", (6.0, 3.2, 1.9), (-1, 0, 0), 7.2, 1100, 880)
    sil.location = (20.0, 20.0, 0.0)
    cam = ortho_cam("CAM_top", (3.0, 2.8, 20.0), (0, 0, -1), 8.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.location = (3.0, 2.8, 60.0)
    render(cam, "top", 1100, 1000)
    VIEWS[f"{ASSET}_top"] = {"ppm": 1100 / 8.0, "centre": [3.0, 2.8]}
    sil.location = (7.4, 6.2, 0.0)
    set_key((-0.50, -0.55, -0.67))
    render(persp_cam("CAM_34", (10.2, 11.4, 4.6), (3.0, 2.4, 1.4), lens=34), "34", 1448, 1086)


def shed_close():
    sheet_look()
    set_fill((0.10, -0.97, -0.22), 1.6)       # all shed cameras look from the courtyard (north) side
    textured_context()
    show(lambda o: near(o, (-2, 12, -2, 12)) and not piece_of(o).startswith("SM_DKP_Modern_StreetLamp"))
    set_key((-0.40, -0.60, -0.69))
    render(persp_cam("c_post", (6.6, 6.4, 0.9), (5.58, 4.85, 0.5), lens=35), "close_post_footing", 1200, 900)
    render(persp_cam("c_band", (4.7, 7.9, 3.2), (3.0, 4.7, 2.45), lens=32), "close_front_band_crate", 1200, 900)
    render(persp_cam("c_under", (3.8, 6.2, 1.2), (3.0, 1.0, 2.7), lens=24), "close_underside_rack", 1200, 900)
    set_key((-0.45, -0.35, -0.82))
    render(persp_cam("c_top", (6.6, 3.8, 4.4), (4.5, 0.4, 3.0), lens=35), "close_top_flashing", 1200, 900)


def shed_context():
    sheet_look()
    set_fill((0.10, -0.97, -0.22), 1.6)       # all shed cameras look from the courtyard (north) side
    textured_context()
    show(lambda o: True)
    set_key((-0.45, -0.60, -0.66))
    render(persp_cam("ctx_yard", (11.5, 13.5, 4.2), (3.0, 2.5, 1.6), lens=32), "context_from_yard", 1448, 1086)


def main():
    for c in (bpy.data.collections.get("Kit"),):
        if c:
            c.hide_render = True
    fn = {("pavilion", "sheet"): pavilion_sheet, ("pavilion", "close"): pavilion_close,
          ("pavilion", "context"): pavilion_context, ("shed", "sheet"): shed_sheet, ("shed", "close"): shed_close,
          ("shed", "context"): shed_context}[(ASSET, WHAT)]
    fn()
    (OUT / f"views_{ASSET}_{WHAT}.json").write_text(json.dumps(VIEWS, indent=1), encoding="utf-8")


main()
