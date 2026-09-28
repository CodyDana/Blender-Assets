"""Comparison sheet, restyle pass 2 (knife grind): the reference next to every form, hero + top, labelled.

The reference column is the study-only third-party asset rendered through the pack's OWN rig
(WorkFiles/shuriken/style_reference/ref_on_rig.py, scaled to 100 mm: ref_rig_scaled100_persp/top.png,
stats in ref_rig_stats.json), so both sides share world, lamps, cameras, view transform and the
image_stats measurement.  Each form column is the final build's gallery pair (baked maps only) with
its measured grind, masses and luminance from the build report.  Built as a flat Blender scene
(emissive image planes + text) and rendered with Cycles, headless:

    blender -b --factory-startup --python pass2_sheet.py -- --out Renders/Shuriken/style_comparison.png
"""
import json
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUT = Path(argv[argv.index("--out") + 1] if "--out" in argv else PROJ / "Renders" / "Shuriken" / "style_comparison.png")
REF_DIR = PROJ / "WorkFiles" / "shuriken" / "style_reference"
REPORTS = PROJ / "WorkFiles" / "shuriken"
RENDERS = PROJ / "Renders" / "Shuriken"
FORMS = [("four_point", "FOUR-POINT  SM_Shuriken_FourPoint  (97 mm, 3.0 mm)"),
         ("eight_point", "EIGHT-POINT  SM_Shuriken_EightPoint  (100 mm, 2.5 mm)"),
         ("square_plate", "SENBAN  SM_Shuriken_SquarePlate  (107.8 mm diag, 1.9 mm)")]

PANEL_W, PANEL_H = 1.6, 0.9
GAP_X, GAP_Y = 0.10, 0.10
BANNER = 0.16
HEADER, FOOTER = 0.12, 0.40
COLUMNS = 1 + len(FORMS)
SHEET_W = COLUMNS * PANEL_W + (COLUMNS + 1) * GAP_X
SHEET_H = BANNER + HEADER + 2 * PANEL_H + GAP_Y + FOOTER + 2 * GAP_Y
PX_PER_UNIT = 600


def emission(name, colour=(1.0, 1.0, 1.0), image=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    if image is not None:
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(image), check_existing=False)
        tex.image.colorspace_settings.name = "sRGB"
        tex.interpolation = "Cubic"
        tree.links.new(tex.outputs["Color"], emit.inputs["Color"])
    else:
        emit.inputs["Color"].default_value = (*colour, 1.0)
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def plane(name, x, y, w, h, material, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(x + 0.5 * w, y + 0.5 * h, z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (w, h, 1.0)
    obj.data.materials.append(material)
    return obj


def text(name, body, x, y, size, colour=(0.92, 0.92, 0.90), z=0.002):
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = "LEFT"
    curve.align_y = "TOP"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (x, y, z)
    obj.data.materials.append(emission(f"M_{name}", colour))
    return obj


def label(name, body, x, y, size, width):
    """Text on a dark box, for the panel corners."""
    plane(f"{name}_box", x, y - size * 1.45, width, size * 1.45, emission(f"M_{name}_box", (0.03, 0.03, 0.035)), z=0.001)
    text(name, body, x + 0.2 * size, y - 0.2 * size, size, (0.95, 0.95, 0.93))


def form_lines(form):
    r = json.loads((REPORTS / f"{form}_report.json").read_text(encoding="utf-8"))
    m = r["measured"]
    g = m.get("grind") or {}
    rs = r.get("render_stats") or {}
    hero = (rs.get(f"{form}_persp") or {}).get("object_luminance") or {}
    top = (rs.get(f"{form}_top") or {}).get("object_luminance") or {}
    ec = (r.get("engine_check") or {}).get("status")
    rng = m.get("ground_mass_vs_study_range") or {}
    width = g.get("grind_width_mm")
    return [
        f"knife grind {g['grind_angle_deg']['area_weighted_mean']:.1f} deg/side, {width:.2f} mm wide, land "
        f"{g['edge_land_mm']['max']:.2f} mm, tip radius {g['tip_radius_mm']:.3f} mm",
        f"mass: outline {m['outline_mass_g']:.2f} g (target {m['mass_target_g']:.0f} +-2, gate "
        f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'})   ground {m['ground_mass_g']:.2f} g "
        f"(study {rng.get('study_min_max_g', ['?', '?'])[0]:g}-{rng.get('study_min_max_g', ['?', '?'])[1]:g} g)",
        f"hero lum mean {hero.get('mean', float('nan')):.3f} p50 {hero.get('p50', float('nan')):.3f}   top lum mean "
        f"{top.get('mean', float('nan')):.3f} p50 {top.get('p50', float('nan')):.3f}",
        f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
        f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   plan silhouette = pass 1",
    ]


def ref_lines():
    stats = json.loads((REF_DIR / "ref_rig_stats.json").read_text(encoding="utf-8"))["scaled100"]
    hero, top = stats["hero"]["object_luminance"], stats["top"]["object_luminance"]
    return [
        "study-only third-party six-point (197 mm, 2.48 mm; licence unknown, never shipped),",
        f"scaled to {stats['span_mm'][1]:.0f} mm and rendered with its own maps through shuriken_lib.render",
        f"hero lum mean {hero['mean']:.3f} p50 {hero['p50']:.3f}   top lum mean {top['mean']:.3f} p50 {top['p50']:.3f}",
        "knife bevels (~38 deg) to a thin bright crest, wear on the bevels, cavity grime, micro-scratches",
    ]


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = int(SHEET_W * PX_PER_UNIT)
scene.render.resolution_y = int(SHEET_H * PX_PER_UNIT)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
world = bpy.data.worlds.new("W_Sheet")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)

plane("Backdrop", 0.0, 0.0, SHEET_W, SHEET_H, emission("M_Backdrop", (0.055, 0.056, 0.060)), z=-0.001)
text("Banner", "Shuriken pack, restyle pass 2 (knife grind): the reference and every form through the SAME gallery "
     "rig, baked maps only, 2026-09-18", GAP_X, SHEET_H - GAP_Y + 0.02, 0.07, (0.97, 0.97, 0.95))
columns = [("REFERENCE (your downloaded asset, same rig)", REF_DIR / "ref_rig_scaled100_persp.png",
            REF_DIR / "ref_rig_scaled100_top.png", ref_lines())]
columns += [(title, RENDERS / f"{form}_persp.png", RENDERS / f"{form}_top.png", form_lines(form)) for form, title in FORMS]
for col, (title, hero, top, lines) in enumerate(columns):
    x = GAP_X + col * (PANEL_W + GAP_X)
    y_top = SHEET_H - GAP_Y - BANNER
    accent = (0.98, 0.80, 0.35) if col == 0 else (0.75, 0.85, 1.0)
    text(f"Title{col}", title, x, y_top, 0.046, accent)
    y_hero = y_top - HEADER - PANEL_H
    plane(f"Hero{col}", x, y_hero, PANEL_W, PANEL_H, emission(f"M_Hero{col}", image=hero))
    label(f"HeroLabel{col}", "hero (persp)", x + 0.015, y_hero + PANEL_H - 0.015, 0.042, 0.36)
    y_topv = y_hero - GAP_Y - PANEL_H
    plane(f"Top{col}", x, y_topv, PANEL_W, PANEL_H, emission(f"M_Top{col}", image=top))
    label(f"TopLabel{col}", "top (spec)", x + 0.015, y_topv + PANEL_H - 0.015, 0.042, 0.31)
    for i, line in enumerate(lines):
        text(f"Line{col}_{i}", line, x + 0.01, y_topv - 0.05 - i * 0.075, 0.029)

cam_data = bpy.data.cameras.new("SheetCam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = max(SHEET_W, SHEET_H * scene.render.resolution_x / scene.render.resolution_y)
cam = bpy.data.objects.new("SheetCam", cam_data)
scene.collection.objects.link(cam)
cam.location = (0.5 * SHEET_W, 0.5 * SHEET_H, 5.0)
scene.camera = cam
OUT.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(OUT)
bpy.ops.render.render(write_still=True)
print("PASS2_SHEET", OUT, scene.render.resolution_x, scene.render.resolution_y)
