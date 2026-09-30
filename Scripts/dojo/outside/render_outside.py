"""ROUND 5 OUTSIDE track: lean review renders (Cycles, GPU, denoised) of Assets/Dojo/DojoOutside.blend (read-only:
nothing is saved), beside the references. The compound context (every other kit, from the showcase) takes its
TEXTURED meshes from the kits' own source blends (read only, matched by piece name and bounds), as the other tracks'
render scripts do; this track's SM_DKX_* pieces are already textured in DojoOutside.blend.

Views (sunset: sun 13 deg from az 160 as the showcase; AgX; the street, gate and landing lamps lit):
  ref1_overview      dojo1_reference1's high view from the south (the approach side in front)
  ref2_establishing  dojo1_reference2's view from the gate (the skyline: house roofs + ridges beyond the walls)
  road_gate          eye level on the road, the gate apron, kerb, gutter and verge
  road_east          along the road to the east: poles, wires, landing, rail fence
  terrace            from the lower lane: the terrace wall, canal, rail fence, landing, lamps
  alley_W / alley_E  the rear-alley fences behind the hall's veranda ends
  walltop_W          a player on the west wall top looking out west (outside ground, lane, houses, ridges)
  skyline_NW         from the courtyard toward the north-west (houses and ridges over the wall)
Run: blender -b --factory-startup Assets/Dojo/DojoOutside.blend --python Scripts/dojo/outside/render_outside.py --
     [--samples 64] [--tag r0] [--only a,b] [--scale 60]
Out: WorkFiles/dojo/build/outside/renders/<tag>/<view>.png (+ views.json)
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OXW = ROOT / "WorkFiles" / "dojo" / "build" / "outside"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


SAMPLES = int(arg("--samples", "64"))
TAG = arg("--tag", "r0")
ONLY = [s for s in arg("--only", "").split(",") if s]
SCALE = int(arg("--scale", "60"))
# round 6: --outdir <dir> (absolute, or relative to the project root) writes there instead of outside/renders/<tag>
OUT = ((ROOT / arg("--outdir", "")) if "--outdir" in ARGS else (OXW / "renders" / TAG)).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
SOURCES = ["DojoKit1.blend", "DojoGround.blend", "CourtyardStone.blend", "TrainingProps.blend", "ModernProps.blend",
           "Taiko.blend", "DojoHall.blend", "DojoOutbuildings.blend", "DojoCorridors.blend", "DojoShed.blend",
           "DojoPavilion.blend", "DojoYardPosts.blend", "DojoGreybox.blend"]


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
    sc.render.image_settings.color_mode = "RGB"
    sc.cycles.max_bounces = 6
    sc.render.resolution_percentage = SCALE


def assembly():
    return list(bpy.data.collections["Assembly"].objects)


def piece_of(o):
    return o.name.split("__")[0]


def textured_context():
    need = {piece_of(o) for o in assembly()} - {n for n in KIT if n.startswith("SM_DKX_")}
    got = {}
    for fn in SOURCES:
        path = ROOT / "Assets" / "Dojo" / fn
        if not path.exists():
            continue
        want = [n for n in need - set(got)]
        if not want:
            break
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
    print("TEXTURED CONTEXT", len(got), "pieces", n, "instances; untextured:", sorted(need - set(got))[:40], flush=True)


def hide_gameplay(show_blockers=False):
    """The invisible 1v1 pieces are hidden (hidden in game in Unreal); round 6: show_blockers draws this track's
    SM_DKX_1v1_* blockers as translucent red (the seal diagram view) and keeps the grey-box ring hidden."""
    for o in assembly():
        p = piece_of(o)
        o.hide_render = p.startswith("SM_DGB_Boundary") or (p.startswith("SM_DKX_1v1_") and not show_blockers)
    if show_blockers:
        m = bpy.data.materials.get("SEAL_PREVIEW") or bpy.data.materials.new("SEAL_PREVIEW")
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.9, 0.08, 0.05, 1)
        b.inputs["Emission Color"].default_value = (0.9, 0.08, 0.05, 1)
        b.inputs["Emission Strength"].default_value = 0.6
        b.inputs["Alpha"].default_value = 0.38
        for o in assembly():
            if piece_of(o).startswith("SM_DKX_1v1_"):
                o.data = o.data.copy()
                o.data.materials.clear()
                o.data.materials.append(m)


def ridge_preview():
    """Round 6: the ridge rings are flat EMISSIVE in Unreal (M_DJ_EmissiveFlat_Master, base colour near black); preview
    them as emission of their target colour (ox_common._RIDGE_EMIT) so the Blender stills show the silhouettes and the
    value / saturation fall-off, not a lit base colour."""
    import ox_common as OX
    for name, (srgb, _e) in OX._RIDGE_EMIT.items():
        m = bpy.data.materials.get(name)
        if m is None:
            continue
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type not in ("OUTPUT_MATERIAL",):
                nt.nodes.remove(n)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = OX.lin3(srgb) + [1.0]
        em.inputs["Strength"].default_value = 2.2
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])


def sunset_world(exposure=0.55):
    el, az = math.radians(13.0), math.radians(160.0)
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # warm glow toward the sun's side: dot(view, sun) mixed into the height gradient
    dp = nt.nodes.new("ShaderNodeVectorMath")
    dp.operation = "DOT_PRODUCT"
    dp.inputs[1].default_value = to_sun
    nt.links.new(tc.outputs["Generated"], dp.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.95, 0.55, 0.36, 1)
    cr.elements[1].position = 0.30
    cr.elements[1].color = (0.36, 0.34, 0.52, 1)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    glow = nt.nodes.new("ShaderNodeMapRange")
    glow.inputs["From Min"].default_value = 0.55
    glow.inputs["From Max"].default_value = 1.0
    nt.links.new(dp.outputs["Value"], glow.inputs["Value"])
    hz = nt.nodes.new("ShaderNodeMapRange")          # the glow only near the horizon
    hz.inputs["From Min"].default_value = 0.35
    hz.inputs["From Max"].default_value = 0.0
    nt.links.new(sep.outputs[2], hz.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(glow.outputs["Result"], mul.inputs[0])
    nt.links.new(hz.outputs["Result"], mul.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (1.6, 0.85, 0.42, 1)
    nt.links.new(mul.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
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


def lamp_lights():
    """Point lights in the lamps (warm, as the showcase's lamp lights): the gate bracket lamps and the two street lamps
    at the landing ends."""
    pts = [((18.8, -2.161, 2.308), 45.0), ((25.2, -2.161, 2.308), 45.0), ((18.8, 2.161, 2.308), 45.0),
           ((25.2, 2.161, 2.308), 45.0)]
    for o in assembly():
        p = piece_of(o)
        if p == "SM_DKP_Modern_StreetLamp_A":
            pts.append(((o.matrix_world @ Vector((-0.30, 0.0, 2.53))), 60.0))
        elif p == "SM_DKP_Modern_StreetLamp_B":
            pts.append(((o.matrix_world @ Vector((0.28, 0.0, 2.05))), 55.0))
        elif p == "SM_DKP_Stone_LanternTall":
            pts.append(((o.matrix_world @ Vector((0.0, 0.0, 1.225))), 20.0))
    for i, (loc, w) in enumerate(pts):
        lt = bpy.data.lights.new(f"Lamp{i}", "POINT")
        lt.energy = w
        lt.color = (1.0, 0.62, 0.32)
        lt.shadow_soft_size = 0.08
        o = bpy.data.objects.new(f"Lamp{i}", lt)
        o.location = loc
        sc.collection.objects.link(o)


def cam(name, loc, look, hfov, w=1448, h=1086):
    c = bpy.data.cameras.new(name)
    c.sensor_fit = "HORIZONTAL"
    c.angle = math.radians(hfov)
    c.clip_start = 0.1
    c.clip_end = 6000.0
    o = bpy.data.objects.new(name, c)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o, w, h


VIEWS = {
    "ref1_overview": ((22.0, -34.0, 34.0), (22.0, 12.0, 0.0), 62.0, 1448, 1086),
    "ref2_establishing": ((22.0, 2.9, 3.1), (22.0, 24.0, 0.3), 74.0, 1448, 1086),
    "road_gate": ((13.0, -6.6, 1.7), (22.0, -1.8, 1.0), 64.0, 1600, 900),
    "road_east": ((20.0, -4.2, 1.7), (70.0, -8.0, 4.0), 66.0, 1600, 900),
    "terrace": ((20.0, -15.2, 0.2), (22.0, -8.0, -0.2), 70.0, 1600, 900),
    "alley_W": ((11.9, 29.0, 2.2), (11.8, 34.05, 1.1), 58.0, 1600, 900),
    "alley_E": ((32.1, 29.0, 2.2), (32.2, 34.05, 1.1), 58.0, 1600, 900),
    "walltop_W": ((-0.5, 12.0, 3.72), (-40.0, 20.0, 3.0), 72.0, 1600, 900),
    "skyline_NW": ((26.0, 6.0, 1.7), (2.0, 60.0, 9.0), 70.0, 1600, 900),
    "junction_E": ((26.5, -5.0, 0.9), (25.0, -2.9, 0.0), 50.0, 1200, 800),
    "junction_W": ((17.0, -5.0, 0.9), (18.9, -2.9, 0.0), 50.0, 1200, 800),
    # round 6
    "far_background": ((22.0, -30.0, 18.0), (22.0, 60.0, 8.0), 80.0, 1920, 1080),
    "approach_road": ((-2.0, -5.8, 1.7), (22.0, -2.4, 2.2), 62.0, 1920, 1080),
    "road_end_E": ((96.0, -5.3, 1.7), (140.0, -4.5, 2.2), 58.0, 1600, 900),
    "horizon_N": ((22.0, 12.0, 9.0), (22.0, 1200.0, 45.0), 34.0, 1920, 820),
    "pocket_W": ((12.3, 27.6, 1.65), (10.45, 33.3, 0.9), 62.0, 1600, 900),
    "pocket_E": ((31.7, 27.6, 1.65), (33.55, 33.3, 0.9), 62.0, 1600, 900),
    "seal_blockers": ((22.0, 30.5, 62.0), (22.0, 30.49, 0.0), 48.0, 1600, 900),
}


def main():
    setup_cycles()
    textured_context()
    hide_gameplay()
    sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "outside"))
    ridge_preview()
    sunset_world()
    lamp_lights()
    done = {}
    for name, (loc, look, hfov, w, h) in VIEWS.items():
        if ONLY and name not in ONLY:
            continue
        hide_gameplay(show_blockers=(name == "seal_blockers"))
        o, w, h = cam("CAM_" + name, loc, look, hfov, w, h)
        sc.camera = o
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        done[name] = {"loc": loc, "look_at": look, "hfov": hfov, "px": [w, h], "file": str(OUT / f"{name}.png")}
        print("RENDERED", name, flush=True)
    (OUT / "views.json").write_text(json.dumps(done, indent=1), encoding="utf-8")


main()
