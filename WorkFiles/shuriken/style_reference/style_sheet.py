"""Comparison sheet: the reference hero + top on the left, each pack form's hero + top to the right.

Every panel is labelled and carries the key STYLE_TARGET metrics measured on that form's baked
maps (style_metrics.py) under it.  Built as a Blender scene (emissive image planes and text) and
rendered with Cycles, flat, so it works headless.

The reference column MUST come from ref_on_rig.py (the study-only LP rendered through the pack's
own shuriken_lib.render rig) and ``--ref-stats`` its ref_rig_stats.json, so the two sides of the
sheet share world, lamps, cameras, view transform and the image_stats measurement; the first
sheet's reference column came from a scratch rig and its numbers misled.

    blender -b --factory-startup --python style_sheet.py -- --out Renders/Shuriken/style_comparison.png \
        --ref-hero <png> --ref-top <png> --ref-metrics <json> --ref-stats <ref_rig_stats.json> [--ref-tag scaled100] \
        --form four_point <hero.png> <top.png> <metrics.json> <report.json> [--form ...]
"""
import json
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def absolute(value):
    """Blender resolves relative image paths against the (absent) blend file: make them absolute."""
    return str(Path(value).resolve()) if value else value


OUT = Path(arg("--out", "style_comparison.png")).resolve()
REF_HERO, REF_TOP, REF_METRICS = absolute(arg("--ref-hero")), absolute(arg("--ref-top")), absolute(arg("--ref-metrics"))
REF_STATS, REF_TAG = absolute(arg("--ref-stats")), arg("--ref-tag", "scaled100")
forms = []
for i, token in enumerate(argv):
    if token == "--form":
        name, *paths = argv[i + 1:i + 6]
        forms.append((name, *[absolute(p) for p in paths]))
TITLES = {"four_point": "SM_Shuriken_FourPoint  (97 mm, 3.0 mm)", "eight_point": "SM_Shuriken_EightPoint  (100 mm, 2.5 mm)",
          "square_plate": "SM_Shuriken_SquarePlate  (108 mm diag, 1.9 mm)"}

PANEL_W, PANEL_H = 1.6, 0.9          # scene units per image (16:9)
GAP_X, GAP_Y = 0.10, 0.10
HEADER, FOOTER = 0.26, 0.75          # header band (title) and metric block under the two images
COLUMN_H = HEADER + 2 * PANEL_H + GAP_Y + FOOTER
COLUMNS = 1 + len(forms)
SHEET_W = COLUMNS * PANEL_W + (COLUMNS + 1) * GAP_X
SHEET_H = COLUMN_H + 2 * GAP_Y
PX_PER_UNIT = 720                    # 1152 px per hero panel


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


def text(name, body, x, y, size, colour=(0.92, 0.92, 0.90), align="LEFT"):
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.align_y = "TOP"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (x, y, 0.002)
    obj.data.materials.append(emission(f"M_{name}", colour))
    return obj


def metric_lines(m):
    if not m:
        return ["metrics: n/a"]
    bc, ro, sc = m["basecolor_stored"], m["roughness"], m["scratches"]
    lines = [
        f"coat p50 stored {m['coat_p50_stored']:.3f}  (linear {m['coat_p50_linear']:.3f})",
        f"border / interior {m['border_over_interior']:.2f}   plate p05-p95 {bc['plate']['p05']:.2f}-{bc['plate']['p95']:.2f}",
        f"metallic p50 {m['metallic']['all']['p50']:.2f}   non-metal {100 * m['metallic']['fraction_below_0.5']:.1f} %",
        f"roughness p50 interior {ro['interior']['p50']:.2f}  border {ro['border']['p50']:.2f}  wall {ro['wall']['p50'] if ro['wall'] else float('nan'):.2f}",
        f"scratches plate {100 * sc['plate_fraction']:.1f} % (coat interior {100 * (sc.get('coat_interior_fraction') or 0):.2f} %)  "
        f"walls {100 * (sc['wall_fraction'] or 0):.1f} %  gain +{sc['mean_brightness_gain']:.2f}",
        f"pits {100 * m['dark_pits']['fraction_of_mask']:.2f} % (coat interior {100 * (m['dark_pits'].get('coat_interior_fraction') or 0):.2f} %)"
        f"   blue-red {m['blue_minus_red']['mean']:+.3f}   {m['px_per_cm_at_analysis']:.0f} px/cm @ {m['analysis_px']}",
    ]
    return lines


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = False
scene.render.resolution_x = int(SHEET_W * PX_PER_UNIT)
scene.render.resolution_y = int(SHEET_H * PX_PER_UNIT)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.display_settings.display_device = "sRGB"
world = bpy.data.worlds.new("W_Sheet")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)

plane("Backdrop", 0.0, 0.0, SHEET_W, SHEET_H, emission("M_Backdrop", (0.055, 0.056, 0.060)), z=-0.001)
columns = [("REFERENCE  (third-party asset through the PACK rig, its maps; study only)", REF_HERO, REF_TOP, REF_METRICS, None)]
ref_stats = (load_json(REF_STATS) or {}).get(REF_TAG) if REF_STATS else None
columns += [(TITLES.get(f[0], f[0]), f[1], f[2], f[3], f[4]) for f in forms]
for col, (title, hero, top, metrics_path, report_path) in enumerate(columns):
    x = GAP_X + col * (PANEL_W + GAP_X)
    y_top = SHEET_H - GAP_Y
    accent = (0.95, 0.80, 0.35) if col == 0 else (0.75, 0.85, 1.0)
    text(f"Title{col}", title, x, y_top - 0.02, 0.058, accent)
    y_hero = y_top - HEADER - PANEL_H
    plane(f"Hero{col}", x, y_hero, PANEL_W, PANEL_H, emission(f"M_Hero{col}", image=hero))
    text(f"HeroLabel{col}", "hero (persp)", x + 0.02, y_hero + PANEL_H - 0.02, 0.04, (0.85, 0.85, 0.85))
    y_topv = y_hero - GAP_Y - PANEL_H
    plane(f"Top{col}", x, y_topv, PANEL_W, PANEL_H, emission(f"M_Top{col}", image=top))
    text(f"TopLabel{col}", "top (spec)", x + 0.02, y_topv + PANEL_H - 0.02, 0.04, (0.85, 0.85, 0.85))
    lines = metric_lines(load_json(metrics_path))
    report = load_json(report_path) if report_path else None
    if report:
        m = report["measured"]
        rs = report.get("render_stats", {})
        hero_mean = (rs.get(f"{report['form']}_persp", {}).get("object_luminance") or {}).get("mean")
        top_mean = (rs.get(f"{report['form']}_top", {}).get("object_luminance") or {}).get("mean")
        chamfer = m.get("chamfer_width_measured_mm") or m.get("facet_plan_width_mm")
        lines.append(f"chamfer {chamfer:.2f} mm  land {m['edge_land_mm']:.2f} mm  mass {m['mass_g']:.1f} g "
                     f"(target {m['mass_target_g']:.0f})  LODs {'/'.join(str(t) for t in report['lod_triangles'])}")
        lines.append(f"hero mean lum {hero_mean:.3f}   top mean lum {top_mean:.3f}   qa {'pass' if report['qa']['passed'] else 'FAIL'}")
    elif col == 0:
        if ref_stats:
            hero_l = (ref_stats.get("hero") or {}).get("object_luminance") or {}
            top_l = (ref_stats.get("top") or {}).get("object_luminance") or {}
            lines.append(f"197 mm six-point, 2.48 mm, 3408 tris; rendered at {ref_stats.get('span_mm', ['?', '?'])[1]} mm "
                         f"({REF_TAG}) through shuriken_lib.render")
            lines.append(f"hero mean lum {hero_l.get('mean', float('nan')):.3f} (p50 {hero_l.get('p50', float('nan')):.3f})"
                         f"   top mean lum {top_l.get('mean', float('nan')):.3f} (p50 {top_l.get('p50', float('nan')):.3f})")
        else:
            lines.append("197 mm six-point, 2.48 mm, 3408 tris; ref_rig_stats.json not given")
    y_text = y_topv - 0.05
    for i, line in enumerate(lines):
        text(f"Metric{col}_{i}", line, x + 0.01, y_text - i * 0.082, 0.046)

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
print("STYLE_SHEET", OUT, scene.render.resolution_x, scene.render.resolution_y)
