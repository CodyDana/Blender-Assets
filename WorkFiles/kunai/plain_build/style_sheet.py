"""Comparison sheet, the PLAIN KUNAI build (library 3.10): the reference next to every form, hero + top - a new column
for SM_Kunai_Plain, the pack's first knife.

Copied from WorkFiles/shuriken/hooked_cross_maint/style_sheet.py by WorkFiles/kunai/plain_build/make_style_sheet.py; only
the banner, the hooked cross's title (no longer the newest) and the new column with its knife footer lines are new.  The
kunai's top view is drawn at 5.0 px/mm (its own 0.18 m frame; the stars' at 6.9 px/mm), which its title says.

(Hooked-cross maintenance history follows.)  Comparison sheet, hooked-cross MAINTENANCE (library 3.9.1).

Copied from hooked_cross/style_sheet.py; only the banner, the hooked cross column title (revision 2, no longer NEW) and
its handedness footer line (it now also reports the texture-sheet gate) changed.

(Hooked-cross build history follows.)  Comparison sheet, hooked-cross build (library 3.9.0): a new column
for SM_Shuriken_HookedCross, the pack's first outline plate.

Copied from spike_maint/style_sheet.py; only the banner, the new column and its footer lines are new (the hooked
cross's line gives the blade grind and its extent, the masses, and the handedness gate on the presented +Z face).
Its plan silhouette is checked against its own un-ground outline (hooked_cross/silhouette_ref.py).

(Spike maintenance history follows.)  Comparison sheet, spike maintenance (library 3.8.1).

Copied from spike/style_sheet.py (the spike build's sheet); only the banner, the spike column title (no longer
NEW) and the bar's luminance line changed: it now gives the coat pixels, the side faces (gated against the anchor
forms' walls in 3.8.1) and the side faces' isolated dark-dot count (render gate hero_bar_walls).

(Spike build history follows.)  Comparison sheet, spike build (library 3.8.0): a new column for
SM_Shuriken_Spike, the pack's first bar.

Copied from six_point_maint/style_sheet.py; only the banner, the spike column and its footer lines are new
(a bar has no knife grind: its line gives the point, the tip radius, the arris round and the centre of mass;
its luminance line gives the coat pixels the like-with-like gates read beside the whole object).  The spike's
plan silhouette is checked against the same bar with square arrises (spike/silhouette_ref.py).

(Six-point maintenance history follows.)

Copied from six_point/style_sheet_six.py (the six-point build's sheet); only the banner and the six-point
column title changed (the six-point is finished now, not NEW).

Copied from restyle_pass2/maint/pass2b_sheet.py (the sheet the restyle shipped) with one new column for
SM_Shuriken_SixPoint; everything else - layout, footer metrics, reference column - is that script's.
The plan-silhouette line is per form: the frozen forms against their restyle-pass-1 meshes, the six-point
against its own un-ground outline (six_point/silhouette_ref.py).

Same layout as restyle_pass2/pass2_sheet.py; the footer adds the visual metrics the same-rig review used,
measured by maint/visual_metrics.py on these very PNGs (--metrics), and the plan-silhouette result
(--silhouette, restyle_pass2/silhouette_check.py output).

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
OUT = Path(argv[argv.index("--out") + 1] if "--out" in argv else PROJ / "Renders" / "Shuriken" / "style_comparison.png").resolve()   # absolute: a relative render path lands at the drive root
REF_DIR = PROJ / "WorkFiles" / "shuriken" / "style_reference"
REPORTS = Path(argv[argv.index("--reports") + 1]) if "--reports" in argv else PROJ / "WorkFiles" / "shuriken"
METRICS = json.loads(Path(argv[argv.index("--metrics") + 1]).read_text(encoding="utf-8")) if "--metrics" in argv else {}
SILHOUETTE = (json.loads(Path(argv[argv.index("--silhouette") + 1]).read_text(encoding="utf-8"))
              if "--silhouette" in argv else {})
RENDERS = Path(argv[argv.index("--renders") + 1]) if "--renders" in argv else PROJ / "Renders" / "Shuriken"
COAT = (json.loads(Path(argv[argv.index("--coat") + 1]).read_text(encoding="utf-8"))   # spike/coat_interior_metrics.py
        if "--coat" in argv else {})
FORMS = [("four_point", "FOUR-POINT  SM_Shuriken_FourPoint  (97 mm, 3.0 mm)"),
         ("eight_point", "EIGHT-POINT  SM_Shuriken_EightPoint  (100 mm, 2.5 mm)"),
         ("square_plate", "SENBAN  SM_Shuriken_SquarePlate  (107.8 mm diag, 1.9 mm)"),
         ("six_point", "SIX-POINT  SM_Shuriken_SixPoint  (98 mm, 2.0 mm)"),
         ("spike", "SPIKE  SM_Shuriken_Spike  (150 mm, 6 mm square, rev 2)"),
         ("hooked_cross", "HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm, rev 2)"),
         ("kunai_plain", "NEW  KUNAI  SM_Kunai_Plain  (280 mm, 5 mm stock; top view at 5.0 px/mm)")]

PANEL_W, PANEL_H = 1.6, 0.9
GAP_X, GAP_Y = 0.10, 0.10
BANNER = 0.16
HEADER, FOOTER = 0.12, 0.52
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
    mt, mh = METRICS.get(f"{form}_top") or {}, METRICS.get(f"{form}_hero") or {}
    objs = {k: v for k, v in (SILHOUETTE.get("objects") or {}).items() if k.startswith(r["asset"] + "_LOD")}
    same = bool(objs) and all(v.get("unchanged") for v in objs.values())
    ref = {"six_point": "un-ground outline", "spike": "square-arris bar",
           "hooked_cross": "un-ground outline"}.get(form, "pass 1")
    sil = f"plan silhouette = {ref}" if same else "plan silhouette: see silhouette json"
    if r.get("geometry") == "kunai":
        coat_h = (rs.get(f"{form}_persp") or {}).get("coat_luminance") or {}
        coat_t = (rs.get(f"{form}_top") or {}).get("coat_luminance") or {}
        wrap_h = (rs.get(f"{form}_persp") or {}).get("wrap_luminance") or {}
        mk = r.get("mass_check_kunai") or {}
        sh = m.get("shoulder") or {}
        gw = g.get("grind_width_mm") or {}
        cc = r.get("collision_choice") or {}
        return [
            f"knife grind {g['grind_angle_deg']:.0f} deg/side, land {g['edge_land_mm']:.2f} mm, tip radius "
            f"{m.get('tip_radius_mm') or float('nan'):.3f} mm, grind {min(gw.values()):.2f}-{max(gw.values()):.2f} mm wide; "
            f"0.7 mm polished band + satin; apex {m['apex_x_mm']:.1f} mm",
            f"shoulder: 16 mm blade base on the 16 x 5 mm neck, {sh.get('runout_mm', 3):g} mm run-out into a "
            f"{sh.get('chamfer_mm', 0.45):g} mm chamfer, V plunge at x {sh.get('plunge_ridge_x_mm', float('nan')):.1f} mm",
            f"steel: un-ground {m['outline_mass_g']:.1f} g (study basis {m['mass_target_g']:.1f} +-2, gate "
            f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'}), finished {m['steel_ground_mass_g']:.1f} g + wrap "
            f"{m['wrap_mass_g']:.1f} g = {m['assembled_mass_g']:.1f} g",
            f"coat (gated) hero {coat_h.get('mean', float('nan')):.3f}/{coat_h.get('p50', float('nan')):.3f} top "
            f"{coat_t.get('mean', float('nan')):.3f}/{coat_t.get('p50', float('nan')):.3f}   whole hero "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}   wrap p50 "
            f"{wrap_h.get('p50', float('nan')):.3f}",
            f"pivot = mass centre x {m['pivot_design_x_mm']:.1f} mm (by volume {m['masses_finished']['centre_if_uniform_density_x_mm']:.1f}); "
            f"2 hulls ({cc.get('two_hulls_mm3', 0) / 1000:.1f} vs one {cc.get('one_hull_mm3', 0) / 1000:.1f} cm3); "
            f"blank 72 x 12 mm lettering band",
            f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
            f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   slots steel + wrap",
        ]
    if r.get("geometry") == "outline_plate":
        ext = (m.get("grind_extent") or {}).get("design") or {}
        hand = r.get("handedness") or {}
        gal = r.get("gallery_presented_face") or {}
        ctl = (hand.get("negative_control") or {})
        return [
            f"blade edge peak p90 {mt.get('edge_peak_p90', float('nan')):.2f} (arm edges: chamfer + wall)   bright bevel "
            f"hero {100 * mh.get('bright_facet_share', float('nan')):.1f} %   fine dark / bright "
            f"{mt.get('fine_dark', float('nan')):.4f} / {mt.get('fine_bright', float('nan')):.4f}",
            f"knife grind on the hook blades {g['grind_angle_deg']['area_weighted_mean']:.1f} deg/side, {width:.2f} mm wide, "
            f"land {g['edge_land_mm']['max']:.2f} mm, tip radius {g['tip_radius_mm']:.3f} mm; elsewhere 0.45 mm chamfer + wall",
            f"grind extent: back arc {(ext.get('back_arc') or {}).get('full_knife_from_tip_mm', float('nan')):.1f} mm + 3 mm "
            f"run-out to the shoulder, inner edge {(ext.get('inner_edge') or {}).get('full_knife_from_tip_mm', float('nan')):.1f}"
            f" mm + 3 mm to the fillet",
            f"mass: outline {m['outline_mass_g']:.2f} g (photo outline 37.09 +-2, gate "
            f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'})   ground {m['ground_mass_g']:.2f} g   hero lum "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}  top {top.get('mean', float('nan')):.3f}/"
            f"{top.get('p50', float('nan')):.3f}",
            f"handedness (left-facing on +Z) {'PASS' if hand.get('passed') else 'FAIL'}, mirrored control "
            f"{'caught' if ctl.get('caught') else 'MISSED'}; gallery +Z {'PASS' if gal.get('passed') else 'FAIL'}; texture "
            f"sheets +Z {'PASS' if (r.get('texture_handedness') or {}).get('passed') else 'FAIL'}   "
            f"photo outline IoU {(r.get('photo_check') or {}).get('analytic_outline', {}).get('iou', float('nan')):.5f}",
            f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
            f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   {sil}",
        ]
    if r.get("geometry") == "bar":
        coat_h = (rs.get(f"{form}_persp") or {}).get("coat_luminance") or {}
        coat_t = (rs.get(f"{form}_top") or {}).get("coat_luminance") or {}
        side = (rs.get(f"{form}_persp") or {}).get("bar_wall_luminance") or {}
        dots = (((rs.get(f"{form}_persp") or {}).get("bar_wall_dots") or {}).get("30pct") or {}).get("dots_per_10k_px",
                                                                                                    float("nan"))
        ci = COAT.get(f"{form}_top") or {}
        stars = [v for k, v in COAT.items() if k.endswith("_top") and k != f"{form}_top"
                 and not k.startswith("reference")] or [{"fine_dark": float("nan"), "core_mean": float("nan")}]
        return [
            f"visible bright edge {mt.get('edge_bright_band_mm', float('nan')):.2f} mm, peak "
            f"{mt.get('edge_peak_p50', float('nan')):.2f}   (bar: the arris round + worn band)",
            f"coat interior (edges excluded): fine dark / bright {ci.get('fine_dark', float('nan')):.4f} / "
            f"{ci.get('fine_bright', float('nan')):.4f}, mean {ci.get('core_mean', float('nan')):.3f}   (stars "
            f"{min(v['fine_dark'] for v in stars):.4f}-{max(v['fine_dark'] for v in stars):.4f}, "
            f"{min(v['core_mean'] for v in stars):.3f}-{max(v['core_mean'] for v in stars):.3f})",
            f"point {m['point_length_mm']:.1f} mm, {m['point_included_deg']:.2f} deg incl., tip radius {m['tip_radius_mm']:.3f} mm;"
            f"  arris round {m['arris_round_mm']:.2f} mm;  CoM {abs(m['centre_of_mass_from_middle_mm']):.2f} mm toward butt",
            f"mass: outline {m['outline_mass_g']:.2f} g (target {m['mass_target_g']:.0f} +-2, gate "
            f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'})   finished {m['ground_mass_g']:.2f} g "
            f"(study {rng.get('study_min_max_g', ['?', '?'])[0]:g}-{rng.get('study_min_max_g', ['?', '?'])[1]:g} g)",
            f"coat (gated) hero {coat_h.get('mean', float('nan')):.3f}/{coat_h.get('p50', float('nan')):.3f} top "
            f"{coat_t.get('mean', float('nan')):.3f}/{coat_t.get('p50', float('nan')):.3f}   side p50 "
            f"{side.get('p50', float('nan')):.3f} (walls 0.268)   side dots {dots:.1f}/10k   whole hero "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}",
            f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
            f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   {sil}",
        ]
    return [
        f"visible bright edge {mt.get('edge_bright_band_mm', float('nan')):.2f} mm, peak {mt.get('edge_peak_p50', float('nan')):.2f}"
        f"   bright bevel share hero {100 * mh.get('bright_facet_share', float('nan')):.1f} % (geometric facets "
        f"{100 * mh.get('facet_share', float('nan')):.0f} %)",
        f"face: large-scale var {mt.get('large_scale_var', float('nan')):.4f}   fine dark / bright "
        f"{mt.get('fine_dark', float('nan')):.4f} / {mt.get('fine_bright', float('nan')):.4f}   hole ring "
        f"{mt.get('hole_ring_range', float('nan')):.3f}",
        f"knife grind {g['grind_angle_deg']['area_weighted_mean']:.1f} deg/side, {width:.2f} mm wide, land "
        f"{g['edge_land_mm']['max']:.2f} mm, tip radius {g['tip_radius_mm']:.3f} mm",
        f"mass: outline {m['outline_mass_g']:.2f} g (target {m['mass_target_g']:.0f} +-2, gate "
        f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'})   ground {m['ground_mass_g']:.2f} g "
        f"(study {rng.get('study_min_max_g', ['?', '?'])[0]:g}-{rng.get('study_min_max_g', ['?', '?'])[1]:g} g)",
        f"hero lum mean {hero.get('mean', float('nan')):.3f} p50 {hero.get('p50', float('nan')):.3f}   top lum mean "
        f"{top.get('mean', float('nan')):.3f} p50 {top.get('p50', float('nan')):.3f}",
        f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
        f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   {sil}",
    ]


def ref_lines():
    stats = json.loads((REF_DIR / "ref_rig_stats.json").read_text(encoding="utf-8"))["scaled100"]
    hero, top = stats["hero"]["object_luminance"], stats["top"]["object_luminance"]
    mt, mh = METRICS.get("reference_top") or {}, METRICS.get("reference_hero") or {}
    return [
        f"visible bright edge {mt.get('edge_bright_band_mm', float('nan')):.2f} mm, peak {mt.get('edge_peak_p50', float('nan')):.2f}"
        f"   bright bevel share hero {100 * mh.get('bright_facet_share', float('nan')):.1f} % (geometric facets "
        f"{100 * mh.get('facet_share', float('nan')):.0f} %)",
        f"face: large-scale var {mt.get('large_scale_var', float('nan')):.4f}   fine dark / bright "
        f"{mt.get('fine_dark', float('nan')):.4f} / {mt.get('fine_bright', float('nan')):.4f}   hole ring "
        f"{mt.get('hole_ring_range', float('nan')):.3f}",
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
text("Banner", "Shuriken pack with the plain kunai (library 3.10.1): the reference and every form (four-point, "
     "eight-point, senban, six-point, spike, hooked cross, NEW kunai - its hero points the blade at the viewer, its top "
     "view has its own frame) through the SAME gallery rig, baked maps only, 2026-09-19", GAP_X,
     SHEET_H - GAP_Y + 0.02, 0.062, (0.97, 0.97, 0.95))
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
