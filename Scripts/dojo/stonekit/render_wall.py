"""Stone kit track 8 (terrace wall) review renders: Cycles, headless, denoised. Opens the track's own blend
(WorkFiles/dojo/build/stonekit/wall/DojoStoneKit_wall.blend, or --blend) read-only: nothing is saved.

--what preview --pieces A,B   quick studio look (3/4 + front) of some pieces, for iteration
--what sheet                  kit sheet views per family: ortho front / side / top + 3/4, transparent film + shadow
                              catcher (compose_wall.py lays them on the reference grey with the 1.8 m silhouettes)
--what sunset                 sunset assembly test: a terrace wall run with an outside corner under a stand-in of the
                              dojo wall (kit 1's own footing / body / cap pieces, appended read-only from
                              Assets/Dojo/DojoKit1.blend), the stair opening with a stair run, turn, landing, rails and
                              lanterns climbing a rough stand-in slope (track 9's pieces when its blend exists, else
                              plain stand-ins), plus views matching the reference crops
--what closeups               stone faces, sangi-zumi corner, step nosing, curb / rail joints

Run: blender -b --factory-startup --python Scripts/dojo/stonekit/render_wall.py -- --what sheet [--samples 96]
Out: WorkFiles/dojo/build/stonekit/renders/wall/ (views.json holds each ortho view's scale for the silhouettes)
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector, noise

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
WORK = ROOT / "WorkFiles" / "dojo" / "build"
OUTD = WORK / "stonekit" / "renders" / "wall"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


WHAT = arg("--what", "preview")
SAMPLES = int(arg("--samples", "64"))
SCALE = float(arg("--scale", "1.0"))
BLEND = Path(arg("--blend", str(WORK / "stonekit" / "wall" / "DojoStoneKit_wall.blend")))
SUB = arg("--sub", "")
OUT = OUTD / SUB if SUB else OUTD
OUT.mkdir(parents=True, exist_ok=True)
VIEWS_PATH = OUT / "views.json"
VIEWS = json.loads(VIEWS_PATH.read_text(encoding="utf-8")) if VIEWS_PATH.exists() else {}

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_")}
for o in KIT.values():
    o.hide_render = True
    o.hide_viewport = False
for o in bpy.data.objects:
    if o.name.startswith("UCX_"):
        o.hide_render = True


# ------------------------------------------------------------------------------------------------ helpers
def setup_cycles(transparent=False):
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
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


def inst(piece, loc=(0, 0, 0), rot=0.0, c=None, name=None, data=None):
    src = data if data is not None else KIT[piece].data
    o = bpy.data.objects.new(name or f"{piece}__v", src)
    o.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    (c or coll("View")).objects.link(o)
    return o


def ortho_cam(name, centre, forward, width_m, up=(0, 0, 1)):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = width_m
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.1
    cam.clip_end = 400.0
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    f = Vector(forward).normalized()
    o.matrix_world = Matrix.Translation(Vector(centre) - f * 80.0) @ f.to_track_quat("-Z", "Y" if abs(f.z) < 0.99 else "Y").to_matrix().to_4x4()
    return o


def persp_cam(name, loc, look, lens=50.0, shift_y=0.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.05
    cam.clip_end = 900.0
    cam.shift_y = shift_y
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(cam, name, w, h):
    sc.camera = cam
    sc.render.resolution_x = int(w * SCALE)
    sc.render.resolution_y = int(h * SCALE)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath, flush=True)


CATCHERS = []


def shadow_catcher(cx, cy, z=0.0, size=120.0):
    me = bpy.data.meshes.new("Catcher")
    h = size / 2
    me.from_pydata([(cx - h, cy - h, z), (cx + h, cy - h, z), (cx + h, cy + h, z), (cx - h, cy + h, z)], [],
                   [(0, 1, 2, 3)])
    o = bpy.data.objects.new("Catcher", me)
    coll("Sheet").objects.link(o)
    o.is_shadow_catcher = True
    CATCHERS.append(o)
    return o


def ortho_view(name, centre, forward, width_m, w, h, meta=None):
    fwd = {"+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0), "-z": (0, 0, -1)}[forward]
    cam = ortho_cam("CAM_" + name, centre, fwd, width_m)
    for c in CATCHERS:
        c.hide_render = True
    render(cam, name, w, h)
    for c in CATCHERS:
        c.hide_render = False
    VIEWS[name] = {"ppm": w * SCALE / width_m, "w": int(w * SCALE), "h": int(h * SCALE), "centre": list(centre),
                   "forward": forward, **(meta or {})}
    VIEWS_PATH.write_text(json.dumps(VIEWS, indent=1), encoding="utf-8")
    bpy.data.objects.remove(cam, do_unlink=True)


def studio(transparent=True, grey=0.62):
    setup_cycles(transparent)
    world = bpy.data.worlds.new("SheetGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (grey, grey, grey, 1.0)
    bg.inputs["Strength"].default_value = 0.75
    sc.world = world
    lt = bpy.data.lights.new("Key", "SUN")
    lt.energy = 3.2
    lt.angle = math.radians(22.0)
    lt.color = (1.0, 0.98, 0.95)
    ko = bpy.data.objects.new("Key", lt)
    sc.collection.objects.link(ko)
    ko.rotation_euler = Vector((0.45, 0.75, -0.62)).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.exposure = 0.25


def clear_view():
    c = bpy.data.collections.get("View")
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)


def bbox_of(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


# ------------------------------------------------------------------------------------------------ preview
def render_preview():
    studio(transparent=False)
    names = arg("--pieces", "").split(",")
    for nm in names:
        if nm not in KIT:
            print("missing", nm)
            continue
        clear_view()
        o = inst(nm)
        lo, hi = bbox_of([o])
        c = (lo + hi) / 2
        size = (hi - lo).length
        cam = persp_cam("CAMp", c + Vector((-0.55, -1.0, 0.45)).normalized() * size * 1.55, c, lens=50)
        render(cam, f"prev_{nm}_34", 1200, 900)
        cam2 = ortho_cam("CAMf", c, (0, 1, 0), max(hi.x - lo.x, hi.z - lo.z) * 1.15)
        render(cam2, f"prev_{nm}_front", 1200, 900)


# ------------------------------------------------------------------------------------------------ sheet
FAMILIES = {
    "straight": ["SM_DKT_Wall_2m_H2", "SM_DKT_Wall_2m_H3", "SM_DKT_Wall_2m_H4", "SM_DKT_Wall_2m_H6",
                 "SM_DKT_Wall_4m_H2", "SM_DKT_Wall_4m_H3", "SM_DKT_Wall_4m_H4", "SM_DKT_Wall_4m_H6"],
    "corners": ["SM_DKT_Wall_CornerOut_H2", "SM_DKT_Wall_CornerOut_H3", "SM_DKT_Wall_CornerOut_H4",
                "SM_DKT_Wall_CornerOut_H6", "SM_DKT_Wall_CornerIn_H2", "SM_DKT_Wall_CornerIn_H3",
                "SM_DKT_Wall_CornerIn_H4", "SM_DKT_Wall_CornerIn_H6"],
    "ends": ["SM_DKT_Wall_EndL_H2", "SM_DKT_Wall_EndL_H3", "SM_DKT_Wall_EndL_H4", "SM_DKT_Wall_EndL_H6",
             "SM_DKT_Wall_EndR_H2", "SM_DKT_Wall_EndR_H3", "SM_DKT_Wall_EndR_H4", "SM_DKT_Wall_EndR_H6"],
    "stairs": ["SM_DKT_Wall_StairOpening_H2", "SM_DKT_Wall_StairOpening_H3", "SM_DKT_Wall_StairOpening_H4"],
    "topfoot": ["SM_DKT_WallCoping_2m", "SM_DKT_WallCoping_4m", "SM_DKT_WallCoping_CornerOut",
                "SM_DKT_WallCoping_CornerIn", "SM_DKT_WallFoot_2m", "SM_DKT_WallFoot_4m",
                "SM_DKT_WallFoot_CornerOut_H4", "SM_DKT_WallFoot_CornerIn_H4"],
}


def lay_family(names, gap=1.2):
    """Lay the pieces left to right (each at its own pivot yaw 0), each piece's foot on the sheet's ground line:
    wall pieces hang from Z 0, so every piece is lifted by its depth -> the lowest point sits at Z 0."""
    clear_view()
    x = 0.0
    placed = []
    for nm in names:
        if nm not in KIT:
            continue
        o = KIT[nm]
        lo = Vector([min(v.co[i] for v in o.data.vertices) for i in range(3)])
        hi = Vector([max(v.co[i] for v in o.data.vertices) for i in range(3)])
        loc = (x - lo.x, 0.0, -lo.z)
        inst(nm, loc)
        placed.append({"piece": nm, "loc": [round(v, 4) for v in loc], "x0": round(x, 4),
                       "x1": round(x + hi.x - lo.x, 4), "zmin": round(lo.z, 4), "zmax": round(hi.z, 4),
                       "ymin": round(lo.y, 4), "ymax": round(hi.y, 4)})
        x += (hi.x - lo.x) + gap
    return placed, x - gap


def render_sheet():
    studio(transparent=True)
    fams = arg("--families", ",".join(FAMILIES)).split(",")
    for fam in fams:
        placed, width = lay_family(FAMILIES[fam])
        if not placed:
            continue
        objs = list(coll("View").objects)
        lo, hi = bbox_of(objs)
        CATCHERS.clear()
        for o in list(coll("Sheet").objects):
            bpy.data.objects.remove(o, do_unlink=True)
        shadow_catcher((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0.0)
        W = (hi.x - lo.x) * 1.06 + 1.5
        H = (hi.z - lo.z) + 0.8
        c = Vector(((lo.x + hi.x) / 2 - 0.7, (lo.y + hi.y) / 2, (hi.z + lo.z) / 2 - 0.2))
        px_w = 2400
        px_h = int(px_w * H / W)
        meta = {"placed": placed, "family": fam}
        ortho_view(f"sheet_{fam}_front", tuple(c), "+y", W, px_w, px_h, meta)
        # side: each piece seen from +x in its own lane would overlap; render the side of the family laid along Y
        clear_view()
        y = 0.0
        side_placed = []
        for pl in placed:
            o = KIT[pl["piece"]]
            lo_ = Vector([min(v.co[i] for v in o.data.vertices) for i in range(3)])
            hi_ = Vector([max(v.co[i] for v in o.data.vertices) for i in range(3)])
            loc = (0.0, y - lo_.y, -lo_.z)
            inst(pl["piece"], loc)
            side_placed.append({"piece": pl["piece"], "loc": [round(v, 4) for v in loc]})
            y += (hi_.y - lo_.y) + 1.0
        objs = list(coll("View").objects)
        lo, hi = bbox_of(objs)
        Wy = (hi.y - lo.y) * 1.06 + 1.5
        Hs = (hi.z - lo.z) + 0.8
        cs = Vector((hi.x + 1, (lo.y + hi.y) / 2 + 0.7, (hi.z + lo.z) / 2 - 0.2))
        ortho_view(f"sheet_{fam}_side", tuple(cs), "-x", Wy, px_w, int(px_w * Hs / Wy),
                   {"placed": side_placed, "family": fam, "axis": "view from +x: world +Y to the right"})
        # top + 3/4 from the front layout
        lay_family(FAMILIES[fam])
        objs = list(coll("View").objects)
        lo, hi = bbox_of(objs)
        Wt = (hi.x - lo.x) * 1.06 + 1.0
        Ht = (hi.y - lo.y) * 1.3 + 1.0
        ct = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z + 1))
        ortho_view(f"sheet_{fam}_top", tuple(ct), "-z", Wt, px_w, int(px_w * Ht / Wt), {"placed": placed})
        cc = (lo + hi) / 2
        size = (hi - lo).length
        cam = persp_cam("CAM34", cc + Vector((-0.40, -1.0, 0.42)).normalized() * size * 1.05, cc, lens=45)
        render(cam, f"sheet_{fam}_34", 2400, 1200)
        bpy.data.objects.remove(cam, do_unlink=True)


# ------------------------------------------------------------------------------------------------ sunset
def sunset_world(elev=7.0, az=160.0):
    """The dojo's sunset (layout.json sun: elevation 7 deg, azimuth 160 deg from +X, 3000 K), render_kit1's painted
    sky: warm glow at the horizon towards the sun, violet-blue overhead."""
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    el, a = math.radians(elev), math.radians(az)
    to_sun = Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el)))
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
    return to_sun


def kit1_standin():
    """Append kit 1's perimeter wall pieces (read-only) as the dojo wall stand-in on the terrace."""
    names = ["SM_DK_WallFooting_4m", "SM_DK_WallBody_4m_T250", "SM_DK_WallCap_4m", "SM_DK_WallFooting_Corner",
             "SM_DK_WallCap_Corner", "SM_DK_WallBody_1m_T250", "SM_DK_WallFooting_1m", "SM_DK_WallCap_1m"]
    src = ROOT / "Assets" / "Dojo" / "DojoKit1.blend"
    with bpy.data.libraries.load(str(src), link=False) as (a, b):
        b.objects = [n for n in a.objects if n in names]
    got = {}
    for o in b.objects:
        if o is not None:
            got[o.name] = o
    return got


def ground_mat():
    m = bpy.data.materials.new("StandIn_Ground")
    m.use_nodes = True
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (0.10, 0.11, 0.05, 1)
    rp.color_ramp.elements[1].color = (0.22, 0.20, 0.13, 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.95
    return m


def terrain_standin(fn, x0, x1, y0, y1, step=0.5, name="StandIn_Slope"):
    """A plain height-field slope stand-in (the user's terrain comes later): z = fn(x, y)."""
    nx = int((x1 - x0) / step) + 1
    ny = int((y1 - y0) / step) + 1
    verts = [(x0 + i * step, y0 + j * step, fn(x0 + i * step, y0 + j * step)) for j in range(ny) for i in range(nx)]
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(ground_mat())
    o = bpy.data.objects.new(name, me)
    coll("Scene").objects.link(o)
    return o


STAIR_BLENDS = [WORK / "stonekit" / "stairs" / "StairKit_build.blend", ROOT / "Assets" / "Dojo" / "DojoStoneKit.blend"]


def stair_pieces(names):
    """Track 9's pieces (read-only append from its build blend, else the shared kit blend). {} if none exist."""
    for src in STAIR_BLENDS:
        if not src.exists():
            continue
        with bpy.data.libraries.load(str(src), link=False) as (a, b):
            b.objects = [n for n in a.objects if n in names]
        got = {o.name: o for o in b.objects if o is not None}
        if got:
            print("track 9 pieces from", src, sorted(got), flush=True)
            return got
    return {}


def place_obj(src_obj, loc, rot, c, name=None):
    o = bpy.data.objects.new(name or src_obj.name + "__a", src_obj.data)
    o.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    c.objects.link(o)
    return o


def rz(v, deg):
    a = math.radians(deg)
    return Vector((math.cos(a) * v[0] - math.sin(a) * v[1], math.sin(a) * v[0] + math.cos(a) * v[1], v[2]))


def snap_of(piece, snap):
    cat = json.loads((WORK / "stonekit" / "kit_catalog.json").read_text(encoding="utf-8"))
    return Vector(cat["pieces"][piece]["snaps"][snap]["loc"])


def d_(s):
    s = max(0.0, s)
    return 0.10 * s + 0.035 * s * s


ASM = {}


def build_assembly():
    """The assembly test (world metres; terrace grade Z 0; the wall faces -Y)."""
    c = coll("Scene")
    run = [("SM_DKT_Wall_EndL_H3", (0, 0, 0), 0), ("SM_DKT_Wall_4m_H3", (1, 0, 0), 0),
           ("SM_DKT_Wall_StairOpening_H3", (5, 0, 0), 0), ("SM_DKT_Wall_4m_H3", (9, 0, 0), 0),
           ("SM_DKT_Wall_2m_H4", (13, 0, 0), 0), ("SM_DKT_Wall_CornerOut_H4", (15, 0, 0), 0),
           ("SM_DKT_Wall_4m_H4", (16, 1, 0), 90)]
    for nm, loc, rot in run:
        inst(nm, loc, rot, c, name=nm + "__asm")
    feet = [("SM_DKT_WallFoot_4m", (1, -d_(3), -3), 0), ("SM_DKT_WallFoot_4m", (9, -d_(3), -3), 0),
            ("SM_DKT_WallFoot_2m", (13, -d_(4), -4), 0), ("SM_DKT_WallFoot_CornerOut_H4", (15, -d_(4), -4), 0),
            ("SM_DKT_WallFoot_4m", (16 + d_(4), 1, -4), 90)]
    for nm, loc, rot in feet:
        if nm in KIT:
            inst(nm, loc, rot, c, name=nm + "__asm")
    # kit 1's perimeter wall on the coping: outer face 0.10 m behind the coping arris (kit 1 SE-corner rule)
    k1 = kit1_standin()
    L = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))["kit1"]
    zb, fh = L["body_top_z"]["T250"], L["footing_h"]
    yi = 1.10
    for nm, loc, rot in (("SM_DK_WallFooting_4m", (10.9, yi, 0), 0), ("SM_DK_WallBody_4m_T250", (10.9, yi, fh), 0),
                         ("SM_DK_WallCap_4m", (10.9, yi, zb), 0), ("SM_DK_WallFooting_Corner", (14.9, yi, 0), 90),
                         ("SM_DK_WallBody_1m_T250", (14.9, yi - 1.0, fh), 90), ("SM_DK_WallCap_Corner", (14.9, yi, zb), 90),
                         ("SM_DK_WallFooting_4m", (14.9, yi, 0), 90), ("SM_DK_WallBody_4m_T250", (14.9, yi, fh), 90),
                         ("SM_DK_WallCap_4m", (14.9, yi, zb), 90),
                         ("SM_DK_WallFooting_1m", (9.9, yi, 0), 0), ("SM_DK_WallBody_1m_T250", (9.9, yi, fh), 0),
                         ("SM_DK_WallCap_1m", (9.9, yi, zb), 0)):
        if nm in k1:
            place_obj(k1[nm], loc, rot, c)
    # the stair path (track 9) from the opening's foot: an L landing turned 180 (open N + W), a flight down to the
    # west, a landing, another flight; rails on both flights and up the opening's flight; timber lanterns
    sf = Vector((5, 0, 0)) + snap_of("SM_DKT_Wall_StairOpening_H3", "stair_foot")
    ASM["stair_foot"] = list(sf)
    t9 = stair_pieces(["SM_DKT_Stair_LandingL_W180", "SM_DKT_Stair_Landing_W180", "SM_DKT_Stair_Flight_W180_R100",
                       "SM_DKT_Stair_Rail_Slope_R100", "SM_DKT_Stair_Rail_Slope_R200", "SM_DKT_Stair_Rail_EndPost",
                       "SM_DKT_Stair_Lantern_Timber"])
    path = []
    if t9:
        cL = sf + Vector((0, -0.9, 0))
        place_obj(t9["SM_DKT_Stair_LandingL_W180"], cL, 180, c)
        wedge = cL + Vector((-0.9, 0, 0))
        f1 = wedge - Vector((2.0, 0, 1.0))
        place_obj(t9["SM_DKT_Stair_Flight_W180_R100"], f1, -90, c)
        cl2 = f1 + Vector((-0.9, 0, 0))
        place_obj(t9["SM_DKT_Stair_Landing_W180"], cl2, 0, c)
        f2 = cl2 + Vector((-0.9, 0, 0)) - Vector((2.0, 0, 1.0))
        place_obj(t9["SM_DKT_Stair_Flight_W180_R100"], f2, -90, c)
        for fp in (f1, f2):
            for sx in (-1, 1):
                place_obj(t9["SM_DKT_Stair_Rail_Slope_R100"], fp + rz((sx * 0.81, -1.0 / 6.0, 0), -90), -90, c)
        for sx in (-1, 1):
            place_obj(t9["SM_DKT_Stair_Rail_EndPost"], f1 + rz((sx * 0.81, -1.0 / 6.0, 0), -90) + Vector((2.0, 0, 1.0)),
                      0, c)
        for sd in ("rail_L", "rail_R"):
            r0 = Vector((5, 0, 0)) + snap_of("SM_DKT_Wall_StairOpening_H3", sd)
            place_obj(t9["SM_DKT_Stair_Rail_Slope_R200"], r0, 0, c)
            place_obj(t9["SM_DKT_Stair_Rail_Slope_R100"], r0 + Vector((0, 4.0, 2.0)), 0, c)
            place_obj(t9["SM_DKT_Stair_Rail_EndPost"], r0 + Vector((0, 6.0, 3.0)), 0, c)
        lan = t9.get("SM_DKT_Stair_Lantern_Timber")
        if lan:
            for loc in ((cL.x + 1.25, cL.y - 0.2, cL.z - 0.02), (cl2.x - 0.1, cl2.y - 1.3, cl2.z - 0.05),
                        (5.3, 0.95, 0.0), (8.7, 0.95, 0.0)):
                place_obj(lan, loc, 0, c)
        path = [list(sf), list(cL), list(cl2), list(f2)]
    ASM["path"] = path
    ASM["track9"] = sorted(t9)
    return c


def ground_fn(x, y):
    """The rough stand-in terrain (the user's landscape replaces it): the wall foot at -3 (x < 13) / -4 (beyond),
    falling from the foot to the stair path (-3 at the L landing, -4 at the second landing, -5 at the bottom) and on
    down the slope; the ground rises to the terrace past the wall end (x < 0)."""
    def foot(x_):
        return -3.0 if x_ < 12.7 else (-4.0 if x_ > 13.3 else -3.0 - (x_ - 12.7) / 0.6)

    def pathz(x_):
        if x_ > 6.1:
            return -3.0
        if x_ > 4.1:
            return -3.0 - (6.1 - x_) / 2.0
        if x_ > 2.3:
            return -4.0
        if x_ > 0.3:
            return -4.0 - (2.3 - x_) / 2.0
        return -5.0 - (0.3 - x_) * 0.35
    zf = foot(x)
    zp = min(pathz(x), zf)
    nz = noise.noise(Vector((x * 0.35, y * 0.35, 0.7))) * 0.25 + noise.noise(Vector((x * 1.3, y * 1.3, 2.1))) * 0.07
    if x > 16.0:
        return -4.0 - 0.30 * max(0.0, x - 16.0 - d_(4) - 1.2) + (nz if x > 18.3 else 0.0) - 0.02
    if y > -1.6:
        z = zf
    elif y > -5.5:
        f = (-1.6 - y) / 3.9
        z = zf + (zp - zf) * f * f * (3 - 2 * f)
    else:
        z = zp - 0.40 * max(0.0, -7.7 - y)
    z -= 0.02
    if y < -2.2 and not (-7.6 < y < -5.5 and -0.2 < x < 8.2):
        z += nz
    if x < 0.2 and y > -1.6:
        z = max(z, min(0.0, zf + (0.2 - x) * 1.1 - 0.02))
    return z


def rocks(c, n=26, seed=4):
    """A few rough stand-in boulders on the slope (not kit pieces)."""
    rng = random.Random(seed)
    m = bpy.data.materials.new("StandIn_Rock")
    m.use_nodes = True
    bs = next(n_ for n_ in m.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.20, 0.19, 0.17, 1)
    bs.inputs["Roughness"].default_value = 0.9
    for i in range(n):
        x, y = rng.uniform(-6, 21), rng.uniform(-13, -2.4)
        if -0.5 < x < 8.6 and -8.2 < y < -4.9:
            continue
        if 4.4 < x < 9.6 and y > -6.2:
            continue
        if 8.6 < x < 21.0 and y > -7.0:          # keep the terrace wall's matching views clear
            continue
        r = rng.uniform(0.35, 1.3)
        me = bpy.data.meshes.new(f"StandIn_Rock{i}")
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=4, radius=r)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"StandIn_Rock{i}", me)
        o.location = (x, y, ground_fn(x, y) + r * 0.2)
        o.scale = (rng.uniform(0.8, 1.4), rng.uniform(0.8, 1.2), rng.uniform(0.5, 0.8))
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        me.update()
        for v in me.vertices:
            v.co += v.co.normalized() * (noise.noise(v.co * 1.7 + Vector((i, 0, 0))) * 0.18 * r)
        if m:
            me.materials.append(m)
        for pl in me.polygons:
            pl.use_smooth = True
        c.objects.link(o)


def terrace_ground(c):
    me = bpy.data.meshes.new("StandIn_Terrace")
    pts = [(-4.0, 0.54), (15.45, 0.54), (15.45, 5.6), (-4.0, 5.6)]
    me.from_pydata([(x, y, -0.003) for x, y in pts], [], [(0, 1, 2, 3)])
    mt = bpy.data.materials.new("StandIn_TerraceEarth")
    mt.use_nodes = True
    bs = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.36, 0.30, 0.23, 1)
    bs.inputs["Roughness"].default_value = 0.95
    me.materials.append(mt)
    o = bpy.data.objects.new("StandIn_Terrace", me)
    c.objects.link(o)


def sunset_scene():
    setup_cycles(False)
    # the test run stands as the dojo's WEST terrace wall: the layout's sun (elevation 7 deg, azimuth 160 deg in dojo
    # coordinates) turned +90 deg into this scene's frame (face -Y here = the dojo's -X)
    L = json.loads((WORK / "layout.json").read_text(encoding="utf-8")).get("sun", {})
    ASM["sun"] = {"elev_deg": L.get("elev_deg", 7.0), "azimuth_scene_deg": L.get("azimuth_deg_from_x", 160.0) + 90.0,
                  "note": "the layout sunset sun; the test run stands as the dojo's west terrace wall"}
    sunset_world(L.get("elev_deg", 7.0), L.get("azimuth_deg_from_x", 160.0) + 90.0)
    sc.view_settings.exposure = float(arg("--exposure", "0.0"))
    c = build_assembly()
    terrain_standin(ground_fn, -8.0, 24.0, -16.0, 0.6, step=0.25)
    terrace_ground(c)
    rocks(c)
    return c


VIEWS_ASM = {
    "asm_overview": ((-9.0, -21.0, 1.5), (8.0, -2.0, -2.2), 32, 1600, 1000),
    "asm_corner": ((25.0, -11.0, -1.2), (15.3, 0.0, -1.6), 35, 1400, 1000),
    "asm_stair_path": ((-3.5, -13.5, -2.2), (5.5, -4.5, -2.6), 30, 1024, 1536),
    "asm_terrace_wall": ((7.6, -10.0, -1.6), (13.2, 0.3, -0.9), 35, 1400, 900),
    "asm_stair_head": ((3.0, -9.5, 0.4), (7.0, -1.0, -1.0), 35, 1400, 900),
}
CLOSE = {
    "close_stone_faces": ((2.9, -3.2, -2.0), (2.9, -0.6, -2.35), 50, 1400, 1000),
    "close_sangi_zumi": ((18.8, -3.8, -2.5), (16.6, -0.9, -2.6), 45, 1200, 1200),
    "close_step_nosing": ((6.35, -4.0, -1.55), (7.0, -2.6, -2.05), 45, 1400, 1000),
    "close_rail_joints": ((7.2, -3.9, -1.1), (6.2, -2.5, -1.35), 50, 1400, 1000),
    "close_coping_top": ((3.2, -1.6, 1.2), (3.2, 0.3, -0.1), 40, 1400, 1000),
}


def render_sunset():
    sunset_scene()
    views = dict(CLOSE) if WHAT == "closeups" else dict(VIEWS_ASM)
    only = arg("--views", "")
    for nm, (loc, look, lens, w, h) in views.items():
        if only and nm not in only.split(","):
            continue
        cam = persp_cam("CAM_" + nm, loc, look, lens=lens)
        render(cam, nm, w, h)
        bpy.data.objects.remove(cam, do_unlink=True)
    (OUT / "assembly.json").write_text(json.dumps(ASM, indent=1), encoding="utf-8")


if WHAT == "preview":
    render_preview()
elif WHAT == "sheet":
    render_sheet()
elif WHAT in ("sunset", "closeups"):
    render_sunset()
