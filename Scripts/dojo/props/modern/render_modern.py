"""Review renders for the dojo MODERN PROPS kit (Cycles, headless, OIDN-denoised). Opens Assets/Dojo/ModernProps.blend
read-only (never saves it) and writes PNGs into WorkFiles/dojo/build/props/modern/renders/<round>/.

  --mode views     per prop: front / side / top orthographic + one 3/4 perspective on a transparent film with a
                   shadow catcher, a plain grey 1.8 m silhouette beside the front and side views (composed into model
                   sheets afterwards by compose_sheets.py)
  --mode closeups  close-ups of the details the reference shows (the pole ones on a review assembly: pole +
                   transformer + guy + every span / telecom / drop wire at its socket)
  --mode lineup    every prop in a row on pale gravel at sunset (warm low sun, the reference-2 mood), with review
                   point lights at the lantern bulbs (stand-ins for the in-game light components)

Wire model sheets draw the conductor 8x thicker from its stored centreline (review preview, labelled on the sheet);
the pole attachment sheets show the pole as a light-grey ghost for context.

Review-only helpers (NOT assets, never exported): the silhouette, a mock 25 deg roof slab under the roof AC, a mock
plaster wall behind the wall props, the lineup ground (the ground kit's T_DKG_Gravel textures, read-only).

Run: blender -b --factory-startup Assets/Dojo/ModernProps.blend --python Scripts/dojo/props/modern/render_modern.py --
     --mode views|closeups|lineup [--round r0] [--samples 64] [--only SM_A,SM_B]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.lock import assert_owner  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


MODE = arg("--mode", "views")
ROUND = arg("--round", "r0")
SAMPLES = int(arg("--samples", "64"))
ONLY = [s for s in arg("--only", "").split(",") if s]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "modern" / "renders" / ROUND
GROUND_TEX = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
WALL_PROPS = ("SM_DKP_Modern_ACUnit_Wall", "SM_DKP_Modern_WallLamp", "SM_DKP_Modern_JunctionBox")
POLE_ATTACH = ("SM_DKP_Modern_PoleTransformer", "SM_DKP_Modern_PoleGuy")
WIRE_THICK = 8.0
T25 = math.tan(math.radians(25))
MOUNT = {"SM_DKP_Modern_ACUnit_Wall": 1.55, "SM_DKP_Modern_WallLamp": 2.45, "SM_DKP_Modern_JunctionBox": 0.30}


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def flat_mat(name, hexs, rough=0.8, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = tuple(srgb_to_lin(int(hexs[i:i + 2], 16) / 255) for i in (1, 3, 5)) + (1,)
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    return m


def props():
    return {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKP_Modern_")}


def setup_render(w, h, transparent):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type in ("OPTIX",)
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        print("GPU setup failed, CPU render:", exc)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


def world(color, strength, horizon=None):
    w = bpy.data.worlds.get("W") or bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type not in ("OUTPUT_WORLD",):
            nt.nodes.remove(n)
    bg = nt.nodes.new("ShaderNodeBackground")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = strength
    if horizon is None:
        bg.inputs["Color"].default_value = color + (1,)
    else:   # vertical gradient: horizon colour at the horizon, `color` at the zenith
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = horizon + (1,)
        ramp.color_ramp.elements[1].position = 0.45
        ramp.color_ramp.elements[1].color = color + (1,)
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])


def add_light(name, kind, loc, target, energy, size=1.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    if kind == "SUN":
        ld.angle = math.radians(size)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(name, loc, target, ortho=None, lens=50.0, up="Y"):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.01, 500
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    bpy.context.scene.camera = ob
    return ob


def mk_obj(name, verts, faces, mat, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def box_obj(name, x0, x1, y0, y1, z0, z1, mat):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return mk_obj(name, v, f, mat)


def silhouette(name, loc, mat):
    """A plain grey 1.8 m human silhouette (review helper), feet at loc, facing -Y."""
    bm = bmesh.new()

    def ell(c, r, sx=1.0, sy=1.0, sz=1.0):
        m = Matrix.Translation(c) @ Matrix.Diagonal((sx, sy, sz, 1))
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=r, matrix=m)

    def limb(p0, p1, r0, r1):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=r0, radius2=r1, depth=d.length, matrix=m)
    ell((0, 0, 1.685), 0.105, 0.92, 1.0, 1.12)
    limb((0, 0, 1.50), (0, 0, 1.60), 0.05, 0.048)
    ell((0, 0, 1.28), 0.2, 0.95, 0.55, 1.25)
    ell((0, 0, 1.00), 0.17, 1.0, 0.62, 0.7)
    for s in (-1, 1):
        ell((0.17 * s, 0, 1.44), 0.075)
        limb((0.19 * s, 0, 1.44), (0.23 * s, 0.01, 1.12), 0.05, 0.042)
        limb((0.23 * s, 0.01, 1.12), (0.25 * s, 0.02, 0.84), 0.042, 0.034)
        ell((0.255 * s, 0.02, 0.80), 0.045, 0.8, 0.6, 1.2)
        limb((0.095 * s, 0, 0.98), (0.10 * s, 0.0, 0.52), 0.085, 0.06)
        limb((0.10 * s, 0.0, 0.52), (0.10 * s, 0.02, 0.08), 0.058, 0.042)
        ell((0.10 * s, -0.05, 0.04), 0.06, 0.8, 1.8, 0.6)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.location = loc
    return ob


def roof_slab(name, x0, x1, y0, y1, mat, z_at=lambda y: y * T25):
    """Mock 25 deg roof under the roof AC (review helper): top face on the roof plane, 12 cm thick."""
    v = []
    for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        v.append((x, y, z_at(y) - 0.12))
    for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        v.append((x, y, z_at(y) - 0.002))
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return mk_obj(name, v, f, mat)


def world_bbox(obs):
    pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def render_to(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered", path)



def wire_preview(ob, factor, mat_name="M_DKP_Modern_Cable"):
    """Review-only thickened copy of a wire (its stored centrelines swept as curves, radius x factor) so a 13 mm
    conductor is visible at model-sheet scale. Never exported; the sheet says so."""
    lines = json.loads(ob["review_centrelines"])
    r = float(ob["review_radius"])
    cu = bpy.data.curves.new(ob.name + "_REV", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r * factor
    cu.bevel_resolution = 2
    for pts in lines:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for k, q in enumerate(pts):
            sp.points[k].co = (q[0], q[1], q[2], 1.0)
    o = bpy.data.objects.new(ob.name + "_REV", cu)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(bpy.data.materials[mat_name])
    o.matrix_world = ob.matrix_world.copy()
    return o


def ghost(ob, mat):
    """Review-only neutral-grey stand-in of another prop (context for the pole attachments)."""
    g = ob.copy()
    bpy.context.scene.collection.objects.link(g)
    for slot in g.material_slots:
        slot.link = "OBJECT"
        slot.material = mat
    g.hide_render = False
    return g


def bulb_points(ob):
    """World centres of each connected BulbLit island (the lantern bulbs) on a prop."""
    me = ob.data
    idx = [i for i, m in enumerate(me.materials) if m and m.name == "M_DKP_Modern_BulbLit"]
    if not idx:
        return []
    pts = [ob.matrix_world @ p.center for p in me.polygons if p.material_index in idx]
    groups = []
    for q in pts:
        for g in groups:
            if (g[0] - q).length < 0.08:
                g.append(q)
                break
        else:
            groups.append([q])
    return [sum(g, Vector()) / len(g) for g in groups]


def bulb_lights(obs, energy=6.0):
    """Review lights at the lantern bulbs (stand-ins for the in-game light components, never exported)."""
    made = []
    for ob in obs:
        for c in bulb_points(ob):
            ld = bpy.data.lights.new("REV_Bulb", "POINT")
            ld.energy = energy
            ld.color = (1.0, 0.62, 0.30)
            ld.shadow_soft_size = 0.02
            lo = bpy.data.objects.new("REV_Bulb", ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = c
            made.append(lo)
    return made


# ------------------------------------------------------------------------------------------------ model sheet views

def mode_views():
    P = props()
    names = ONLY or list(P)
    sil_mat = flat_mat("REV_Silhouette", "#8E8E8E", 0.9)
    helper_mat = flat_mat("REV_Helper", "#8E8A83", 0.9)
    world((0.62, 0.62, 0.62), 0.55)
    # soft even studio: big key front-left-top, fill right, rim back
    add_light("Key", "AREA", (-6, -8, 9), (0, 0, 1), 2600, size=8)
    add_light("Fill", "AREA", (8, -5, 4), (0, 0, 1), 800, size=8)
    add_light("Rim", "AREA", (2, 9, 7), (0, 0, 1), 800, size=8)
    catcher = mk_obj("REV_Catcher", [(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [(0, 1, 2, 3)], helper_mat)
    catcher.is_shadow_catcher = True
    hold = bpy.data.materials.new("REV_Holdout")
    hold.use_nodes = True
    hnt = hold.node_tree
    for n_ in list(hnt.nodes):
        if n_.type != "OUTPUT_MATERIAL":
            hnt.nodes.remove(n_)
    hnt.links.new(hnt.nodes.new("ShaderNodeHoldout").outputs[0],
                  next(n_ for n_ in hnt.nodes if n_.type == "OUTPUT_MATERIAL").inputs["Surface"])
    below = box_obj("REV_BelowGrade", -30, 30, -30, 30, -3.0, -0.002, hold)   # hides the pole butt below grade
    meta = {}
    for name in names:
        for o in P.values():
            o.hide_render = o.name != name
        ob = P[name]
        helpers = []
        lo, hi = world_bbox([ob])
        is_roof = name.endswith("ACUnit_Roof")
        is_wall = name in WALL_PROPS
        is_wire = "_Wire_" in name
        if is_roof:
            helpers.append(roof_slab("REV_Roof", lo.x - 0.6, hi.x + 0.6, -1.2, 2.0, helper_mat))
        if is_wire:
            ob.hide_render = True
            helpers.append(wire_preview(ob, WIRE_THICK))
        if name in POLE_ATTACH:
            helpers.append(ghost(P["SM_DKP_Modern_UtilityPole"], helper_mat))
        catcher.hide_render = is_roof or is_wall or is_wire
        below.hide_render = is_roof or is_wall or is_wire     # wires hang below their pivot: no below-grade holdout
        if is_wall:
            wz0 = -MOUNT[name]
            helpers.append(box_obj("REV_Wall", lo.x - 0.25, hi.x + 0.25, 0.0, 0.06, wz0, hi.z + 0.15, helper_mat))
        # silhouettes: one beside the front view (to the right), one beside the side view (to the right = +Y)
        zf = -MOUNT[name] if is_wall else 0.0      # wall props: the figure stands on the ground below the mount
        if is_wire:
            zf = lo.z                               # wires: the figure stands level with the lowest point of the wire
        gap = 0.62 if is_wall else 0.45
        s_front = silhouette("REV_SilF", (hi.x + gap, (lo.y + hi.y) / 2, zf), sil_mat)
        if is_roof:   # stand the side-view figure on the roof slope in front of the unit
            s_side = silhouette("REV_SilS", ((lo.x + hi.x) / 2, -0.75, -0.75 * T25), sil_mat)
        else:
            s_side = silhouette("REV_SilS", ((lo.x + hi.x) / 2, hi.y + 0.45, zf), sil_mat)
        s_side.rotation_euler = (0, 0, math.radians(90))
        bpy.context.view_layer.update()
        allobs = [ob] + helpers
        views = {}
        # common pixel density from the largest ortho extent
        flo, fhi = world_bbox(allobs + [s_front])
        slo, shi = world_bbox(allobs + [s_side])
        tlo, thi = world_bbox([ob])
        if not (is_wall or is_roof or is_wire):      # floor props: frame from the ground up (the pole's butt is below grade)
            flo.z = max(flo.z, -0.03)
            slo.z = max(slo.z, -0.03)
        ext = {"front": (fhi.x - flo.x, fhi.z - flo.z), "side": (shi.y - slo.y, shi.z - slo.z),
               "top": (thi.x - tlo.x, thi.y - tlo.y)}
        big = max(max(e) for e in ext.values())
        pxm = 1100.0 / (big * 1.08)
        if is_wire:
            pxm = min(pxm, 1600.0 / (big * 1.08))
        for view in ("front", "side", "top"):
            ew, eh = ext[view]
            w = max(160, int(ew * 1.08 * pxm + 60))
            h = max(160, int(eh * 1.08 * pxm + 60))
            if is_wire and view != "top":
                h = max(h, 220)
            setup_render(w, h, True)
            ortho = max(w, h) / pxm
            s_front.hide_render = view != "front"
            s_side.hide_render = view != "side"
            if view == "front":
                c = (flo + fhi) / 2
                cam = camera("CamF", (c.x, flo.y - 30, c.z), (c.x, 0, c.z), ortho=ortho, up="Y")
            elif view == "side":
                c = (slo + shi) / 2
                cam = camera("CamS", (shi.x + 30, c.y, c.z), (0, c.y, c.z), ortho=ortho, up="Y")
            else:
                c = (tlo + thi) / 2
                s_front.hide_render = s_side.hide_render = True
                cam = camera("CamT", (c.x, c.y, thi.z + 30), (c.x, c.y, 0), ortho=ortho, up="Y")
            render_to(OUT / "_views" / f"{name}_{view}.png")
            bpy.data.objects.remove(cam)
            views[view] = [w, h]
        # 3/4 perspective from the front-left, above
        s_front.hide_render = s_side.hide_render = True
        lo, hi = world_bbox([ob] if (is_wall or name in POLE_ATTACH) else allobs)
        c = (lo + hi) / 2
        rad = (hi - lo).length / 2
        setup_render(1100, 1100, True)
        if is_wire:
            c = Vector((c.x, c.y, c.z))
            d = Vector((-0.35, -1.0, 0.25)).normalized()
            cam = camera("Cam34", c + d * rad * 1.35, c, lens=35)
        else:
            d = Vector((-0.75, -1.0, 0.62)).normalized()
            cam = camera("Cam34", c + d * rad * 2.6, c, lens=50)
        render_to(OUT / "_views" / f"{name}_34.png")
        bpy.data.objects.remove(cam)
        views["34"] = [1100, 1100]
        meta[name] = {"views": views, "px_per_m": round(pxm, 2)}
        if is_wire:
            meta[name]["note"] = f"wire drawn {WIRE_THICK:.0f}x thicker for this sheet only (review preview)"
        if name in POLE_ATTACH:
            meta[name]["note"] = "light grey = the utility pole, shown for context (not part of this asset)"
        for h_ in helpers + [s_front, s_side]:
            bpy.data.objects.remove(h_)
    tag = ("_" + ONLY[0].replace("SM_DKP_Modern_", "")) if ONLY else ""
    (OUT / "_views" / f"views_meta{tag}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def place(ob, loc, rot_deg=0.0):
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(rot_deg))


def dup(ob):
    o2 = ob.copy()
    bpy.context.scene.collection.objects.link(o2)
    o2.hide_render = False
    return o2


def assemble_pole(P, loc, rot_deg, drop_target, incoming=True, guy=True, transformer=True):
    """Review assembly (copies, never exported): pole + transformer + guy at the pole's own transform, a span wire
    out of every insulator socket (and one coming in), the telecom bundle, and a service drop to `drop_target`."""
    made = []
    pole = dup(P["SM_DKP_Modern_UtilityPole"])
    place(pole, loc, rot_deg)
    made.append(pole)
    if transformer:
        t = dup(P["SM_DKP_Modern_PoleTransformer"])
        place(t, loc, rot_deg)
        made.append(t)
    if guy:
        g = dup(P["SM_DKP_Modern_PoleGuy"])
        place(g, loc, rot_deg)
        made.append(g)
    bpy.context.view_layer.update()
    src = P["SM_DKP_Modern_UtilityPole"]
    mw = pole.matrix_world
    socks = {c.name.split(src.name + "_")[-1]: mw @ c.matrix_local.translation for c in src.children
             if c.name.startswith("SOCKET_")}
    line_yaw = rot_deg + 90.0                       # spans are built along +X; the line runs along the pole's local Y
    dirv = Vector((math.cos(math.radians(line_yaw)), math.sin(math.radians(line_yaw)), 0))
    for key, p in socks.items():
        if key.startswith("Wire_"):
            w = dup(P["SM_DKP_Modern_Wire_Span25"])
            place(w, p, line_yaw)
            made.append(w)
            if incoming:
                w2 = dup(P["SM_DKP_Modern_Wire_Span25"])
                place(w2, p - dirv * 25.0, line_yaw)
                made.append(w2)
    for sgn in ((1, -1) if incoming else (1,)):
        tel = dup(P["SM_DKP_Modern_Wire_Telecom25"])
        place(tel, socks["Telecom"] if sgn > 0 else socks["Telecom"] - dirv * 25.0, line_yaw)
        made.append(tel)
    if drop_target is not None:
        dr = dup(P["SM_DKP_Modern_Wire_Drop12"])
        p0 = socks["Drop_1"]
        d = Vector(drop_target) - p0
        place(dr, p0, math.degrees(math.atan2(d.y, d.x)))
        dr.scale = (math.hypot(d.x, d.y) / 12.0, 1, d.z / -3.0)
        made.append(dr)
    return made


# ------------------------------------------------------------------------------------------------ close-ups

POLE_ASM = "POLE_ASM"
CLOSEUPS = {
    # name: (prop or POLE_ASM, camera location, target, lens)
    "vending_front_detail": ("SM_DKP_Modern_VendingMachine", (0.85, -2.2, 1.15), (0.0, -0.37, 0.85), 38),
    "vending_display_window": ("SM_DKP_Modern_VendingMachine", (0.35, -1.12, 1.55), (-0.04, -0.37, 1.45), 45),
    "vending_coin_strip": ("SM_DKP_Modern_VendingMachine", (0.55, -0.95, 1.00), (0.22, -0.37, 0.85), 45),
    "vending_top_lip": ("SM_DKP_Modern_VendingMachine", (-1.1, -1.6, 2.35), (0.0, -0.15, 1.62), 45),
    "vending_side_depth": ("SM_DKP_Modern_VendingMachine", (2.6, -0.2, 1.0), (0.0, 0.0, 0.88), 40),
    "acroof_fan_front": ("SM_DKP_Modern_ACUnit_Roof", (-0.45, -1.25, 1.55), (-0.17, 0.05, 1.44), 50),
    "acroof_fan_blades_oblique": ("SM_DKP_Modern_ACUnit_Roof", (0.35, -0.95, 1.85), (-0.17, 0.05, 1.43), 55),
    "acroof_stand_runners": ("SM_DKP_Modern_ACUnit_Roof", (-2.1, -0.9, 0.9), (0.0, 0.8, 0.45), 35),
    "acroof_valves_lineset": ("SM_DKP_Modern_ACUnit_Roof", (2.0, -0.7, 1.55), (0.62, 0.5, 0.95), 38),
    "acroof_rear_slope": ("SM_DKP_Modern_ACUnit_Roof", (2.0, 2.6, 2.0), (0.3, 1.4, 0.85), 38),
    "acroof_top": ("SM_DKP_Modern_ACUnit_Roof", (-1.2, -1.4, 2.9), (0.0, 0.56, 1.86), 38),
    "acwall_fan_valves": ("SM_DKP_Modern_ACUnit_Wall", (0.95, -1.05, 0.55), (0.08, -0.2, 0.22), 45),
    "walllamp_head": ("SM_DKP_Modern_WallLamp", (-0.95, -1.65, 0.20), (0.0, -0.36, -0.08), 40),
    "walllamp_side": ("SM_DKP_Modern_WallLamp", (1.6, -0.35, 0.05), (0.0, -0.25, -0.10), 40),
    "streetlampA_head": ("SM_DKP_Modern_StreetLamp_A", (-1.2, -1.9, 3.0), (-0.14, 0.0, 2.62), 48),
    "streetlampB_head": ("SM_DKP_Modern_StreetLamp_B", (1.2, -1.7, 2.6), (0.14, 0.0, 2.2), 48),
    "streetlampA_base": ("SM_DKP_Modern_StreetLamp_A", (0.9, -1.3, 0.8), (0.0, 0.0, 0.3), 45),
    "pole_crossarms": (POLE_ASM, (-2.2, -3.0, 7.7), (0.0, -0.1, 6.9), 38),
    "pole_transformer": (POLE_ASM, (-1.7, -2.3, 5.4), (0.0, -0.35, 5.8), 40),
    "pole_riser_box": (POLE_ASM, (2.0, -1.5, 3.9), (0.15, 0.0, 3.5), 40),
    "pole_coil_telecom": (POLE_ASM, (-2.1, -1.2, 5.1), (-0.2, 0.0, 4.65), 40),
    "guy_anchor": (POLE_ASM, (1.7, 1.6, 1.3), (0.0, 3.4, 0.35), 40),
    "wire_span_end_insulator": (POLE_ASM, (-1.35, -1.1, 7.75), (-0.85, -0.05, 7.50), 55),
    "wire_drop_deadend": (POLE_ASM, (0.95, -0.75, 6.38), (0.40, 0.05, 6.17), 50),
    "wire_midspan_telecom": (POLE_ASM, (0.75, 12.2, 4.45), (-0.30, 12.5, 4.36), 60),
    # r2: the wires from close range (judges: 'review renders of the wires from close range')
    "wire_span_close": (POLE_ASM, (1.9, 3.4, 7.55), (-0.1, 0.3, 7.25), 35),
    "wire_span_along": (POLE_ASM, (1.2, -1.6, 7.9), (0.0, 8.0, 7.0), 30),
    "wire_sag_midspan": (POLE_ASM, (3.2, 12.5, 6.3), (0.0, 12.5, 6.85), 35),
    "wire_drop_close": (POLE_ASM, (2.6, -0.4, 5.6), (3.6, 1.3, 5.2), 35),
    "junction_box": ("SM_DKP_Modern_JunctionBox", (0.8, -1.35, 0.72), (0.0, -0.08, 0.42), 45),
}


def mode_closeups():
    P = props()
    helper_mat = flat_mat("REV_Helper", "#8E8A83", 0.9)
    world((0.62, 0.62, 0.62), 0.55)
    add_light("Key", "AREA", (-4, -6, 6), (0, 0, 1), 1300, size=6)
    add_light("Fill", "AREA", (6, -4, 3), (0, 0, 1), 400, size=6)
    add_light("Rim", "AREA", (2, 6, 5), (0, 0, 1), 400, size=6)
    floor = mk_obj("REV_Floor", [(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [(0, 1, 2, 3)], helper_mat)
    roof = roof_slab("REV_Roof", -1.3, 1.3, -0.4, 2.0, helper_mat)
    wall = box_obj("REV_Wall", -1.2, 1.2, 0.0, 0.06, -0.6, 1.2, helper_mat)
    asm = assemble_pole(P, (0, 0, 0), 0.0, (8.0, 3.0, 3.2))
    lights = {n: bulb_lights([P[n]], energy=4.0) for n in P if "Lamp" in n}
    for key, (name, loc, tgt, lens) in CLOSEUPS.items():
        if ONLY and name not in ONLY and not (name == POLE_ASM and "SM_DKP_Modern_UtilityPole" in ONLY):
            continue
        for o in P.values():
            o.hide_render = o.name != name
        for o in asm:
            o.hide_render = name != POLE_ASM
        roof.hide_render = not name.endswith("ACUnit_Roof")
        wall.hide_render = name not in WALL_PROPS
        floor.hide_render = name in WALL_PROPS or name.endswith("ACUnit_Roof")
        for owner, lst in lights.items():
            for lo_ in lst:
                lo_.hide_render = owner != name
        setup_render(1200, 900, False)
        cam = camera("CamC", loc, tgt, lens=lens)
        render_to(OUT / f"closeup_{key}.png")
        bpy.data.objects.remove(cam)


# ------------------------------------------------------------------------------------------------ sunset line-up

def gravel_mat():
    m = bpy.data.materials.new("REV_Gravel")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.25, 0.25, 0.25)       # 4 m tile
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(sfx, nc):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(str(GROUND_TEX / f"T_DKG_Gravel_{sfx}.png"), check_existing=True)
        if nc:
            n.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    bc, orm = img("BC", False), img("ORM", True)
    nt.links.new(bc.outputs["Color"], b.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], b.inputs["Roughness"])
    return m


def mode_lineup():
    P = props()
    for o in P.values():
        o.hide_render = False
    plaster = flat_mat("REV_Plaster", "#CFC4B0", 0.9)
    tile = flat_mat("REV_RoofTile", "#55585C", 0.6)
    sil_mat = flat_mat("REV_Silhouette", "#7E7E7E", 0.9)
    mk_obj("REV_Ground", [(-40, -30, 0), (60, -30, 0), (60, 40, 0), (-40, 40, 0)], [(0, 1, 2, 3)], gravel_mat())
    place(P["SM_DKP_Modern_VendingMachine"], (-5.2, 0.0, 0.0), 0)
    roof_slab("REV_Roof", -3.75, -2.05, -0.3, 2.15, tile, z_at=lambda y: 0.35 + y * T25)
    place(P["SM_DKP_Modern_ACUnit_Roof"], (-2.9, 0.0, 0.35), 0)
    box_obj("REV_RoofBase", -3.75, -2.05, -0.3, 2.15, 0.0, 0.232, plaster)
    box_obj("REV_Wall", -1.3, 2.3, 1.0, 1.25, 0.0, 2.6, plaster)
    place(P["SM_DKP_Modern_ACUnit_Wall"], (-0.5, 1.0, 0.75), 0)
    place(P["SM_DKP_Modern_WallLamp"], (1.1, 1.0, 2.1), 0)
    place(P["SM_DKP_Modern_JunctionBox"], (1.75, 1.0, 0.25), 0)
    place(P["SM_DKP_Modern_StreetLamp_A"], (3.6, 0.2, 0.0), 180)
    place(P["SM_DKP_Modern_StreetLamp_B"], (5.3, 0.2, 0.0), 180)
    for n in ("SM_DKP_Modern_UtilityPole", "SM_DKP_Modern_PoleTransformer", "SM_DKP_Modern_PoleGuy",
              "SM_DKP_Modern_Wire_Span25", "SM_DKP_Modern_Wire_Drop12", "SM_DKP_Modern_Wire_Telecom25"):
        P[n].hide_render = True
    assemble_pole(P, (7.6, 2.2, 0.0), -90.0, (2.2, 1.0, 2.45))
    silhouette("REV_Sil", (2.85, -0.3, 0.0), sil_mat)
    bpy.context.view_layer.update()
    bulb_lights([P["SM_DKP_Modern_WallLamp"], P["SM_DKP_Modern_StreetLamp_A"], P["SM_DKP_Modern_StreetLamp_B"]],
                energy=8.0)
    world((0.16, 0.20, 0.42), 0.8, horizon=(1.0, 0.55, 0.30))
    sun_dir = Vector((0.85, 0.50, -0.13)).normalized()
    add_light("Sun", "SUN", (0, 0, 10), Vector((0, 0, 10)) + sun_dir, 5.0, size=0.8, color=(1.0, 0.52, 0.26))
    setup_render(1920, 1080, False)
    bpy.context.scene.cycles.samples = max(SAMPLES, 96)
    camera("CamLine", (1.6, -11.2, 2.0), (1.7, 1.0, 2.9), lens=24)
    render_to(OUT / "lineup_sunset.png")
    camera("CamLine2", (-2.9, -5.6, 1.8), (-2.5, 0.6, 1.1), lens=28)
    render_to(OUT / "lineup_sunset_left.png")
    camera("CamLine3", (3.2, -6.4, 2.6), (6.2, 1.5, 3.6), lens=26)
    render_to(OUT / "lineup_sunset_right.png")


def main():
    assert_owner("DojoModernProps", "claude")
    for o in bpy.data.objects:
        if o.name.startswith("UCX_") or o.name.startswith("SOCKET_"):
            o.hide_render = True
    {"views": mode_views, "closeups": mode_closeups, "lineup": mode_lineup}[MODE]()


main()
