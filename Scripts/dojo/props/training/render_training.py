"""Cycles review renders of the kit 9 training props (Assets/Dojo/TrainingProps.blend), headless, denoised.

Writes raw views to <out>/raw/ (make_training_sheets.py lays them out):
  <prop>_front / _side / _top   orthographic at PPM px/m, transparent film + shadow catcher (the sheet background
                                is composited later), even soft studio light
  <prop>_34                     3/4 perspective, same light
  <prop>_collision              (f1) the same 3/4 view with the UCX hulls drawn as translucent orange shells with
                                wire edges over the mesh (the collision classes are in layout_training.json)
  silhouette_front              a plain 1.80 m human figure, front ortho at the same PPM (mask only)
  close_<prop>_<detail>         perspective close-ups of the details the reference sheet shows
  lineup_sunset                 all seven props in a row on pale gravel under a warm low sun (the look target is
                                dojo1_reference2's sunset)

Run: blender -b --factory-startup Assets/Dojo/TrainingProps.blend --python Scripts/dojo/props/training/render_training.py --
     --out <dir> [--what sheets,closeups,lineup] [--props SM_...,...] [--samples 48]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline import lock  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = Path(arg("--out", str(ROOT / "WorkFiles/dojo/build/props/training/renders/r2"))).resolve()
RAW = OUT / "raw"
WHAT = set(arg("--what", "sheets,closeups,lineup,context").split(","))
SAMPLES = int(arg("--samples", "48"))
PPM = 400                      # px per metre on every orthographic view (same on every sheet)
EXPOSURE = float(arg("--exposure", "-0.8"))
LOOK = arg("--look", "AgX - Medium High Contrast")

PROPS = ["SM_DKP_Train_Makiwara", "SM_DKP_Train_StrikingPost", "SM_DKP_Train_WoodenDummy",
         "SM_DKP_Train_LongArmDummy", "SM_DKP_Train_WeaponRack", "SM_DKP_Train_Bench", "SM_DKP_Train_Stool"]
ONLY = arg("--props", None)
if ONLY:
    PROPS = [p for p in PROPS if p in ONLY.split(",")]
# side view direction that matches the reference sheet (the rack's cradles face right in the sheet's side view)
SIDE_FROM = {"SM_DKP_Train_WeaponRack": -1}

# close-ups: prop, name, look-at (prop local), camera offset from the look-at, lens mm
CLOSEUPS = [
    ("SM_DKP_Train_Makiwara", "rope_pad", (0, 0, 1.07), (-0.70, -1.30, 0.20), 50),
    ("SM_DKP_Train_Makiwara", "top_collar", (0, 0, 1.33), (-0.40, -0.75, 0.25), 50),
    ("SM_DKP_Train_Makiwara", "sleeve_base", (0.0, 0.0, 0.24), (-0.75, -1.00, 0.45), 45),
    ("SM_DKP_Train_Makiwara", "base_front", (0.0, 0.0, 0.25), (0.0, -1.45, 0.20), 45),
    ("SM_DKP_Train_StrikingPost", "sleeve_iron", (0.10, -0.10, 0.30), (-0.35, -0.80, 0.25), 50),
    ("SM_DKP_Train_StrikingPost", "sill_blocks", (0.20, 0.0, 0.10), (-0.20, -0.90, 0.35), 50),
    ("SM_DKP_Train_WoodenDummy", "arms", (0, -0.30, 1.33), (-0.85, -1.30, 0.20), 45),
    ("SM_DKP_Train_WoodenDummy", "leg_knee", (-0.25, -0.35, 0.45), (-1.35, -0.75, 0.25), 40),
    ("SM_DKP_Train_WoodenDummy", "leg_mortise", (-0.12, -0.13, 0.58), (-0.55, -0.95, 0.20), 50),
    ("SM_DKP_Train_WoodenDummy", "corner_block", (0.37, -0.37, 0.14), (0.45, -0.75, 0.35), 50),
    ("SM_DKP_Train_WoodenDummy", "base_braces", (0.10, -0.10, 0.18), (0.55, -1.05, 0.45), 40),
    ("SM_DKP_Train_LongArmDummy", "arm_tip", (0.85, -0.05, 1.40), (0.10, -0.80, 0.20), 50),
    ("SM_DKP_Train_LongArmDummy", "arm_root", (0.20, -0.05, 1.40), (0.60, -0.95, 0.25), 45),
    ("SM_DKP_Train_LongArmDummy", "base_corner", (0.45, 0.0, 0.14), (0.40, -0.90, 0.40), 45),
    ("SM_DKP_Train_WeaponRack", "tenon_wedge", (-0.95, -0.12, 0.86), (-0.55, -0.85, 0.25), 45),
    ("SM_DKP_Train_WeaponRack", "cradles", (-0.30, -0.12, 0.50), (-0.45, -1.50, 0.40), 40),
    ("SM_DKP_Train_WeaponRack", "foot_knee_brace", (-0.72, -0.05, 0.20), (0.05, -0.95, 0.25), 45),
    ("SM_DKP_Train_Bench", "end_joint", (-0.70, -0.18, 0.30), (-0.55, -0.85, 0.25), 45),
    ("SM_DKP_Train_Bench", "top_planks", (0.30, 0.0, 0.45), (-0.45, -0.90, 0.55), 45),
    ("SM_DKP_Train_Stool", "detail", (0, 0, 0.26), (-0.85, -1.15, 0.45), 50),
]


# --------------------------------------------------------------------------- scene helpers

def setup_render(samples, transparent):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == dev_type
                sc.cycles.device = "GPU"
                break
        except TypeError:
            continue
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 6
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = LOOK
    except TypeError:
        pass
    sc.view_settings.exposure = EXPOSURE
    sc.render.resolution_percentage = 100


def new_obj(name, data, coll=None):
    o = bpy.data.objects.new(name, data)
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area_light(name, loc, target, size, power, color=(1, 1, 1)):
    L = bpy.data.lights.new(name, "AREA")
    L.shape = "DISK"
    L.size = size
    L.energy = power
    L.color = color
    o = new_obj(name, L)
    o.location = loc
    look_at(o, target)
    return o


def studio(coll):
    """Even soft studio light (the sheet's look): a grey world, a big soft key from the front-left above, a fill from
    the right and a soft top light. A shadow catcher floor gives the contact shadows."""
    w = bpy.data.worlds.new("W_Studio")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.78, 0.78, 0.78, 1)
    bg.inputs["Strength"].default_value = 0.55
    bpy.context.scene.world = w
    lights = [area_light("L_Key", (-3.5, -5.0, 4.5), (0, 0, 0.9), 5.0, 750.0),
              area_light("L_Fill", (4.5, -3.5, 2.5), (0, 0, 0.8), 5.0, 300.0),
              area_light("L_Top", (0.5, 1.5, 6.0), (0, 0, 0.5), 6.0, 380.0)]
    me = bpy.data.meshes.new("CatcherPlane")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=15.0)
    bm.to_mesh(me)
    bm.free()
    floor = new_obj("ShadowCatcher", me)
    floor.is_shadow_catcher = True
    return lights + [floor]


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def prop_obj(name):
    return bpy.data.objects[name]


def show_only(names):
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("SM_DKP_Train_"):
            o.hide_render = o.name not in names
        if o.name.startswith("UCX_"):
            o.hide_render = True


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def ortho_render(o, view, path, margin=0.12):
    """Front (along +Y), side (+X -> -X or -X -> +X) or top (down -Z, front at the bottom) at PPM px/m."""
    lo, hi = world_bbox(o)
    lo = lo - Vector((margin, margin, 0.0))
    hi = hi + Vector((margin, margin, margin))
    c = (lo + hi) / 2
    cam = bpy.data.cameras.new("OrthoCam")
    cam.type = "ORTHO"
    cam.clip_start = 0.01
    cam.clip_end = 100
    co = new_obj("OrthoCam", cam)
    if view == "front":
        w, h = hi.x - lo.x, hi.z - lo.z + 0.06
        co.location = (c.x, lo.y - 10, lo.z - 0.06 + h / 2)
        co.rotation_euler = (math.radians(90), 0, 0)
    elif view == "side":
        s = SIDE_FROM.get(o.name, 1)
        w, h = hi.y - lo.y, hi.z - lo.z + 0.06
        co.location = ((hi.x + 10) if s > 0 else (lo.x - 10), c.y, lo.z - 0.06 + h / 2)
        co.rotation_euler = (math.radians(90), 0, math.radians(90 if s > 0 else -90))
    else:
        w, h = hi.x - lo.x, hi.y - lo.y
        co.location = (c.x, c.y, hi.z + 10)
        co.rotation_euler = (0, 0, 0)
    catcher = bpy.data.objects.get("ShadowCatcher")
    if catcher:   # the top view has no ground line: no floor shadow (it read as a grey box on the sheet)
        catcher.hide_render = view == "top"
    rx, ry = int(round(w * PPM)), int(round(h * PPM))
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    cam.ortho_scale = max(rx, ry) / PPM
    sc.camera = co
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    remove([co])
    return {"view": view, "px": [rx, ry], "extent_m": [round(w, 4), round(h, 4)], "ppm": PPM}


def persp_render(target, offset, lens, path, res=(1200, 900)):
    cam = bpy.data.cameras.new("PerspCam")
    cam.lens = lens
    cam.clip_start = 0.02
    co = new_obj("PerspCam", cam)
    co.location = Vector(target) + Vector(offset)
    look_at(co, target)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.camera = co
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    remove([co])


def view34(o, path):
    lo, hi = world_bbox(o)
    c = (lo + hi) / 2
    rad = (hi - lo).length / 2
    lens = 50.0
    fov = 2 * math.atan(18.0 / lens)   # 36 mm sensor width, the shorter (vertical) side at 4:3 is 27 mm
    fov_v = 2 * math.atan(13.5 / lens)
    dist = rad / math.sin(min(fov, fov_v) / 2) * 0.80
    az, el = math.radians(-35), math.radians(22)   # from the front-left, above
    off = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    persp_render(c, off, lens, path, res=(900, 1000))


# --------------------------------------------------------------------------- collision overlay

def ucx_material():
    m = bpy.data.materials.get("M_Review_UCX")
    if m:
        return m
    m = bpy.data.materials.new("M_Review_UCX")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.35, 0.05, 1)
    bsdf.inputs["Alpha"].default_value = 0.30
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.15
    w = bpy.data.materials.new("M_Review_UCX_Wire")
    w.use_nodes = True
    wb = next(n for n in w.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    wb.inputs["Base Color"].default_value = (0.6, 0.12, 0.0, 1)
    wb.inputs["Emission Color"].default_value = (1.0, 0.3, 0.0, 1)
    wb.inputs["Emission Strength"].default_value = 0.6
    return m


def collision_view(o, path):
    """The prop's 3/4 view with its UCX hulls shown (translucent fill + wire edges)."""
    fill = ucx_material()
    wire = bpy.data.materials["M_Review_UCX_Wire"]
    temp = []
    for h in [c for c in o.children if c.name.startswith("UCX_")]:
        for mat, wf in ((fill, False), (wire, True)):
            me = h.data.copy()
            me.materials.clear()
            me.materials.append(mat)
            c = new_obj("VIS_" + h.name + ("_w" if wf else ""), me)
            c.matrix_world = h.matrix_world.copy()
            if wf:
                mod = c.modifiers.new("W", "WIREFRAME")
                mod.thickness = 0.006
            temp.append(c)
    view34(o, path)
    remove(temp)


# --------------------------------------------------------------------------- silhouette

def silhouette():
    """A plain 1.80 m human figure (skin modifier on a stick figure, then subdivision), used only as a mask."""
    V = {"pelvis": (0, 0, 0.96), "spine": (0, 0, 1.16), "chest": (0, 0, 1.36), "neck": (0, 0, 1.53),
         "head": (0, 0, 1.63), "crown": (0, 0, 1.74),
         "shL": (-0.20, 0, 1.44), "elL": (-0.25, 0, 1.14), "wrL": (-0.28, 0, 0.87), "haL": (-0.29, 0, 0.77),
         "shR": (0.20, 0, 1.44), "elR": (0.25, 0, 1.14), "wrR": (0.28, 0, 0.87), "haR": (0.29, 0, 0.77),
         "hiL": (-0.10, 0, 0.92), "knL": (-0.11, 0, 0.51), "anL": (-0.11, 0, 0.09), "toL": (-0.12, -0.12, 0.03),
         "hiR": (0.10, 0, 0.92), "knR": (0.11, 0, 0.51), "anR": (0.11, 0, 0.09), "toR": (0.12, -0.12, 0.03)}
    E = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head"), ("head", "crown"),
         ("chest", "shL"), ("shL", "elL"), ("elL", "wrL"), ("wrL", "haL"),
         ("chest", "shR"), ("shR", "elR"), ("elR", "wrR"), ("wrR", "haR"),
         ("pelvis", "hiL"), ("hiL", "knL"), ("knL", "anL"), ("anL", "toL"),
         ("pelvis", "hiR"), ("hiR", "knR"), ("knR", "anR"), ("anR", "toR")]
    R = {"pelvis": 0.15, "spine": 0.13, "chest": 0.16, "neck": 0.055, "head": 0.095, "crown": 0.075,
         "shL": 0.06, "elL": 0.045, "wrL": 0.035, "haL": 0.04, "shR": 0.06, "elR": 0.045, "wrR": 0.035, "haR": 0.04,
         "hiL": 0.085, "knL": 0.055, "anL": 0.04, "toL": 0.035, "hiR": 0.085, "knR": 0.055, "anR": 0.04,
         "toR": 0.035}
    names = list(V)
    me = bpy.data.meshes.new("Silhouette")
    me.from_pydata([V[n] for n in names], [(names.index(a), names.index(b)) for a, b in E], [])
    o = new_obj("Silhouette", me)
    sk = o.modifiers.new("Skin", "SKIN")
    for i, n in enumerate(names):
        o.data.skin_vertices[0].data[i].radius = (R[n], R[n] * 0.75)
    o.data.skin_vertices[0].data[names.index("pelvis")].use_root = True
    sub = o.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    bpy.context.view_layer.update()
    lo, hi = world_bbox(o)
    k = 1.80 / (hi.z - lo.z)
    o.scale = (k, k, k)
    o.location.z = -lo.z * k
    mat = bpy.data.materials.new("Sil")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.2, 0.2, 0.2, 1)
    o.data.materials.append(mat)
    return o


# --------------------------------------------------------------------------- sunset line-up

def gravel_material():
    m = bpy.data.materials.new("M_Review_Gravel")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 70.0
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.47, 0.43, 0.37, 1)
    ramp.color_ramp.elements[1].color = (0.78, 0.73, 0.64, 1)
    nt.links.new(vor.outputs["Color"], ramp.inputs["Fac"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.5
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(noise.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    vd = nt.nodes.new("ShaderNodeTexVoronoi")
    vd.feature = "DISTANCE_TO_EDGE"
    vd.inputs["Scale"].default_value = 70.0
    nt.links.new(tc.outputs["Object"], vd.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(vd.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def sunset_world():
    w = bpy.data.worlds.new("W_Sunset")
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (1.0, 0.52, 0.22, 1)
    els[1].position, els[1].color = 0.35, (0.42, 0.42, 0.52, 1)
    e = els.new(0.10)
    e.color = (0.95, 0.62, 0.45, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    bpy.context.scene.world = w


def kelvin_rgb(k):
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def lineup(path):
    setup_render(max(SAMPLES, 96), transparent=False)
    sunset_world()
    names = ["SM_DKP_Train_Makiwara", "SM_DKP_Train_StrikingPost", "SM_DKP_Train_WoodenDummy",
             "SM_DKP_Train_LongArmDummy", "SM_DKP_Train_WeaponRack", "SM_DKP_Train_Bench", "SM_DKP_Train_Stool"]
    inst, x = [], 0.0
    placed = {}
    for n in names:
        src = prop_obj(n)
        lo, hi = world_bbox(src)
        o = new_obj("LU_" + n, src.data)
        o.location = (x - lo.x, 0.0, 0.0)
        placed[n] = (x - lo.x)
        x += (hi.x - lo.x) + 0.40
        inst.append(o)
    show_only([])
    total = x - 0.40
    for o in inst:
        o.location.x -= total / 2
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400.0)
    bm.to_mesh(me)
    bm.free()
    ground = new_obj("Ground", me)
    ground.data.materials.append(gravel_material())
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 4.5
    sun.color = kelvin_rgb(3000)
    sun.angle = math.radians(0.6)
    so = new_obj("Sun", sun)
    el, az = math.radians(9.0), math.radians(118.0)   # low sun from the front-right: travels back-left, long shadows behind
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)))   # travel direction
    so.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    bpy.context.view_layer.update()
    bpy.context.scene.view_settings.exposure = EXPOSURE + 0.4
    persp_render((0.2, 0.3, 0.85), (-1.0, -9.6, 0.55), 26, path, res=(1800, 720))
    remove(inst + [ground, so])
    return {"sun_elev_deg": 9.0, "sun_kelvin": 3000, "sun_travel_azimuth_deg": 118.0, "row_length_m": round(total, 3),
            "placement_x": {k: round(v - total / 2, 3) for k, v in placed.items()}}


def context(path):
    """r2: the west training yard as laid out (layout_training.json, the grey-box frame) at sunset: every west-yard
    prop at its placement on pale gravel, a plain stand-in for the perimeter wall (library M_DJ_PlasterEarth over
    M_DJ_GraniteRubble footing, box UVs), seen from the courtyard floor at eye height."""
    sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
    import dojo_materials as djm
    setup_render(max(SAMPLES, 96), transparent=False)
    sunset_world()
    lay = json.loads((ROOT / "WorkFiles/dojo/build/props/training/layout_training.json").read_text(encoding="utf-8"))
    inst = []
    for i, it in enumerate(lay["instances"]):
        if it["loc"][0] > 10.0:
            continue
        o = new_obj(f"CX_{i}_{it['piece']}", prop_obj(it["piece"]).data)
        o.location = tuple(it["loc"])
        o.rotation_euler = (0.0, 0.0, math.radians(it["rot_z"]))
        inst.append(o)
    show_only([])
    me = bpy.data.meshes.new("CtxGround")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=200.0)
    bm.to_mesh(me)
    bm.free()
    ground = new_obj("CtxGround", me)
    ground.data.materials.append(gravel_material())
    extra = [ground]
    for nm, mat, (x0, x1, y0, y1, z0, z1), setn in (
            ("CtxWallFoot", "M_DJ_GraniteRubble", (-0.60, 0.0, 2.0, 20.0, 0.0, 0.60), "GraniteRubble"),
            ("CtxWall", "M_DJ_PlasterEarth", (-0.50, -0.10, 2.0, 20.0, 0.60, 2.60), "PlasterEarth")):
        wm = bpy.data.meshes.new(nm)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
            v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
            v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
        bm.to_mesh(wm)
        bm.free()
        wm.materials.append(djm.make_material(mat))
        wo = new_obj(nm, wm)
        djm.box_uv(wo, setn, space="WORLD")
        djm.bake_wear(wo, ground_z=0.0)
        extra.append(wo)
    sun = bpy.data.lights.new("SunCtx", "SUN")
    sun.energy = 4.5
    sun.color = kelvin_rgb(3000)
    sun.angle = math.radians(0.6)
    so = new_obj("SunCtx", sun)
    el, az = math.radians(9.0), math.radians(160.0)   # low sun from the east (the courtyard side), raking the yard
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)))
    so.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    bpy.context.view_layer.update()
    bpy.context.scene.view_settings.exposure = EXPOSURE + 0.4
    persp_render((3.0, 11.0, 0.85), (6.2, -7.4, 0.80), 30, path, res=(1800, 1000))
    remove(inst + extra + [so])
    return {"instances": len(inst), "sun_elev_deg": 9.0, "sun_kelvin": 3000, "camera_eye_m": 1.65}


# --------------------------------------------------------------------------- main

def main():
    lock.assert_owner("DojoTrainingProps", "claude")
    RAW.mkdir(parents=True, exist_ok=True)
    report = {"ppm": PPM, "samples": SAMPLES, "views": {}}
    if "sheets" in WHAT or "closeups" in WHAT:
        setup_render(SAMPLES, transparent=True)
        rig = studio(bpy.context.scene.collection)
        if "sheets" in WHAT:
            sil = silhouette()
            show_only([])
            report["views"]["silhouette"] = ortho_render(sil, "front", RAW / "silhouette_front.png", margin=0.05)
            sil.hide_render = True
            for n in PROPS:
                show_only([n])
                o = prop_obj(n)
                report["views"][n] = {v: ortho_render(o, v, RAW / f"{n}_{v}.png") for v in ("front", "side", "top")}
                view34(o, RAW / f"{n}_34.png")
                collision_view(o, RAW / f"{n}_collision.png")
        if "closeups" in WHAT:
            for n, label, tgt, off, lens in CLOSEUPS:
                if n not in PROPS:
                    continue
                show_only([n])
                persp_render(tgt, off, lens, RAW / f"close_{n}_{label}.png", res=(1100, 825))
        remove(rig)
    if "lineup" in WHAT:
        report["lineup"] = lineup(RAW / "lineup_sunset.png")
    if "context" in WHAT:
        report["context"] = context(RAW / "context_sunset.png")
    (OUT / "render_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("done", OUT)


main()
