# -*- coding: utf-8 -*-
"""Stage 4: write INK_NOTES.md from ink_colour.json, plus a debug schematic that
is drawn entirely from measured numbers (no reference pixels anywhere in it)."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

J = json.load(open(HERE + "/ink_colour.json", encoding="utf-8"))
M = J["measurements"]


def g(d, path, default=None):
    cur = d
    for p in path.split("/"):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


KEYS = [("V1", "V1"), ("V2", "V2"), ("OURS_basecolour", "OURS")]


def row(label, path, fmt="%.4g", unit=""):
    cells = []
    for k, _ in KEYS:
        v = g(M[k], path)
        if v is None:
            cells.append("-")
        elif isinstance(v, (int, float)):
            cells.append((fmt % v) + (" " + unit if unit else ""))
        elif isinstance(v, list):
            cells.append(", ".join(str(x) for x in v))
        else:
            cells.append(str(v))
    return "| %s | %s |" % (label, " | ".join(cells))


L = []
A = L.append
A("# Paper bomb: ink and colour metrology")
A("")
A("Measured 2026-09-19 against both reference images and against our shipped")
A("basecolour map. Machine-readable companion: `ink_colour.json` in this folder.")
A("")
A("**Legal / product note.** Every figure here is a measurement. No pixel of either")
A("reference was reproduced, traced, masked, thresholded, vectorised or otherwise")
A("derived into anything a build can consume. The rectified arrays live only in the")
A("session scratchpad. The only images written under the project are schematics")
A("drawn from these numbers, in `debug/`, prefixed `DEBUG_NEVER_SHIP`.")
A("")
A("## Conventions")
A("")
A("- Origin is the **tag's top-left paper corner**, not the image canvas. `u = x/W`,")
A("  `v = y/H`, and millimetres on the shipped 70.0 x 156.0 mm card via `u*70`, `v*156`.")
A("- **stored** = the 8-bit number in the PNG over 255 (sRGB-encoded). **linear** =")
A("  the sRGB EOTF applied. A PNG carries no colourspace tag, so this was pinned down")
A("  by decoding the IDAT directly and comparing against Blender's `Image.pixels`,")
A("  which returned the stored value to the last bit. Every hex here is stored sRGB.")
A("- **alpha** (ink opacity) = `1 - linear_G / local_paper_field_G`. The paper field is")
A("  a masked blur of paper pixels at 4.5 % of tag width, refined three times, so edge")
A("  darkening and stains belong to the paper and are never miscounted as ink.")
A("- **ink mass fraction** = mean of alpha over the paper. Unlike an area count it")
A("  weights kasure holes and soft halos correctly, so it is what the eye integrates.")
A("- Area fractions are fractions of the paper **octagon** (rectangle less the four")
A("  chamfers), with a 0.30 mm rim excluded.")
A("")
A("## Rectification")
A("")
A("**Neither reference needed correcting.** Both are axis-aligned to better than")
A("0.04 degrees and square to better than 0.05 %:")
A("")
A("| | V1 | V2 |")
A("|---|---|---|")
for k, lbl in (("left_off_vertical", "left edge off vertical"),
               ("right_off_vertical", "right edge off vertical"),
               ("top_off_horizontal", "top edge off horizontal"),
               ("bottom_off_horizontal", "bottom edge off horizontal")):
    a = g(J, "rectification/per_source/V1/edge_angles_deg/" + k)
    b = g(J, "rectification/per_source/V2/edge_angles_deg/" + k)
    A("| %s | %+.4f deg | %+.4f deg |" % (lbl, a, b))
for k, lbl in (("width_top_over_bottom", "width top / bottom"),
               ("height_left_over_right", "height left / right")):
    a = g(J, "rectification/per_source/V1/keystone/" + k)
    b = g(J, "rectification/per_source/V2/keystone/" + k)
    A("| %s | %.5f | %.5f |" % (lbl, a, b))
A("| tag size in source px | %s | %s |"
  % (g(J, "rectification/per_source/V1/tag_px_w_h"),
     g(J, "rectification/per_source/V2/tag_px_w_h")))
A("| sampling | %.3f px/mm | %.3f px/mm |"
  % (g(J, "rectification/per_source/V1/source_px_per_mm"),
     g(J, "rectification/per_source/V2/source_px_per_mm")))
A("| aspect h/w | %.4f | %.4f |"
  % (g(J, "rectification/per_source/V1/aspect_h_over_w"),
     g(J, "rectification/per_source/V2/aspect_h_over_w")))
A("| corner chamfer, mean along an edge | %.2f mm | %.2f mm |"
  % (g(J, "rectification/per_source/V1/corner_chamfer_mm"),
     g(J, "rectification/per_source/V2/corner_chamfer_mm")))
A("")
A("Correction applied: a sub-pixel crop to the fitted paper rectangle, then a")
A("bilinear resample to a common 840 x 1872 grid (12 px/mm). Nothing else. Every")
A("high-frequency statistic below (fibre spectrum, kasure hole size, edge roughness)")
A("was measured at **native** resolution so the resample stays out of it.")
A("")
A("One thing that went wrong and is worth recording: an adaptive threshold set from a")
A("high percentile landed *above* the paper level and traced the ink instead of the")
A("paper, giving V1 a spurious 5.85 degree bottom edge. The half-maximum between the")
A("measured background and paper levels is what fixed it.")
A("")
A("## The headline")
A("")
for k, v in J["headline"].items():
    A("- **%s** - %s" % (k.replace("_", " "), v))
A("")
A("## Paper")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("base colour, centre 44 % box (stored sRGB)",
      "paper/centre_44pct_box/stored_srgb_hex"))
A(row("  same, 8-bit", "paper/centre_44pct_box/stored_srgb_median_8bit"))
A(row("  hue, deg", "paper/centre_44pct_box/hsv_stored/h_deg", "%.2f"))
A(row("  saturation", "paper/centre_44pct_box/hsv_stored/s", "%.4f"))
A(row("  value", "paper/centre_44pct_box/hsv_stored/v", "%.4f"))
A(row("  linear RGB", "paper/centre_44pct_box/linear_median"))
A(row("  linear luma", "paper/centre_44pct_box/linear_luma_median", "%.4f"))
A(row("edges, outer 2 mm band (stored sRGB)", "paper/outer_2mm_band/stored_srgb_hex"))
A(row("plateau linear luma (beyond 12 mm in)",
      "paper/edge_darkening/plateau_luma_lin", "%.5f"))
A(row("rim darkening depth", "paper/edge_darkening/depth_at_outer_0_5mm_pct", "%.2f", "%"))
A(row("half-recovery distance", "paper/edge_darkening/half_recovery_mm", "%.2f", "mm"))
A(row("95 % of plateau at", "paper/edge_darkening/reach_mm_to_95pct", "%.2f", "mm"))
A(row("99 % of plateau at", "paper/edge_darkening/reach_mm_to_99pct", "%.2f", "mm"))
A(row("evenness: spread across the 4 sides",
      "paper/edge_darkening_evenness/spread_max_minus_min", "%.4f"))
A(row("global lighting gradient across width",
      "paper/global_gradient/pct_across_width", "%+.2f", "%"))
A(row("global lighting gradient down height",
      "paper/global_gradient/pct_across_height", "%+.2f", "%"))
A("")
A("The reference's edge darkening is a **broad, gentle, even vignette**: about 15 % of")
A("paper luminance at the rim, half recovered by 4.75 mm, 95 % recovered by 7.25 mm,")
A("and the four sides agree to 1.5 points. Ours is deeper (21.9 %), reaches three")
A("times further (95 % only at 14.75 mm) and is 12.4 points uneven side to side.")
A("")
A("### Mottle and stains")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("mottle RMS, % of paper luma", "mottle_and_stains/rms_pct", "%.3f"))
A(row("correlation length (blotch size)",
      "mottle_and_stains/spectrum/correlation_length_mm", "%.3f", "mm"))
A(row("power at wavelengths 3-10 mm",
      "mottle_and_stains/spectrum/band_power_fraction/3_to_10mm", "%.4f"))
A(row("power at wavelengths 1-3 mm",
      "mottle_and_stains/spectrum/band_power_fraction/1_to_3mm", "%.4f"))
A(row("spectrum log-log slope", "mottle_and_stains/spectrum/slope_loglog", "%.2f"))
A(row("stains darker than 3 %, count",
      "mottle_and_stains/stains/darker_than_3_pct/count", "%d"))
A(row("  their area", "mottle_and_stains/stains/darker_than_3_pct/total_area_frac_of_tag",
      "%.5f"))
A(row("  median equivalent diameter",
      "mottle_and_stains/stains/darker_than_3_pct/equiv_diam_mm/p50", "%.3f", "mm"))
A(row("  median elongation",
      "mottle_and_stains/stains/darker_than_3_pct/elongation_median", "%.2f"))
A(row("stains darker than 6 %, count",
      "mottle_and_stains/stains/darker_than_6_pct/count", "%d"))
A(row("  their area", "mottle_and_stains/stains/darker_than_6_pct/total_area_frac_of_tag",
      "%.5f"))
A(row("stains darker than 10 %, count",
      "mottle_and_stains/stains/darker_than_10_pct/count", "%d"))
A("")
A("The mottle spectrum is **red** in all three (power falls with frequency, slope")
A("about -5 to -7), so there is no periodic 'grain wavelength' to match; the honest")
A("descriptors are the correlation length and the band powers. Our amplitude is right")
A("and our scale is wrong: too much 3-10 mm, half the reference's 1-3 mm content.")
A("")
A("### Folds, creases and implied shadow")
A("")
A("Neither reference has any. The band-pass detector finds no line spanning either")
A("tag, and the global lighting gradient is small in both. They are flat, evenly lit")
A("sheets. Our basecolour carries two horizontal crease lines, at 51.6 mm (v 0.331)")
A("and 104.4 mm (v 0.669), covering 46 % and 51 % of the tag width. The mesh already")
A("has real creases, so that is shading counted twice, and it is shading the reference")
A("does not have at all.")
A("")
A("### Paper fibre texture (measured at native resolution)")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("native sampling", "paper_fibre_texture/native_px_per_mm", "%.3f", "px/mm"))
A(row("Nyquist", "paper_fibre_texture/nyquist_cycles_per_mm", "%.2f", "cyc/mm"))
A(row("clean patches found", "paper_fibre_texture/n_patches", "%d"))
A(row("grain amplitude, % of paper luma",
      "paper_fibre_texture/residual_rms_pct_of_paper_luma", "%.2f"))
A(row("dominant cell size", "paper_fibre_texture/dominant_cell_size_mm", "%.3f", "mm"))
A(row("anisotropy max/min", "paper_fibre_texture/anisotropy_max_over_min", "%.2f"))
A(row("preferred orientation", "paper_fibre_texture/preferred_orientation_deg",
      "%.0f", "deg"))
A("")
A("Use **V1 only**. V2's Nyquist is 1.96 cyc/mm, so its 2.35 mm 'cell' and its 5.79")
A("anisotropy are measuring its own downsample. V1 says a 0.50 mm cell (4.4 source px)")
A("at 17.0 % amplitude, close to isotropic at 1.90. Ours is 9.8 % amplitude and")
A("strongly streaked at 17.2 - though that rests on only two clean patches, so treat")
A("the 125 degree angle as indicative and the streak itself as real.")
A("")
A("## Black ink")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("core colour (stored sRGB)", "black_ink/colour_core/stored_srgb_hex"))
A(row("  8-bit", "black_ink/colour_core/stored_srgb_median_8bit"))
A(row("  linear luma", "black_ink/colour_core/linear_luma_median", "%.5f"))
A(row("neutrality R-B (stored)", "black_ink/darkest/neutrality_R_minus_B_stored_median",
      "%.4f"))
A(row("median value in the stroke core, 8-bit",
      "black_ink/darkest/median_stored_srgb_8bit", "%d"))
A(row("p1 of value, 8-bit", "black_ink/darkest/p1_stored_srgb_8bit", "%d"))
A(row("minimum value reached, 8-bit", "black_ink/darkest/min_stored_srgb_8bit", "%d"))
A(row("minimum linear luma", "black_ink/darkest/min_linear_luma", "%.6f"))
A(row("p0.1 linear luma", "black_ink/darkest/p0_1_linear_luma", "%.6f"))
A(row("p1 linear luma", "black_ink/darkest/p1_linear_luma", "%.6f"))
A(row("alpha, median", "black_ink/alpha_distribution/p50", "%.4f"))
A(row("alpha, p5", "black_ink/alpha_distribution/p5", "%.4f"))
A(row("within-stroke p5-p95 swing, /255",
      "black_ink/within_stroke_variation/stored_value_p5_p95_span_8bit", "%.1f"))
A(row("modulation depth (swing / own median)", "derived/black_modulation_depth", "%.3f"))
A(row("**paper : ink contrast ratio**", "derived/paper_over_black_contrast_ratio",
      "%.1f", ": 1"))
A("")
A("Our shipped **render** reaches 15.9 : 1 (paper linear luma 0.3858, ink 0.0243), so")
A("lighting recovers some of the gap but nowhere near it.")
A("")
A("**Flat fill or loaded-to-dry?** Neither reference ramps. Fitting alpha against")
A("height inside every element gives the reference a slope of -0.001 to +0.001 - its")
A("black is opaque at alpha 0.99 at the top of a column and 0.99 at the bottom. All of")
A("its dry-brush character comes from **holes punched clean through a solid fill**, not")
A("from a density ramp. Ours does the opposite: a semi-transparent wash at alpha")
A("0.84-0.92 that additionally fades 3.5 to 6.7 alpha points down each column.")
A("")
A("## Reds")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
for nm, lbl in (("border_red", "border"), ("ring_red", "ring"),
                ("seal_block_red_lower_left", "seal block"),
                ("small_seal_red_lower_right", "small seal")):
    A(row("%s: stored sRGB" % lbl, "reds/per_element/%s/stored_srgb_hex" % nm))
    A(row("  hue deg", "reds/per_element/%s/hsv_stored/h_deg" % nm, "%.2f"))
    A(row("  saturation", "reds/per_element/%s/hsv_stored/s" % nm, "%.4f"))
    A(row("  value", "reds/per_element/%s/hsv_stored/v" % nm, "%.4f"))
    A(row("  alpha_R over paper",
          "reds/per_element/%s/opacity_over_paper/alpha_R" % nm, "%.4f"))
    A(row("  alpha_G over paper",
          "reds/per_element/%s/opacity_over_paper/alpha_G" % nm, "%.4f"))
    A(row("  hue variation within a stroke, std deg",
          "reds/per_element/%s/hsv_variation/h_deg_std" % nm, "%.2f"))
    A(row("  value variation within a stroke, std",
          "reds/per_element/%s/hsv_variation/v_std" % nm, "%.4f"))
A(row("hue spread across the four", "reds/comparison/hue_spread_deg", "%.3f", "deg"))
A(row("saturation spread across the four", "reds/comparison/sat_spread", "%.4f"))
A(row("value spread across the four", "reds/comparison/val_spread", "%.4f"))
A(row("weight spread, alpha_R", "derived/red_weight_spread_alpha_R", "%.4f"))
A("")
A("**Is it the same red?** In the reference, yes as a pigment and no as a laid-on")
A("weight. Hue spread is 1.14 degrees and saturation spread 0.021 - a single ink -")
A("but value spreads 0.139 and alpha_R runs from 0.375 at the small seal to 0.590 at")
A("the border. The border is deliberately the **heaviest** red on the sheet. In our")
A("build all four reds are the same colour *and* the same weight (value spread 0.008),")
A("the border is our lightest rather than our heaviest, and every one of them is about")
A("a third short on saturation: blue channel 72/255 against the reference's 21/255.")
A("")
A("Red opacity over paper is strongly channel-split in both: alpha_G is 0.98 in the")
A("reference (the paper's green is almost entirely absorbed) while alpha_R is only")
A("0.38-0.59. That split is what makes it read as red rather than as a dark mark, and")
A("ours is much weaker on both (alpha_G 0.85, alpha_R 0.23-0.33).")
A("")
A("## Coverage")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("total ink mass fraction", "coverage/total/ink_mass_frac", "%.4f"))
A(row("solid area fraction (alpha > 0.5)", "coverage/total/solid_area_frac", "%.4f"))
A(row("black ink mass", "coverage/total/black_ink_mass_frac", "%.4f"))
A(row("red ink mass", "coverage/total/red_ink_mass_frac", "%.4f"))
A(row("black area / red area", "coverage/total/black_over_red_area", "%.3f"))
for nm, lbl in (("centre_glyph_black", "centre glyph, black"),
                ("enso_ring_red", "enso ring, red"),
                ("upper_left_column_black", "upper-left column 火遁術"),
                ("upper_right_column_black", "upper-right column 爆炎陣"),
                ("lower_right_column_black", "lower-right 焼尽"),
                ("lower_centre_column_black", "lower-centre 瞬業"),
                ("flame_emblem_black", "flame emblem"),
                ("seal_block_lower_left_red", "seal block, red"),
                ("small_seal_lower_right_red", "small seal 火道, red"),
                ("border_zone_outer_8_4mm_red", "border zone, red")):
    A(row(lbl + " - ink mass",
          "coverage/per_element/%s/ink_mass_frac_of_tag" % nm, "%.5f"))
A("")
A("## Enso ring")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("centre u", "segmentation/ring_fit/centre_uv/0", "%.4f"))
A(row("centre v", "segmentation/ring_fit/centre_uv/1", "%.4f"))
A(row("centre, mm", "segmentation/ring_fit/centre_mm"))
A(row("polar outer radius", "stroke_edge_roughness/enso_ring_polar/outer/mean_radius_mm",
      "%.3f", "mm"))
A(row("polar inner radius", "stroke_edge_roughness/enso_ring_polar/inner/mean_radius_mm",
      "%.3f", "mm"))
A(row("stroke width", "derived/ring_stroke_width_mm", "%.3f", "mm"))
A(row("ellipticity h/w", "segmentation/ring_fit/ellipticity_h_over_w", "%.4f"))
A(row("outer edge roughness RMS",
      "stroke_edge_roughness/enso_ring_polar/outer/roughness_rms_mm", "%.4f", "mm"))
A(row("inner edge roughness RMS",
      "stroke_edge_roughness/enso_ring_polar/inner/roughness_rms_mm", "%.4f", "mm"))
A(row("outer raggedness, cycles per revolution",
      "stroke_edge_roughness/enso_ring_polar/outer/dominant_cycles_per_revolution", "%d"))
A(row("outer raggedness wavelength",
      "stroke_edge_roughness/enso_ring_polar/outer/dominant_wavelength_mm_along_edge",
      "%.3f", "mm"))
A("")
A("## Dry brush (kasure)")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
for nm, lbl in (("enso_ring", "ring"), ("centre_glyph_black", "centre glyph"),
                ("all_black_outside_ring", "all black outside the ring")):
    A(row("%s: hole count" % lbl, "kasure_dry_brush/%s/hole_count" % nm, "%d"))
    A(row("  holes per 100 mm2 of stroke",
          "kasure_dry_brush/%s/hole_count_per_100mm2_of_stroke" % nm, "%.2f"))
    A(row("  hole area / stroke area",
          "kasure_dry_brush/%s/hole_area_fraction_of_stroke" % nm, "%.4f"))
    A(row("  median hole diameter",
          "kasure_dry_brush/%s/hole_equiv_diam_mm/p50" % nm, "%.3f", "mm"))
    A(row("  p95 hole diameter",
          "kasure_dry_brush/%s/hole_equiv_diam_mm/p95" % nm, "%.3f", "mm"))
    A(row("  median hole elongation",
          "kasure_dry_brush/%s/hole_elongation/p50" % nm, "%.2f"))
    A(row("  mean alpha inside the stroke envelope",
          "kasure_dry_brush/%s/mean_alpha_inside_envelope" % nm, "%.4f"))
A(row("ring holes within 30 deg of the stroke direction",
      "kasure_dry_brush/enso_ring/alignment_with_stroke_direction/"
      "frac_within_30deg_of_stroke", "%.4f"))
A("")
A("Random orientation would give 0.333, so the reference's holes are strongly")
A("**elongated along the stroke**, which is what a splitting brush does. Ours are too,")
A("at a similar median elongation and a similar median size. The gap is purely in")
A("**how many** and in how dark the surrounding ink is.")
A("")
A("## Stroke edge roughness and bleed")
A("")
A("| | V1 | V2 | OURS |")
A("|---|---|---|---|")
A(row("black: mean boundary deviation",
      "stroke_edge_roughness/black_all/mean_deviation_amplitude_mm", "%.4f", "mm"))
A(row("black: mean lobe spacing along the edge",
      "stroke_edge_roughness/black_all/mean_lobe_spacing_mm", "%.3f", "mm"))
A(row("red: mean boundary deviation",
      "stroke_edge_roughness/red_all/mean_deviation_amplitude_mm", "%.4f", "mm"))
A(row("red: mean lobe spacing along the edge",
      "stroke_edge_roughness/red_all/mean_lobe_spacing_mm", "%.3f", "mm"))
A(row("black edge 10-90 transition width",
      "ink_bleed/black/transition_width_10_to_90_mm", "%.4f", "mm"))
A(row("  same, in native pixels", "ink_bleed/black/transition_width_in_native_px",
      "%.2f", "px"))
A(row("  one native pixel", "ink_bleed/black/one_native_px_mm", "%.4f", "mm"))
A(row("  soft halo beyond anti-aliasing",
      "ink_bleed/black/soft_halo_beyond_antialiasing_mm", "%.4f", "mm"))
A(row("  outward distance to 10 % of plateau",
      "ink_bleed/black/outward_mm_to_10pct", "%.4f", "mm"))
A(row("red: soft halo beyond anti-aliasing",
      "ink_bleed/red/soft_halo_beyond_antialiasing_mm", "%.4f", "mm"))
A("")
A("Any raster shows about one native pixel of anti-aliasing at a stroke edge, so only")
A("the excess is bleed. V1's excess is 0.112 mm - the reference has very little bleed,")
A("its edges are crisp and its softness is all kasure. Ours is 0.172 mm on top of a")
A("finer pixel, so our edges are genuinely softer.")
A("")
A("## Where V1 and V2 disagree")
A("")
A("| what | V1 | V2 | follow | why |")
A("|---|---|---|---|---|")
for d in J["v1_v2_disagreements"]:
    A("| %s | %s | %s | **%s** | %s |"
      % (d["what"], d["v1"], d["v2"], d["follow"], d["why"]))
A("")
A("## Our build, worst first")
A("")
A("| # | element | metric | reference | ours | delta |")
A("|---|---|---|---|---|---|")
for d in J["our_build_deltas"]:
    A("| %d | %s | %s | %s | %s | **%s** |"
      % (d["rank"], d["element"], d["metric"], d["reference"], d["ours"], d["delta"]))
A("")
A("### Why each one matters")
A("")
for d in J["our_build_deltas"]:
    A("%d. **%s - %s** (%s -> %s, %s). %s"
      % (d["rank"], d["element"], d["metric"], d["reference"], d["ours"],
         d["delta"], d["matters"]))
A("")
A("## What is uncertain")
A("")
for u in J["uncertain"]:
    A("- %s" % u)
A("")
A("## Provenance")
A("")
A("Blender 5.2 headless, factory startup, numpy only. PNGs decoded from their IDAT")
A("chunks by `pngread.py` so stored 8-bit values are exact and no colour management is")
A("involved. Scripts: %s." % ", ".join("`%s`" % s for s in J["provenance"]["scripts"]))
A("")

with open(HERE + "/INK_NOTES.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
print("wrote INK_NOTES.md,", len(L), "lines")

# ------------------------------------------------- debug schematic
W, H = 560, 1248
img = np.ones((H, W, 4), dtype=np.float32)
img[..., 3] = 1.0
ppmm = W / 70.0


def px(um, vm):
    return um * ppmm, vm * ppmm


def dot(x, y, col, r=1.6):
    x0, x1 = int(max(0, x - r)), int(min(W, x + r + 1))
    y0, y1 = int(max(0, y - r)), int(min(H, y + r + 1))
    img[y0:y1, x0:x1, :3] = col


def ellipse(cx, cy, rx, ry, col, n=1400):
    t = np.linspace(0, 2 * np.pi, n)
    for x, y in zip(cx + rx * np.cos(t), cy + ry * np.sin(t)):
        dot(x, y, col, 1.2)


def rect(x0, y0, x1, y1, col):
    for x in np.linspace(x0, x1, 900):
        dot(x, y0, col, 1.0)
        dot(x, y1, col, 1.0)
    for y in np.linspace(y0, y1, 1600):
        dot(x0, y, col, 1.0)
        dot(x1, y, col, 1.0)


# tag outline with a 7.6 mm chamfer
C = 7.6 * ppmm
pts = [(C, 0), (W - C, 0), (W, C), (W, H - C), (W - C, H), (C, H), (0, H - C), (0, C)]
for i in range(len(pts)):
    a, b = pts[i], pts[(i + 1) % len(pts)]
    for t in np.linspace(0, 1, 1400):
        dot(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), (0.15, 0.15, 0.15), 1.2)

COL = {"V1": (0.85, 0.10, 0.10), "V2": (0.95, 0.55, 0.10),
       "OURS_basecolour": (0.10, 0.35, 0.85)}
for k, col in COL.items():
    rf = g(M[k], "segmentation/ring_fit")
    pol = g(M[k], "stroke_edge_roughness/enso_ring_polar")
    cx, cy = px(*rf["centre_mm"])
    rx = rf["mid_stroke_semi_axes_mm"][0] * ppmm
    ry = rf["mid_stroke_semi_axes_mm"][1] * ppmm
    ellipse(cx, cy, rx, ry, col)
    if pol:
        f_out = pol["outer"]["mean_radius_mm"] / (0.5 * (rf["mid_stroke_semi_axes_mm"][0]
                                                         + rf["mid_stroke_semi_axes_mm"][1]))
        f_in = pol["inner"]["mean_radius_mm"] / (0.5 * (rf["mid_stroke_semi_axes_mm"][0]
                                                        + rf["mid_stroke_semi_axes_mm"][1]))
        ellipse(cx, cy, rx * f_out, ry * f_out, tuple(min(1, c + 0.35) for c in col))
        ellipse(cx, cy, rx * f_in, ry * f_in, tuple(min(1, c + 0.35) for c in col))
    gb = g(M[k], "elements/centre_glyph/bbox_mm")
    if gb:
        rect(gb[0] * ppmm, gb[1] * ppmm, gb[2] * ppmm, gb[3] * ppmm, col)

try:
    import bpy
    name = "DEBUG_NEVER_SHIP_ring_and_glyph_schematic"
    im = bpy.data.images.new(name, width=W, height=H, alpha=True)
    im.pixels.foreach_set(img[::-1].ravel())
    im.filepath_raw = DBG = HERE + "/debug/%s.png" % name
    im.file_format = "PNG"
    im.save()
    print("wrote", DBG)
except Exception as exc:
    print("schematic save failed:", exc)

with open(HERE + "/debug/README.txt", "w", encoding="utf-8") as fh:
    fh.write("""DEBUG - NEVER SHIP
==================

Everything in this folder is diagnostic output from the paper-bomb reference
metrology pass. Nothing here may be consumed by a build, shipped in a pack, or
used as source art. Several agents write here; this note applies to all of it.

From the INK AND COLOUR pass (see ../INK_NOTES.md and ../ink_colour.json):

  DEBUG_NEVER_SHIP_ring_and_glyph_schematic.png
      DRAWN FROM MEASURED NUMBERS ONLY. Fitted enso-ring ellipses (mid-stroke,
      outer and inner) and centre-glyph bounding boxes for V1 (red), V2
      (orange) and our build (blue), over a 70 x 156 mm card outline with a
      7.6 mm corner chamfer. It contains no pixel of either reference image and
      is not a crop, mask, trace, threshold or derivative of one.

  probe01.json          file facts for both references and our four shipped
                        maps, plus the stored-vs-linear cross-check that proved
                        Blender's Image.pixels returns stored sRGB for 8-bit
                        PNGs.
  stage1_rectify.json   fitted tag quadrilaterals, edge angles, keystone
                        diagnostics and the rectification homographies.
  diag_edges.py         one-shot: why the first edge fit traced ink, not paper.
  diag_seg.py           one-shot: ink/red threshold selection from the data.
  patch_sev.py          one-shot: severity ranking helper.

Rectified reference arrays were cached only in the session scratchpad, never
under the project. If a _cache/ directory appears here it means PB_SCRATCH was
unset on some run; delete it.

Other files in this folder belong to the layout and typography passes.
""")
print("wrote debug/README.txt")
