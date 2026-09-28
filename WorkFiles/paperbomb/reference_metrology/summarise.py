# -*- coding: utf-8 -*-
import json, sys, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "typography_raw.json")
d = json.load(open(p, encoding="utf-8"))
M = d["measurements"]
keys = [k for k in ("V1", "V2", "OURS_ART", "OURS_ATLAS") if k in M]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
sel = args[0] if args else "all"


def g(o, *path, default=None):
    for k in path:
        if o is None:
            return default
        o = o.get(k) if isinstance(o, dict) else None
    return default if o is None else o


def row(label, fn):
    vals = []
    for k in keys:
        try:
            v = fn(M[k])
        except Exception:
            v = None
        vals.append("--" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v)))
    print(f"  {label:<44}" + "".join(f"{v:>15}" for v in vals))


print("ELEMENT".ljust(46) + "".join(f"{k:>15}" for k in keys))

if sel in ("all", "ring"):
    print("\n--- RED RING ---")
    row("centre x (mm)", lambda m: g(m, 'ring', 'centre', 'x_mm'))
    row("centre y (mm)", lambda m: g(m, 'ring', 'centre', 'y_mm'))
    row("centre x (frac)", lambda m: g(m, 'ring', 'centre', 'x_frac'))
    row("centre y (frac)", lambda m: g(m, 'ring', 'centre', 'y_frac'))
    row("r mid mean (mm)", lambda m: g(m, 'ring', 'r_mid_mean_mm'))
    row("r inner mean (mm)", lambda m: g(m, 'ring', 'r_inner_mean_mm'))
    row("r outer mean (mm)", lambda m: g(m, 'ring', 'r_outer_mean_mm'))
    row("semi-major (mm)", lambda m: g(m, 'ring', 'ellipse', 'semi_major_mm'))
    row("semi-minor (mm)", lambda m: g(m, 'ring', 'ellipse', 'semi_minor_mm'))
    row("axis ratio b/a", lambda m: g(m, 'ring', 'ellipse', 'axis_ratio'))
    row("eccentricity", lambda m: g(m, 'ring', 'ellipse', 'eccentricity'))
    row("major axis deg", lambda m: g(m, 'ring', 'ellipse', 'major_axis_deg'))
    row("thickness mean (mm)", lambda m: g(m, 'ring', 'thickness_mm', 'mean'))
    row("thickness median (mm)", lambda m: g(m, 'ring', 'thickness_mm', 'median'))
    row("thickness p05 (mm)", lambda m: g(m, 'ring', 'thickness_mm', 'p05'))
    row("thickness p95 (mm)", lambda m: g(m, 'ring', 'thickness_mm', 'p95'))
    row("thickness max/min", lambda m: g(m, 'ring', 'thickness_mm', 'max_over_min'))
    row("thickness CV", lambda m: g(m, 'ring', 'thickness_mm', 'cv'))
    row("radial ink coverage mean", lambda m: g(m, 'ring', 'radial_ink_coverage', 'mean'))
    row("angular coverage", lambda m: g(m, 'ring', 'angular_coverage'))
    row("n angular gaps", lambda m: g(m, 'ring', 'n_angular_gaps'))
    row("biggest gap (deg)", lambda m: g(m, 'ring', 'angular_gaps', default=[{}])[0].get('width_deg') if g(m, 'ring', 'angular_gaps') else None)
    row("frac angles 1 band", lambda m: g(m, 'ring', 'frac_angles_with_1_band'))
    row("frac angles >=2 bands", lambda m: g(m, 'ring', 'frac_angles_with_2plus_bands'))
    row("frac angles >=3 bands", lambda m: g(m, 'ring', 'frac_angles_with_3plus_bands'))
    row("ring ink area (mm2)", lambda m: g(m, 'ring', 'ring_ink_area_mm2'))
    row("lap thickness at start (mm)", lambda m: g(m, 'ring', 'lap_ends', 'thickness_at_start_mm'))
    row("lap thickness at end (mm)", lambda m: g(m, 'ring', 'lap_ends', 'thickness_at_end_mm'))
    row("lap coverage at start", lambda m: g(m, 'ring', 'lap_ends', 'coverage_at_start'))
    row("lap coverage at end", lambda m: g(m, 'ring', 'lap_ends', 'coverage_at_end'))

if sel in ("all", "centre"):
    print("\n--- CENTRE GLYPH 爆 ---")
    for f, lab in (('x0_mm', 'bbox x0 mm'), ('x1_mm', 'bbox x1 mm'), ('y0_mm', 'bbox y0 mm'),
                   ('y1_mm', 'bbox y1 mm'), ('w_mm', 'bbox w mm'), ('h_mm', 'bbox h mm'),
                   ('cx_mm', 'bbox cx mm'), ('cy_mm', 'bbox cy mm'), ('w_over_h', 'w/h')):
        row(lab, lambda m, f=f: g(m, 'centre_glyph', 'bbox', f))
    row("mass-box(90%) w mm", lambda m: g(m, 'centre_glyph', 'mass_box_90', 'w_mm'))
    row("mass-box(90%) h mm", lambda m: g(m, 'centre_glyph', 'mass_box_90', 'h_mm'))
    row("mass-box(90%) w/h", lambda m: g(m, 'centre_glyph', 'mass_w_over_h'))
    row("ink area mm2", lambda m: g(m, 'centre_glyph', 'ink_area_mm2'))
    row("fill of bbox", lambda m: g(m, 'centre_glyph', 'fill_of_bbox'))
    row("n components", lambda m: g(m, 'centre_glyph', 'n_components'))
    row("stroke max (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_max_mm'))
    row("stroke mean ridge (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_mean_ridge_mm'))
    row("stroke median ridge (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_median_ridge_mm'))
    row("stroke p05 ridge (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_p05_ridge_mm'))
    row("stroke p95 ridge (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_p95_ridge_mm'))
    row("stroke ribbon mean (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'stroke_ribbon_mean_mm'))
    row("thick/thin p95/p05", lambda m: g(m, 'centre_glyph', 'stroke', 'thick_thin_ratio'))
    row("thick/thin max/min", lambda m: g(m, 'centre_glyph', 'stroke', 'thick_thin_ratio_maxmin'))
    row("vstroke median (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'vstroke_median_mm_x'))
    row("hstroke median (mm)", lambda m: g(m, 'centre_glyph', 'stroke', 'hstroke_median_mm_y'))
    print("  -- in ring --")
    row("ring mean diam (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'ring_mean_diameter_mm'))
    row("glyph w / ring diam", lambda m: g(m, 'centre_glyph', 'in_ring', 'glyph_bbox_w_over_ring_diam'))
    row("glyph h / ring diam", lambda m: g(m, 'centre_glyph', 'in_ring', 'glyph_bbox_h_over_ring_diam'))
    row("glyph diag / ring diam", lambda m: g(m, 'centre_glyph', 'in_ring', 'glyph_diag_over_ring_diam'))
    row("glyph area / ring inner area", lambda m: g(m, 'centre_glyph', 'in_ring', 'glyph_area_over_ring_inner_area'))
    row("bbox offset x (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'bbox_centre_offset_mm')[0])
    row("bbox offset y (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'bbox_centre_offset_mm')[1])
    row("ink centroid offset x (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'ink_centroid_offset_mm')[0])
    row("ink centroid offset y (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'ink_centroid_offset_mm')[1])
    row("clear space min (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'clear_space_mm', 'min'))
    row("clear space median (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'clear_space_mm', 'median'))
    row("clear space mean (mm)", lambda m: g(m, 'centre_glyph', 'in_ring', 'clear_space_mm', 'mean'))
    row("frac angles glyph crosses ring", lambda m: g(m, 'centre_glyph', 'in_ring', 'frac_angles_glyph_crosses_ring_band'))

if sel in ("all", "flame"):
    print("\n--- FLAME EMBLEM ---")
    for f, lab in (('x0_mm', 'bbox x0 mm'), ('x1_mm', 'bbox x1 mm'), ('y0_mm', 'bbox y0 mm'),
                   ('y1_mm', 'bbox y1 mm'), ('w_mm', 'bbox w mm'), ('h_mm', 'bbox h mm'),
                   ('cx_mm', 'cx mm'), ('cy_mm', 'cy mm'), ('w_over_h', 'w/h')):
        row(lab, lambda m, f=f: g(m, 'flame_emblem', 'bbox', f))
    row("ink area mm2", lambda m: g(m, 'flame_emblem', 'ink_area_mm2'))
    row("fill of bbox", lambda m: g(m, 'flame_emblem', 'fill_of_bbox'))
    row("n components", lambda m: g(m, 'flame_emblem', 'n_components'))
    row("n tongues (top 46%)", lambda m: g(m, 'flame_emblem', 'n_tongues_top46pct'))
    row("n enclosed holes", lambda m: g(m, 'flame_emblem', 'n_enclosed_holes'))
    row("mirror IoU", lambda m: g(m, 'flame_emblem', 'mirror_symmetry', 'best_iou'))
    row("mirror verdict", lambda m: g(m, 'flame_emblem', 'mirror_symmetry', 'verdict'))
    row("stroke max (mm)", lambda m: g(m, 'flame_emblem', 'stroke', 'stroke_max_mm'))
    row("stroke mean ridge (mm)", lambda m: g(m, 'flame_emblem', 'stroke', 'stroke_mean_ridge_mm'))
    row("stroke p05 ridge (mm)", lambda m: g(m, 'flame_emblem', 'stroke', 'stroke_p05_ridge_mm'))
    row("thick/thin p95/p05", lambda m: g(m, 'flame_emblem', 'stroke', 'thick_thin_ratio'))

if sel in ("all", "cols"):
    for col in ('upper_left', 'upper_right', 'lower_right', 'lower_centre', 'lower_left'):
        k = 'column_' + col
        if not any(k in M[x] for x in keys):
            continue
        print(f"\n--- COLUMN {col} ---")
        row("n cells", lambda m, k=k: g(m, k, 'n_cells'))
        for f, lab in (('x0_mm', 'bbox x0 mm'), ('x1_mm', 'bbox x1 mm'), ('y0_mm', 'bbox y0 mm'),
                       ('y1_mm', 'bbox y1 mm'), ('w_mm', 'bbox w mm'), ('h_mm', 'bbox h mm'),
                       ('cx_mm', 'axis cx mm')):
            row(lab, lambda m, k=k, f=f: g(m, k, 'bbox', f))
        row("axis mean x (mm)", lambda m, k=k: g(m, k, 'axis', 'axis_mean_x_mm'))
        row("axis lean (deg from vert)", lambda m, k=k: g(m, k, 'axis', 'lean_deg_from_vertical'))
        row("advance mm [0]", lambda m, k=k: (g(m, k, 'advance_mm') or [None])[0])
        row("advance mm [1]", lambda m, k=k: (g(m, k, 'advance_mm') or [None, None])[1])
        row("gap mm [0]", lambda m, k=k: (g(m, k, 'gap_mm') or [None])[0])
        row("gap mm [1]", lambda m, k=k: (g(m, k, 'gap_mm') or [None, None])[1])
        for i in range(3):
            row(f"glyph[{i}] w mm", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'bbox', 'w_mm'))
            row(f"glyph[{i}] h mm", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'bbox', 'h_mm'))
            row(f"glyph[{i}] w/h", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'bbox', 'w_over_h'))
            row(f"glyph[{i}] cy mm", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'bbox', 'cy_mm'))
            row(f"glyph[{i}] stroke med mm", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'stroke', 'stroke_median_ridge_mm'))
            row(f"glyph[{i}] vstroke mm", lambda m, k=k, i=i: g((g(m, k, 'glyphs') or [None] * 4)[i] if len(g(m, k, 'glyphs') or []) > i else None, 'stroke', 'vstroke_median_mm_x'))

if sel in ("all", "seals"):
    for s in ('seal_big', 'seal_small'):
        print(f"\n--- {s.upper()} ---")
        for f, lab in (('x0_mm', 'outer x0 mm'), ('y0_mm', 'outer y0 mm'), ('w_mm', 'outer w mm'),
                       ('h_mm', 'outer h mm'), ('w_over_h', 'outer w/h')):
            row(lab, lambda m, s=s, f=f: g(m, s, 'outer_bbox', f))
        for f, lab in (('w_mm', 'inner w mm'), ('h_mm', 'inner h mm')):
            row(lab, lambda m, s=s, f=f: g(m, s, 'inner_bbox', f))
        for f in ('left', 'right', 'top', 'bottom'):
            row(f"frame stroke {f} mm", lambda m, s=s, f=f: g(m, s, 'frame_stroke_mm', f))
        row("fill of bbox", lambda m, s=s: g(m, s, 'fill_of_bbox'))
        row("interior red fill", lambda m, s=s: g(m, s, 'interior_red_fill'))
        row("n interior holes", lambda m, s=s: g(m, s, 'n_interior_holes'))
        row("n device islands", lambda m, s=s: g(m, s, 'n_device_islands'))
        row("device w mm", lambda m, s=s: g(m, s, 'device_bbox', 'w_mm'))
        row("device h mm", lambda m, s=s: g(m, s, 'device_bbox', 'h_mm'))
        row("device area mm2", lambda m, s=s: g(m, s, 'device_area_mm2'))
        row("device stroke med mm", lambda m, s=s: g(m, s, 'device_stroke', 'stroke_median_ridge_mm'))
        row("corner fill tl", lambda m, s=s: g(m, s, 'corner_fill', 'tl'))
        row("corner fill br", lambda m, s=s: g(m, s, 'corner_fill', 'br'))

if sel in ("all", "frame"):
    print("\n--- BORDER RULE ---")
    for side in ('left', 'right'):
        row(f"{side} rules x mm", lambda m, side=side: str([r['x_mm'] for r in (g(m, 'border_rule', side) or [])]))
        row(f"{side} rule widths mm", lambda m, side=side: str([r['width_mm'] for r in (g(m, 'border_rule', side) or [])]))
    for side in ('top', 'bottom'):
        row(f"{side} rules y mm", lambda m, side=side: str([r['y_mm'] for r in (g(m, 'border_rule', side) or [])]))
    print("\n--- SEGMENTATION / TAG ---")
    row("rect px w", lambda m: m['rectified_px'][0])
    row("rect px h", lambda m: m['rectified_px'][1])
    row("px/mm x", lambda m: m['px_per_mm_x'])
    row("px/mm y", lambda m: m['px_per_mm_y'])
    row("anisotropy y/x", lambda m: m['anisotropy_y_over_x'])
    row("paper luma p75 stored", lambda m: g(m, 'segmentation', 'paper_luma_p75_stored'))
    row("ink floor luma stored", lambda m: g(m, 'segmentation', 'ink_floor_luma_p005_stored'))
    row("black threshold stored", lambda m: g(m, 'segmentation', 'black_threshold_stored'))
    row("redness p99.5 stored", lambda m: g(m, 'segmentation', 'redness_p995_stored'))
    row("black coverage", lambda m: g(m, 'segmentation', 'black_coverage'))
    row("red coverage", lambda m: g(m, 'segmentation', 'red_coverage'))
    row("rotation applied deg", lambda m: g(m, 'rectification', 'rotation_deg_applied'))
    row("keystone vconv deg", lambda m: g(m, 'rectification', 'keystone_vertical_convergence_deg'))
    row("keystone hconv deg", lambda m: g(m, 'rectification', 'keystone_horizontal_convergence_deg'))
    row("width taper %", lambda m: g(m, 'rectification', 'width_taper_pct'))
    row("top band splits", lambda m: str(m.get('top_band_splits_mm')))
