"""Katana renders - always from the SHIPPED game blend with its BAKED maps (image textures), Cycles.

    blender -b Assets/Katana/Katana.blend --factory-startup --python Scripts/Katana/katana_render.py -- --set <set> --out <dir>

Sets:
    sheet    side / top / end orthographic at the design sheet's scale (5 px per mm, the sheet's own framing of row 1),
             white background -> sheet_side.png, sheet_top.png, sheet_end.png (+ *_mask.png alpha masks)
    gallery  hero 3/4, tsuka close-up, kissaki close-up (raking light for the hamon), habaki/tsuba close-up,
             wireframe, LOD strip
    fbx      sheet views from a re-import of the EXPORTED FBX (proves the shipped bytes) -> fbx_sheet_*.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import katana_spec as K  # noqa: E402

ROOT = HERE.parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "gallery")
OUT = Path(arg("--out", str(ROOT / "Renders" / "Katana"))).resolve() if Path(arg("--out", "x")).is_absolute() else (ROOT / arg("--out", "Renders/Katana")).resolve()
SAMPLES = int(arg("--samples", "128"))
LIGHT = float(arg("--light", "1.0"))
HAMON_LIGHT = float(arg("--hamon-light", "40"))
ONLY = [v for v in arg("--only", "").split(",") if v]
HL_POS = tuple(float(v) for v in arg("--hl-pos", "-1.4,-1.0,0.30").split(","))
KEY = float(arg("--key", "8"))
STRIP = float(arg("--strip", "0"))
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
NAME = K.NAME
PX_PER_MM = 5.0          # the design sheet: 7000 px over 1400 mm


def gpu():
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"


def world_studio(bg=(1, 1, 1), bg_strength=1.0, env_strength=0.3):
    """Camera sees a flat background; reflections see a soft top-bright / bottom-dark studio."""
    w = bpy.data.worlds.new("KAT_Studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bgc = nt.nodes.new("ShaderNodeBackground")
    bgc.inputs["Color"].default_value = (*bg, 1)
    bgc.inputs["Strength"].default_value = bg_strength
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.01, 0.01, 0.012, 1)
    ramp.color_ramp.elements[1].position = 0.80
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mid = ramp.color_ramp.elements.new(0.55)
    mid.color = (0.35, 0.35, 0.37, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    env = nt.nodes.new("ShaderNodeBackground")
    env.inputs["Strength"].default_value = env_strength
    nt.links.new(ramp.outputs["Color"], env.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs["Background"], mix.inputs[1])
    nt.links.new(bgc.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    lo.location = Vector(loc)
    d = (Vector(target) - Vector(loc)).normalized()
    lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
    return lo


def show_only(objs):
    keep = set(o.name for o in objs)
    for o in sc.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep


def cam_axes(right, up):
    r = Vector(right).normalized()
    u = Vector(up)
    u = (u - r * u.dot(r)).normalized()
    z = r.cross(u)
    return Matrix((r, u, z)).transposed()


CAM = None


def camera():
    global CAM
    if CAM is None:
        cd = bpy.data.cameras.new("KAT_cam")
        CAM = bpy.data.objects.new("KAT_cam", cd)
        sc.collection.objects.link(CAM)
    sc.camera = CAM
    return CAM


def shot(path, centre_mm, right, up, px_w, px_h, ortho_mm=None, persp=None, transparent=False):
    cam = camera()
    cd = cam.data
    rot = cam_axes(right, up)
    c = Vector(centre_mm) * 0.001
    back = rot.col[2]
    if persp:
        cd.type = "PERSP"
        cd.lens = persp[1]
        cam.matrix_world = Matrix.Translation(c + back * persp[0] * 0.001) @ rot.to_4x4()
    else:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_mm * 0.001
        cam.matrix_world = Matrix.Translation(c + back * 3.0) @ rot.to_4x4()
    cd.clip_start = 0.001
    cd.clip_end = 20.0
    sc.render.resolution_x = px_w
    sc.render.resolution_y = px_h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("WROTE", path, flush=True)


# --------------------------------------------------------------------------------- sheet framing
# The sheet's row 1 (katana side view): sword z = 0 at sheet x 285 mm, the tsuka axis at sheet y 990 mm; the sheet is
# 1400 x 1200 mm rendered at 7000 x 6000 px. Our crops use the same 5 px / mm and the same centre, so the pixels can be
# laid over the sheet's.
from katana_render_crops import SIDE_CROP, TOP_CROP, END_CROP, TSUKA2_CROP, KISSAKI3_CROP  # noqa: E402
ROW_A, ROW_A_TOP, OX, END_X = 990.0, 1100.0, 70.0 + 215.0, 1180.0


def crop_centre_sword(crop, view):
    cxp, cyp = (crop[0] + crop[2]) / 2, (crop[1] + crop[3]) / 2
    sx, sy = cxp / PX_PER_MM, 1200.0 - cyp / PX_PER_MM
    if view == "side":
        return (ROW_A - sy, 0.0, sx - OX)
    if view == "top":
        return (0.0, sy - ROW_A_TOP, sx - OX)
    return (ROW_A - sy, sx - END_X, 0.0)


def sheet_views(prefix="sheet"):
    sc.cycles.samples = SAMPLES
    for view, crop, right, up in (("side", SIDE_CROP, (0, 0, 1), (-1, 0, 0)),
                                  ("top", TOP_CROP, (0, 0, 1), (0, 1, 0)),
                                  ("end", END_CROP, (0, 1, 0), (-1, 0, 0))):
        if ONLY and view not in ONLY:
            continue
        w, h = crop[2] - crop[0], crop[3] - crop[1]
        c = crop_centre_sword(crop, view)
        if view == "end":
            c = (c[0], c[1], 900.0)
        shot(OUT / f"{prefix}_{view}.png", c, right, up, w, h, ortho_mm=max(w, h) / PX_PER_MM, transparent=False)
        shot(OUT / f"{prefix}_{view}_mask.png", c, right, up, w, h, ortho_mm=max(w, h) / PX_PER_MM, transparent=True)
    # detail views at the sheet's detail scales: 4a tsuka wrap omote 2:1 (10 px/mm), 4c kissaki omote 3:1 (15 px/mm)
    a = (K.S_TIP - 37.0) / K.R
    ax, az = K.CX - K.R * math.cos(a), K.CZ + K.R * math.sin(a)
    for name, crop, centre, ppm in (("tsuka2x", TSUKA2_CROP, (0.0, 0.0, -84.0), 10.0),
                                    ("kissaki3x", KISSAKI3_CROP, (ax - 20.0 / 3.0, 0.0, az), 15.0)):
        if ONLY and name not in ONLY:
            continue
        w, h = crop[2] - crop[0], crop[3] - crop[1]
        shot(OUT / f"{prefix}_{name}.png", centre, (0, 0, 1), (-1, 0, 0), w, h, ortho_mm=max(w, h) / ppm)
        shot(OUT / f"{prefix}_{name}_mask.png", centre, (0, 0, 1), (-1, 0, 0), w, h, ortho_mm=max(w, h) / ppm,
             transparent=True)


def lights_sheet():
    # soft key from the camera side above, a long strip softbox the blade reflects, a cool fill and a rim
    area("key", (-0.9, -1.3, 0.9), (0, 0, 0.25), 1.2, LIGHT * KEY)
    strip = area("strip", (-0.55, -0.9, 0.45), (0.02, 0, 0.35), 0.4, LIGHT * STRIP)
    strip.data.shape = "RECTANGLE"
    strip.data.size = 1.6
    strip.data.size_y = 0.35
    area("fill", (0.9, -1.0, -0.3), (0, 0, 0.1), 2.0, LIGHT * 4, color=(0.92, 0.95, 1.0))
    area("rim", (0.4, 1.2, 0.6), (0, 0, 0.3), 1.0, LIGHT * 8)
    # off-axis frontal softbox: its mirror image misses the polished ji, the frosted hamon's wider lobe catches it
    hl = area("hamon_soft", HL_POS, (0.0, 0.0, 0.30), 1.0, LIGHT * HAMON_LIGHT)
    hl.data.shape = "RECTANGLE"
    hl.data.size = 0.5
    hl.data.size_y = 2.2


def gallery():
    lods = [bpy.data.objects[f"{NAME}_LOD{i}"] for i in range(3)]
    show_only([lods[0]])
    # hero 3/4 (studio white background)
    shot(OUT / "katana_hero.png", (30, 0, 240), (0.32, -0.25, 0.92), (-0.93, -0.12, 0.3), 2400, 1350, persp=(1500, 50))
    # tsuka close-up
    shot(OUT / "katana_tsuka.png", (0, 0, -88), (0.05, -0.3, 1.0), (-1, 0.1, 0.05), 2400, 1000, persp=(430, 70))
    # habaki / tsuba / fuchi
    shot(OUT / "katana_habaki.png", (0, 0, 56), (0.65, -0.75, 0.15), (-0.2, 0.0, 1.0), 1600, 1600, persp=(230, 70))
    # kissaki close-up, side, raking light from above-front
    a = K.S_TIP / K.R
    t = (math.sin(a - 0.03), 0, math.cos(a - 0.03))
    shot(OUT / "katana_kissaki.png", (68, -4, 728), t, (-t[2], 0, t[0]), 2000, 1000, persp=(260, 85))
    # blade mid (hamon read)
    shot(OUT / "katana_hamon.png", (25, 0, 420), (math.sin(0.06), 0, math.cos(0.06)), (-math.cos(0.06), 0, math.sin(0.06)),
         2400, 800, persp=(520, 60))
    # LOD strip: three copies side by side (orthographic side view)
    for i, o in enumerate(lods):
        o.hide_render = False
        o.location = (-0.0, 0.16 * 0, 0)
    strip = []
    for i, o in enumerate(lods):
        show_only([o])
        shot(OUT / f"katana_lod{i}.png", (20, 0, 275), (0, 0, 1), (-1, 0, 0), 2000, 400, ortho_mm=1000)
        shot(OUT / f"katana_lod{i}_tsuka.png", (0, 0, -88), (0.05, -0.3, 1.0), (-1, 0.1, 0.05), 1200, 500, persp=(430, 70))
    show_only([lods[0]])


def wire():
    """Wireframe overlay render (Workbench) of LOD0."""
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = (0.8, 0.8, 0.8)
    o = bpy.data.objects[f"{NAME}_LOD0"]
    m = o.modifiers.new("wf", "WIREFRAME")
    m.thickness = 0.00012
    m.use_replace = False
    shot(OUT / "katana_wire_tsuka.png", (0, 0, -88), (0.05, -0.3, 1.0), (-1, 0.1, 0.05), 2400, 1000, persp=(430, 70))
    shot(OUT / "katana_wire.png", (20, 0, 275), (0, 0, 1), (-1, 0, 0), 2400, 480, ortho_mm=1000)
    o.modifiers.remove(m)


def main():
    gpu()
    world_studio(env_strength=1.0)
    if SET == "fbx":
        for o in list(sc.objects):
            if o.type == "MESH" or o.type == "EMPTY":
                bpy.data.objects.remove(o, do_unlink=True)
        mats = {m.name: m for m in bpy.data.materials}
        bpy.ops.import_scene.fbx(filepath=str(ROOT / "Exports" / "Katana" / f"{NAME}.fbx"))
        imp = [o for o in sc.objects if o.type == "MESH" and not o.name.startswith("UCX_")]
        for o in sc.objects:
            if o.name.startswith("UCX_"):
                o.hide_render = True
        for o in imp:
            for i, slot in enumerate(o.material_slots):
                base = slot.material.name.split(".")[0] if slot.material else None
                if base in mats and slot.material is not mats[base]:
                    slot.material = mats[base]
            o.hide_render = "LOD0" not in o.name
        lights_sheet()
        sheet_views("fbx_sheet")
        return
    if SET == "sheet":
        show_only([bpy.data.objects[f"{NAME}_LOD0"]])
        lights_sheet()
        sheet_views("sheet")
    elif SET == "gallery":
        lights_sheet()
        gallery()
        wire()
    print("KAT_RENDER_DONE", flush=True)


main()
