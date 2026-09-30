"""Renders for the stone-kit STAIR PATH track (9): Cycles, headless, denoised.

Modes (after --):
  --preview a,b,...   one 3/4 studio view per named piece (name substrings) -> renders/stairs/preview/
  --sheet             every piece: ortho front / side / top + a 3/4 view on grey with a 1.8 m silhouette
                      -> renders/stairs/sheet/<piece>_{front,side,top,persp}.png (compose_stairs.py lays out the sheet)
  --assembly          the sunset assembly test: a stair run with a straight landing, a turn landing, rails, cheeks and
                      lanterns climbing a rough stand-in slope to a stand-in terrace with kit 1's wall on top
                      -> renders/stairs/assembly_*.png
  --closeups          stone faces (cheek rubble), a step nosing, a rail joint, the lanterns -> renders/stairs/cu_*.png
  --match             our views for the side-by-side sheets -> renders/stairs/match_*.png
  --samples N         Cycles samples (default 64; sheet 32)
Reads WorkFiles/dojo/build/stonekit/stairs/StairKit_build.blend (the builder's own blend) and, read-only, kit 1's
Assets/Dojo/DojoKit1.blend for the stand-in dojo wall.
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
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
BUILD_BLEND = WORK / "stairs" / "StairKit_build.blend"
RENDERS = WORK / "renders" / "stairs"
KIT1_BLEND = ROOT / "Assets" / "Dojo" / "DojoKit1.blend"
COLL = "StoneKit_Stairs"
P = "SM_DKT_Stair_"
R, T = 1.0 / 6.0, 1.0 / 3.0


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


SAMPLES = int(arg("--samples", "64"))


# ------------------------------------------------------------------------------------------------ rig
def setup_cycles(samples):
    sc = bpy.context.scene
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


def studio_rig(exposure=0.35):
    """render_sp.py / dkd_common's neutral grey studio: key + fill suns, grey world, AgX medium-high contrast."""
    sc = bpy.context.scene
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
    view(exposure)


def view(exposure):
    sc = bpy.context.scene
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = exposure


def sunset_rig(exposure=0.6, elev=13.0, az_from_x=160.0, sun=4.2):
    """The dojo's review sunset (dkd_common.sunset_rig numbers): a warm low sun and an orange-to-violet sky."""
    sc = bpy.context.scene
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
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
    el, az = math.radians(elev), math.radians(az_from_x)
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = sun
    lt.angle = math.radians(0.8)
    lt.color = (1.0, 0.63, 0.36)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    view(exposure)
    return so


def cam(name, loc, look, lens=50.0, ortho=None):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    c.sensor_width = 36.0
    c.clip_start = 0.02
    c.clip_end = 500.0
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    o = bpy.data.objects.new(name, c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = Vector(look) - Vector(loc)
    up = "Y" if abs(d.normalized().z) < 0.99 else "Y"
    o.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    return o


def render(c, path, w, h):
    sc = bpy.context.scene
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
    """A plain 1.8 m figure (dark matte): legs, torso, arms, head from simple solids."""
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
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(flat_mat("M_Silhouette", (0.05, 0.05, 0.055)))
    o.location = loc
    return o


def load_kit():
    bpy.ops.wm.open_mainfile(filepath=str(BUILD_BLEND))
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    kit = bpy.data.collections[COLL]
    pieces = {o.name: o for o in kit.objects if o.parent is None and o.type == "MESH"}
    for o in kit.objects:
        if o.name.startswith("UCX_"):
            o.hide_render = True
    return sc, kit, pieces


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def only_visible(pieces, keep):
    for n, o in pieces.items():
        o.hide_render = n not in keep


# ------------------------------------------------------------------------------------------------ preview / sheet
def piece_views(pieces, names, out_dir, views=("persp",), res=640):
    sil = silhouette((0, 0, 0))
    floor = floor_plane()
    for n in names:
        o = pieces[n]
        only_visible(pieces, {n})
        lo, hi = bbox(o)
        sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
        floor.location.z = lo.z - 0.0005
        slo = Vector((min(lo.x, hi.x + 0.2), lo.y, lo.z))
        shi = Vector((hi.x + 0.75, hi.y, max(hi.z, lo.z + 1.85)))
        ctr = (slo + shi) / 2
        ext = shi - slo
        short = n.replace(P, "")
        for v in views:
            if v == "front":
                c = cam("C", (ctr.x, slo.y - 20, ctr.z), (ctr.x, slo.y, ctr.z), ortho=max(ext.x, ext.z) * 1.08)
            elif v == "side":
                sil.location = (ctr.x, hi.y + 0.45, lo.z)
                c = cam("C", (slo.x - 20, (lo.y + hi.y + 0.9) / 2, ctr.z), (slo.x, (lo.y + hi.y + 0.9) / 2, ctr.z),
                        ortho=max(ext.y + 0.9, ext.z) * 1.08)
            elif v == "top":
                sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
                c = cam("C", (ctr.x, ctr.y + 1e-3, hi.z + 20), (ctr.x, ctr.y, hi.z), ortho=max(ext.x, ext.y) * 1.08)
            else:
                sil.location = (hi.x + 0.45, (lo.y + hi.y) / 2, lo.z)
                d = Vector((-0.62, -1.0, 0.62)).normalized()
                rad = max(ext.length / 2, 0.6)
                dist = rad / math.tan(math.radians(17.0)) * 1.05
                c = cam("C", ctr + d * dist, ctr, lens=50.0)
            render(c, out_dir / f"{short}_{v}.png", res, res)
            bpy.data.objects.remove(c, do_unlink=True)
    bpy.data.objects.remove(sil, do_unlink=True)


def floor_plane():
    me = bpy.data.meshes.new("Floor")
    s = 60.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("Floor", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(flat_mat("M_Floor", (0.30, 0.30, 0.30), 0.95))
    return o


# ------------------------------------------------------------------------------------------------ assembly
def place(pieces, name, loc, rot, coll, tag=""):
    src = pieces[P + name]
    o = bpy.data.objects.new(f"{name}{tag}", src.data)
    o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    coll.objects.link(o)
    return o


def rz(v, deg):
    a = math.radians(deg)
    return Vector((math.cos(a) * v[0] - math.sin(a) * v[1], math.sin(a) * v[0] + math.cos(a) * v[1], v[2]))


LAYOUT = []        # (piece, loc, rot)
FOOT = []          # stair footprints for the terrain carve: (x0, x1, y0, y1, z_top_fn)


def build_layout():
    """The assembly (world +Y up the slope, the cliff on -X, the drop on +X). Every placement is computed from the
    catalog grid: flights chain by (0, run, rise), landings by W / 2, the rail line is inset 1/6 m (RI) and set back
    1/6 m, so it turns the landing corner exactly."""
    W = 1.8
    hw = W / 2
    RI = hw - 1.0 / 6.0              # the rail line
    L = []
    # the lower landing on the path, flight 1 (1.0 m) straight up: cheek on the cliff side (-X), rail on the drop (+X)
    L.append(("Landing_W180", (0, -hw, 0), 0))
    L.append(("Flight_W180_R100", (0, 0, 0), 0))
    L.append(("Cheek_R100", (-(hw + 0.2), 0, 0), 0))
    L.append(("Cheek_L180", (-(hw + 0.2), -W, 0), 0))
    L.append(("Rail_Flat_L180", (RI, -W - T / 2, 0), 0))
    L.append(("Rail_Slope_R100", (RI, -T / 2, 0), 0))
    L.append(("Lantern_Stone", (-0.52, -1.40, 0.0), 0))
    # landing 1 (straight on), two timber lanterns against the cheek
    L.append(("Landing_W180", (0, 2.0 + hw, 1.0), 0))
    L.append(("Cheek_L180", (-(hw + 0.2), 2.0, 1.0), 0))
    L.append(("Rail_Flat_L180", (RI, 2.0 - T / 2, 1.0), 0))
    L.append(("Lantern_Timber", (-hw + 0.27, 2.0 + 0.30, 1.0), 0))
    L.append(("Lantern_Timber", (-hw + 0.27, 2.0 + W - 0.30, 1.0), 0))
    # flight 2 (2.0 m) straight on
    y2 = 2.0 + W
    L.append(("Flight_W180_R200", (0, y2, 1.0), 0))
    L.append(("Cheek_R200", (-(hw + 0.2), y2, 1.0), 0))
    L.append(("Rail_Slope_R200", (RI, y2 - T / 2, 1.0), 0))
    # the turn landing: a LEFT turn into the cliff (LandingL at rot -90: arrive S, leave W, curbs on E and N);
    # the rail follows the outside: along E (L180), a corner post, across N (T180, turned +90) to flight 3's first post
    y3 = y2 + 4.0
    L.append(("LandingL_W180", (0, y3 + hw, 3.0), -90))
    L.append(("Rail_Flat_L180", (RI, y3 - T / 2, 3.0), 0))
    L.append(("Rail_CornerPost", (RI, y3 - T / 2 + W, 3.0), 0))
    L.append(("Rail_Flat_T180", (RI, y3 - T / 2 + W, 3.0), 90))
    L.append(("Lantern_Timber", (hw - 0.50, y3 + W - 0.50, 3.0), 0))
    # flight 3 (1.0 m) climbing -X into the cliff notch (rot +90), cheeks on both sides, the rail on its right (N)
    L.append(("Flight_W180_R100", (-hw, y3 + hw, 3.0), 90))
    L.append(("Cheek_R100", (-hw, y3 + hw - (hw + 0.2), 3.0), 90))
    L.append(("Cheek_R100", (-hw, y3 + hw + (hw + 0.2), 3.0), 90))
    L.append(("Rail_Slope_R100", (-hw + T / 2, y3 + hw + RI, 3.0), 90))
    # the terrace top: a landing at the terrace edge, the rail on to an end post, a stone lantern
    xt = -hw - 2.0 - hw
    L.append(("Landing_W180", (xt, y3 + hw, 4.0), 0))
    L.append(("Rail_Flat_L180", (-hw - 2.0 + T / 2, y3 + hw + RI, 4.0), 90))
    L.append(("Rail_EndPost", (-hw - 2.0 + T / 2 - W, y3 + hw + RI, 4.0), 90))
    L.append(("Lantern_Stone", (xt + 0.45, y3 + 0.35, 4.0), 0))
    return L




def terrain(support, x0, x1, y0, y1, step=0.25, seed=5):
    """A rough stand-in slope (heightfield): the path level, a cliff rising on the -X side (capped at the terrace
    level), falling away on +X, lumpy noise; under every flight / landing footprint it sits 0.30 below the stone and
    it banks up to the stair edges (never above them), so nothing floats."""
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    verts, faces = [], []
    off = Vector((seed * 1.3, seed * 0.7, 0.0))
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * step, y0 + j * step
            lvl = path_level(y, x)
            if x < -1.3:
                h = min(lvl + (-1.3 - x) * 1.25 - 0.15, 4.35)
            elif x > 1.25:
                h = lvl - 0.25 - (x - 1.25) * 0.55
            else:
                h = lvl - 0.35
            n1 = noise.noise(Vector((x * 0.45, y * 0.45, 0.3)) + off)
            n2 = noise.noise(Vector((x * 1.6, y * 1.6, 1.7)) + off)
            h += 0.30 * n1 + 0.10 * n2
            zt, d = support(x, y)
            if zt is not None:
                if d <= 0.0:
                    h = zt - 0.30
                else:
                    h = max(h, zt - 0.30 - 0.9 * d)
                    if d < 0.35:
                        h = min(h, zt - 0.05)
            verts.append((x, y, h))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new("StandInSlope")
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new("StandInSlope", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(ground_mat())
    return o


def path_level(y, x):
    """The stair path's walking level (the layout's flights and landings)."""
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


def clamp01(v):
    return max(0.0, min(1.0, v))


def ground_mat():
    """Stand-in ground: mossy olive-grey with rock breakup (procedural, render-only)."""
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


def boulders(n, box, seed, zfn):
    rng = random.Random(seed)
    mat = bpy.data.materials.get("M_DJ_Granite_Tri")      # the library granite on its triplanar (object box) path
    for i in range(n):
        x, y = rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3])
        r = rng.uniform(0.35, 0.9)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
        off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
        for v in bm.verts:
            v.co = v.co * Vector((1.0, rng.uniform(0.8, 1.2), 0.7)) + v.co.normalized() * (0.12 * r * noise.noise(v.co * 2.2 + off))
        me = bpy.data.meshes.new(f"Boulder{i}")
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        o = bpy.data.objects.new(f"Boulder{i}", me)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, zfn(x, y) - 0.25 * r)
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        if mat:
            me.materials.append(mat)
            me.uv_layers.new(name="UV0")


def kit1_wall(coll, loc, rot, n_mod=3):
    """Kit 1's wall (footing + body T250 + cap, 4 m modules) appended READ-ONLY from DojoKit1.blend: the style anchor
    standing on the stand-in terrace."""
    want = ["SM_DK_WallFooting_4m", "SM_DK_WallBody_4m_T250", "SM_DK_WallCap_4m"]
    with bpy.data.libraries.load(str(KIT1_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in want if n in src.objects]
    got = {o.name: o for o in dst.objects if o is not None}
    zs = {"SM_DK_WallFooting_4m": 0.0, "SM_DK_WallBody_4m_T250": 0.60}
    body = got.get("SM_DK_WallBody_4m_T250")
    if body:
        zs["SM_DK_WallCap_4m"] = max((body.matrix_world @ Vector(c)).z for c in body.bound_box) + 0.0
    for k in range(n_mod):
        for nm, src in got.items():
            o = bpy.data.objects.new(f"{nm}_{k}", src.data)
            o.matrix_world = Matrix.Translation(Vector(loc) + rz((4.0 * k, 0, zs.get(nm, 0.0)), rot)) @ \
                Matrix.Rotation(math.radians(rot), 4, "Z")
            coll.objects.link(o)
    return got


def assembly(pieces, kit):
    sc = bpy.context.scene
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    for o in pieces.values():
        o.hide_render = True
    L = build_layout()
    placed = []
    lights = []
    cat = json.loads((WORK / "kit_catalog.json").read_text(encoding="utf-8"))["pieces"]
    for i, (nm, loc, rot) in enumerate(L):
        o = place(pieces, nm, Vector(loc), rot, asm, f"__{i:02d}")
        placed.append((nm, o))
        if nm.startswith("Lantern"):
            ll = cat[P + nm]["extra"]["light_local"]
            lw = o.matrix_world @ Vector(ll)
            lt = bpy.data.lights.new(f"LanternLight{i}", "POINT")
            lt.energy = 6.0
            lt.color = (1.0, 0.62, 0.30)
            lt.shadow_soft_size = 0.05
            lo = bpy.data.objects.new(f"LanternLight{i}", lt)
            sc.collection.objects.link(lo)
            lo.location = lw
            lights.append(lo)

    # footprints (world): flights and landings; support(x, y) -> (walking level there, distance outside the piece)
    def support(x, y):
        best, bd = None, 9.0
        for nm, o in placed:
            if not (nm.startswith("Flight") or nm.startswith("Landing")):
                continue
            q = o.matrix_world.inverted() @ Vector((x, y, 0))
            ext = obj_ext(o)
            dx = max(ext[0] - q.x, 0.0, q.x - ext[3])
            dy = max(ext[1] - q.y, 0.0, q.y - ext[4])
            d = math.hypot(dx, dy)
            if d > 2.5:
                continue
            z0 = o.matrix_world.translation.z
            if nm.startswith("Flight"):
                n = round(ext[4] / T)
                zt = z0 + max(0.0, min(n * R, (math.floor(max(q.y, 0.0) / T) + 1) * R)) if q.y >= -0.05 else z0
            else:
                zt = z0
            if d < bd - 1e-6 or (abs(d - bd) < 1e-6 and (best is None or zt < best)):
                best, bd = zt, d
        return best, bd

    terr = terrain(support, -12.0, 8.0, -5.0, 15.0)
    # the stand-in terrace (track 8 builds the real retaining wall): a rubble-faced block whose top is the dojo
    # level +4.0, its east face at the top landing's west edge (x = -4.7), so the path arrives flush
    tb = bpy.data.meshes.new("StandInTerrace")
    bmx = bmesh.new()
    bmesh.ops.create_cube(bmx, size=1.0, matrix=Matrix.Translation((-10.7, 9.0, 1.5)) @ Matrix.Diagonal((12.0, 16.0, 5.0, 1)))
    bmx.to_mesh(tb)
    bmx.free()
    to = bpy.data.objects.new("StandInTerrace", tb)
    sc.collection.objects.link(to)
    tb.materials.append(bpy.data.materials.get("M_DJ_GraniteRubble"))
    tb.uv_layers.new(name="UV0")
    import sys as _s
    _s.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
    import dojo_materials as djm
    djm.box_uv(to, "GraniteRubble", space="WORLD", uv_map="UV0")
    # kit 1's wall (the style anchor) on the terrace: a run along +Y set back from the edge beside the arrival, and a
    # run along -X behind it
    kit1_wall(asm, (-7.4, 3.6, 4.0), 90, n_mod=1)          # south of the arrival (y 3.6 .. 7.6)
    kit1_wall(asm, (-7.4, 10.0, 4.0), 90, n_mod=1)         # north of it (y 10 .. 14): a 2.4 m opening for the path
    boulders(10, (1.6, 7.5, -4.0, 8.0), 11, lambda x, y: path_level(y, 0.0) - 0.45 - 0.55 * max(0.0, x - 1.25))
    return placed, lights


def obj_ext(o):
    vs = o.data.vertices
    key = o.data.name
    if key not in _EXT:
        xs = [v.co.x for v in vs]
        ys = [v.co.y for v in vs]
        zs = [v.co.z for v in vs]
        _EXT[key] = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    return _EXT[key]


_EXT = {}


# ------------------------------------------------------------------------------------------------ main
def main():
    sc, kit, pieces = load_kit()
    setup_cycles(SAMPLES)
    if "--preview" in ARGS:
        subs = arg("--preview").split(",")
        names = [n for n in sorted(pieces) if any(s in n for s in subs)]
        studio_rig()
        piece_views(pieces, names, RENDERS / "preview", views=tuple(arg("--views", "persp").split(",")),
                    res=int(arg("--res", "720")))
    if "--sheet" in ARGS:
        studio_rig()
        piece_views(pieces, sorted(pieces), RENDERS / "sheet", views=("front", "side", "top", "persp"), res=420)
    if "--assembly" in ARGS or "--closeups" in ARGS or "--match" in ARGS:
        sunset_rig(exposure=float(arg("--exposure", "0.6")), elev=14.0, az_from_x=float(arg("--sun-az", "-35")))
        placed, lights = assembly(pieces, kit)
        shots = assembly_shots()
        which = []
        if "--assembly" in ARGS:
            which += [s for s in shots if s[0].startswith("assembly")]
        if "--closeups" in ARGS:
            which += [s for s in shots if s[0].startswith("cu_")]
        if "--match" in ARGS:
            which += [s for s in shots if s[0].startswith("match_")]
        if arg("--shot"):
            which = [s for s in which if any(k in s[0] for k in arg("--shot").split(","))]
        for (nm, loc, look, lens, w, h) in which:
            c = cam(nm, loc, look, lens=lens)
            render(c, RENDERS / f"{nm}.png", w, h)
        if "--save-scene" in ARGS:
            bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "stairs" / "StairKit_assembly.blend"))


def assembly_shots():
    """(name, camera loc, look-at, lens mm, w, h). World +Y runs up the slope; the sunset sun comes from az 160 deg."""
    return [
        ("assembly_overview", (10.5, -6.5, 8.5), (-1.2, 5.0, 2.2), 30, 1600, 1000),
        ("assembly_up_the_path", (1.0, -6.4, 1.9), (-0.2, 4.0, 2.2), 32, 1400, 1000),
        ("assembly_turn", (4.2, 5.8, 5.6), (-1.4, 9.2, 3.4), 30, 1400, 1000),
        ("assembly_down", (-5.6, 10.6, 7.2), (0.4, 2.0, 0.8), 30, 1400, 1000),
        ("cu_step_nosing", (0.55, -1.05, 0.55), (0.1, 0.45, 0.28), 50, 1200, 900),
        ("cu_cheek_stone", (-0.30, 4.6, 2.55), (-1.1, 5.5, 2.35), 45, 1200, 900),
        ("cu_rail_joint", (1.35, 1.45, 1.95), (0.733, 1.833, 1.80), 60, 1200, 900),
        ("cu_lanterns", (0.45, 1.25, 1.85), (-0.63, 2.9, 1.55), 40, 1200, 900),
        ("cu_landing_turn", (2.3, 7.0, 4.8), (-0.2, 8.9, 3.1), 35, 1200, 900),
        ("match_stairs_low", (1.7, -2.6, 3.3), (-0.2, 0.9, 0.35), 32, 1020, 858),
        ("match_stairs_mid", (0.25, -2.6, 1.45), (-0.1, 3.2, 1.75), 30, 720, 900),
        ("match_lanterns", (0.30, 1.0, 1.70), (-0.62, 2.95, 1.45), 38, 850, 600),
    ]


main()
