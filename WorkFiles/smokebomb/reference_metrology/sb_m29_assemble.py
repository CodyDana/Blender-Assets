"""Stage 29: assemble reference_spec.json (machine twin of References/SmokeBomb/REFERENCE_SPEC.md) from the
stage outputs + the by-eye strip/crossing reading. Every row carries a tolerance."""
import sys, os, json, hashlib
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
s1 = L.load("sb_s1_silhouette.json"); s18 = L.load("sb_s18_fits.json"); s20 = L.load("sb_s20_light_colour.json")
s21 = L.load("sb_s21_weave.json"); s22 = L.load("sb_s22_silh_fray.json"); s23 = L.load("sb_s23_bands.json")
s24 = L.load("sb_s24_light2.json"); s27 = L.load("sb_s27_streaks.json")
D = 2 * S.R


def row(value, tol, unit, how, **kw):
    r = dict(value=value, tol=tol, unit=unit, method=how); r.update(kw); return r


def fr(px):
    return round(px / D, 4)


spec = {}
spec['meta'] = dict(
    reference=REF.replace("C:/Users/Cody/Desktop/Blender_Projects/", ""), sha256=hashlib.sha256(open(REF, 'rb').read()).hexdigest(),
    size_px=[1254, 1254], identical_to="Downloads/smokebomb.png (same sha256)", measured="2026-09-21",
    role="reference metrologist (claude)", status="MEASURED unless a row says DESIGNED",
    units="px = reference pixels; D = ball diameter in the reference = %.1f px; frac_D = px / D; arc angles on the sphere in degrees" % D,
    image_frame="x right, y down, origin top-left pixel corner",
    image_angle="degrees CCW from the 3 o'clock direction about the ball centre, y up (90 = 12 o'clock, 180 = 9 o'clock, 270 = 6 o'clock)",
    camera_frame="X right, Y up, Z toward the camera; lat/lon: lat from the X-Z plane toward +Y, lon from +Z (facing the camera) toward +X (right)",
    back_projection="orthographic about the silhouette circle (centre %.2f, %.2f; R %.2f px) -- see camera.projection" % (S.CX, S.CY, S.R),
    scripts="WorkFiles/smokebomb/reference_metrology/sb_m00..sb_m29 (Blender 5.2 Python, NumPy 2)",
    debug_diagram="WorkFiles/smokebomb/reference_metrology/debug/DEBUG_NEVER_SHIP_sb_strip_layout_LABELLED.png",
    trace_file="WorkFiles/smokebomb/reference_metrology/sb_trace.json (measurement use only; the build must not read it or the reference pixels)",
    colour_values="stored sRGB 0-1 unless named _lin")

# ---------------- silhouette ----------------
c = s1['circle']; e = s1['ellipse']
steps4 = [s for s in s22['steps'] if abs(s['jump_px']) >= 4]
spec['silhouette'] = dict(
    edge_rule="half-maximum between the background (stored lum %.3f) and the cloth just inside the rim (%.3f)" % (s1['bg_lum'], s1['rim_lum']),
    centre_px=row([round(c['cx'], 2), round(c['cy'], 2)], "+-3 px", "px", "geometric circle fit to 3600 radial edge samples"),
    diameter_px=row(round(2 * c['r'], 1), "+-1.0 %", "px", "circle fit", frac_of_frame_width=round(2 * c['r'] / 1254, 4)),
    circularity_rms_dev=row(round(c['rms'] / c['r'] * 100, 2), "build 0.8..1.8", "% of R", "rms radial deviation from the fitted circle",
                            px=round(c['rms'], 2)),
    max_out_in=row([round(c['max'], 1), round(c['min'], 1)], "+-4 px each", "px", "largest outward / inward radial departure"),
    ellipse_axes_px=row([round(e['b'], 1), round(e['a'], 1)], "+-3 px", "px", "direct LSQ ellipse; long axis along image angle 125 deg (upper-left to lower-right), ratio %.4f" % (e['b'] / e['a']),
                        long_axis_image_angle_deg=125, long_axis_tol_deg=20),
    harmonics_px={k: round(v['amp_px'], 2) for k, v in s1['harmonics'].items() if int(k) <= 8},
    sectors_30deg=[dict(from_deg=s['from_deg'], to_deg=s['to_deg'], dev_pct_R=s['dev_pct_R']) for s in s22['sectors']],
    flattening=row(["30-60 deg: -1.75 %R", "180-210 deg: -1.67 %R"], "+-0.7 %R", "%R", "sector mean radius vs fitted R"),
    bulge=row(["120-150 deg: +1.83 %R", "88 deg (top, at the whorl): local +14.9 px = +3.2 %R over ~6 deg"], "+-0.7 %R; top bump +-5 px", "%R", "sector mean / high-pass peak"),
    outline_bumpiness=row(round(s1['hp_rms'] / c['r'] * 100, 2), "0.5..1.0", "% of R (rms)", "radius minus its n<=6 Fourier reconstruction",
                          px_rms=round(s1['hp_rms'], 2), px_range=[round(s1['hp_min'], 1), round(s1['hp_max'], 1)]),
    strip_edge_steps=row(dict(count_ge_4px=len(steps4), median_abs_px=round(float(np.median([abs(s['jump_px']) for s in steps4])), 1),
                              max_abs_px=round(float(max(abs(s['jump_px']) for s in steps4)), 1)),
                         "count 8..16; median 4.5..7 px; max <= 10 px", "px", "radius jumps > 4 px within 0.5 deg of arc",
                         where_deg=[s['deg'] for s in steps4]),
    thread_tips_past_outline=row(dict(max_reach_px=7.4, n_reach_gt_3px=len(s22['wisps_gt3px'])), "max <= 9 px; no thread longer than 10 px beyond the outline",
                                 "px", "outermost 97%-of-step crossing minus the 50% edge",
                                 note="only fibre fuzz and one small hook (T4, image angle ~155 deg) break the outline; no loose thread hangs off the ball"),
    no_features=["no fuse", "no knot", "no tag", "no cord", "no tear, cut, scorch or dirt", "no free strip end anywhere on the visible side"])

# ---------------- camera ----------------
spec['camera'] = dict(
    projection=row("orthographic (long-lens equivalent)", "use orthographic for the comparison render", "-",
                   "a centred sphere's outline is a circle at every focal length and the reference has no other perspective cue; the spec's sphere positions were back-projected orthographically, so an orthographic camera reproduces them exactly. With a 100 mm FF lens a point 45 deg from the view axis lands 9 % R further out than orthographic, with 200 mm 4.7 % R -- so do not mix a perspective camera with these numbers."),
    ortho_scale=row(round(1254 / D, 4), "+-1 %", "D per frame width", "frame width / ball diameter"),
    frame=row([1254, 1254], "exact aspect 1:1", "px", "file size"),
    ball_centre_in_frame=row([round(S.CX, 1), round(S.CY, 1)], "+-3 px", "px", "circle fit"),
    elevation=row(0.0, "convention", "deg",
                  "a sphere on a seamless white ground has no horizon, no contact shadow and no ground plane, so elevation is not measurable. The strip layout is specified in the camera frame; rendering at elevation 0 with the ball oriented as specified IS the reference view.",
                  alternative_if_top_whorl_is_world_up=dict(camera_elevation_deg=34.6, tol=5, whorl_lean_in_frame_deg_right_of_vertical=9.4, status="DERIVED convenience, not a second measurement")),
    background=row(dict(stored=0.996, rgb_8bit=[254, 254, 254]), "+-0.004", "stored sRGB", "all four corners and rings 25..240 px outside the ball: mean 0.9960, std 0.002; uniform, no gradient, no shadow, no ground line"),
    focal_length_note="any lens >= 85 mm FF also explains the outline; not measurable")

# ---------------- lighting ----------------
spec['lighting'] = dict(
    method="16 px blocks, 75th percentile of linear luminance (the lit top of the cloth, crevices excluded), fitted on the sphere normals",
    key=row(dict(az_deg=s24['key']['az_deg'], el_deg=s24['key']['el_deg'], dir_to_light=s24['key']['vec']), "az +-25, el +-10", "deg (camera frame; az + = right, el + = up)", "key+fill+ambient Lambert fit, alternating grid search"),
    fill=row(dict(az_deg=s24['fill']['az_deg'], el_deg=s24['fill']['el_deg'], dir_to_light=s24['fill']['vec']), "az +-25, el +-15", "deg", "same fit; lights the LEFT limb from the left-rear"),
    fill_over_key=row(round(s24['fill_over_key'], 2), "+-0.2", "ratio", "fit coefficients"),
    ambient_over_key=row(round(s24['ambient_over_key'], 2), "+-0.15", "ratio", "fit coefficients"),
    softness=row("large soft sources: no terminator line, no cast shadow, shading ramps smoothly (wrap ~0.1); brightest visible normal (0.22, 0.89, 0.40), darkest (-0.09, -0.56, 0.82), max/min 4.15",
                 "max/min 3.2..5.2", "-", "order-2 SH irradiance fit, R2 %.2f" % s24['sh2']['R2']),
    quadrant_targets_lin=row(s20['lighting']['quadrants'], "each +-15 % after the render's overall exposure is matched at the centre", "linear luminance (block p75)", "same block statistic -- measure the builder's render the same way"),
    specular=row("none: no glossy hot spot anywhere; highlights are only fibre/rim sparkle (see cloth.sheen)", "-", "-", "p99.9 of the disc is 0.615 stored and lives on fibres and rolled edges"))

# ---------------- colour / albedo ----------------
alb = s23['albedo']
k = 0.043 / (0.2126 * 0.378 + 0.7152 * 0.325 + 0.0722 * 0.298)
alb_rgb = np.array([0.378, 0.325, 0.298]) * k
spec['colour'] = dict(
    albedo_lum_lin=row(round(alb['median'] * (s20['lighting']['lambert_ambient']['a'] + s20['lighting']['lambert_ambient']['b']), 4), "+-0.010", "linear reflectance",
                       "region mean linear luminance / modelled irradiance, irradiance scaled so a perfect white facing the key reads 1.0 (the backdrop reads 0.996). If the backdrop was lit hotter than the ball (common), the true albedo is higher; 0.043 matches the kunai wrap's dark cotton (~0.04)."),
    albedo_rgb_lin=row(alb_rgb.round(4).tolist(), "each +-25 %", "linear", "albedo luminance x measured chromaticity"),
    albedo_rgb_srgb=row(L.lin_to_srgb(alb_rgb).round(3).tolist(), "+-0.03", "stored sRGB", "same", hex="#%02X%02X%02X" % tuple((L.lin_to_srgb(alb_rgb) * 255).round().astype(int))),
    chromaticity_lin=row([0.378, 0.325, 0.298], "r +-0.012, g +-0.008", "r/(r+g+b)...", "pooled region means (all strips agree within r 0.375-0.386)"),
    hue_deg=row(20.5, "+-4", "deg (HSV, sRGB)", "region means: 17.5..23.9"),
    saturation_hsv=row(0.13, "+-0.03", "-", "region means 0.113..0.160 (darker regions read slightly more saturated)"),
    band_to_band=row("no strip-to-strip colour difference beyond lighting: chromaticity identical within 1.5 %%; shading-normalised luminance spread (cv %.2f) follows the lighting-model residual (left limb reads bright, bottom reads dark), not the strips" % alb['cv'],
                     "build: one BC for all strips, per-strip variation <= 5 %", "-", "11 regions", regions={k_: v['albedo_white1'] for k_, v in alb['regions'].items()}),
    pixel_targets_srgb=row({k_: round(v, 4) for k_, v in s20['disc_lum_srgb_percentiles'].items()}, "p10/p50/p90 each +-12 %", "stored sRGB luminance, disc r<0.9R",
                           "what the viewer sees: the render of the shipped asset must reproduce these under the specified camera and light"),
    region_means_srgb={k_: v['mean_srgb'] for k_, v in s20['colour']['regions'].items()})

# ---------------- cloth ----------------
spec['cloth'] = dict(
    construction=row("plain-weave cotton-like tape, warp-faced: the visible texture is striations ALONG each strip; the cross (weft) structure is a faint irregular grid",
                     "-", "-", "FFT of 64 px patches in 7 strips: 39-58 % of texture power within +-20 deg of the along-strip lines, 13-20 % across"),
    warp_pitch=row(dict(px=4.1, frac_D=fr(4.1)), "px 3.4..5.5", "px", "dominant spectral peak per patch: A 4.3/4.1, B 4.0, C 3.4, U 3.6, W 3.2, X 5.5, rim 3.0-3.9",
                   threads_across_a_wide_strip=round(0.221 * D / 4.1)),
    weft=row("no stable period (3..18 px across patches); read as irregular cross-dots at ~2x the warp pitch", "-", "-", "weft wedge peak"),
    texture_contrast=row(dict(highpass_log_std=0.13, lin_p90_over_p10=8.0), "log std 0.10..0.16; p90/p10 5..13", "-", "per patch: 0.10..0.15 log std; p90/p10 4.8..13"),
    persistent_streaks=row(dict(per_100px_across=7.3, amp_log=0.073, spacing_px=9.6), "per 100 px 5..10; amp 0.05..0.09", "-",
                           "warp lines averaged 120-220 px along the strip: A 6.6, B 7.7, C 5.0, X 9.8 per 100 px; these are the only 'slub'-like features"),
    slubs=row("no distinct slubs (thick knots) are resolvable -- do not add them beyond the persistent streaks", "-", "-", "visual + streak statistics"),
    correlation=row(dict(along_px=[5, 10, 31, 6], across_px=[4.0, 3.5, 4.5, 3.5]), "along 4..30, across 3..5", "px", "autocorrelation to 0.3 (A, B, C, X)"),
    sheen=row(dict(speckle_fraction=round(s20['speckle_fraction'], 4), speckle_srgb=[round(v, 3) for v in s20['speckle_mean_srgb']],
                   speckle_chroma=[round(v, 3) for v in s20['speckle_chroma']], density_centre_to_limb=[0.051, 0.047, 0.041, 0.032]),
              "fraction 0.03..0.055", "-",
              "pixels > 3x the 6-px local median: fibre sparkle, warm light grey (tinted by the dye, not white), thinning toward the limb; no broad sheen lobe"),
    roughness_reading="matte cloth: no specular lobe; sparkle comes from fibre ends and rolled edges")

# ---------------- steps / fray / threads ----------------
fz = s22['fray']
spec['step_and_fray'] = dict(
    step_height=row(dict(px=5.7, frac_D=fr(5.7)), "px 4..8.5 (frac_D 0.004..0.009)", "px",
                    "direct: radius jumps where strip edges cross the outline (12 jumps >= 4 px, median 5.7); consistent with the shading: rim highlight 4..8 px wide on the over strip, crevice 2.5..3.5 px on the under strip"),
    edge_signature=row({k_: dict(rim_px=v['rim_offset_px'], crevice_px=v['crevice_offset_px'], rim_log=v['rim_height_log'], crevice_log=v['crevice_depth_log'])
                        for k_, v in fz.items() if k_ in ("WLO", "BLO", "ALO", "CLO", "WUP", "CUP", "BUP")},
                       "rim 0.4..1.2 log brighter; crevice 0.3..0.65 log darker", "px offsets across the edge (sign = normal of the traced polyline)",
                       "mean aligned cross profile along each edge",
                       reading="every over-strip edge reads as a ROLLED, fuzzy rim 1.5-3x brighter than the strip, with an occlusion crevice 30-47 % darker on the strip beneath"),
    fray_amplitude=row(dict(rms_px=1.5, p95_px=3.5, frac_D_rms=fr(1.5)), "rms 0.9..2.0 px; p95 2..5 px", "px",
                       "edge position jitter about a 41-px running median, per edge: " + ", ".join("%s %.2f" % (k_, v['rms_px']) for k_, v in fz.items())),
    fray_wavelength=row(dict(px=11.5, frac_D=fr(11.5)), "px 8..15", "px", "2 / zero-crossing rate of the jitter: " + ", ".join("%s %.1f" % (k_, v['mean_wavelength_px']) for k_, v in fz.items())),
    loose_threads=[
        dict(id="T1", where="hangs from W's lower edge at (801,703) down over A", tip_px=[797, 741], length_px=38, frac_D=fr(38), thickness_px="2-3", shape="curly, forks ~12 px from the tip", tol="position +-6 px, length +-8 px"),
        dict(id="T2", where="hangs from W's lower edge at (936,783) down over A", tip_px=[932, 812], length_px=29, frac_D=fr(29), thickness_px="2-3", shape="slight fork near the edge", tol="position +-6 px, length +-8 px"),
        dict(id="T3", where="short fibre curl lying on A", centre_px=[375, 607], length_px=14, frac_D=fr(14), shape="forked curl", tol="+-8 px"),
        dict(id="T4", where="hook on the outline at the left", centre_px=[191, 432], image_angle_deg=155, protrusion_px=6, frac_D=fr(6), tol="+-3 px"),
        dict(id="T5", where="stub at W's lower edge near the right limb", centre_px=[989, 820], length_px=9, frac_D=fr(9), tol="+-5 px")],
    loose_thread_count=row(dict(prominent=2, minor=3), "exactly 2 prominent; minor 2..4", "count", "visual scan + thin-ridge detector (strip-crossing bright ridges)"))

# ---------------- strips ----------------
bw = s23['bands']


def W_(k_):
    b = bw[k_]
    return dict(arc_deg=b['width_arc_deg']['median'], arc_deg_p10_p90=[b['width_arc_deg']['p10'], b['width_arc_deg']['p90']],
                frac_D=b['width_frac_D']['median'], image_px=b['width_image_px']['median'])


ED = s23['edges']
spec['strips'] = [
    dict(id="W", family="belt", rank="topmost", visible_width=W_("W"), width_is="true (both edges its own)", width_tol="+-15 %",
         twisted_section=dict(from_px=[363, 390], to_px=[610, 550], visible_width=W_("W_twist"), reading="the strip is seen edge-on / rolled for ~290 px: a raised double rim 6-15 px wide, then it opens"),
         edges=["WTW", "WUP", "WLO"], enters="from under R_in at (363,390)", leaves="right limb between image angles 334 and 349 deg",
         over=["A", "X", "B", "U0"], under=["R_in"], features=["T1", "T2", "T5 hang from its lower edge"]),
    dict(id="A", family="belt", visible_width=W_("A_visible"), width_is="visible only (upper edge hidden under W): true width >= this", width_tol="+-12 %",
         edges=["ALO (own)", "WLO/WTW (W's)"], path="from under R_in at the upper-left (282..363, 390..455) its lower edge drops almost vertically (x 282->340 over y 455->635) then sweeps right and down across the centre; the edge is NOT a circle (best small circle 11.8 px rms) -- follow the control points",
         enters="from under R_in at the upper-left", leaves="right limb between 330 and 334 deg", over=["C", "L3", "D family", "E"], under=["W", "R_in"]),
    dict(id="B", family="belt", visible_width=W_("B"), width_is="true", width_tol="+-10 %", edges=["BUP", "BLO"],
         path="both edges are near great circles (BUP pole lat %.1f lon %.1f, rms %.1f px; BLO pole lat %.1f lon %.1f, rms %.1f px); it tapers to a point under W" % (
             s18['edges']['BUP']['great']['pole_lat_deg'], s18['edges']['BUP']['great']['pole_lon_deg'], s18['edges']['BUP']['great']['rms_px'],
             s18['edges']['BLO']['great']['pole_lat_deg'], s18['edges']['BLO']['great']['pole_lon_deg'], s18['edges']['BLO']['great']['rms_px']),
         enters="from under W (tip between (556,510) and (705,586))", leaves="right limb between 12 and 26 deg", over=["X", "U1..U5"], under=["W"]),
    dict(id="X", family="belt", visible_width=W_("X_visible"), width_is="visible wedge only (no own edge visible)", width_tol="+-20 %",
         edges=["BLO (B's)", "WUP (W's)"], enters="from under B/W at x~705", leaves="right limb between 349 and 12 deg", over=[], under=["B", "W"]),
    dict(id="C", family="belt", visible_width=W_("C"), width_is="true", width_tol="+-10 %", edges=["CUP", "CLO"],
         enters="left limb between 198 and 221 deg", leaves="under A along A's lower edge between (365,676) and (625,843)", over=["L3", "L4", "L5", "D family"], under=["A"]),
    dict(id="R_in / L5", family="rim (upper-left + left limb)", visible_width=dict(upper_part=W_("R_in"), left_limb_part_px="~40 (foreshortened)"),
         width_is="visible", width_tol="+-25 %", edges=["LIN (inner, own)"],
         path="from beside the top whorl (580,306) it sweeps left and down around the upper-left, then runs down the left limb as L5 to (258,712)",
         over=["W (left end)", "A (top-left)", "U0", "L4"], under=["C (at its lower end)"]),
    dict(id="R2", family="rim", visible_width=W_("R2"), width_is="visible", width_tol="+-25 %", edges=["LC", "LA"],
         leaves="upper-left limb between 140 and 167 deg", over=[], under=[], note="order against R_in/R3 not resolvable"),
    dict(id="R3", family="rim", visible_width=dict(image_px="10..40 (foreshortened, between LA and the limb)"), edges=["LA"],
         leaves="upper-left limb at ~140 deg", note="outermost upper-left strip"),
    dict(id="L3", family="left limb", visible_width=W_("L3_visible"), width_is="visible (right edge under A)", width_tol="+-20 %", edges=["L3L"],
         enters="from under R_in at ~(270,452)", leaves="under C at ~(310,700)", over=[], under=["A", "C", "R_in", "L4? (low confidence)"]),
    dict(id="L4", family="left limb", visible_width=W_("L4"), width_is="visible", width_tol="+-25 %", edges=["L3L", "LIN lower"],
         enters="from under R_in", leaves="under C", under=["R_in/L5", "C"]),
    dict(id="U0", family="upper (to the whorl)", visible_width=dict(image_px="~135", frac_D=0.145, tol="+-25 %"),
         path="from under W's twisted section up-right to the whorl, between R_in and the V-gap UA", under=["W", "R_in"]),
    dict(id="U1..U4", family="upper (to the whorl)", visible_width={k_: W_(k_) for k_ in ("U1", "U2", "U3", "U4")}, width_tol="+-25 %",
         edges=["UA", "UC", "UD", "UE", "UF"], path="fan from B's upper edge up to the top whorl; U1/U2 run up-right, U3/U4 bend over toward the right; UE/UF run down toward the right limb",
         under=["B"], note="U0 and U1 are separated by an open V-gap (dark wedge) that closes at W"),
    dict(id="U5", family="upper-right limb", visible_width=dict(image_px="60..80"), edges=["UF"], leaves="upper-right limb", under=["B"]),
    dict(id="D family", family="bottom", visible_width={"D_a": W_("D_a"), "D_b": W_("D_b")}, width_tol="+-20 %", edges=["D14", "D57", "D9", "D19", "D27"],
         path="3-4 steep strips run from under C/A down and right to the bottom limb, converging toward image angle ~265-280 deg; two strips run along the bottom outline",
         under=["C", "A"]),
    dict(id="E", family="bottom-right", visible_width=dict(image_px="~140 at x=800 (visible)"), edges=["ALO (A's)", "D27"],
         path="runs along the lower-right outline under A", under=["A"])]
for s_ in spec['strips']:
    s_['edge_control_points'] = {e_.split(' ')[0].split('/')[0]: ED[e_.split(' ')[0].split('/')[0]] for e_ in s_.get('edges', []) if e_.split(' ')[0].split('/')[0] in ED}

spec['crossings'] = [
    dict(over="W", under="A", where="all along W's lower edge (540,522)->(1046,838)", evidence="T1/T2 hang from W onto A; bright rim on W, crevice on A; outline step 5.8 px at 332 deg", confidence="high"),
    dict(over="W", under="X", where="W's upper edge x 705->1048", evidence="rim on W; X has no own edge", confidence="high"),
    dict(over="W", under="B", where="B's tip (556,510)..(705,586)", evidence="both B edges end at W (T-junctions)", confidence="high"),
    dict(over="W", under="U0", where="(496,486)", evidence="UA ends at W's twisted section", confidence="medium"),
    dict(over="R_in", under="W", where="(363,390)", evidence="W's twisted end emerges from R_in's crevice", confidence="high"),
    dict(over="R_in", under="A", where="(282,455)", evidence="A's lower edge ends at R_in's crevice", confidence="high"),
    dict(over="R_in", under="U0", where="R_in inner edge (378..505, 314..387)", evidence="deep crevice on the U0 side", confidence="medium"),
    dict(over="B", under="X", where="B's lower edge (705,586)->(1080,535)", evidence="rim on B, crevice on X; outline step 6.2 px at 11.8 deg", confidence="high"),
    dict(over="B", under="U1..U5", where="B's upper edge (556,510)->(1070,418)", evidence="U edges end at it; the rolled rim carries B's along-strip texture", confidence="medium-high"),
    dict(over="A", under="C", where="(365,676) and (625,843)", evidence="both C edges end at A's lower edge", confidence="high"),
    dict(over="A", under="L3", where="A's lower edge x 282->365", evidence="L3's right edge hidden", confidence="medium"),
    dict(over="A", under="D family / E", where="A's lower edge x 540->1028", evidence="crevice below, D9 ends at the A/C junction", confidence="high"),
    dict(over="C", under="L3, L4, L5", where="C's upper edge (190,768)->(365,676)", evidence="L edges end at C; outline step 6.7 px at 196 deg", confidence="high"),
    dict(over="C", under="D family", where="C's lower edge (270,935)->(625,843)", evidence="D14/D57 end at it; rim on C, crevice below", confidence="high"),
    dict(over="L4", under="L3", where="(250..310, 480..700)", evidence="shading rule only (rim on L4 side)", confidence="low"),
    dict(over="(gap)", under="-", where="U0/U1 V-gap from (496,486) opening to ~30 px at (585,390); whorl V-gap (626..693, 188..254)", evidence="dark wedges: strips abut without overlap", confidence="high")]
spec['layering_note'] = ("The order is NOT one stack: R_in over A, A over C, C over L5 (= R_in's lower end) is a cycle -- the strips are woven. "
                         "Build crossing-local layering (per-crossing radial offset of one step height), not a global layer index.")
spec['inferred_continuity'] = dict(
    status="INFERRED from measured great-circle fits (the joining stretch is hidden under A and W)",
    B_equals_C=dict(evidence=["the great circle through C's upper edge meets the right limb at %.1f deg, inside B's exit band 12..26 deg" % s18['edges']['CUP']['great']['limb_crossings_deg'][1],
                              "the great circles through B's edges return to the limb at %.1f / %.1f deg, inside C's entry band 198..221 deg" % (s18['edges']['BLO']['great']['limb_crossings_deg'][0], s18['edges']['BUP']['great']['limb_crossings_deg'][0]),
                              "pole of CUP within 7.7 deg of BLO's and 13.3 deg of BUP's"],
                    build="one strip: enters lower-left as C (0.227 D), passes under A then W, emerges as B (0.173 D) -- ~25 % taper across the hidden stretch"),
    X=dict(reading="either a separate strip parallel to A or the upper part of A showing above W; not resolvable",
           build="separate strip >= 0.18 D wide, parallel to A, under B and W"))
spec['whorls'] = dict(
    top=row(dict(image_px=[690, 252], sphere=[0.135, 0.812, 0.568], deg_from_view_axis=55.4, lean_right_of_vertical_deg=9.4), "+-10 px", "px",
            "apex of the whorl V-gap and the convergence of R2/R3/R_in (from the left), U0..U4 (from below), U5/UF (to the right); the whorl V-gap is ~90 px long and ~20 px wide at its open end"),
    bottom=row("at or just behind the bottom outline, image angle 265..280 deg; not visible", "-", "-", "convergence of the D family edges"))

spec['far_side'] = dict(
    status="DESIGNED -- NOT MEASURED. The reference shows one hemisphere (orthographic: exactly half the ball). Nothing below is evidence.",
    proposal=[
        "Continue every visible strip on its own path across the back; add no strip that cannot be traced from a visible one.",
        "A and W leave the right limb at 330..349 deg heading down-right; the great circles through their edges return to the visible side at 147..164 deg, where A and W have already passed under R_in/R2 at the upper-left. On the back run A and W from the right limb under the bottom-back and up over the back to the upper-left limb, closing each loop at the measured widths (+-15 %).",
        "B and C are one strip on the front (INFERRED, see inferred_continuity): close its loop across the back from the right limb (12..26 deg) to the lower-left limb (198..221 deg), widening from 0.173 D at B's end to 0.227 D at C's end.",
        "X continues under B/W over the back and ends tucked under the D family near the bottom convergence.",
        "The U family and R family continue through the top whorl and down the back as meridian-like strips that converge on the bottom whorl, which sits 10..20 deg behind the bottom outline (sphere ~ (0.05, -0.97, -0.25)).",
        "Keep the same crossing style as the front: roughly half of the crossings with W/A-like strips on top; step height, fray, sparkle and colour identical to the front.",
        "The tape's free end, if modelled at all, is TUCKED under a strip on the back -- no visible flap, no knot, no fuse, no tag (the front shows none)."],
    acceptance="a back view must read as the same object: same strip widths (0.04..0.24 D), a whorl at each pole, no feature the front lacks")

spec['cannot_show'] = ["the far hemisphere", "the ball's real size (all lengths are fractions of D)", "camera elevation and focal length",
                       "which of R_in/R2/R3 is on top of which", "X's and A's hidden edges", "the order of L3/L4 (low confidence)",
                       "true tape thickness beyond the silhouette steps"]
spec['acceptance_checks'] = [
    "render SM_SmokeBomb from the BAKED maps with an orthographic camera (scale 1.351 D per frame width), 1254x1254, backdrop 0.996, lights per 'lighting'",
    "outline: circle fit within +-1 % D, rms dev 0.8..1.8 % R, 8..16 steps >= 4 px, no thread beyond 9 px",
    "strips: every strip in 'strips' present, width within tolerance, entering/leaving at the listed limb angles +-6 deg, every 'crossings' row in the stated order",
    "pixel targets: disc p10/p50/p90 stored luminance within +-12 %; quadrant lighting ratios within +-15 %",
    "look first: overlay the render on the reference at 50 % and flip; any strip, whorl gap, twisted section or thread that reads differently is a failure even if the numbers pass"]
L.dump("reference_spec.json", spec)
print("written", len(json.dumps(spec)))
