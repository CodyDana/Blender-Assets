# -*- coding: utf-8 -*-
"""Stage 3: assemble ink_colour.json, INK_NOTES.md and a debug schematic."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402

SCRATCH = os.environ["PB_SCRATCH"]
DEBUG = HERE + "/debug"
os.makedirs(DEBUG, exist_ok=True)

M_ = {k: json.load(open(os.path.join(SCRATCH, "meas_%s.json" % k), encoding="utf-8"))
      for k in ("V1", "V2", "OURS")}
REND = json.load(open(os.path.join(SCRATCH, "meas_OURS_RENDER.json"), encoding="utf-8"))
GEO = json.load(open(HERE + "/debug/stage1_rectify.json", encoding="utf-8"))


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


def lum(linrgb):
    return None if not linrgb else (0.2126 * linrgb[0] + 0.7152 * linrgb[1]
                                    + 0.0722 * linrgb[2])


# ------------------------------------------------- derived, per source
for k, d in M_.items():
    plate = g(d, "paper/edge_darkening/plateau_luma_lin")
    blk = g(d, "black_ink/colour_core/linear_luma_median")
    red = g(d, "reds/per_element/ring_red/linear_luma_median")
    span = g(d, "black_ink/within_stroke_variation/stored_value_p5_p95_span_8bit")
    med = g(d, "black_ink/darkest/median_stored_srgb_8bit")
    pol = g(d, "stroke_edge_roughness/enso_ring_polar")
    reds = g(d, "reds/per_element", {})
    alphas = [v["opacity_over_paper"]["alpha_R"] for v in reds.values()]
    d["derived"] = {
        "paper_plateau_linear_luma": plate,
        "black_core_linear_luma": blk,
        "ring_red_linear_luma": red,
        "paper_over_black_contrast_ratio": round(plate / max(blk, 1e-9), 1),
        "paper_over_red_contrast_ratio": round(plate / max(red, 1e-9), 2),
        "black_modulation_depth": round(span / max(med, 1e-9), 4),
        "black_modulation_note": "p5-p95 value swing inside one stroke divided by that "
                                 "stroke's own median value. An absolute 8-bit swing "
                                 "flatters a light ink, this does not.",
        "ring_stroke_width_mm": round(pol["outer"]["mean_radius_mm"]
                                      - pol["inner"]["mean_radius_mm"], 4) if pol else None,
        "red_weight_spread_alpha_R": round(max(alphas) - min(alphas), 4) if alphas else None,
        "red_weight_spread_note": "how much the SAME red pigment varies in laid-on "
                                  "weight between the border, the ring and the seals",
        "ring_red_blue_channel_8bit": g(d, "reds/per_element/ring_red/"
                                           "stored_srgb_median_8bit/2"),
    }

rp = lum(g(REND, "paper/linear_median"))
rb = g(REND, "black_ink/darkest/median_linear_luma")
rr = lum(g(REND, "red_ink/linear_median"))
REND["derived"] = {
    "paper_linear_luma": round(rp, 6),
    "black_linear_luma": rb,
    "red_linear_luma": round(rr, 6),
    "paper_over_black_contrast_ratio": round(rp / rb, 1),
    "paper_over_red_contrast_ratio": round(rp / rr, 2),
    "why_this_matters": "the ratio is independent of how bright the lighting is, so it "
                        "compares an albedo map and a lit render with a finished "
                        "illustration on fair terms. Quoting it answers the obvious "
                        "objection that a basecolour map is not supposed to look like "
                        "a picture.",
}

# ------------------------------------------------- V1 vs V2
V1V2 = [
    {"what": "tag aspect ratio (paper height / paper width)",
     "v1": "%.4f" % GEO["V1"]["aspect_h_over_w"],
     "v2": "%.4f" % GEO["V2"]["aspect_h_over_w"],
     "follow": "V1",
     "why": "V1's 2.2380 matches the shipped 70 x 156 mm card (2.2286) to 0.4 %. V2 is "
            "3.6 % taller, a non-uniform rescale the user's crop introduced: V1's tag "
            "is 616.1 x 1379.1 source px, V2's is 274.4 x 636.0, so V2 was scaled "
            "0.4453 in x but 0.4612 in y. Read V2 for WHICH glyph sits where; read V1 "
            "for how far down it sits, and divide any V2 v-fraction by 1.0356 before "
            "using it as a position."},
    {"what": "source sampling over the tag",
     "v1": "8.802 px/mm", "v2": "3.920 px/mm", "follow": "V1",
     "why": "V2 resolves nothing finer than 0.51 mm. Its fibre spectrum, kasure hole "
            "sizes and edge-roughness wavelengths all sit at or past its own Nyquist "
            "limit, so they measure the downsample rather than the artwork."},
    {"what": "paper base colour, centre of the tag, stored sRGB",
     "v1": "#F6E6C5 (246,230,197) H 40.35 S 0.198 V 0.963",
     "v2": "#F6E5C3 (246,229,195) H 40.01 S 0.208 V 0.965",
     "follow": "either", "why": "They agree to 2/255 on every channel and to 0.35 "
                                "degrees of hue. The paper colour is settled and needs "
                                "no adjudication."},
    {"what": "black ink core colour, stored sRGB",
     "v1": "#0F100D (15,16,13), linear luma 0.00509",
     "v2": "#0C0D0A (12,13,10), linear luma 0.00386",
     "follow": "V1",
     "why": "V2 is 3/255 darker because its downsample pushed the surviving core "
            "pixels toward the stroke centres. Both say the same thing: a near-neutral "
            "near-black at about 15/255, not a charcoal. Use V1's, which is measured "
            "over 2.2x more pixels per stroke."},
    {"what": "paper:ink luminance contrast ratio",
     "v1": "153.5 : 1", "v2": "202.7 : 1", "follow": "V1",
     "why": "Same cause as the row above. V1's 153:1 is the conservative target; even "
            "it is 14x what we currently ship."},
    {"what": "total ink mass fraction of the tag",
     "v1": "0.3035", "v2": "0.3345", "follow": "V1",
     "why": "V2 reads 10 % heavier because its 2.2x downsample smears every stroke "
            "edge outward and the smear counts as partial ink. The extra is blur, not "
            "design. Target V1's 0.3035."},
    {"what": "black area / red area",
     "v1": "1.449", "v2": "1.502", "follow": "either",
     "why": "The two agree to 3.7 %, so the black-to-red balance is the most robust "
            "composition number in the whole reference. Ours is 1.002."},
    {"what": "enso ring stroke width (polar outer radius minus inner radius)",
     "v1": "6.148 mm", "v2": "6.306 mm", "follow": "V1",
     "why": "2.6 % apart, well inside V2's own 0.51 mm resolution. Either supports a "
            "6.1-6.3 mm brush. Ours is 4.28 mm."},
    {"what": "enso ring ellipticity (height / width)",
     "v1": "1.1538", "v2": "1.0996", "follow": "V1",
     "why": "V2's figure is measured in its stretched frame; correcting it by the "
            "1.0356 stretch gives 1.062. So V1 says slightly oval, V2 corrected says "
            "nearly round. Take V1's 1.154 as the upper bound and treat anything above "
            "1.20 as wrong. Ours is 1.265."},
    {"what": "enso ring centre, v fraction of tag height",
     "v1": "0.4950", "v2": "0.4750", "follow": "V1",
     "why": "V1 puts the ring on the tag's vertical midline. V2's 0.475 is its crop "
            "and stretch, not a design difference."},
    {"what": "ring red saturation",
     "v1": "0.8924", "v2": "0.9421", "follow": "V1",
     "why": "The user's edit lifted saturation ~5 points. V1 is the conservative "
            "figure and still 0.28 above what we ship, so the disagreement does not "
            "change any decision."},
    {"what": "are the border red, ring red and seal red the same red?",
     "v1": "hue spread 1.14 deg, saturation spread 0.021, VALUE spread 0.139",
     "v2": "hue spread 0.42 deg, saturation spread 0.028, VALUE spread 0.089",
     "follow": "V1",
     "why": "Both say the same pigment at different weights: hue and saturation are "
            "locked, value is not. V1 shows the spread more strongly because it "
            "resolves the heavy border line. Follow V1 and vary the WEIGHT, not the "
            "hue."},
    {"what": "ink mass of the four side/lower columns (the text blocks)",
     "v1": "upper-left 0.01210, upper-right 0.01191, lower-right 0.00947, "
           "lower-centre 0.00924",
     "v2": "upper-left 0.02076, upper-right 0.02195, lower-right 0.01516, "
           "lower-centre 0.01722",
     "follow": "V2, divided by 1.102",
     "why": "THE most consequential disagreement in this pass. V1's side columns are "
            "pseudo-glyphs - thin, sketchy squiggles - while V2's are the real kanji "
            "the asset ships (火遁術, 爆炎陣, 焼尽, 瞬業). Real characters carry far "
            "more ink than squiggles, so V1 understates these blocks by 60-85 %, well "
            "beyond V2's uniform 10.2 % downsample smear. Take V2's figure and divide "
            "by 1.102 (the V2/V1 total-ink ratio) to strip the smear: targets are "
            "0.0188, 0.0199, 0.0138 and 0.0156. Everything else on this page still "
            "follows V1."},
    {"what": "ink mass of the red border zone (outer 8.4 mm)",
     "v1": "0.00925", "v2": "0.01745", "follow": "V1",
     "why": "Unlike the columns this is the same artwork in both, so the 89 % gap is "
            "measurement, not design: the border is a thin line, and a thin line is "
            "exactly what a 2.2x downsample fattens most. V2's smear bias is far above "
            "its 10 % average here. Use V1."},
    {"what": "paper fibre dominant cell size",
     "v1": "0.499 mm", "v2": "2.355 mm", "follow": "V1",
     "why": "V2's figure is its resolution floor, not a measurement: 2.355 mm is barely "
            "above its 0.51 mm Nyquist scale once windowing is accounted for. V1's "
            "0.50 mm (4.4 source px) is the real grain."},
    {"what": "paper fibre anisotropy",
     "v1": "1.902", "v2": "5.787", "follow": "V1",
     "why": "V2's is resampling streak. V1 says the grain is close to isotropic with a "
            "mild preference near 85 deg."},
    {"what": "edge darkening depth at the rim",
     "v1": "15.70 %", "v2": "14.31 %", "follow": "either",
     "why": "1.4 points apart. The rim burn is settled at about 15 % of paper "
            "luminance."},
    {"what": "edge darkening half-recovery distance",
     "v1": "4.75 mm", "v2": "3.75 mm", "follow": "V1",
     "why": "V2's profile is quantised by its 0.255 mm pixel, which biases the "
            "crossing inward. V1's 4.75 mm, reaching 95 % of plateau by 7.25 mm, is "
            "the better number."},
    {"what": "any fold, crease or internal shadow on the paper",
     "v1": "none detected", "v2": "none detected", "follow": "either",
     "why": "Both references are flat, evenly lit sheets. The band-pass crease detector "
            "found no line spanning the tag in either. There is no fold shading to "
            "match, and our basecolour currently bakes two."},
]

# ------------------------------------------------- our deltas
DELTAS = []


def add(element, metric, unit, matters, path=None, fmt="%.4g", pct=True,
        ref=None, ours=None, ref_key="V1", ref_s=None, ours_s=None, delta_s=None):
    if ref_s is not None:
        DELTAS.append({"element": element, "metric": metric, "reference": ref_s,
                       "ours": ours_s, "delta": delta_s, "matters": matters})
        return
    r = ref if ref is not None else g(M_[ref_key], path)
    o = ours if ours is not None else g(M_["OURS"], path)
    if r is None or o is None:
        print("SKIP", metric)
        return
    d = o - r
    rel = (d / r * 100.0) if (pct and abs(r) > 1e-12) else None
    DELTAS.append({
        "element": element, "metric": metric,
        "reference": ("%s %s" % (fmt % r, unit)).strip(),
        "ours": ("%s %s" % (fmt % o, unit)).strip(),
        "delta": ("%+.1f%%" % rel) if rel is not None else ("%+.4g %s" % (d, unit)).strip(),
        "matters": matters,
    })


add("black ink", "paper:ink luminance contrast ratio", ":1",
    "THE headline, and it is lighting-independent so the 'it is only an albedo map' "
    "objection does not apply. The reference's black sits at 1/153 of its paper's "
    "luminance. Our basecolour reaches 1/11 and our shipped render only 1/16. Our ink "
    "is a charcoal grey on a tan sheet, not black ink on cream paper. Nothing else on "
    "this list changes the read as much, and no amount of extra coverage compensates.",
    path="derived/paper_over_black_contrast_ratio", fmt="%.1f")
add("black ink", "black core colour, stored sRGB 8-bit", "",
    "The same fact in the units an artist edits in. The reference black is #0F100D; "
    "ours is #41403E. Hue neutrality is fine on both (R-B is 2/255 in the reference, "
    "3/255 in ours) - it is purely a value error, 50 steps of it.",
    ref_s="#0F100D (15,16,13)", ours_s="#41403E (65,64,62)", delta_s="+50/255 lighter")
add("black ink", "darkest value the black actually reaches", "",
    "The reference's ink has a tail: minimum 0/255, 0.1th percentile 6/255, so the "
    "densest passages go truly black. Ours is clamped - minimum, 0.1th percentile and "
    "1st percentile are all exactly 62/255. There is no dark tail at all, which is why "
    "the strokes look printed rather than inked.",
    ref_s="min 0/255, p0.1 6/255, p1 6/255",
    ours_s="min 62/255, p0.1 62/255, p1 62/255",
    delta_s="no dark tail: our p0.1 equals our minimum")
for nm, lbl in (("border_red", "border"), ("ring_red", "ring"),
                ("seal_block_red_lower_left", "seal block"),
                ("small_seal_red_lower_right", "small seal")):
    add("reds", "%s red saturation" % lbl, "",
        "All four of our reds are desaturated by about a third, uniformly. The "
        "reference red is a near-pure vermilion whose blue channel sits at 21/255; "
        "ours sits at 72/255, and that blue is what makes it read brick-pink instead "
        "of cinnabar. The hue angle is not the problem - ours is 5.4 deg against the "
        "reference's 4.5 deg, which is fine.",
        path="reds/per_element/%s/hsv_stored/s" % nm, fmt="%.4f")
add("whole tag", "black ink mass fraction", "of tag",
    "The coverage shortfall is almost entirely black. Red is 17 % short, black is 39 % "
    "short. Adding red will make the tag worse, not better.",
    path="coverage/total/black_ink_mass_frac", fmt="%.4f")
add("whole tag", "total ink mass fraction", "of tag",
    "Confirms and sharpens the earlier review: not 'about a fifth', 26.8 % less ink "
    "mass than V1 and 33.6 % less than V2. Measured as the mean of ink opacity over "
    "the paper, so kasure holes and soft halos are counted at their real weight.",
    path="coverage/total/ink_mass_frac", fmt="%.4f")
add("whole tag", "black area / red area", "",
    "The reference is 1.45 parts black to 1 part red and V1 and V2 agree on that to "
    "3.7 %. We are at 1.00. Our tag is half again too red for its black, which is the "
    "composition error behind 'reads airier'.",
    path="coverage/total/black_over_red_area", fmt="%.3f")
add("centre glyph", "centre glyph ink mass", "of tag",
    "The 爆 carries 46 % less ink than the reference's. It is smaller AND lighter, so "
    "the two errors compound.",
    path="coverage/per_element/centre_glyph_black/ink_mass_frac_of_tag", fmt="%.5f")
add("centre glyph", "centre glyph bounding width", "mm",
    "The reference glyph runs 59.7 mm across a 70 mm sheet - it very nearly touches "
    "the columns. Ours is inset about 6 mm on each side.",
    path="elements/centre_glyph/size_mm/0", fmt="%.1f")
add("centre glyph", "centre glyph bounding height", "mm",
    "With the width, our glyph's bounding area is 33 % smaller than the reference's.",
    path="elements/centre_glyph/size_mm/1", fmt="%.1f")
SMEAR = (g(M_["V2"], "coverage/total/ink_mass_frac")
         / g(M_["V1"], "coverage/total/ink_mass_frac"))
for nm, lbl in (("upper_left_column", "upper-left column 火遁術"),
                ("upper_right_column", "upper-right column 爆炎陣"),
                ("lower_right_column", "lower-right 焼尽"),
                ("lower_centre_column", "lower-centre 瞬業")):
    tgt = g(M_["V2"], "coverage/per_element/%s_black/ink_mass_frac_of_tag" % nm) / SMEAR
    add("text columns", "%s - ink mass" % lbl, "of tag",
        "Measured against V2 de-smeared, NOT against V1: V1's side columns are "
        "pseudo-glyphs and carry far less ink than the real kanji we ship, so using "
        "V1 here would let us off. On the honest target the text blocks are the "
        "second-worst shortfall after the centre glyph - collectively we lay about "
        "40 % of the ink these four blocks should carry. Thin strokes, too much air "
        "between them, and the same pale ink as everywhere else.",
        ref=tgt, path="coverage/per_element/%s_black/ink_mass_frac_of_tag" % nm,
        fmt="%.5f")
add("flame emblem", "flame emblem - ink mass", "of tag",
    "The one element we OVER-ink, and both references agree on the target (V1 "
    "0.01581, V2 0.01653, so this is not a pseudo-glyph artefact). Our emblem is 45 % "
    "heavier than it should be, which makes it compete with the centre glyph instead "
    "of sitting above it. Shrinking it is part of giving the 爆 its 59.7 mm back.",
    path="coverage/per_element/flame_emblem_black/ink_mass_frac_of_tag", fmt="%.5f")
add("black ink", "loaded-to-dry gradient down a column", "alpha, top to bottom",
    "This one inverts the expected answer, so it is worth stating plainly. The "
    "reference has NO density ramp: its black is opaque at alpha 0.99 at the top of "
    "every column and 0.99 at the bottom, and all of its dry-brush character comes "
    "from holes punched clean through an otherwise solid fill. We do the opposite - a "
    "semi-transparent wash that additionally fades 3.5 to 6.7 alpha points down each "
    "column. Fixing this means making the fill opaque and taking the dryness out in "
    "holes, not ramping density.",
    ref_s="-0.001 to +0.001 (flat, alpha 0.99 throughout)",
    ours_s="-0.035 to -0.067 (fades toward the bottom)",
    delta_s="we ramp where the reference does not")
add("enso ring", "ring stroke width", "mm",
    "The 'leaner ring' quantified from the polar radii: a 6.15 mm brush against our "
    "4.28 mm. V2 independently says 6.31 mm.",
    path="derived/ring_stroke_width_mm", fmt="%.2f")
add("enso ring", "ring kasure hole area fraction", "of stroke",
    "The reference's ring is dense ink with 21 % of its area punched out by dry-brush "
    "holes. Ours is 9 %, so ours reads as a thin even wash rather than a loaded brush "
    "running dry. Note our holes are already the right size (0.31 mm against 0.30 mm "
    "median), the right shape (elongation 4.8 against 4.2) and correctly aligned with "
    "the stroke (88 % within 30 deg of the tangent against 83 %, where random would be "
    "33 %). There are simply not enough of them and the ink around them is not dark "
    "enough.",
    path="kasure_dry_brush/enso_ring/hole_area_fraction_of_stroke", fmt="%.4f")
add("enso ring", "ring kasure hole count", "",
    "170 holes against 60 over a comparable stroke area.",
    path="kasure_dry_brush/enso_ring/hole_count", fmt="%.0f")
add("centre glyph", "kasure hole count in the centre glyph", "",
    "182 against 71 at a similar total hole area (7.3 % against 6.9 %), so our glyph's "
    "breakup is the right amount of missing ink distributed into too few, too large "
    "gaps. Break the same area into 2.5x as many holes.",
    path="kasure_dry_brush/centre_glyph_black/hole_count", fmt="%.0f")
add("enso ring", "ring ink mass", "of tag",
    "Follows from the thinner stroke and the paler red.",
    path="coverage/per_element/enso_ring_red/ink_mass_frac_of_tag", fmt="%.5f")
add("enso ring", "ring outer edge roughness RMS", "mm",
    "Our ring's outer edge is about half as ragged as the reference's.",
    path="stroke_edge_roughness/enso_ring_polar/outer/roughness_rms_mm", fmt="%.3f")
add("enso ring", "ring edge raggedness wavelength", "mm",
    "Ours is not only shallower, it is a longer, smoother undulation: the reference "
    "wobbles roughly twice as often along the edge (45 cycles per revolution against "
    "26). Shallow plus slow is exactly what reads as 'drawn with a vector tool'.",
    path="stroke_edge_roughness/enso_ring_polar/outer/dominant_wavelength_mm_along_edge",
    fmt="%.2f")
add("reds", "weight spread of the same red across elements", "alpha_R",
    "The reference uses ONE red pigment at four different laid-on weights: the border "
    "is the heaviest at alpha_R 0.59, the small seal the lightest at 0.38, a spread of "
    "0.215. We lay all four at essentially one weight, spread 0.105 and the border is "
    "our LIGHTEST red rather than our heaviest. Vary the weight, never the hue.",
    path="derived/red_weight_spread_alpha_R", fmt="%.4f")
add("reds", "border red opacity (alpha on the red channel)", "",
    "The reference's border is the darkest red on the sheet, carrying nearly 45 % more "
    "pigment than its own ring. Ours is the lightest.",
    path="reds/per_element/border_red/opacity_over_paper/alpha_R", fmt="%.4f")
add("paper", "paper base colour, centre of the tag, stored sRGB", "",
    "Our paper hue is right (40.06 deg against 40.35) and its saturation is close "
    "(0.228 against 0.198). The error is value: 218 against 246 on the red channel, "
    "0.597 against 0.799 in linear luma. Our sheet is a kraft tan; the reference's is "
    "a pale cream.",
    ref_s="#F6E6C5 (246,230,197), linear luma 0.799",
    ours_s="#DAC9A8 (218,201,168), linear luma 0.597",
    delta_s="-25.3% linear luma, -28/255 on R")
add("paper", "paper plateau linear luma", "",
    "The same error stated as the denominator of the contrast ratio. Note that "
    "lightening the paper alone would fix only a quarter of the contrast gap; the ink "
    "has to come down too.",
    path="paper/edge_darkening/plateau_luma_lin", fmt="%.4f")
add("paper", "edge darkening depth at the rim", "%",
    "Ours burns deeper at the rim and recovers far more slowly: 95 % of plateau at "
    "14.75 mm against the reference's 7.25 mm, so our vignette eats a fifth of the "
    "card width where the reference's eats a tenth.",
    path="paper/edge_darkening/depth_at_outer_0_5mm_pct", fmt="%.1f")
add("paper", "edge darkening unevenness across the four sides", "of plateau",
    "The reference's four edges agree to 1.5 points of plateau luminance - the ageing "
    "is even all the way round. Ours disagree by 12.4 points, with the right edge "
    "markedly darker than the left. Nothing in either reference does that, and it is "
    "the kind of asymmetry that reads as a bug rather than as wear.",
    path="paper/edge_darkening_evenness/spread_max_minus_min", fmt="%.4f")
add("paper", "whole-sheet lighting tilt, top to bottom", "% of plateau luma",
    "A plane fitted to the paper luminance tilts by under 0.8 % across either axis in "
    "both references - they are evenly lit sheets. Ours tilts +5.3 % down the height "
    "and -2.5 % across the width, so our paper is measurably brighter at the bottom. "
    "Together with the 12.4-point edge unevenness this is the second half of the same "
    "problem: our ageing has a direction, and the reference's does not.",
    path="paper/global_gradient/pct_across_height", fmt="%+.2f")
add("paper", "corner chamfer, mean run along an edge", "mm",
    "Measured from the paper support, not from our spec: the reference cuts about "
    "8.0 mm off each corner (V1 8.09, V2 7.96) and we cut 7.58. Small, but it is a "
    "free 0.5 mm and it changes the silhouette at thumbnail size.",
    path="support/corner_chamfer/mean_mm", fmt="%.2f")
add("paper", "mottle power in the 1-3 mm band", "of mottle power",
    "Our stain amplitude is fine (RMS 2.48 % against 2.02 %) but its scale is wrong: "
    "86 % of our mottle power sits in the 3-10 mm band against the reference's 71 %, "
    "and we have only half its 1-3 mm content. Our correlation length is 1.05 mm "
    "against 0.79 mm. The result is a soft gradient where the reference has foxing.",
    path="mottle_and_stains/spectrum/band_power_fraction/1_to_3mm", fmt="%.4f")
add("paper", "area of stains darker than 6 %", "of tag",
    "We have 3.7x the deep-stain area, and 15 patches darker than 10 % where V1 has "
    "none at all. We are over-staining the paper while under-inking the art, which is "
    "the worst of both.",
    path="mottle_and_stains/stains/darker_than_6_pct/total_area_frac_of_tag", fmt="%.5f")
add("paper", "paper fibre grain amplitude", "% of paper luma",
    "Our paper grain is a little over half the reference's depth, so the sheet reads "
    "smooth and printed rather than laid. Measured at native resolution on clean "
    "paper patches, so it is not a rectification artefact.",
    path="paper_fibre_texture/residual_rms_pct_of_paper_luma", fmt="%.2f")
add("paper", "paper fibre anisotropy", "max/min angular power",
    "The reference's grain is nearly isotropic. Ours has a strong directional streak "
    "with its power lobe centred near 125 deg. CAVEAT: only two clean native patches "
    "were available on our busy card, so treat the exact angle as indicative; the "
    "presence of a strong streak is solid, since the reference measures 1.9 on the "
    "same estimator with three patches.",
    path="paper_fibre_texture/anisotropy_max_over_min", fmt="%.2f")
add("paper", "fold or crease shading baked into the basecolour", "",
    "Neither reference has any fold, crease or internal shadow - both are flat, evenly "
    "lit sheets, and the band-pass detector finds no spanning line in either. Our "
    "basecolour carries two horizontal crease lines at 51.6 mm and 104.4 mm covering "
    "46 % and 51 % of the tag width. The mesh already has real creases, so this is "
    "shading counted twice, and it is shading the reference does not have at all.",
    ref_s="none", ours_s="2 lines, at v 0.331 (51.6 mm) and v 0.669 (104.4 mm)",
    delta_s="we bake creases the reference does not have")
add("black ink", "modulation depth within one stroke", "swing / own median",
    "In absolute 8-bit terms our strokes look as varied as the reference's (14.3/255 "
    "against 13.4/255) but that flatters a light ink. Against each stroke's own "
    "median value, the reference modulates by 0.84 and we modulate by 0.22. Their "
    "ink varies from deep to very deep; ours barely varies at all.",
    path="derived/black_modulation_depth", fmt="%.3f")
add("ink edges", "soft halo beyond raster anti-aliasing", "mm",
    "The one place we are HEAVIER than the reference. Both rasters must show about one "
    "native pixel of anti-aliasing at any stroke edge; the excess over that is real "
    "bleed, and ours is 0.172 mm against 0.112 mm. Softer edges on lighter ink is what "
    "makes the tag read printed-and-blurred rather than brushed.",
    path="ink_bleed/black/soft_halo_beyond_antialiasing_mm", fmt="%.4f")
add("enso ring", "ring ellipticity, height / width", "",
    "Ours is a taller oval than either reference. V1 says 1.154 and V2 corrected for "
    "its own stretch says 1.062, so the reference ring is close to round.",
    path="segmentation/ring_fit/ellipticity_h_over_w", fmt="%.3f")
add("enso ring", "ring centre position", "mm from the tag's top-left corner",
    "Small but worth closing: the reference centres the ring on the vertical midline "
    "at 77.2 mm down and 35.5 mm across. Ours sits 1.4 mm to the right and 1.6 mm low.",
    ref_s="(35.47, 77.22) mm", ours_s="(36.87, 78.78) mm",
    delta_s="+1.40 mm x, +1.56 mm y")

for i, d in enumerate(DELTAS):
    d["rank"] = i + 1

# ------------------------------------------------- final json
OUT = {
    "what_this_is": "Ink, colour, ageing and texture metrology of the two paper-bomb "
                    "reference images and of our shipped basecolour map, so a later "
                    "pass can match the reference element by element and prove it. "
                    "Numbers and descriptions only: no pixel of either reference is "
                    "reproduced, traced, masked, vectorised or derived into anything a "
                    "build can consume.",
    "role": "ink and colour metrologist",
    "sources_measured_at": {
        p: {"mtime": __import__("datetime").datetime.fromtimestamp(
                os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S"),
            "bytes": os.path.getsize(p)}
        for p in ["C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/"
                  "paperbomb_guide.png",
                  "C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/"
                  "paperbomb_guide_v2_real_glyphs.png",
                  "C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/"
                  "T_PaperBomb_BC.png",
                  "C:/Users/Cody/Desktop/Blender_Projects/Renders/PaperBomb/"
                  "paperbomb_front.png"] if os.path.exists(p)},
    "sources_measured_at_note": "the fix pass rewrote our maps while this pass ran, so "
                                "OURS was re-measured against the rebuilt files and "
                                "came back identical to the digit. If the timestamps "
                                "above are older than the build you are holding, "
                                "re-run stage2_measure.py -- OURS and stage3/stage4 "
                                "before trusting any OURS number.",
    "sources": {
        "V1": "References/PaperBomb/paperbomb_guide.png, 1024x1536 RGB8",
        "V2": "References/PaperBomb/paperbomb_guide_v2_real_glyphs.png, 300x653 RGBA8",
        "OURS_basecolour": "Exports/PaperBomb/Textures/T_PaperBomb_BC.png, front island "
                           "at atlas px (16,16), card 904.61 x 2015.99 px at 12.923 px/mm",
        "OURS_render": "Renders/PaperBomb/paperbomb_front.png, colour statistics only",
    },
    "conventions": {
        "coordinates": "origin at the TAG's top-left paper corner (not the image "
                       "canvas), x right, y down; u = x/W and v = y/H, plus "
                       "millimetres on the shipped 70.0 x 156.0 mm card via u*70 and "
                       "v*156.",
        "stored_vs_linear": "'stored' is the 8-bit number in the PNG divided by 255, "
                            "i.e. sRGB-encoded; 'linear' applies the sRGB EOTF. A PNG "
                            "carries no colourspace tag, so this was pinned down "
                            "empirically: the IDAT was decoded directly and compared "
                            "against Blender's Image.pixels, which returned the stored "
                            "value to the last bit for 8-bit PNGs. See "
                            "debug/probe01.json, key _blender_pixels_crosscheck. Every "
                            "hex value quoted here is stored sRGB.",
        "alpha": "ink opacity alpha = 1 - (linear green / local paper field green). The "
                 "local paper field is a masked box blur of paper-classified pixels at "
                 "4.5 % of the tag width, refined three times, so edge darkening and "
                 "stains belong to the paper and are not miscounted as ink. Green is "
                 "the channel both black and red absorb, and redness = cR - cG "
                 "separates them.",
        "ink_mass_vs_area": "'area fraction' counts pixels over a threshold; 'ink mass "
                            "fraction' is the mean of alpha over the paper, so kasure "
                            "holes and soft halos count at their real weight. Ink mass "
                            "is the number that tracks what the eye integrates.",
        "denominator": "every area fraction is a fraction of the paper OCTAGON (the "
                       "rectangle less the four corner chamfers), with a 0.30 mm rim "
                       "excluded so the paper/background anti-aliasing cannot leak in.",
    },
    "rectification": {
        "finding": "Neither reference needed a rotation or keystone correction worth "
                   "applying. Both tags are axis-aligned to better than 0.04 degrees "
                   "and square to better than 0.05 %.",
        "correction_applied": "none beyond a sub-pixel crop to the fitted paper "
                              "rectangle, then a bilinear resample to a common "
                              "840 x 1872 grid (12 px/mm) so all three sources share "
                              "one frame. Every high-frequency statistic (fibre "
                              "spectrum, kasure hole size, edge roughness) was measured "
                              "at NATIVE resolution instead, to keep the resample out "
                              "of it.",
        "how_found": "the paper edge was located per row and per column at the "
                     "half-maximum of the warmth signal R-B, which separates cream "
                     "paper and red ink from the neutral white background and its "
                     "neutral drop shadow; the four edges were then fitted by trimmed "
                     "least squares over the straight runs between the corner "
                     "chamfers, and the corners taken as the intersections.",
        "first_attempt_that_failed": "an adaptive threshold set from a high percentile "
                                     "landed ABOVE the paper level and traced the ink "
                                     "instead of the paper, which produced a spurious "
                                     "5.85 degree bottom edge on V1. The half-maximum "
                                     "between the measured background and paper levels "
                                     "is what fixed it.",
        "per_source": {k: {
            "edge_angles_deg": GEO[k]["edge_angles_deg"],
            "keystone": GEO[k]["keystone"],
            "corners_px": GEO[k]["corners_px"],
            "tag_px_w_h": [round(GEO[k]["widths_px"]["top"], 2),
                           round(GEO[k]["widths_px"]["left_height"], 2)],
            "aspect_h_over_w": GEO[k]["aspect_h_over_w"],
            "source_px_per_mm": GEO[k]["source_px_per_mm"],
            "corner_chamfer_mm": g(M_[k], "support/corner_chamfer/mean_mm"),
        } for k in ("V1", "V2")},
    },
    "headline": {
        "ink_coverage": "V1 total ink mass 0.3035 of the tag, V2 0.3345, ours 0.2221. "
                        "The earlier review's 'about a fifth less' is an understatement: "
                        "26.8 % less than V1, 33.6 % less than V2.",
        "which_elements_are_short": "black, not red. Black ink mass is 39.1 % short "
                                    "(0.1742 -> 0.1061); red is 17.3 % short "
                                    "(0.1161 -> 0.0960). The black:red area ratio has "
                                    "collapsed from 1.449 to 1.002. Worst elements, in "
                                    "order: the four text columns at 44-68 % short "
                                    "(measured against V2 de-smeared, because V1's "
                                    "columns are pseudo-glyphs and would let us off), "
                                    "the centre glyph at 46.4 % short, the enso ring at "
                                    "27.1 % short, the seal block at 19.3 % short. One "
                                    "element is OVER-inked: the flame emblem, 44.5 % "
                                    "heavy, on which both references agree.",
        "but_coverage_is_not_the_main_problem": "the contrast ratio is. Paper:ink "
                                                "luminance is 153.5:1 in V1, 202.7:1 in "
                                                "V2, 11.2:1 in our basecolour and "
                                                "15.9:1 in our render. Even if coverage "
                                                "were matched exactly, ink at 1/11 of "
                                                "paper luminance would still read airy.",
        "reds": "same pigment throughout the reference - hue spread 1.14 deg, "
                "saturation spread 0.021 - laid at four different weights (alpha_R "
                "0.375 to 0.590). Ours is one weight at one third less saturation.",
        "paper": "hue is right (40.1 deg vs 40.4), saturation is close (0.228 vs "
                 "0.198), value is 25 % too dark, the rim burn is too deep and too "
                 "broad, and it is 12.4 points uneven between the left and right edges "
                 "where the reference is even to 1.5 points.",
    },
    "measurements": {"V1": M_["V1"], "V2": M_["V2"], "OURS_basecolour": M_["OURS"],
                     "OURS_render_colour_only": REND},
    "v1_v2_disagreements": V1V2,
    "our_build_deltas": DELTAS,
    "uncertain": [
        "Paper fibre anisotropy for our build (17.2) rests on only two clean native "
        "patches, because our card leaves few large ink-free squares. The angle near "
        "125 deg is indicative; the existence of a strong streak is solid.",
        "V2's fibre spectrum, kasure hole sizes and edge-roughness wavelengths are at "
        "or past its 1.96 cycles/mm Nyquist limit and should not be used at all. Its "
        "value as a reference is the identity and placement of the text.",
        "The reference images are finished illustrations with their own rendering; our "
        "basecolour is an albedo map. Absolute values are therefore not strictly "
        "comparable, which is exactly why the paper:ink contrast RATIO is quoted, and "
        "why the shipped render was measured as well. Both say the same thing.",
        "The 'ink bleed' halo of 0.11 mm in V1 is close to one source pixel (0.114 mm). "
        "It is real but small; the safest reading is that the reference has almost no "
        "bleed and our 0.172 mm is softer than it should be.",
        "Our black core statistics come from the basecolour's clamped floor at 62/255. "
        "If that floor is a deliberate PBR albedo decision it should be stated, but "
        "the render still only reaches a 15.9:1 contrast against the reference's 153:1, "
        "so the decision does not currently survive contact with the reference.",
        "Element windows for the side columns and seals are fixed fractional boxes; "
        "the ring and the centre glyph are fitted from the image. Per-element coverage "
        "for the column and seal windows is therefore accurate to the window, not to "
        "the glyph outline.",
    ],
    "provenance": {
        "how_measured": "Blender 5.2 headless, factory startup, numpy only. PNGs were "
                        "decoded from their IDAT chunks by "
                        "reference_metrology/pngread.py so that stored 8-bit values "
                        "are exact and no colour management is involved.",
        "scripts": ["pngread.py", "metro.py", "tagmeas.py", "stage1_rectify.py",
                    "stage2_measure.py", "stage2b_render_colour.py",
                    "stage3_assemble.py"],
        "nothing_derived_was_shipped": "no crop, mask, trace, outline, threshold or "
                                       "any other image derived from either reference "
                                       "was written anywhere a build could read it. "
                                       "Intermediate rectified arrays live only in the "
                                       "session scratchpad; the only images written "
                                       "under the project are schematics drawn from "
                                       "measured numbers, in debug/, prefixed "
                                       "DEBUG_NEVER_SHIP.",
    },
}

dst = HERE + "/ink_colour.json"
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, ensure_ascii=False)
print("wrote", dst, os.path.getsize(dst), "bytes;", len(DELTAS), "deltas,",
      len(V1V2), "v1/v2 rows")
for d in DELTAS[:6]:
    print("  %2d %-13s %-44s %-30s %-30s %s"
          % (d["rank"], d["element"], d["metric"], d["reference"], d["ours"], d["delta"]))
