"""Review renders for kit 8 (Cycles, headless, denoised). Opens Assets/Dojo/CourtyardStone.blend READ-ONLY (never saves).

  sheets   : per prop, front / side / top orthographic + one 3/4 perspective on a plain light-grey background with even
             soft light, a plain grey 1.8 m silhouette beside the front and side views (panels; compose_stone.py lays
             them out like the reference sheet)
  closeups : the reference's key details
  lineup   : every prop in a row at sunset (warm low sun) on pale gravel

Run: blender -b --factory-startup --python Scripts/dojo/props/stone/render_stone.py -- --what sheets|closeups|lineup
     [--keys a,b] [--samples 64] [--out WorkFiles/dojo/build/props/stone/renders/r0]
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
BLEND = ROOT / "Assets" / "Dojo" / "CourtyardStone.blend"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "stone"
GRAVEL = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"     # kit 2's graded CC0 gravel (read only, review ground)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = Path(arg("--out", str(WORK / "renders" / "r0"))).resolve()   # absolute: Blender resolves a relative render path against the drive root
SAMPLES = int(arg("--samples", "64"))
LAYOUT = json.loads((WORK / "layout_stone.json").read_text(encoding="utf-8"))
ASM = LAYOUT["assembly_offsets_well_space"]
S = "SM_DKP_Stone_"
SIL_GREY = float(arg("--sil", "0.16"))
KEY = float(arg("--key", "350"))
WORLD = float(arg("--world", "0.38"))

SHEETS = {
    "lantern_tall": [(S + "LanternTall", (0, 0, 0))],
    "lantern_short": [(S + "LanternShort", (0, 0, 0))],
    "well": [(n, tuple(o)) for n, o in ASM["well"]],
    "well_gable": [(n, tuple(o)) for n, o in ASM["well_gable"]],
    "well_ring": [(S + "Well", (0, 0, 0))],
    "well_cover": [(S + "WellCover", "ground")],
    "well_bucket": [(S + "WellBucket", "ground")],
    "well_pulley": [(S + "WellPulley", "ground")],
    "well_rope": [(S + "WellRope", "ground")],
    "cistern": [(S + "Cistern", (0, 0, 0))],
    "crate": [(S + "Crate", (0, 0, 0))],
    "crate_half": [(S + "CrateHalf", (0, 0, 0))],
}


# --------------------------------------------------------------------------- scene helpers

def setup_render(res_x, res_y, transparent=True):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as exc:   # noqa: BLE001
        print("GPU setup:", exc)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception as exc:   # noqa: BLE001
        print("denoiser:", exc)
    sc.cycles.sample_clamp_indirect = 4.0
    sc.render.resolution_x, sc.render.resolution_y = int(res_x), int(res_y)
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            continue


def clear_review():
    coll = bpy.data.collections.get("Review")
    if coll:
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        coll = bpy.data.collections.new("Review")
        bpy.context.scene.collection.children.link(coll)
    for c in bpy.context.scene.collection.children:
        if c.name != "Review":
            c.hide_render = True
            c.hide_viewport = True
    return coll


def place(coll, name, loc):
    src = bpy.data.objects[name]
    o = bpy.data.objects.new(name + "_rv", src.data)
    if loc == "ground":
        zmin = min(v.co.z for v in src.data.vertices)
        loc = (0, 0, -zmin)
    o.location = loc
    coll.objects.link(o)
    return o


def bounds(objs):
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def silhouette(coll, x, y, facing):
    """Plain grey 1.8 m human silhouette card (a flat outline, the reference sheets' scale figure)."""
    half = [(0.0, 1.80), (0.045, 1.795), (0.08, 1.775), (0.10, 1.74), (0.105, 1.69), (0.098, 1.64), (0.08, 1.60),
            (0.065, 1.575), (0.068, 1.545), (0.14, 1.515), (0.205, 1.49), (0.235, 1.44), (0.245, 1.30),
            (0.25, 1.10), (0.245, 0.93), (0.24, 0.84), (0.225, 0.76), (0.195, 0.73), (0.175, 0.77), (0.19, 0.93),
            (0.192, 1.10), (0.185, 1.26), (0.172, 1.33), (0.16, 1.25), (0.148, 1.10), (0.16, 1.00), (0.172, 0.93),
            (0.165, 0.80), (0.145, 0.55), (0.13, 0.35), (0.125, 0.10), (0.135, 0.03), (0.14, 0.0), (0.035, 0.0),
            (0.04, 0.08), (0.045, 0.35), (0.05, 0.60), (0.03, 0.83), (0.0, 0.86)]
    pts = half + [(-px, pz) for px, pz in reversed(half[1:-1])]
    bm = bmesh.new()
    vs = [bm.verts.new((px, 0.0, pz)) for px, pz in pts]
    edges = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    me = bpy.data.meshes.new("Silhouette")
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.get("Sil") or bpy.data.materials.new("Sil")
    mat.use_nodes = True
    nt = mat.node_tree
    em = nt.nodes.new("ShaderNodeEmission")        # flat, unlit grey: the same tone in every view
    em.inputs["Color"].default_value = (SIL_GREY, SIL_GREY, SIL_GREY, 1)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me.materials.append(mat)
    o = bpy.data.objects.new("Silhouette", me)
    o.location = (x, y, 0)
    o.rotation_euler = (0, 0, math.radians({"front": 0, "side": 90}[facing]))
    o.visible_shadow = False
    coll.objects.link(o)
    return o


def studio(coll):
    """Plain light-grey world, a big soft key from the upper front-left and a soft fill: even, sheet-like light."""
    w = bpy.data.worlds.get("Studio") or bpy.data.worlds.new("Studio")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.42, 0.43, 1)
    bg.inputs["Strength"].default_value = WORLD
    bpy.context.scene.world = w
    for name, loc, energy, size in (("Key", (-3.5, -4.5, 5.0), KEY, 4.0), ("Fill", (4.5, -2.0, 2.5), KEY * 0.25, 5.0),
                                    ("Top", (0, 0, 6.0), KEY * 0.25, 5.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size = energy, size
        ld.color = (1.0, 0.97, 0.93) if name == "Key" else (0.95, 0.97, 1.0)
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(lo)
    # shadow catcher ground: soft contact shadows on the transparent background
    me = bpy.data.meshes.new("Catcher")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=12)
    bm.to_mesh(me)
    bm.free()
    g = bpy.data.objects.new("Catcher", me)
    g.is_shadow_catcher = True
    coll.objects.link(g)


def cam(coll, name, loc, target, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_end = 200
    co = bpy.data.objects.new(name, cd)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(co)
    bpy.context.scene.camera = co
    return co


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


# --------------------------------------------------------------------------- sheets

def sheet(key):
    coll = clear_review()
    objs = [place(coll, n, loc) for n, loc in SHEETS[key]]
    bpy.context.view_layer.update()          # matrix_world is stale until the depsgraph updates
    lo, hi = bounds(objs)
    studio(coll)
    size = hi - lo
    zmax = max(hi.z, 1.8) + 0.08
    zmin = -0.04
    ppm = 900 / (zmax - zmin)
    pad = 0.12
    info = {"key": key, "ppm": ppm, "bbox_min": list(lo), "bbox_max": list(hi)}
    (OUT / "parts").mkdir(parents=True, exist_ok=True)
    # front (camera at -Y looking +Y), silhouette to the left
    sil_x = lo.x - 0.45 - 0.25
    sil = silhouette(coll, sil_x, (lo.y + hi.y) / 2, "front")
    x0, x1 = sil_x - 0.25 - pad, hi.x + pad
    w, h = x1 - x0, zmax - zmin
    setup_render(w * ppm, h * ppm)
    cam(coll, "CamFront", ((x0 + x1) / 2, lo.y - 20, (zmin + zmax) / 2), ((x0 + x1) / 2, 0, (zmin + zmax) / 2), max(w, h))
    render(OUT / "parts" / f"{key}_front.png")
    info["front_px"] = [round(w * ppm), round(h * ppm)]
    # side (camera at +X looking -X: image right = +Y), silhouette at the left (-Y)
    sil.location = ((lo.x + hi.x) / 2, lo.y - 0.45 - 0.25, 0)
    sil.rotation_euler = (0, 0, math.radians(90))
    y0, y1 = lo.y - 0.45 - 0.5 - pad, hi.y + pad
    w = y1 - y0
    setup_render(w * ppm, h * ppm)
    cam(coll, "CamSide", (hi.x + 20, (y0 + y1) / 2, (zmin + zmax) / 2), (0, (y0 + y1) / 2, (zmin + zmax) / 2), max(w, h))
    render(OUT / "parts" / f"{key}_side.png")
    info["side_px"] = [round(w * ppm), round(h * ppm)]
    # top (front at the bottom of the image)
    sil.hide_render = True
    bpy.data.objects["Catcher"].hide_render = True     # no cast-shadow smear in the plan view
    x0, x1, y0, y1 = lo.x - pad, hi.x + pad, lo.y - pad, hi.y + pad
    w, hh = x1 - x0, y1 - y0
    setup_render(w * ppm, hh * ppm)
    cam(coll, "CamTop", ((x0 + x1) / 2, (y0 + y1) / 2, hi.z + 20), ((x0 + x1) / 2, (y0 + y1) / 2, 0), max(w, hh))
    bpy.context.scene.camera.rotation_euler = (0, 0, 0)
    render(OUT / "parts" / f"{key}_top.png")
    info["top_px"] = [round(w * ppm), round(hh * ppm)]
    # 3/4 perspective from the front-left, above eye level
    c = (lo + hi) / 2
    r = max(size.x, size.y, size.z)
    d = r * 1.85 + 0.4
    loc = (c.x - d * 0.62, c.y - d * 0.78, c.z + d * 0.42)
    setup_render(800, 900)
    cam(coll, "CamPersp", loc, (c.x, c.y, c.z - size.z * 0.05), lens=50)
    bpy.data.objects["Catcher"].hide_render = False
    render(OUT / "parts" / f"{key}_persp.png")
    (OUT / "parts" / f"{key}_info.json").write_text(json.dumps(info, indent=1, default=float), encoding="utf-8")


# --------------------------------------------------------------------------- close-ups

CLOSEUPS = {
    # name: (sheet key, camera loc, target, lens)
    "cu_lantern_cap": ("lantern_tall", (-0.95, -1.55, 2.05), (0, 0, 1.62), 50),
    "cu_lantern_cap_top": ("lantern_tall", (-0.35, -0.55, 3.0), (0, 0, 1.70), 45),
    "cu_lantern_lightbox": ("lantern_tall", (-0.55, -1.10, 1.30), (0, 0, 1.18), 50),
    "cu_lantern_base_moss": ("lantern_tall", (-0.85, -1.3, 0.75), (0, 0, 0.30), 50),
    "cu_lantern_short": ("lantern_short", (-0.9, -1.6, 1.15), (0, 0, 0.66), 50),
    "cu_well_pulley_bucket": ("well", (-0.50, -1.10, 1.50), (0.05, 0, 1.30), 50),
    "cu_well_blocks": ("well", (-1.25, -1.25, 0.70), (-0.45, -0.3, 0.40), 50),
    "cu_well_cover_beam": ("well", (-0.35, -1.25, 1.55), (0, 0, 0.90), 42),
    "cu_well_roof": ("well", (-1.3, -1.9, 2.6), (0, 0, 2.05), 45),
    "cu_well_gable_roof": ("well_gable", (-1.1, -1.7, 2.6), (0, 0, 2.05), 45),
    "cu_well_gable_under": ("well_gable", (-0.9, -1.3, 1.25), (0, 0, 1.95), 32),
    "cu_cistern_corner": ("cistern", (-1.2, -1.35, 0.55), (-0.55, -0.55, 0.40), 50),
    "cu_cistern_lid": ("cistern", (-1.0, -1.35, 1.95), (0, 0, 1.2), 42),
    "cu_crate_corner": ("crate", (-1.15, -1.25, 1.45), (-0.45, -0.45, 1.0), 45),
    # r2 checks: skids seated flush under the posts (low, grazing), the cap from the sheet's front, the short lantern
    # cap, the well joints from close range
    "cu_crate_skid": ("crate", (-0.95, -1.35, 0.22), (-0.30, -0.45, 0.06), 45),
    "cu_crate_half_skid": ("crate_half", (0.95, -1.35, 0.20), (0.30, -0.45, 0.06), 45),
    "cu_lantern_cap_front": ("lantern_tall", (0.0, -2.2, 1.62), (0, 0, 1.62), 60),
    "cu_lantern_short_cap": ("lantern_short", (-0.7, -1.1, 1.25), (0, 0, 0.93), 50),
    "cu_well_joints": ("well_ring", (-0.95, -1.45, 0.80), (-0.30, -0.40, 0.40), 50),
}


def closeups(keys=None):
    for name, (key, loc, target, lens) in CLOSEUPS.items():
        if keys and name not in keys:
            continue
        coll = clear_review()
        for n, off in SHEETS[key]:
            place(coll, n, off)
        studio(coll)
        setup_render(1200, 900, transparent=False)
        cam(coll, "CamCU", loc, target, lens=lens)
        render(OUT / f"{name}.png")


# --------------------------------------------------------------------------- sunset line-up

def lineup():
    coll = clear_review()
    groups = [("lantern_short", 0.0), ("lantern_tall", 1.6), ("well", 3.9), ("well_gable", 6.6), ("cistern", 9.1),
              ("crate", 10.9), ("crate_half", 12.4)]
    for key, x in groups:
        for n, off in SHEETS[key]:
            o = place(coll, n, off if off != "ground" else (0, 0, 0))
            o.location.x += x
    # a second half crate stacked on the first: the route-7 height
    o = place(coll, S + "CrateHalf", (12.4, 0, 0.625))
    o.rotation_euler.z = math.radians(90)
    # pale gravel ground (kit 2's texture, 4 m tile)
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=150)
    uvl = bm.loops.layers.uv.new("UV0")
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.x / 4.0, lp.vert.co.y / 4.0)
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("Gravel_review")
    mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(GRAVEL / "T_DKG_Gravel_BC.png"))
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(GRAVEL / "T_DKG_Gravel_ORM.png"))
    orm.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], b.inputs["Roughness"])
    me.materials.append(mat)
    g = bpy.data.objects.new("Ground", me)
    coll.objects.link(g)
    # sunset: warm low sun from the front-left, dusky sky
    w = bpy.data.worlds.new("Sunset")
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    mapn = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # gradient on the view direction's z: horizon warm peach, zenith dusky blue-violet
    sepz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sepz.inputs[0])
    nt.links.new(sepz.outputs["Z"], ramp.inputs["Fac"])
    # f1: r0's ramp ran 0 -> 0.35 and the camera only sees z of about 0-0.3, so the sky read flat peach
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, 0.50, 0.24, 1)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = (0.16, 0.18, 0.38, 1)
    mid = ramp.color_ramp.elements.new(0.07)
    mid.color = (0.85, 0.45, 0.42, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35
    bpy.context.scene.world = w
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 4.0
    sd.color = (1.0, 0.62, 0.36)
    sd.angle = math.radians(1.5)
    so = bpy.data.objects.new("Sun", sd)
    so.rotation_euler = (math.radians(90 - 9), 0, math.radians(-35))
    coll.objects.link(so)
    setup_render(1920, 900, transparent=False)
    sc = bpy.context.scene
    sc.view_settings.exposure = 0.3
    cam(coll, "CamLine", (6.2, -12.8, 2.3), (6.2, 0, 0.85), lens=32)
    render(OUT / "lineup_sunset.png")


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    what = arg("--what", "sheets")
    keys = arg("--keys", None)
    keys = keys.split(",") if keys else None
    OUT.mkdir(parents=True, exist_ok=True)
    if what in ("sheets", "all"):
        for k in SHEETS:
            if keys is None or k in keys:
                sheet(k)
    if what in ("closeups", "all"):
        closeups(keys)
    if what in ("lineup", "all"):
        lineup()


main()
