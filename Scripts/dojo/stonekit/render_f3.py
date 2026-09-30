"""Stone kit FIX ROUND 3 (f3): render_f2.py with the f3 output folder, the kerbs seated in a soil bank on the stand-in
slope and the 1.52 m f3 lantern in the rail-clearance checks. From f2: stone kit FIX ROUND 2 (f2, the owner's reading; built on render_f1.py) review renders: Cycles, headless, denoised. Opens the shared kit blend
Assets/Dojo/DojoStoneKit.blend READ-ONLY (collections StoneKit_Wall + StoneKit_Stairs; nothing is saved) and, read-only,
kit 1's Assets/Dojo/DojoKit1.blend for the stand-in dojo wall / footing.

  --what sheet     every piece: ortho front / side / top + a 3/4 view on studio grey with a 1.8 m figure
                   -> renders/f1/sheet/<piece>_{front,side,top,persp}.png (compose_f1.py lays out the kit sheets)
  --what wall      sunset assembly A: a terrace-wall run with an outside corner under kit 1's dojo wall / footing, the
                   stair opening and the path continuing down along the wall foot (rails on the drop side only, no rail
                   on the wall-face flight: judge delta 12; timber lanterns only: delta 11) + wall close-ups
  --what stairs    sunset assembly B: a stair run with a straight landing, a turn landing, rails and timber lanterns
                   climbing a rough stand-in slope to a stand-in terrace + stair close-ups + reference-matching views
  --views a,b      only these view names;  --samples N (default 96; sheet 32)
  --what preview   dev previews of single pieces (--pieces a,b --blend <file> --out <dir>)
Out: WorkFiles/dojo/build/stonekit/renders/f2/ (f2: straight 1:10 wall profile, kerbs, the low cheek, the r0 framings
     for the reference pairs)
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
SK = WORK / "stonekit"
OUT = SK / "renders" / "f3"
KIT_BLEND = ROOT / "Assets" / "Dojo" / "DojoStoneKit.blend"
STAND_KIT1 = True
KIT1_BLEND = ROOT / "Assets" / "Dojo" / "DojoKit1.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
R, T = 1.0 / 6.0, 1.0 / 3.0


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = Path(arg("--out", str(OUT))).resolve()


WHAT = arg("--what", "sheet")
SAMPLES = int(arg("--samples", "32" if WHAT == "sheet" else "96"))
ONLY = set(arg("--views", "").split(",")) - {""}
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(arg("--blend", str(KIT_BLEND))))
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
KIT = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_") and o.parent is None}
for o in bpy.data.objects:
    if o.name.startswith("UCX_"):
        o.hide_render = True
for o in KIT.values():
    o.hide_render = True
CAT = json.loads((SK / "kit_catalog.json").read_text(encoding="utf-8"))["pieces"]


# ------------------------------------------------------------------------------------------------ rig
def setup_cycles(samples):
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
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
    sc.render.image_settings.color_mode = "RGB"
    sc.cycles.max_bounces = 8
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"


def look(name, exposure):
    try:
        sc.view_settings.look = name
    except TypeError:
        pass
    sc.view_settings.exposure = exposure


def studio_rig():
    world = bpy.data.worlds.new("StudioGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1.0)
    bg.inputs["Strength"].default_value = 1.35
    sc.world = world
    for name, e, ang, d in (("Key", 2.6, 25.0, (0.40, 0.84, -0.38)), ("Fill", 1.3, 40.0, (-0.25, 0.96, -0.10))):
        lt = bpy.data.lights.new(name, "SUN")
        lt.energy = e
        lt.angle = math.radians(ang)
        o = bpy.data.objects.new(name, lt)
        sc.collection.objects.link(o)
        o.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
    look("AgX - Medium High Contrast", 0.35)


def sunset_rig(elev, az_from_x, sun=4.2, exposure=0.3):
    """The dojo's review sunset (render_wall / render_stairs): a warm low sun, an orange-to-violet sky with a glow
    towards the sun."""
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    el, a = math.radians(elev), math.radians(az_from_x)
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
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.0
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 6.0
    nt.links.new(mx.outputs[0], pw.inputs[0])
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
    lt.energy = sun
    lt.angle = math.radians(0.8)
    lt.color = (1.0, 0.63, 0.36)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    look("AgX - Base Contrast", exposure)
    return to_sun


def cam(name, loc, look_at, lens=50.0, ortho=None):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    c.sensor_width = 36.0
    c.clip_start = 0.02
    c.clip_end = 900.0
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    o = bpy.data.objects.new(name, c)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(c, path, w, h):
    sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path, flush=True)


def flat_mat(name, rgb, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def silhouette(loc, h=1.8):
    bm = bmesh.new()
    k = h / 1.8

    def boxp(cx, cy, cz, sx, sy, sz):
        m = Matrix.Translation((cx * k, cy * k, cz * k)) @ Matrix.Diagonal((sx * k, sy * k, sz * k, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    boxp(-0.09, 0, 0.44, 0.13, 0.16, 0.88)
    boxp(0.09, 0, 0.44, 0.13, 0.16, 0.88)
    boxp(0, 0, 1.18, 0.40, 0.22, 0.62)
    boxp(-0.25, 0, 1.12, 0.09, 0.11, 0.66)
    boxp(0.25, 0, 1.12, 0.09, 0.11, 0.66)
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.11 * k,
                              matrix=Matrix.Translation((0, 0, 1.69 * k)))
    me = bpy.data.meshes.new("Silhouette180")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("Silhouette180", me)
    sc.collection.objects.link(o)
    me.materials.append(flat_mat("M_Silhouette", (0.05, 0.05, 0.055)))
    o.location = loc
    return o


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


# ------------------------------------------------------------------------------------------------ sheet
def render_sheet():
    setup_cycles(SAMPLES)
    studio_rig()
    sil = silhouette((0, 0, 0))
    me = bpy.data.meshes.new("Floor")
    s = 80.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("Floor", me)
    sc.collection.objects.link(floor)
    me.materials.append(flat_mat("M_Floor", (0.30, 0.30, 0.30), 0.95))
    names = sorted(KIT)
    sub = arg("--pieces", "")
    if sub:
        names = [n for n in names if any(k in n for k in sub.split(","))]
    res = int(arg("--res", "480"))
    for n in names:
        o = KIT[n]
        for q in KIT.values():
            q.hide_render = q is not o
        lo, hi = bbox(o)
        floor.location.z = lo.z - 0.0005
        slo = Vector((lo.x, lo.y, lo.z))
        shi = Vector((hi.x + 0.75, hi.y, max(hi.z, lo.z + 1.85)))
        ctr = (slo + shi) / 2
        ext = shi - slo
        short = n.replace("SM_DKT_", "")
        for v in ("front", "side", "top", "persp"):
            if v == "front":
                sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
                c = cam("C", (ctr.x, slo.y - 30, ctr.z), (ctr.x, slo.y, ctr.z), ortho=max(ext.x, ext.z) * 1.08)
            elif v == "side":
                sil.location = (ctr.x, hi.y + 0.45, lo.z)
                yc = (lo.y + hi.y + 0.9) / 2
                c = cam("C", (lo.x - 30, yc, ctr.z), (lo.x, yc, ctr.z),
                        ortho=max(hi.y - lo.y + 0.9, ext.z) * 1.08)
            elif v == "top":
                sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
                c = cam("C", (ctr.x, ctr.y + 1e-3, hi.z + 30), (ctr.x, ctr.y, hi.z), ortho=max(ext.x, ext.y) * 1.08)
            else:
                sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
                d = Vector((-0.62, -1.0, 0.62)).normalized()
                rad = max(ext.length / 2, 0.6)
                dist = rad / math.tan(math.radians(17.0)) * 1.05
                c = cam("C", ctr + d * dist, ctr, lens=50.0)
            c.data.clip_end = 2000.0
            render(c, OUT / "sheet" / f"{short}_{v}.png", res, res)
            bpy.data.objects.remove(c, do_unlink=True)


# ------------------------------------------------------------------------------------------------ scene helpers
def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


def place(name, loc, rot, c=None, tag=""):
    src = KIT["SM_DKT_" + name] if not name.startswith("SM_") else KIT[name]
    o = bpy.data.objects.new(f"{name}{tag}", src.data)
    o.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    (c or coll("Asm")).objects.link(o)
    return o


def rz(v, deg):
    a = math.radians(deg)
    return Vector((math.cos(a) * v[0] - math.sin(a) * v[1], math.sin(a) * v[0] + math.cos(a) * v[1], v[2]))


LIGHTS = []
CLEAR = {}


def lantern_light(o, piece="SM_DKT_Stair_Lantern_Timber"):
    ll = CAT[piece]["extra"]["light_local"]
    lt = bpy.data.lights.new(f"LanternLight{len(LIGHTS)}", "POINT")
    lt.energy = 6.0
    lt.color = (1.0, 0.62, 0.30)
    lt.shadow_soft_size = 0.05
    lo = bpy.data.objects.new(lt.name, lt)
    sc.collection.objects.link(lo)
    lo.location = o.matrix_world @ Vector(ll)
    LIGHTS.append(lo)


def lantern(loc, rot=0.0, c=None):
    o = place("Stair_Lantern_Timber", loc, rot, c)
    lantern_light(o)
    return o


def ground_mat():
    m = bpy.data.materials.new("M_StandIn_Ground")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.6
    nz.inputs["Detail"].default_value = 10.0
    nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.30
    cr.elements[0].color = (0.045, 0.058, 0.022, 1)
    cr.elements[1].position = 0.72
    cr.elements[1].color = (0.105, 0.098, 0.085, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def heightfield(fn, x0, x1, y0, y1, step=0.25, name="StandIn_Slope"):
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    verts = [(x0 + i * step, y0 + j * step, fn(x0 + i * step, y0 + j * step)) for j in range(ny) for i in range(nx)]
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1)
             for i in range(nx - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(ground_mat())
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    return o


def rock_mat():
    return flat_mat("M_StandIn_Rock", (0.20, 0.19, 0.17), 0.9)


def boulders(n, box, seed, zfn, avoid=()):
    rng = random.Random(seed)
    m = rock_mat()
    k = 0
    while k < n:
        x, y = rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3])
        if any(a[0] < x < a[1] and a[2] < y < a[3] for a in avoid):
            continue
        r = rng.uniform(0.35, 1.1)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
        off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
        for v in bm.verts:
            v.co = v.co * Vector((1.0, rng.uniform(0.8, 1.2), 0.7)) + v.co.normalized() * (0.14 * r * noise.noise(v.co * 2.2 + off))
        me = bpy.data.meshes.new(f"Boulder{seed}_{k}")
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        sc.collection.objects.link(o)
        o.location = (x, y, zfn(x, y) - 0.25 * r)
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        k += 1


def kit1_parts(names):
    with bpy.data.libraries.load(str(KIT1_BLEND), link=False) as (a, b):
        b.objects = [n for n in a.objects if n in names]
    return {o.name: o for o in b.objects if o is not None}


def place_obj(src, loc, rot, c, name=None):
    o = bpy.data.objects.new(name or src.name + "__a", src.data)
    o.matrix_world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    c.objects.link(o)
    return o


def d_(s):
    """f2: the default wall profile is the straight 1:10 batter (the Sweep variants are not in the assembly)."""
    s = max(0.0, s)
    return 0.10 * s


def snap(piece, name):
    return Vector(CAT[piece]["snaps"][name]["loc"])


# ------------------------------------------------------------------------------------------------ scene A: terrace wall
def scene_wall():
    setup_cycles(SAMPLES)
    L = json.loads((WORK / "layout.json").read_text(encoding="utf-8")).get("sun", {})
    sunset_rig(L.get("elev_deg", 7.0), L.get("azimuth_deg_from_x", 160.0) + 90.0, exposure=float(arg("--exposure", "0.0")))
    c = coll("Asm")
    run = [("Wall_EndL_H3", (0, 0, 0), 0), ("Wall_4m_H3", (1, 0, 0), 0), ("Wall_StairOpening_H3", (5, 0, 0), 0),
           ("Wall_4m_H3", (9, 0, 0), 0), ("Wall_2m_H4", (13, 0, 0), 0), ("Wall_CornerOut_H4", (15, 0, 0), 0),
           ("Wall_4m_H4", (16, 1, 0), 90)]
    for nm, loc, rot in run:
        place(nm, loc, rot, c)
    for nm, loc, rot in (("WallFoot_4m", (1, -d_(3), -3), 0), ("WallFoot_4m", (9, -d_(3), -3), 0),
                         ("WallFoot_2m", (13, -d_(4), -4), 0), ("WallFoot_CornerOut_H4", (15, -d_(4), -4), 0),
                         ("WallFoot_4m", (16 + d_(4), 1, -4), 90)):
        place(nm, loc, rot, c)
    # kit 1's perimeter wall on the coping (outer footing face 0.10 behind the coping arris)
    k1 = kit1_parts(["SM_DK_WallFooting_4m", "SM_DK_WallBody_4m_T250", "SM_DK_WallCap_4m", "SM_DK_WallFooting_Corner",
                     "SM_DK_WallCap_Corner", "SM_DK_WallBody_1m_T250", "SM_DK_WallFooting_1m", "SM_DK_WallCap_1m"])
    Lk = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))["kit1"]
    zb, fh = Lk["body_top_z"]["T250"], Lk["footing_h"]
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
    # the path from the opening's foot: an L landing (turned 180: arrive from the wall, leave west), a flight down to a
    # landing, another flight; rails on the DROP side only, never on the wall-face flight (delta 12)
    W, hw = 1.8, 0.9
    RI = hw - 1.0 / 6.0
    sf = Vector((5, 0, 0)) + snap("SM_DKT_Wall_StairOpening_H3", "stair_foot")
    cL = sf + Vector((0, -hw, 0))
    place("Stair_LandingL_W180", cL, 180, c)
    wedge = cL + Vector((-hw, 0, 0))
    f1 = wedge - Vector((2.0, 0, 1.0))
    place("Stair_Flight_W180_R100", f1, -90, c)
    cl2 = f1 + Vector((-hw, 0, 0))
    place("Stair_Landing_W180", cl2, 0, c)
    f2 = cl2 + Vector((-hw, 0, 0)) - Vector((2.0, 0, 1.0))
    place("Stair_Flight_W180_R100", f2, -90, c)
    for fp in (f1, f2):                               # the drop side (south): local +x at rot -90 = world -Y
        place("Stair_Rail_Slope_R100", fp + rz((RI, -T / 2, 0), -90), -90, c)
        place("Stair_Cheek_R100", fp + rz((-(hw + 0.2), 0, 0), -90), -90, c)      # the wall side: low cheek
    end_f2 = f2 + rz((RI, 2.0 - T / 2, 1.0), -90)
    place("Stair_Rail_Flat_L180", end_f2, -90, c)     # poles across cl2 between f2's end post and f1's start post
    place("Stair_Cheek_L180", cl2 + Vector((-hw, hw + 0.2, 0)), -90, c)
    lan = [cl2 + Vector((0.15, 0.52, 0.0)), cL + Vector((0.52, -0.52, 0.0)),
           Vector((5.30, 0.95, 0.0)), Vector((8.70, 0.95, 0.0))]      # the last two flank the stair head (the gate)
    # f2r2: one lantern per landing; the measured clearance from every lantern's roof (eave half-width 0.22 m, 0 ..
    # 1.35 m tall) to every rail vertex (the r0 defect: a rail through a lantern roof)
    rails = [o for o in c.objects if "Rail" in o.name]
    clear = []
    for q in lan:
        best = 9.0
        for o in rails:
            M = o.matrix_world
            for v in o.data.vertices:
                w = M @ v.co
                if q.z - 0.05 <= w.z <= q.z + 1.55:
                    best = min(best, math.hypot(w.x - q.x, w.y - q.y))
        clear.append(round(best - 0.20, 3))
    CLEAR["wall_scene_lantern_to_rail_clearance_m"] = clear
    for q in lan:
        lantern(q, 0, c)

    def foot(x_):
        return -3.0 if x_ < 12.7 else (-4.0 if x_ > 13.3 else -3.0 - (x_ - 12.7) / 0.6)

    def pathz(x_):
        if x_ > wedge.x:
            return cL.z
        if x_ > f1.x:
            return cL.z - (wedge.x - x_) / 2.0
        if x_ > f1.x - W:
            return f1.z
        if x_ > f2.x:
            return f1.z - (f1.x - W - x_) / 2.0
        return f2.z - (f2.x - x_) * 0.35

    def gfn(x, y):
        zf = foot(x)
        zp = min(pathz(x), zf)
        nz = noise.noise(Vector((x * 0.35, y * 0.35, 0.7))) * 0.25 + noise.noise(Vector((x * 1.3, y * 1.3, 2.1))) * 0.07
        if x > 16.0:
            return -4.0 - 0.30 * max(0.0, x - 16.0 - d_(4) - 1.2) + (nz if x > 18.3 else 0.0) - 0.02
        yn, ys = cL.y + hw + 0.45, cL.y - hw - 0.1
        if x >= wedge.x + W:
            z = zf
        elif y > yn:                                   # between the path's cheek side and the wall foot
            f = max(0.0, min(1.0, (y - yn) / 2.5))
            z = (zp + 0.08) + (zf - (zp + 0.08)) * f * f * (3 - 2 * f)
        elif y > ys:                                   # the path corridor: under the stones (their sides show)
            z = zp - 0.25 if y < cL.y + hw + 0.1 else zp + 0.05
        else:                                          # falling away to the river side
            z = zp - 0.25 - 0.45 * (ys - y) + nz
        z -= 0.03
        if x < 0.2 and y > -1.6:
            z = max(z, min(0.0, zf + (0.2 - x) * 1.1 - 0.02))
        return z
    heightfield(gfn, -8.0, 24.0, -16.0, 0.6, step=0.25)
    tm = flat_mat("M_StandIn_TerraceEarth", (0.36, 0.30, 0.23), 0.95)
    me = bpy.data.meshes.new("StandIn_Terrace")
    me.from_pydata([(x, y, -0.003) for x, y in ((-4.0, 0.54), (15.45, 0.54), (15.45, 5.6), (-4.0, 5.6))], [],
                   [(0, 1, 2, 3)])
    me.materials.append(tm)
    c.objects.link(bpy.data.objects.new("StandIn_Terrace", me))
    boulders(14, (-6, 21, -13, -3.2), 4, gfn, avoid=((f2.x - 1.5, wedge.x + 3.0, cL.y - 2.5, 0.6), (8.6, 21.0, -7.0, 0.6)))
    return {"stair_foot": list(sf), "cL": list(cL), "cl2": list(cl2), "f1": list(f1), "f2": list(f2), **CLEAR}


VIEWS_WALL = {
    "asm_overview": ((-9.0, -21.0, 1.5), (8.0, -2.0, -2.2), 32, 1600, 1000),
    "asm_corner": ((25.0, -11.0, -1.2), (15.3, 0.0, -1.6), 35, 1400, 1000),
    "asm_terrace_wall": ((7.6, -10.0, -1.6), (13.2, 0.3, -0.9), 35, 1400, 900),
    "asm_stair_head": ((3.0, -9.5, 0.4), (7.0, -1.0, -1.0), 35, 1400, 900),
    "asm_stair_path": ((-3.5, -13.5, -2.2), (5.5, -4.5, -2.6), 30, 1024, 1536),
    "close_stone_faces": ((2.9, -3.2, -2.0), (2.9, -0.6, -2.35), 50, 1400, 1000),
    "close_sangi_zumi": ((18.8, -3.8, -2.5), (16.6, -0.9, -2.6), 45, 1200, 1200),
    "close_step_nosing": ((6.35, -4.0, -1.55), (7.0, -2.6, -2.05), 45, 1400, 1000),     # r0's framing and name
    "close_coping_top": ((3.2, -1.6, 1.2), (3.2, 0.3, -0.1), 40, 1400, 1000),
    "match_wall_lower": ((11.0, -6.2, -2.6), (11.0, 0.0, -1.9), 40, 1000, 780),
}


# ------------------------------------------------------------------------------------------------ scene B: stair path
def scene_stairs():
    """World +Y up the slope, the cliff on -X, the drop on +X. Every placement from the catalog grid."""
    setup_cycles(SAMPLES)
    sunset_rig(14.0, float(arg("--sun-az", "-75")), exposure=float(arg("--exposure", "0.45")))   # f3: -75 (f2 -35 threw each lantern's shadow onto the slope right behind it: the "doubled lantern" read)
    c = coll("Asm")
    W, hw = 1.8, 0.9
    RI = hw - 1.0 / 6.0
    lay = []
    # lower path landing + flight 1 (1 m): low cheek on the cliff side, rail on the drop side
    lay += [("Stair_Landing_W180", (0, -hw, 0), 0), ("Stair_Flight_W180_R100", (0, 0, 0), 0),
            ("Stair_Cheek_R100", (-(hw + 0.2), 0, 0), 0), ("Stair_Cheek_L180", (-(hw + 0.2), -W, 0), 0),
            ("Stair_Rail_EndPost", (RI, -W - T / 2, 0), 0), ("Stair_Rail_Flat_L180", (RI, -W - T / 2, 0), 0),
            ("Stair_Rail_Slope_R100", (RI, -T / 2, 0), 0)]
    # landing 1, flight 2 (2 m)
    y2 = 2.0 + W
    lay += [("Stair_Landing_W180", (0, 2.0 + hw, 1.0), 0), ("Stair_Cheek_L180", (-(hw + 0.2), 2.0, 1.0), 0),
            ("Stair_Rail_Flat_L180", (RI, 2.0 - T / 2, 1.0), 0),
            ("Stair_Flight_W180_R200", (0, y2, 1.0), 0), ("Stair_Cheek_R200", (-(hw + 0.2), y2, 1.0), 0),
            ("Stair_Rail_Slope_R200", (RI, y2 - T / 2, 1.0), 0)]
    # the turn: LandingL at rot -90 (a LEFT turn into the cliff); the rail round the outside: poles along E to a corner
    # post, then the T span turned +90 to flight 3's first post
    y3 = y2 + 4.0
    lay += [("Stair_LandingL_W180", (0, y3 + hw, 3.0), -90), ("Stair_Rail_Flat_L180", (RI, y3 - T / 2, 3.0), 0),
            ("Stair_Rail_CornerPost", (RI, y3 - T / 2 + W, 3.0), 0), ("Stair_Rail_Flat_T180", (RI, y3 - T / 2 + W, 3.0), 90),
            ("Stair_Cheek_L180", (-(hw + 0.2), y3, 3.0), 0)]
    # flight 3 (1 m) climbing -X into the cliff notch: cheek on its south (cliff) side, rail on the north (drop) side
    f3 = Vector((-hw, y3 + hw, 3.0))
    lay += [("Stair_Flight_W180_R100", tuple(f3), 90), ("Stair_Cheek_Low_R100", tuple(f3 + rz((-(hw + 0.2), 0, 0), 90)), 90),
            ("Stair_Rail_Slope_R100", tuple(f3 + rz((RI, -T / 2, 0), 90)), 90)]
    # the top landing on the terrace edge, the rail on to an end post
    xt = -hw - 2.0 - hw
    top_end = f3 + rz((RI, 2.0 - T / 2, 1.0), 90)
    lay += [("Stair_Landing_W180", (xt, y3 + hw, 4.0), 0), ("Stair_Rail_Flat_L180", tuple(top_end), 90),
            ("Stair_Rail_EndPost", tuple(top_end + rz((0, W, 0), 90)), 90)]
    # f2: low kerbs of squared blocks along the open (drop, +X) edges of the landings, the reference's path edging;
    # the rail line stands 1/6 m inside them; round the turn a corner block and the N edge
    KO = hw + 0.114
    lay += [("Stair_Kerb_L180", (KO, -W, 0.0), 0), ("Stair_Kerb_L180", (KO, 2.0, 1.0), 0),
            ("Stair_Kerb_L180", (KO, y3, 3.0), 0), ("Stair_Kerb_Corner", (KO, y3 + W + 0.004, 3.0), 0),
            ("Stair_Kerb_L180", (hw, y3 + W + 0.114, 3.0), 90),
            ("Stair_Kerb_L180", (xt + hw, y3 + W + 0.114, 4.0), 90)]
    placed = []
    for nm, loc, rot in lay:
        placed.append((nm, place(nm, loc, rot, c)))
    lan_locs = [(-0.55, -0.55, 0.0), (-0.55, 2.0 + hw, 1.0), (-0.52, y3 + 0.38, 3.0), (xt - 0.5, y3 + 0.35, 4.0)]
    # f2: measured clearance between every lantern (eave half-width 0.22 m, 0 .. 1.31 m tall) and every rail piece's
    # vertices within that height band: the r0 defect was a rail running into a lantern roof
    clear = []
    for lx, ly, lz in lan_locs:
        best = 9.0
        for nm, o in placed:
            if "Rail" not in nm:
                continue
            M = o.matrix_world
            for v in o.data.vertices:
                w = M @ v.co
                if lz - 0.05 <= w.z <= lz + 1.55:
                    best = min(best, math.hypot(w.x - lx, w.y - ly))
        clear.append(round(best - 0.20, 3))
    CLEAR["lantern_to_rail_clearance_m"] = clear
    CLEAR["lanterns_per_landing"] = 1
    # timber lanterns: one per landing, on the cliff side, clear of every rail line (delta 6 / the r0 defect)
    for loc in lan_locs:
        lantern(loc, 0, c)

    def path_level(y, x):
        if y < 0:
            return 0.0
        if y < 2.0:
            return y / 2
        if y < 3.8:
            return 1.0
        if y < 7.8:
            return 1.0 + (y - 3.8) / 2
        if x > -0.9:
            return 3.0
        return min(4.0, 3.0 + (-0.9 - x) / 2.0)

    ext = {}

    def obj_ext(o):
        k = o.data.name
        if k not in ext:
            vs = o.data.vertices
            ext[k] = (min(v.co.x for v in vs), min(v.co.y for v in vs), max(v.co.x for v in vs), max(v.co.y for v in vs))
        return ext[k]

    def support(x, y):
        best, bd = None, 9.0
        for nm, o in placed:
            if not ("Flight" in nm or "Landing" in nm or "Cheek" in nm or "Kerb" in nm):
                continue
            q = o.matrix_world.inverted() @ Vector((x, y, 0))
            e = obj_ext(o)
            dx = max(e[0] - q.x, 0.0, q.x - e[2])
            dy = max(e[1] - q.y, 0.0, q.y - e[3])
            dd = math.hypot(dx, dy)
            if dd > 2.5:
                continue
            z0 = o.matrix_world.translation.z
            if "Flight" in nm or "Cheek_R" in nm or "Cheek_Low_R" in nm:
                n = round(e[3] / T)
                zt = z0 + max(0.0, min(n * R, (math.floor(max(q.y, 0.0) / T) + 1) * R)) if q.y >= -0.05 else z0
            else:
                zt = z0
            sink = 0.03 if "Kerb" in nm else (0.10 if "Cheek_Low" in nm else 0.28)
            if dd < bd - 1e-6 or (abs(dd - bd) < 1e-6 and (best is None or zt - sink < best[0] - best[1])):
                best, bd = (zt, sink), dd
        return best, bd

    off = Vector((6.5, 3.5, 0.0))

    def tfn(x, y):
        lvl = path_level(y, x)
        if x < -1.4:
            h = min(lvl + (-1.4 - x) * 1.25 - 0.10, 4.35)
        elif x > 1.25:
            h = lvl - 0.25 - (x - 1.25) * 0.55
        else:
            h = lvl - 0.30
        h += 0.30 * noise.noise(Vector((x * 0.45, y * 0.45, 0.3)) + off) + 0.10 * noise.noise(Vector((x * 1.6, y * 1.6, 1.7)) + off)
        sp, dd = support(x, y)
        if sp is not None:
            zt, sink = sp
            if dd <= 0.0:
                h = zt - sink
            else:
                h = max(h, zt - sink - 0.9 * dd)
                if dd < 0.35:
                    h = min(h, zt - 0.04)
        # f3: every kerb sits in a soil bank (its buried side never shows: the f2 'spike' under the kerb was the stand-in
        # slope cutting away from the kerb's buried end), whichever piece is nearest
        for nm_, o_ in placed:
            if "Kerb" not in nm_:
                continue
            q = o_.matrix_world.inverted() @ Vector((x, y, 0))
            e = obj_ext(o_)
            dk = math.hypot(max(e[0] - q.x, 0.0, q.x - e[2]), max(e[1] - q.y, 0.0, q.y - e[3]))
            if dk < 1.0:
                h = max(h, o_.matrix_world.translation.z - 0.03 - 0.45 * max(0.0, dk - 0.30))
        return h
    heightfield(tfn, -12.0, 8.0, -5.0, 15.0, step=0.25)
    tb = bpy.data.meshes.new("StandInTerrace")
    bmx = bmesh.new()
    bmesh.ops.create_cube(bmx, size=1.0, matrix=Matrix.Translation((-10.7, 9.0, 1.5)) @ Matrix.Diagonal((12.0, 16.0, 5.0, 1)))
    bmx.to_mesh(tb)
    bmx.free()
    tb.materials.append(rock_mat())
    sc.collection.objects.link(bpy.data.objects.new("StandInTerrace", tb))
    k1 = kit1_parts(["SM_DK_WallFooting_4m", "SM_DK_WallBody_4m_T250", "SM_DK_WallCap_4m"])
    body = k1.get("SM_DK_WallBody_4m_T250")
    zs = {"SM_DK_WallFooting_4m": 0.0, "SM_DK_WallBody_4m_T250": 0.60}
    if body:
        zs["SM_DK_WallCap_4m"] = max((body.matrix_world @ Vector(q)).z for q in body.bound_box)
    for (x0, y0) in ((-7.4, 3.6), (-7.4, 10.0)):
        for nm, src in k1.items():
            place_obj(src, Vector((x0, y0, 4.0 + zs.get(nm, 0.0))), 90, c)
    boulders(10, (1.6, 7.5, -4.0, 8.0), 11, lambda x, y: path_level(y, 0.0) - 0.45 - 0.55 * max(0.0, x - 1.25))
    return {"layout": [(nm, list(loc), rot) for nm, loc, rot in lay], **CLEAR}


VIEWS_STAIRS = {
    "assembly_overview": ((10.5, -6.5, 8.5), (-1.2, 5.0, 2.2), 30, 1600, 1000),
    "assembly_up_the_path": ((1.0, -6.4, 1.9), (-0.2, 4.0, 2.2), 32, 1400, 1000),
    "assembly_turn": ((4.2, 5.8, 5.6), (-1.4, 9.2, 3.4), 30, 1400, 1000),
    "assembly_down": ((-5.6, 10.6, 7.2), (0.4, 2.0, 0.8), 30, 1400, 1000),
    "cu_step_nosing": ((0.55, -1.05, 0.55), (0.1, 0.45, 0.28), 50, 1200, 900),
    "cu_step_side": ((2.4, 0.2, 0.6), (0.9, 1.2, 0.35), 40, 1200, 900),
    "cu_cheek_stone": ((0.10, 4.4, 2.4), (-1.1, 5.5, 2.15), 42, 1200, 900),
    "cu_rail_joint": ((1.35, 1.45, 1.95), (0.733, 1.833, 1.80), 60, 1200, 900),         # r0's framing
    "cu_lanterns": ((0.45, 1.25, 1.85), (-0.63, 2.9, 1.55), 40, 1200, 900),              # r0's framing
    "cu_kerb": ((2.3, -2.6, 0.75), (0.95, -0.9, 0.0), 40, 1200, 900),
    "cu_cheek_low": ((-1.2, 5.4, 4.5), (-1.9, 7.6, 3.40), 40, 1200, 900),
    "cu_landing_turn": ((2.3, 7.0, 4.8), (-0.2, 8.9, 3.1), 35, 1200, 900),
    "cu_landing_flags": ((0.9, 1.1, 2.3), (0.0, 2.9, 1.0), 40, 1200, 900),
    "match_stairs_low": ((1.7, -2.6, 3.3), (-0.2, 0.9, 0.35), 32, 1020, 858),
    "match_stairs_mid": ((0.25, -2.6, 1.45), (-0.1, 3.2, 1.75), 30, 720, 900),
    "match_lanterns": ((0.30, 1.0, 1.70), (-0.62, 2.95, 1.45), 38, 850, 600),            # r0's framing
    "match_lantern_close": ((0.05, 1.75, 1.55), (-0.55, 2.9, 1.55), 45, 580, 800),
}


def shoot(views):
    for nm, (loc, look_at, lens, w, h) in views.items():
        if ONLY and nm not in ONLY:
            continue
        c = cam("CAM_" + nm, loc, look_at, lens=lens)
        render(c, OUT / f"{nm}.png", w, h)
        bpy.data.objects.remove(c, do_unlink=True)


def preview():
    """Dev previews (not deliverables): each --pieces piece alone under the wall assembly's sunset, a flat stand-in
    ground at its foot and kit 1's real footing on the coping (tone check), front 3/4 + a close view."""
    setup_cycles(SAMPLES)
    sunset_rig(7.0, 250.0, exposure=float(arg("--exposure", "0.0")))
    c = coll("Prev")
    k1 = kit1_parts(["SM_DK_WallFooting_4m"])
    names = [n for n in sorted(KIT) if any(k == n.replace("SM_DKT_", "") for k in arg("--pieces", "").split(","))]
    for n in names:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        src = KIT[n]
        o = place(n, (0, 0, 0), 0, c)
        lo, hi = bbox(src)
        h = max(0.5, -lo.z)
        me = bpy.data.meshes.new("PrevGround")
        me.from_pydata([(-20, -20, lo.z + 0.35), (20, -20, lo.z + 0.35), (20, -0.3, lo.z + 0.35), (-20, -0.3, lo.z + 0.35)],
                       [], [(0, 1, 2, 3)])
        me.materials.append(flat_mat("M_PrevGround", (0.10, 0.09, 0.07), 0.95))
        c.objects.link(bpy.data.objects.new("PrevGround", me))
        if "Wall" in n and "Foot" not in n and "SM_DK_WallFooting_4m" in k1:
            place_obj(k1["SM_DK_WallFooting_4m"], (0.0, 1.10, 0.0), 0, c)
        w = hi.x - lo.x
        ctr = Vector(((lo.x + hi.x) / 2, 0.0, (lo.z + 0.35 + hi.z) / 2))
        dist = max(w, hi.z - lo.z) * 1.9 + 1.5
        for tag, d_, lens in (("34", Vector((-0.45, -1.0, 0.18)), 35), ("front", Vector((0.0, -1.0, 0.05)), 35)):
            cm = cam("CP", ctr + d_.normalized() * dist, ctr, lens=lens)
            render(cm, OUT / f"prev_{n.replace('SM_DKT_', '')}_{tag}.png", 1200, 800)
            bpy.data.objects.remove(cm, do_unlink=True)
        cm = cam("CP", ctr + Vector((0.3, -2.6, 0.2)), ctr + Vector((0.2, 0, 0)), lens=45)
        render(cm, OUT / f"prev_{n.replace('SM_DKT_', '')}_close.png", 1200, 800)
        bpy.data.objects.remove(cm, do_unlink=True)


def daylight_rig(elev=62.0, az_from_x=-120.0, sun=4.0, exposure=0.0):
    """f2r2 (STONE_BUILDING_STUDY 3.11 / 6.4): the reference-matched DAYLIGHT test rig for the colour and form gates
    (SG10 / SG11): a high, slightly warm sun from the front-left (the reference's lit crowns and shaded lower rims), a
    pale blue sky. Absolute values are not compared across rigs, only ratios, hue and the dark-joint fraction."""
    world = bpy.data.worlds.new("Daylight")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.70, 0.76, 0.86, 1.0)
    bg.inputs["Strength"].default_value = 0.85
    sc.world = world
    el, a = math.radians(elev), math.radians(az_from_x)
    to_sun = Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el)))
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = sun
    lt.angle = math.radians(1.5)
    lt.color = (1.0, 0.95, 0.88)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    look("AgX - Base Contrast", exposure)
    return to_sun


GATE_VIEWS = {   # (loc, look_at, lens, w, h): Wall_4m_H3 at the origin, face to -Y
    # the reference close crop covers about 2.8 x 2.2 m of terrace wall (90 x 70 source px at ~32 px/m)
    # f2r2: framed to the reference crop's stone size in px (about 6 stones across: ~1.6 m wide)
    "gate_stone_faces": ((2.0, -2.95, -1.50), (2.0, 0.0, -1.58), 50, 1170, 910),   # f3: backed off 1.3 x: the f3 stones are 1.3 x larger, the view keeps ~6 stones across (matched stone size in px)
    # a straight-on elevation of the whole module (layout read)
    "gate_elevation": ((2.0, -30.0, -1.7), (2.0, 0.0, -1.7), None, 1600, 1300),
    # the grazing-light 'sponge' test at 1.5 m
    "gate_grazing": ((0.6, -1.5, -1.2), (2.2, -0.1, -1.6), 35, 1400, 900),
}


def gate():
    """f2r2: the measured-gate renders of one wall piece (--pieces, default Wall_4m_H3) under the daylight rig, and the
    grazing close-up under a raking sun."""
    setup_cycles(SAMPLES)
    nm = arg("--pieces", "Wall_4m_H3")
    c = coll("Gate")
    o = place(nm, (0, 0, 0), 0, c)
    me = bpy.data.meshes.new("GateGround")
    me.from_pydata([(-20, -20, -3.02), (20, -20, -3.02), (20, 0.5, -3.02), (-20, 0.5, -3.02)], [], [(0, 1, 2, 3)])
    me.materials.append(flat_mat("M_GateGround", (0.10, 0.09, 0.07), 0.95))
    c.objects.link(bpy.data.objects.new("GateGround", me))
    k1 = kit1_parts(["SM_DK_WallFooting_4m"])
    if "SM_DK_WallFooting_4m" in k1:
        place_obj(k1["SM_DK_WallFooting_4m"], (0.0, 1.10, 0.0), 0, c)
    sun = daylight_rig(exposure=float(arg("--exposure", "0.6")))
    look(arg("--look", "AgX - Medium High Contrast"), float(arg("--exposure", "0.6")))
    for vn, (loc, at, lens, w, h) in GATE_VIEWS.items():
        if ONLY and vn not in ONLY:
            continue
        if vn == "gate_grazing":
            so = bpy.data.objects["Sun"]
            el, a = math.radians(14.0), math.radians(185.0)
            so.rotation_euler = (-Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el)))).to_track_quat("-Z", "Y").to_euler()
        cm = cam("CG", loc, at, lens=lens or 50, ortho=(4.6 if lens is None else None))
        render(cm, OUT / f"{vn}.png", w, h)
        bpy.data.objects.remove(cm, do_unlink=True)


if WHAT == "sheet":
    render_sheet()
elif WHAT == "gate":
    gate()
elif WHAT == "preview":
    preview()
elif WHAT == "wall":
    info = scene_wall()
    (OUT / "assembly_wall.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    shoot(VIEWS_WALL)
elif WHAT == "stairs":
    info = scene_stairs()
    (OUT / "assembly_stairs.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    shoot(VIEWS_STAIRS)
