"""Cycles review renders of the dojo ground kit in context (Assets/Dojo/DojoGround.blend + layout_ground.json).

Context: the grey-box from the dojo-greybox-kit1 workflow (Assets/Dojo/DojoGreybox.blend) is APPENDED READ-ONLY into
this render session (never saved; its file is never written): its "Assembly" collection minus its own flat floors
(Floor_Fight / Floor_Path / Floor_Yards) and the invisible 1v1 boundary; its outside ground is lowered 3 cm so it never
fights our ground. If that file is missing, plain grey blocks are built at the spec positions (context_blocks()).

Lighting: the layout's sunset sun (warm, low, from the west-north-west) and a gradient sunset sky (warm horizon, glow
toward the sun, violet-blue zenith), matching dojo1_reference2's time of day. Cycles GPU, OIDN denoise, AgX.

Run: blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_ground.py --
     [--cams C_Establish,C_Overview,C_PlayerEye] [--samples 64] [--out DIR] [--exposure EV] [--scale 1.0]
     [--no-greybox]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "ground"
GREYBOX = ROOT / "Assets" / "Dojo" / "DojoGreybox.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


SUN_W = float(arg("--sun", "7.5"))          # W/m2 (r0 tests: 4.5 read dim; f1: 6.0 -> 7.5 so the lit sand reaches ~195)
SKY_STRENGTH = float(arg("--sky", "0.6"))   # f1: 0.8 -> 0.6, deeper contact shadow (judge delta 11)
EXPOSURE = float(arg("--exposure", "0.0"))
LOOK = arg("--look", "AgX - Medium High Contrast")
SKY_HORIZON = (1.00, 0.56, 0.34)
SKY_ZENITH = (0.26, 0.30, 0.52)
SKY_GLOW = (1.00, 0.62, 0.30)


def kelvin_rgb(k):
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def grey_mat(name, v):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (v, v, v, 1)
    b.inputs["Roughness"].default_value = 0.85
    return m


# --------------------------------------------------------------------------- context

def append_greybox(coll):
    with bpy.data.libraries.load(str(GREYBOX), link=False) as (src, dst):
        dst.collections = ["Assembly"] if "Assembly" in src.collections else []
    gb = bpy.data.collections.get("Assembly.001") or next(
        (c for c in bpy.data.collections if c.name.startswith("Assembly") and c.library is None and c.name != "Assembly"), None)
    if gb is None:
        return None
    gb.name = "GreyboxContext"
    coll.children.link(gb)
    drop = ("SM_DGB_Floor_Fight", "SM_DGB_Floor_Path", "SM_DGB_Floor_Yards", "SM_DGB_Boundary")
    kept = 0
    bpy.context.view_layer.update()
    for o in list(gb.all_objects):
        fam = o.name.split("__")[0]
        if fam.startswith(drop) or o.name.startswith("UCX_"):
            bpy.data.objects.remove(o)
            continue
        if fam == "SM_DGB_Ground_Outside":
            o.location.z -= 0.03
        ymax = max((o.matrix_world @ Vector(c)).y for c in o.bound_box) if o.type == "MESH" else 99.0
        o["ctx_group"] = ("gatehouse" if fam.startswith(("SM_DGB_Gatehouse", "SM_DGB_Gate_Leaves")) else
                          "south_wall" if ymax <= 0.01 else "other")   # the wall runs and the piers in its line
        kept += 1
    return kept


def box(coll, name, x0, x1, y0, y1, z0, z1, mat, group="other"):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o["ctx_group"] = group
    coll.objects.link(o)
    return o


def poly(coll, name, verts, faces, mat, group="other"):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o["ctx_group"] = group
    coll.objects.link(o)
    return o


def context_blocks(coll):
    """Fallback grey blocks at the DOJO_ARENA_SPEC positions (section 4)."""
    body, roof = grey_mat("CTX_Grey", 0.42), grey_mat("CTX_GreyRoof", 0.10)
    box(coll, "CTX_Wall_S_W", -1, 20, -1, 0, 0, 2.0, body, "south_wall")
    box(coll, "CTX_Wall_S_E", 24, 45, -1, 0, 0, 2.0, body, "south_wall")
    box(coll, "CTX_Gate_Leaves", 20, 24, -0.7, -0.5, 0, 3.4, body, "gatehouse")
    box(coll, "CTX_Wall_N", -1, 45, 36, 37, 0, 2.0, body)
    box(coll, "CTX_Wall_W", -1, 0, 0, 36, 0, 2.0, body)
    box(coll, "CTX_Wall_E", 44, 45, 0, 36, 0, 2.0, body)
    for x in (19.6, 24.0):
        for y in (-0.8, 1.8):
            box(coll, "CTX_GatePost", x, x + 0.4, y, y + 0.4, 0, 3.25, body, "gatehouse")
    poly(coll, "CTX_GateRoof", [(18, -2.5, 3.25), (26, -2.5, 3.25), (26, 0, 4.4), (18, 0, 4.4), (26, 2.5, 3.25), (18, 2.5, 3.25)],
         [(0, 1, 2, 3), (3, 2, 4, 5)], roof, "gatehouse")
    box(coll, "CTX_Veranda", 11, 33, 22, 34, 0, 0.5, body)
    box(coll, "CTX_StepBand", 11, 33, 21.4, 22.0, 0, 0.25, body)
    box(coll, "CTX_HallBody", 13, 31, 24, 34, 0.5, 5.5, body)
    zl, zh = 3.0, 4.17
    poly(coll, "CTX_RoofLower", [(10.5, 21.5, zl), (33.5, 21.5, zl), (31, 24, zh), (13, 24, zh),
                                 (10.5, 34.5, zl), (13, 34, zh), (33.5, 34.5, zl), (31, 34, zh)],
         [(0, 1, 2, 3), (0, 3, 5, 4), (1, 6, 7, 2)], roof)
    poly(coll, "CTX_RoofUpper", [(12.1, 23.1, 5.5), (31.9, 23.1, 5.5), (31.9, 34.9, 5.5), (12.1, 34.9, 5.5),
                                 (18.0, 29.0, 8.3), (26.0, 29.0, 8.3)],
         [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)], roof)
    for sx in (0, 1):
        x0, x1 = (0.0, 7.6) if sx == 0 else (36.4, 44.0)
        box(coll, "CTX_Outbuilding", x0, x1, 27.4, 36, 0, 3.25, body)
        poly(coll, "CTX_OutRoof", [(x0, 27.4, 3.25), (x1, 27.4, 3.25), (x1, 31.7, 5.25), (x0, 31.7, 5.25),
                                   (x1, 36, 3.25), (x0, 36, 3.25)], [(0, 1, 2, 3), (3, 2, 4, 5)], roof)
        cx0, cx1 = (7.6, 10.5) if sx == 0 else (33.5, 36.4)
        box(coll, "CTX_Corridor", cx0, cx1, 29.5, 32.5, 0, 0.5, body)
        box(coll, "CTX_CorridorRoof", cx0, cx1, 29.3, 32.7, 3.0, 3.2, roof)
    box(coll, "CTX_ShedRoof", 0, 6, 0, 5, 2.5, 2.65, roof)
    box(coll, "CTX_PavPlinth", 39, 43, 1, 5, 0, 1.0, body)
    poly(coll, "CTX_PavRoof", [(38.4, 0.4, 3.25), (43.6, 0.4, 3.25), (43.6, 5.6, 3.25), (38.4, 5.6, 3.25), (41, 3, 4.5)],
         [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], roof)
    for x in (19.0, 25.0):
        box(coll, "CTX_Lantern", x - 0.25, x + 0.25, 20.25, 20.75, 0, 1.8, body)
    for x0 in (11.0, 31.8):
        box(coll, "CTX_Cistern", x0, x0 + 1.2, 20.2, 21.4, 0, 1.25, body)
    for x in (3.5, 40.5):
        box(coll, "CTX_TreeTrunk", x - 0.2, x + 0.2, 15.8, 16.2, 0, 4.2, body)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(x, 16.0, 5.2))
        s = bpy.context.active_object
        s.scale = (3.2, 3.2, 1.3)
        s.data.materials.append(grey_mat("CTX_GreyTree", 0.12))
        for c in s.users_collection:
            c.objects.unlink(s)
        coll.objects.link(s)
        s["ctx_group"] = "other"
    box(coll, "CTX_OutsideGround", -40, 84, -40, 76, -0.23, -0.03, grey_mat("CTX_GreyGround", 0.25))


# --------------------------------------------------------------------------- world, sun, render

def sunset_world(sun_travel):
    w = bpy.data.worlds.new("SunsetSky")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Generated"], nrm.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm.outputs[0], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.05
    mr.inputs["From Max"].default_value = 0.40
    nt.links.new(sep.outputs[2], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = SKY_HORIZON + (1,)
    ramp.color_ramp.elements[1].color = SKY_ZENITH + (1,)
    ramp.color_ramp.interpolation = "EASE"
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    to_sun = Vector(sun_travel).normalized() * -1.0
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(nrm.outputs[0], dot.inputs[0])
    dot.inputs[1].default_value = tuple(to_sun)
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.0
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    nt.links.new(mx.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    nt.links.new(pw.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = SKY_GLOW + (1,)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = SKY_STRENGTH
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def add_sun(sc, L):
    ld = bpy.data.lights.new(L["name"], "SUN")
    ld.energy = SUN_W
    ld.color = kelvin_rgb(L["kelvin"])
    ld.angle = math.radians(0.6)
    o = bpy.data.objects.new(L["name"], ld)
    o.rotation_euler = Vector(L["travel_dir"]).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(o)
    return o


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
    sc.view_settings.look = LOOK
    sc.view_settings.exposure = EXPOSURE


def dapple_canopies(frac=0.50, scale=5.0):   # r0 round 1: 0.35 let nearly all light through
    """Review stand-in for real foliage: the grey-box canopies are solid blocks and threw one hard black blot across
    the west field. For SHADOW rays only, a noise mask lets about half the light through in leaf-sized gaps (the camera
    still sees the solid grey-box canopy). In-memory copy only; the grey-box file is never written."""
    for m in bpy.data.materials:
        if not ("Canopy" in m.name or m.name == "CTX_GreyTree") or not m.use_nodes:
            continue
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        src = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
        if src is None:
            continue
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 6.0
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = frac - 0.04
        ramp.inputs["From Max"].default_value = frac + 0.04
        ramp.inputs["To Min"].default_value = 0.0
        ramp.inputs["To Max"].default_value = 1.0
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        fac = nt.nodes.new("ShaderNodeMath")
        fac.operation = "MULTIPLY"
        nt.links.new(lp.outputs["Is Shadow Ray"], fac.inputs[0])
        nt.links.new(ramp.outputs["Result"], fac.inputs[1])
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(fac.outputs[0], mix.inputs[0])
        nt.links.new(src, mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        print("dappled", m.name)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    sc = bpy.context.scene
    data = json.loads((WORK / "layout_ground.json").read_text(encoding="utf-8"))
    ctx = bpy.data.collections.new("Context")
    sc.collection.children.link(ctx)
    kept = None
    if GREYBOX.exists() and "--no-greybox" not in ARGS:
        try:
            kept = append_greybox(ctx)
        except Exception as exc:  # noqa: BLE001
            print("grey-box append failed, using blocks:", exc)
    # the grey-box's outside ground has a hole under the wall line; the gate approach paving (kit 1 / kit 12, not
    # this kit) is stood in by a plain grey slab so the establishing view has a floor under the camera, as reference 2
    box(ctx, "CTX_GateApproach", -1.0, 45.0, -14.0, 0.0, -0.06, -0.01, grey_mat("CTX_Paving", 0.30), "other")
    if not kept:
        context_blocks(ctx)
        print("context: plain grey blocks at the spec positions")
    else:
        print(f"context: grey-box appended read-only ({kept} objects)")
    dapple_canopies()
    sun = next(L for L in data["lights"] if L["type"] == "sun")
    add_sun(sc, sun)
    sc.world = sunset_world(sun["travel_dir"])
    setup_cycles(sc, int(arg("--samples", "64")))
    out = Path(arg("--out", str(WORK / "renders" / "f1")))
    out.mkdir(parents=True, exist_ok=True)
    want = arg("--cams", "")
    scale = float(arg("--scale", "1.0"))
    for c in data["cameras"]:
        if want and c["name"] not in want.split(","):
            continue
        cd = bpy.data.cameras.new(c["name"])
        cd.lens = c["lens_mm"]
        cd.sensor_width = 36.0
        cd.shift_y = c.get("shift_y", 0.0)
        cd.clip_start = 0.05
        cd.clip_end = 2000.0
        co = bpy.data.objects.new(c["name"], cd)
        sc.collection.objects.link(co)
        co.location = c["loc"]
        look_at(co, c["look_at"])
        hide = set(c.get("hide_from_camera", []))
        for o in list(ctx.all_objects):
            if o is None:   # removed grey-box floors can leave stale entries in the collection cache
                continue
            # r0: gone entirely from this view (camera, shadow and bounce; the piers' yellow bounced onto the gravel)
            o.hide_render = o.get("ctx_group", "other") in hide
        sc.camera = co
        sc.render.resolution_x, sc.render.resolution_y = (int(v * scale) for v in c.get("res", [1600, 900]))
        sc.render.filepath = str(out / f"{c['name']}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath, flush=True)


main()
