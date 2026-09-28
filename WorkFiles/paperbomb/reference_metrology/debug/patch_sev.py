# -*- coding: utf-8 -*-
"""One-shot: insert explicit severity ranks into stage3_assemble.py's add() calls."""
import io
import re

p = (r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/"
     r"reference_metrology/stage3_assemble.py")
s = io.open(p, encoding="utf-8").read()

SEV = [
    ("derived_contrast/paper_over_black_contrast_ratio", 1),
    ("black_ink/colour_core/linear_luma_median", 2),
    ("reds/per_element/%s/hsv_stored/s", 3),
    ("coverage/total/black_ink_mass_frac", 4),
    ("coverage/total/ink_mass_frac", 5),
    ("coverage/total/black_over_red_area", 6),
    ("coverage/per_element/centre_glyph_black/ink_mass_frac_of_tag", 7),
    ("elements/centre_glyph/size_mm/0", 8),
    ("elements/centre_glyph/size_mm/1", 9),
    ("segmentation/ring_fit/stroke_width_mm_on_x_axis", 10),
    ("kasure_dry_brush/enso_ring/hole_area_fraction_of_stroke", 11),
    ("kasure_dry_brush/enso_ring/hole_count", 12),
    ("coverage/per_element/enso_ring_red/ink_mass_frac_of_tag", 13),
    ("stroke_edge_roughness/enso_ring_polar/outer/roughness_rms_mm", 14),
    ("stroke_edge_roughness/enso_ring_polar/outer/dominant_wavelength_mm_along_edge", 15),
    ("paper/edge_darkening/plateau_luma_lin", 16),
    ("paper/centre_44pct_box/hsv_stored/s", 17),
    ("paper/edge_darkening_evenness/spread_max_minus_min", 18),
    ("paper/edge_darkening/depth_at_outer_0_5mm_pct", 19),
    ("paper_fibre_texture/residual_rms_pct_of_paper_luma", 20),
    ("mottle_and_stains/spectrum/band_power_fraction/1_to_3mm", 21),
    ("mottle_and_stains/stains/darker_than_6_pct/total_area_frac_of_tag", 22),
    ("paper_fibre_texture/anisotropy_max_over_min", 23),
    ("reds/per_element/border_red/opacity_over_paper/alpha_R", 24),
    ("black_ink/within_stroke_variation/stored_value_p5_p95_span_8bit", 25),
    ("kasure_dry_brush/all_black_outside_ring/hole_count", 26),
    ("ink_bleed/black/soft_halo_beyond_antialiasing_mm", 27),
    ("segmentation/ring_fit/ellipticity_h_over_w", 28),
    ("segmentation/ring_fit/centre_mm/0", 29),
]

n = 0
for path, rank in SEV:
    needle = '"' + path + '"'
    idx = s.find(needle)
    if idx < 0:
        print("MISS", path)
        continue
    st = s.rindex("add(", 0, idx)
    m = st + 4
    depth = 1
    while depth > 0:
        if s[m] == "(":
            depth += 1
        elif s[m] == ")":
            depth -= 1
        m += 1
    call = s[st:m]
    if "sev=" in call:
        continue
    body = call[:-1].rstrip()
    if body.endswith(","):
        body = body[:-1]
    s = s[:st] + body + ", sev=%d)" % rank + s[m:]
    n += 1

io.open(p, "w", encoding="utf-8").write(s)
print("patched", n, "add() calls;", s.count("sev="), "now carry a rank")
