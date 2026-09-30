"""Cycles review renders of the taiko set (Assets/Dojo/Taiko.blend, never saved here).

  sheets   : a model sheet per prop (Drum, Stand, Stick) and for the assembled Set, laid out like the reference:
             front | side over top | 3/4 perspective; plain light-grey background (the sheet's 186,185,187), even soft
             light, a plain grey 1.8 m silhouette beside the front and side views (orthographic, same scale)
  closeups : the reference's close-up panels: hide + tacks + ring handle, stand joint, the two sticks
  lineup   : the group line-up at sunset (warm low sun) on pale gravel (kit 2's T_DKG_Gravel, read-only)

Run: blender -b --factory-startup Assets/Dojo/Taiko.blend --python Scripts/dojo/props/taiko/render_taiko.py --
     [--only sheets,closeups,lineup] [--samples 64] [--out DIR] [--props Drum,Stand,Stick,Set] [--exposure EV]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko"
GRAVEL = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = Path(arg("--out", str(WORK / "renders" / "r2")))
SAMPLES = int(arg("--samples", "96"))
ONLY = arg("--only", "sheets,closeups,lineup").split(",")
CLOSEUPS = arg("--closeups", "hide,joint,sticks,lean").split(",")
PROPS = arg("--props", "Drum,Stand,Stick,Set").split(",")
EXPOSURE = float(arg("--exposure", "0.3"))   # r2: hide face rendered 180 vs the sheet 200 at 0.0
BG = np.array([186, 185, 187]) / 255.0       # the reference sheet's background, display space
VIEW_W, VIEW_H = 900, 720
GAP = 10
LAYOUT = json.loads((WORK / "layout_taiko.json").read_text(encoding="utf-8"))
NAMES = {"Drum": "SM_DKP_Taiko_Drum", "Stand": "SM_DKP_Taiko_Stand", "Stick": "SM_DKP_Taiko_Stick"}


def kelvin_rgb(k):
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def setup_cycles(sc, samples):
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        print("GPU setup failed, CPU render:", exc)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        sc.cycles.denoising_prefilter = "ACCURATE"
    except (AttributeError, TypeError) as exc:
        print("denoiser settings:", exc)
    sc.cycles.sample_clamp_indirect = 5.0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = EXPOSURE
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"


def flat_mat(name, rgb, rough=0.8, emit=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit is not None:
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 1.0
    return m


# --------------------------------------------------------------------------- scene helpers

def link_new(coll, name, mesh, M=Matrix.Identity(4)):
    o = bpy.data.objects.new(name, mesh)
    o.matrix_world = M
    coll.objects.link(o)
    return o


def silhouette(coll):
    """A plain grey 1.8 m figure (head top at 1.800), built from primitives, facing -Y."""
    bm = bmesh.new()

    def cyl(x, y, z0, z1, r0, r1, seg=16):
        m = Matrix.Translation((x, y, (z0 + z1) / 2))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0, matrix=m)

    def sph(x, y, z, r, sx=1.0, sy=1.0, sz=1.0):
        m = Matrix.Translation((x, y, z)) @ Matrix.Diagonal((sx * r, sy * r, sz * r, 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0, matrix=m)
    for s in (-1, 1):
        cyl(s * 0.095, 0.0, 0.06, 0.50, 0.050, 0.068)           # shin
        cyl(s * 0.100, 0.0, 0.48, 0.92, 0.068, 0.085)           # thigh
        sph(s * 0.095, -0.04, 0.035, 0.05, 1.0, 2.2, 0.7)        # foot
        cyl(s * 0.225, 0.0, 1.10, 1.42, 0.042, 0.052)           # upper arm
        cyl(s * 0.245, 0.0, 0.80, 1.12, 0.033, 0.042)           # forearm
        sph(s * 0.248, 0.0, 0.76, 0.045, 0.8, 0.8, 1.3)          # hand
    cyl(0.0, 0.0, 0.88, 1.10, 0.15, 0.15, 20)                   # hips/waist
    sph(0.0, 0.0, 0.96, 0.17, 1.0, 0.62, 0.55)
    cyl(0.0, 0.0, 1.08, 1.44, 0.15, 0.20, 20)                   # chest
    sph(0.0, 0.0, 1.40, 0.21, 1.05, 0.60, 0.42)                  # shoulders
    cyl(0.0, 0.0, 1.46, 1.60, 0.052, 0.050)                     # neck
    sph(0.0, 0.0, 1.692, 0.108)                                  # head: top at 1.800
    me = bpy.data.meshes.new("Silhouette_1p8m")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat_mat("MAT_Silhouette", (0, 0, 0), emit=(0.105, 0.105, 0.108)))
    return link_new(coll, "Silhouette", me)


def bbox_world(objs):
    pts = []
    for o in objs:
        pts += [o.matrix_world @ v.co for v in o.data.vertices]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def studio(sc, floor_z):
    """Even soft studio light: uniform grey world plus a large soft key and fill; a shadow-catcher floor."""
    w = bpy.data.worlds.new("Studio")
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (0.62, 0.62, 0.64, 1)
    bgn.inputs["Strength"].default_value = 0.6   # r1: 0.9 (hide face rendered 235 vs the sheet 201)
    sc.world = w
    sc.render.film_transparent = True
    coll = bpy.data.collections.new("Studio")
    sc.collection.children.link(coll)
    me = bpy.data.meshes.new("Floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat_mat("MAT_Floor", (0.5, 0.5, 0.5)))
    fl = link_new(coll, "Floor", me, Matrix.Translation((0, 0, floor_z)))
    fl.is_shadow_catcher = True
    for name, loc, power, size in (("Key", (-4.0, -5.0, 6.0), 600.0, 5.0), ("Fill", (5.0, -3.0, 3.0), 200.0, 5.0),
                                   ("Top", (0.5, 2.0, 7.0), 200.0, 6.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power
        ld.size = size
        ld.color = (1.0, 0.98, 0.95)
        o = bpy.data.objects.new(name, ld)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(o)
    return coll, fl


def camera(sc, name, loc, target, ortho=None, lens=50.0, up_y=False):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.sensor_width = 36.0
    cd.clip_start = 0.01
    cd.clip_end = 200
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y" if not up_y else "Y").to_euler()
    if up_y:   # top view: screen up = +Y
        o.rotation_euler = (0.0, 0.0, 0.0)
    sc.collection.objects.link(o)
    return o


def render(sc, cam, path, res=(VIEW_W, VIEW_H)):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered", path)
    return path


def load_rgba(path):
    im = bpy.data.images.load(str(path))
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return px


def on_bg(px):
    a = px[..., 3:4]
    rgb = px[..., :3] * a + BG[None, None, :] * (1 - a)
    return np.concatenate([rgb, np.ones_like(a)], axis=2)


def save_px(px, path):
    h, w = px.shape[:2]
    img = bpy.data.images.new(Path(path).stem, w, h, alpha=False)
    img.pixels[:] = px.ravel()
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# --------------------------------------------------------------------------- scenes

def prop_objects(sc, which, coll):
    """Fresh instances (linked mesh data) of one prop, or the assembled set in stand-local coordinates."""
    objs = []
    if which == "Set":
        for inst in LAYOUT["instances"]:
            M = Matrix([row for row in inst["stand_local_matrix"]])
            objs.append(link_new(coll, inst["name"] + "_view", bpy.data.objects[inst["piece"]].data, M))
    else:
        src = bpy.data.objects[NAMES[which]]
        objs.append(link_new(coll, which + "_view", src.data))
    return objs


def hide_sources():
    for c in ("Taiko_Drum", "Taiko_Stand", "Taiko_Stick", "Taiko_Layout"):
        if c in bpy.data.collections:
            bpy.data.collections[c].hide_render = True


def model_sheet(which):
    sc = bpy.context.scene
    coll = bpy.data.collections.new("View_" + which)
    sc.collection.children.link(coll)
    objs = prop_objects(sc, which, coll)
    lo, hi = bbox_world(objs)
    st, floor = studio(sc, lo.z)
    sil = silhouette(coll)
    sil_h = 1.80
    size = hi - lo
    c = (lo + hi) / 2
    # ortho scale shared by front and side: prop + gap + figure, and the taller of the prop and the figure
    wide = max(size.x, size.y) + 0.45 + 0.50
    tall = max(size.z, sil_h)
    ortho = max(wide * 1.12, tall * 1.10 * VIEW_W / VIEW_H)
    views = {}
    # front: camera at -Y looking +Y; figure at the left (-X), feet on the floor
    sil.matrix_world = Matrix.Translation((lo.x - 0.45 - 0.25, c.y, lo.z))
    cx = (lo.x - 0.95 + hi.x) / 2
    cz = lo.z + tall / 2
    cam = camera(sc, "CamFront", (cx, lo.y - 20, cz), (cx, 0, cz), ortho=ortho)
    views["front"] = render(sc, cam, OUT / f"_{which}_front.png")
    # side: camera at +X looking -X (screen right = +Y); figure at the left (-Y), facing the camera
    sil.matrix_world = Matrix.Translation((c.x, lo.y - 0.45 - 0.25, lo.z)) @ Matrix.Rotation(math.radians(90), 4, "Z")
    cy = (lo.y - 0.95 + hi.y) / 2
    cam = camera(sc, "CamSide", (hi.x + 20, cy, cz), (0, cy, cz), ortho=ortho)
    views["side"] = render(sc, cam, OUT / f"_{which}_side.png")
    sil.hide_render = True
    # top: straight down, screen up = +Y; fitted to the prop alone
    ortho_top = max(size.x * 1.25, size.y * 1.25 * VIEW_W / VIEW_H, 0.3)
    cam = camera(sc, "CamTop", (c.x, c.y, hi.z + 20), (c.x, c.y, 0), ortho=ortho_top, up_y=True)
    floor.hide_render = True   # r0: the soft shadows spread over the whole top tile and greyed it
    views["top"] = render(sc, cam, OUT / f"_{which}_top.png")
    floor.hide_render = False
    # 3/4 perspective from the front-left, above (the reference close-up's angle: the -X head faces front-left)
    d = Vector((-0.60, -0.74, 0.40)).normalized()
    rad = (size.length / 2)
    dist = rad / math.tan(math.radians(15.5)) * 1.05
    cam = camera(sc, "Cam34", c + d * dist, c, lens=50.0)
    views["34"] = render(sc, cam, OUT / f"_{which}_34.png")
    # compose: front | side over top | 3/4
    tiles = {k: on_bg(load_rgba(p)) for k, p in views.items()}
    H = 2 * VIEW_H + 3 * GAP
    W = 2 * VIEW_W + 3 * GAP
    sheet = np.ones((H, W, 4), dtype=np.float32)
    sheet[..., :3] = BG * 0.93
    # image rows are bottom-up in Blender pixel buffers: the top row of the sheet is the highest index
    place = {"front": (GAP, VIEW_H + 2 * GAP), "side": (VIEW_W + 2 * GAP, VIEW_H + 2 * GAP),
             "top": (GAP, GAP), "34": (VIEW_W + 2 * GAP, GAP)}
    for k, (x0, y0) in place.items():
        sheet[y0:y0 + VIEW_H, x0:x0 + VIEW_W] = tiles[k]
    out = OUT / f"sheet_{which}.png"
    save_px(sheet, out)
    print("sheet", out, {"ortho_front_side_m": round(ortho, 4), "px_per_m": round(VIEW_W / ortho, 2),
                         "ortho_top_m": round(ortho_top, 4)})
    # clean the scene for the next sheet
    for o in list(coll.objects) + list(st.objects):
        bpy.data.objects.remove(o)
    for cn in ("CamFront", "CamSide", "CamTop", "Cam34"):
        o = bpy.data.objects.get(cn)
        if o:
            bpy.data.objects.remove(o)
    bpy.data.collections.remove(coll)
    bpy.data.collections.remove(st)
    return {"ortho_front_side_m": ortho, "px_per_m_front_side": VIEW_W / ortho, "sheet": str(out)}


def lying(M_place, stick_data):
    """A stick lying on the floor: the taper is levelled so the stick rests along its length, then lifted to z = 0."""
    L = max(v.co.x for v in stick_data.vertices)
    r0 = max(math.hypot(v.co.y, v.co.z) for v in stick_data.vertices if v.co.x < 0.05)
    r1 = max(math.hypot(v.co.y, v.co.z) for v in stick_data.vertices if v.co.x > L - 0.05)
    R = M_place @ Matrix.Rotation(-math.atan2(r1 - r0, L), 4, "Y")
    zmin = min((R @ v.co).z for v in stick_data.vertices)
    return Matrix.Translation((0, 0, -zmin)) @ R


def closeups():
    sc = bpy.context.scene
    coll = bpy.data.collections.new("View_Closeups")
    sc.collection.children.link(coll)
    objs = prop_objects(sc, "Set", coll)
    st, floor = studio(sc, 0.0)
    out = {}
    if "hide" in CLOSEUPS:   # hide + torn collar + tacks + ring handle (the -X head, the -Y handle)
        cam = camera(sc, "CU_Hide", (-1.20, -1.60, 1.62), (-0.38, -0.50, 1.33), lens=50.0)
        out["closeup_hide_tacks_ring"] = render(sc, cam, OUT / "_cu_hide.png", (900, 600))
    if "joint" in CLOSEUPS:  # r2: stand joint at the -X/-Y post: the iron wrap round the rail end, rivets, kusabi block
        cam = camera(sc, "CU_Joint", (-1.22, -1.30, 0.92), (-0.66, -0.50, 0.50), lens=55.0)
        out["closeup_stand_joint"] = render(sc, cam, OUT / "_cu_joint.png", (900, 600))
    if "lean" in CLOSEUPS:   # r2: the sticks leaning at the far (+X/-Y) post, on the rail end's iron wrap
        cam = camera(sc, "CU_Lean", (-0.35, -2.55, 1.20), (0.75, -0.55, 0.45), lens=45.0)
        out["closeup_sticks_leaning"] = render(sc, cam, OUT / "_cu_lean.png", (900, 600))
    for o in objs:
        o.hide_render = True
    if "sticks" in CLOSEUPS:  # the two sticks lying side by side (as the reference's bottom panel)
        s = bpy.data.objects[NAMES["Stick"]].data
        link_new(coll, "StickA", s, lying(Matrix.Translation((0.0, 0.0, 0.0)) @ Matrix.Rotation(math.radians(-8), 4, "Z")
                                          @ Matrix.Rotation(0.4, 4, "X"), s))
        link_new(coll, "StickB", s, lying(Matrix.Translation((0.07, -0.14, 0.0)) @ Matrix.Rotation(math.radians(-8), 4, "Z")
                                          @ Matrix.Rotation(1.9, 4, "X"), s))
        cam = camera(sc, "CU_Sticks", (0.44, -1.60, 0.72), (0.44, -0.08, 0.02), lens=50.0)
        out["closeup_sticks"] = render(sc, cam, OUT / "_cu_sticks.png", (900, 600))
    for k, p in list(out.items()):
        px = on_bg(load_rgba(p))
        dst = OUT / f"{k}.png"
        save_px(px, dst)
        out[k] = str(dst)
    for o in list(coll.objects) + list(st.objects):
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(coll)
    bpy.data.collections.remove(st)
    return out


def lineup():
    """The set at sunset: warm low sun, gradient sunset sky, pale gravel ground."""
    sc = bpy.context.scene
    sc.render.film_transparent = False
    coll = bpy.data.collections.new("View_Lineup")
    sc.collection.children.link(coll)
    D = bpy.data.objects
    # left to right: stand, drum (resting on the ground), two sticks lying, the assembled set
    link_new(coll, "L_Stand", D[NAMES["Stand"]].data, Matrix.Translation((0.0, 0.0, 0.0)))
    link_new(coll, "L_Drum", D[NAMES["Drum"]].data, Matrix.Translation((1.95, 0.25, 0.600)) @
             Matrix.Rotation(math.radians(-25), 4, "Z"))
    for k, (x, y, yaw, roll) in enumerate(((3.05, -0.35, 70.0, 0.4), (3.25, -0.30, 78.0, 2.1))):
        sd = D[NAMES["Stick"]].data
        link_new(coll, f"L_Stick{k}", sd, lying(Matrix.Translation((x, y, 0.0)) @
                                               Matrix.Rotation(math.radians(yaw), 4, "Z") @
                                               Matrix.Rotation(roll, 4, "X"), sd))
    base = Matrix.Translation((5.0, 0.6, 0.0))
    for inst in LAYOUT["instances"]:
        M = Matrix([row for row in inst["stand_local_matrix"]])
        link_new(coll, "L_Set_" + inst["name"], D[inst["piece"]].data, base @ M)
    # gravel ground (kit 2's graded CC0 gravel, read-only; tile 4 m)
    gm = bpy.data.materials.new("MAT_Gravel")
    gm.use_nodes = True
    nt = gm.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    have = (GRAVEL / "T_DKG_Gravel_BC.png").exists()
    if have:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.25, 0.25, 0.25)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

        def img(sfx, data):
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = bpy.data.images.load(str(GRAVEL / f"T_DKG_Gravel_{sfx}.png"), check_existing=True)
            if data:
                n.image.colorspace_settings.name = "Non-Color"
            nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
            return n
        bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        sn = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(nrm.outputs["Color"], sn.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sn.outputs[1], inv.inputs[1])
        cb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sn.outputs[0], cb.inputs[0])
        nt.links.new(inv.outputs[0], cb.inputs[1])
        nt.links.new(sn.outputs[2], cb.inputs[2])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.42, 0.40, 0.38, 1)
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(gm)
    link_new(coll, "Ground", me)
    # sunset sky + low warm sun from the front-left (dojo1_reference2: sunset, warm raking light)
    travel = Vector((0.78, 0.52, -0.16)).normalized()
    w = bpy.data.worlds.new("SunsetSky")
    w.use_nodes = True
    wt = w.node_tree
    for n in list(wt.nodes):
        if n.type != "OUTPUT_WORLD":
            wt.nodes.remove(n)
    wo = next(n for n in wt.nodes if n.type == "OUTPUT_WORLD")
    tc = wt.nodes.new("ShaderNodeTexCoord")
    nrm = wt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    wt.links.new(tc.outputs["Generated"], nrm.inputs[0])
    sep = wt.nodes.new("ShaderNodeSeparateXYZ")
    wt.links.new(nrm.outputs[0], sep.inputs[0])
    mr = wt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.05
    mr.inputs["From Max"].default_value = 0.45
    wt.links.new(sep.outputs[2], mr.inputs["Value"])
    ramp = wt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1.00, 0.56, 0.34, 1)
    ramp.color_ramp.elements[1].color = (0.26, 0.30, 0.52, 1)
    ramp.color_ramp.interpolation = "EASE"
    wt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    dot = wt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    wt.links.new(nrm.outputs[0], dot.inputs[0])
    dot.inputs[1].default_value = tuple(-travel)
    mx = wt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    wt.links.new(dot.outputs["Value"], mx.inputs[0])
    pw = wt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 6.0
    wt.links.new(mx.outputs[0], pw.inputs[0])
    mix = wt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    wt.links.new(pw.outputs[0], mix.inputs["Factor"])
    wt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = (1.0, 0.62, 0.30, 1)
    bgn = wt.nodes.new("ShaderNodeBackground")
    bgn.inputs["Strength"].default_value = 0.8
    wt.links.new(mix.outputs["Result"], bgn.inputs["Color"])
    wt.links.new(bgn.outputs[0], wo.inputs["Surface"])
    sc.world = w
    ld = bpy.data.lights.new("Sun_Sunset", "SUN")
    ld.energy = 5.5
    ld.color = kelvin_rgb(2500)
    ld.angle = math.radians(0.6)
    so = bpy.data.objects.new("Sun_Sunset", ld)
    so.rotation_euler = travel.to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(so)
    cam = camera(sc, "CamLineup", (2.45, -8.6, 1.75), (2.45, 0.2, 0.55), lens=38.0)   # r0: the stand was cut off
    p = render(sc, cam, OUT / "lineup_sunset.png", (1800, 900))
    # r2 context shot: the assembled set on a 1.0 m granite plinth stand-in (the pavilion's plinth height, library
    # M_DJ_Granite, box UVs) seen from the courtyard at eye height, in the same sunset
    sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
    import dojo_materials as djm
    ctx = Matrix.Translation((14.0, 2.0, 1.0)) @ Matrix.Rotation(math.radians(-35), 4, "Z")
    pm = bpy.data.meshes.new("CtxPlinth")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 4.0, v.co.y * 4.0, v.co.z * 1.0 - 0.5))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.02, segments=2, affect="EDGES")
    bm.to_mesh(pm)
    bm.free()
    pm.materials.append(djm.make_material("M_DJ_Granite"))
    po = link_new(coll, "CtxPlinth", pm, ctx)
    djm.box_uv(po, "Granite")
    djm.bake_wear(po, ground_z=0.0)
    for inst in LAYOUT["instances"]:
        M = Matrix([row for row in inst["stand_local_matrix"]])
        link_new(coll, "C_Set_" + inst["name"], D[inst["piece"]].data, ctx @ M)
    cam = camera(sc, "CamContext", (14.0 - 6.6, 2.0 - 5.6, 2.35), (14.0, 2.0, 1.45), lens=45.0)
    pc = render(sc, cam, OUT / "context_sunset.png", (1600, 1000))
    return {"lineup_sunset": str(p), "context_sunset": str(pc),
            "gravel_texture": "kit 2 T_DKG_Gravel (read-only)" if have else "flat stand-in",
            "sun_elevation_deg": round(math.degrees(math.asin(-travel.z)), 1), "sun_kelvin": 2500}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    setup_cycles(sc, SAMPLES)
    hide_sources()
    rep = {}
    if "sheets" in ONLY:
        for w in PROPS:
            rep["sheet_" + w] = model_sheet(w)
    if "closeups" in ONLY:
        rep.update(closeups())
    rp = OUT / "render_report.json"
    if rp.exists():   # r0 lesson: a partial re-render must not wipe the earlier entries
        old = json.loads(rp.read_text(encoding="utf-8"))
        old.update(rep)
        rep = old
    if "lineup" in ONLY:
        rep.update(lineup())
    (OUT / "render_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print("REPORT", json.dumps(rep, default=str))


main()
