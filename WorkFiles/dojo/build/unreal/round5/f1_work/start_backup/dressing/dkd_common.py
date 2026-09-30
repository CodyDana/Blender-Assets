"""ROUND 5 (2026-09-29): shared helpers for the EMBLEM + WEATHERING track (Scripts/dojo/dressing/, SM_DKD_* / T_DKD_*).

Owned by the dressing track (lock DojoDressing, Assets/Dojo/DojoDressing.blend). Uses, read-only:
  - Assets/Dojo/DojoShowcase.blend + WorkFiles/dojo/build/showcase/layout_showcase.json: the composed compound (context
    for the plaque fits, the decal placements, the traversal checks and the review renders)
  - every kit's own source blend: its TEXTURED meshes for the review renders (matched by piece name AND bounds, as
    Scripts/dojo/shed/render_sp.py does)
  - Exports/ArmoryKit/Textures/T_AK_Emblem*.png: the user's own emblem (copied byte for byte as T_DKD_Emblem_*)

Blender side only (bpy). The texture generator (make_decal_textures.py) is numpy only.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
DW = WORK / "dressing"
RENDERS = DW / "renders"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Dressing"
TEX_DIR = EXPORT_DIR / "Textures"
BLEND = ROOT / "Assets" / "Dojo" / "DojoDressing.blend"
SHOWCASE_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
SHOWCASE_LAYOUT = WORK / "showcase" / "layout_showcase.json"
ARMORY_TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
REFS = ROOT / "References" / "Dojo"
LOCK = "DojoDressing"
UE_DIR = "/Game/DojoKit/Dressing"

# each kit's own source blend (textured meshes for the renders); the prefix picks the file, the bounds confirm it
SOURCES = [("SM_DKH_", "DojoHall.blend"), ("SM_DKO_", "DojoOutbuildings.blend"), ("SM_DKC_", "DojoCorridors.blend"),
           ("SM_DKS_", "DojoShed.blend"), ("SM_DKV_", "DojoPavilion.blend"), ("SM_DKG_", "DojoGround.blend"),
           ("SM_DKP_Stone_", "CourtyardStone.blend"), ("SM_DKP_Train_", "TrainingProps.blend"),
           ("SM_DKP_Modern_", "ModernProps.blend"), ("SM_DKP_Taiko_", "Taiko.blend"),
           ("SM_DKP_Yard_", "DojoYardPosts.blend"), ("SM_DK_", "DojoKit1.blend"), ("SM_DGB_", "DojoGreybox.blend")]


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    a = args()
    return a[a.index(name) + 1] if name in a else default


def piece_of(o):
    return o.name.split("__")[0]


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]


def assembly():
    c = bpy.data.collections.get("Assembly")
    return list(c.objects) if c else []


def instances_of(piece):
    return [o for o in assembly() if piece_of(o) == piece]


# ------------------------------------------------------------------------------------------------ context
def load_showcase(kit, asm):
    """Append the showcase compound (read-only source): its Kit pieces + UCX into `kit`, its Assembly instances into
    `asm`. Returns the number of instances."""
    with bpy.data.libraries.load(str(SHOWCASE_BLEND), link=False) as (src, dst):
        dst.objects = list(src.objects)
    n = 0
    for o in dst.objects:
        if o is None:
            continue
        if "__" in o.name:
            asm.objects.link(o)
            n += 1
        elif o.type in ("MESH", "EMPTY"):
            kit.objects.link(o)
    return n


def textured_context():
    """Swap each Assembly instance's mesh for its kit's own textured mesh (same name, bounds within 1 cm)."""
    kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
    need = {piece_of(o) for o in assembly()}
    got = {}
    for prefix, fn in SOURCES:
        path = ROOT / "Assets" / "Dojo" / fn
        want = sorted(n for n in need - set(got) if n.startswith(prefix))
        if not want or not path.exists():
            continue
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            names = set(src.objects)
            dst.objects = [n for n in want if n in names]
        for o in dst.objects:
            if o is None or o.type != "MESH":
                continue
            ref = kit.get(o.name.split(".")[0])
            if ref is None:
                continue
            bs = [min(Vector(c)[i] for c in o.bound_box) for i in range(3)] + \
                 [max(Vector(c)[i] for c in o.bound_box) for i in range(3)]
            br = [min(Vector(c)[i] for c in ref.bound_box) for i in range(3)] + \
                 [max(Vector(c)[i] for c in ref.bound_box) for i in range(3)]
            if max(abs(u - v) for u, v in zip(bs, br)) < 0.01:
                got[ref.name] = o.data
    n = 0
    for o in assembly():
        p = piece_of(o)
        if p in got:
            o.data = got[p]
            n += 1
    for o in assembly():            # the 1v1 boundary (red, a ceiling at +20) never renders
        if piece_of(o).startswith("SM_DGB_Boundary"):
            o.hide_render = True
    print("TEXTURED CONTEXT", len(got), "of", len(need), "pieces;", n, "instances", flush=True)
    return got


# ------------------------------------------------------------------------------------------------ render rig
def setup_cycles(samples=96):
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


def sunset_rig(exposure=0.6, elev=13.0, az_from_x=160.0, sun=4.2):
    """The round-4 review renders' sunset (render_sp.py): a warm low sun from the west-north-west (the showcase
    layout's sun azimuth) and an orange-to-violet gradient sky, AgX medium-high contrast."""
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
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = exposure
    return so


def studio_rig(exposure=0.35):
    """render_sp.py's neutral grey studio (key + fill suns, grey world): for reading the dressing's own colours."""
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
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = exposure


def set_light(name, direction, energy=None):
    o = bpy.data.objects[name]
    o.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()
    if energy is not None:
        o.data.energy = energy


def persp_cam(name, loc, look, lens=50.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.05
    cam.clip_end = 900.0
    o = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x = int(w)
    sc.render.resolution_y = int(h)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path, flush=True)


def ground_plane(z=-0.03, size=400.0, colour=(0.20, 0.18, 0.16)):
    """A plain dark ground far outside the compound (the grey-box outside ground ends at +-15 m)."""
    me = bpy.data.meshes.new("FarGround")
    h = size / 2
    me.from_pydata([(22 - h, 18 - h, z), (22 + h, 18 - h, z), (22 + h, 18 + h, z), (22 - h, 18 + h, z)], [],
                   [(0, 1, 2, 3)])
    o = bpy.data.objects.new("FarGround", me)
    bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new("FarGround")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = 0.95
    me.materials.append(m)
    return o


# ------------------------------------------------------------------------------------------------ frames / Unreal
def ue_loc_cm(p):
    return [round(p[0] * 100.0, 2), round(-p[1] * 100.0, 2), round(p[2] * 100.0, 2)]


def ue_dir(d):
    return Vector((d[0], -d[1], d[2]))


def ue_rotator_from_axes(x_ue, z_ue):
    """Rotator (roll, pitch, yaw) of a UE frame whose local X is x_ue and local Z is z_ue (both in Unreal space).
    UE is left-handed with Y = Z x X (the plain cross product formula): identity axes give Y = (0, 1, 0)."""
    X = Vector(x_ue).normalized()
    Z = (Vector(z_ue) - X * Vector(z_ue).dot(X)).normalized()
    Y = Z.cross(X)
    M = Matrix((X, Y, Z)).transposed()                 # columns = axes
    yaw = math.degrees(math.atan2(X.y, X.x))
    pitch = math.degrees(math.atan2(X.z, math.hypot(X.x, X.y)))
    R0 = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(-pitch), 3, "Y")
    rem = R0.transposed() @ M
    roll = math.degrees(math.atan2(rem[2][1], rem[1][1]))
    # self-check: rebuild Rz(yaw) Ry(-pitch) Rx(roll) and compare the columns
    Rb = R0 @ Matrix.Rotation(math.radians(roll), 3, "X")
    err = max(abs(Rb[i][j] - M[i][j]) for i in range(3) for j in range(3))
    if err > 1e-4:
        raise ValueError(f"rotator rebuild error {err}")
    return round(roll, 3) + 0.0, round(pitch, 3) + 0.0, round(yaw, 3) + 0.0


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")
