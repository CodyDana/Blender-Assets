"""bhstudy_calc.py - every DERIVED number in BLACKHAT_STUDY.md (pure Python + numpy, no bpy).

Inputs are the MEASURED ratios in bhstudy_unwrap.json / bhstudy_ribs_lashings.json and the ESTIMATE design size.
Run with Blender's bundled Python:  "<blender>/5.2/python/bin/python.exe" bhstudy_calc.py
"""
import json, math
import numpy as np

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/study_calc"
fit = json.load(open(OUT + "/bhstudy_unwrap.json"))
R = {}

# ---------------------------------------------------------------- scale
D_OUT_MM = 500.0                       # ESTIMATE: outer diameter over the rim roll
D_OUT_PX = 2 * fit["outer_semi_major_px"]
mm_px = D_OUT_MM / D_OUT_PX
R["scale_mm_per_px"] = mm_px
R["ref_px_per_mm"] = 1 / mm_px

# ---------------------------------------------------------------- cone
pitch = np.mean([fit["projection"]["pitch_deg_direct"], fit["projection"]["pitch_deg_slope"]])
pitch_lo, pitch_hi = fit["projection"]["pitch_deg_direct"], fit["projection"]["pitch_deg_slope"]
ROLL_D = 14.0                            # ESTIMATE from ~18-20 px front roll height (see study 3)
r_roll = ROLL_D / 2
R_cone = D_OUT_MM / 2 - r_roll           # skin meets the roll at the roll centreline radius (approx)
h = R_cone * math.tan(math.radians(pitch))
s = R_cone / math.cos(math.radians(pitch))
R.update(pitch_deg=pitch, pitch_range_deg=[pitch_lo, pitch_hi], apex_full_angle_deg=180 - 2 * pitch,
         R_cone_mm=R_cone, cone_height_mm=h, slant_mm=s,
         cone_height_range_mm=[R_cone * math.tan(math.radians(pitch_lo)), R_cone * math.tan(math.radians(pitch_hi))])
# development (cone is developable): sector angle, lateral area
dev_deg = 360 * R_cone / s
R["development_sector_deg"] = dev_deg
area_lat = math.pi * R_cone * s
R["cone_lateral_area_cm2"] = area_lat / 100
# crown cap covers f < f_cap
CAP_D = 50.0                                  # 67 px measured -> 50 mm
f_cap = (CAP_D / 2) / R_cone
R["cap_diameter_mm"] = CAP_D
R["cap_slant_fraction"] = f_cap
area_skin = area_lat * (1 - f_cap ** 2)
R["skin_area_outer_cm2"] = area_skin / 100

# ribs
N_RIB = 9
R["rib_count"] = N_RIB
R["rib_spacing_deg"] = 360 / N_RIB
R["rib_spacing_at_rim_mm"] = 2 * math.pi * R_cone / N_RIB
R["rib_length_mm"] = s * (1 - f_cap)
# lashings
N_LASH = 18
R["lashing_count"] = N_LASH
R["lashing_spacing_at_rim_mm"] = 2 * math.pi * (R_cone + r_roll) / N_LASH

# ---------------------------------------------------------------- texel density (skin unique UVs)
def ppcm(area_cm2, tex, pack):
    return tex * math.sqrt(pack / area_cm2)
R["texel_skin_2048_pack0.70_px_per_cm"] = ppcm(area_skin / 100, 2048, 0.70)
R["texel_skin_4096_pack0.70_px_per_cm"] = ppcm(area_skin / 100, 4096, 0.70)
# the whole straw slot: skin outer + inner (inner shares? no: plain underside gets its own small island set at low density)
roll_area = 2 * math.pi * (R_cone + r_roll) * math.pi * ROLL_D  # torus area
rib_area = N_RIB * R["rib_length_mm"] * math.pi * 2.5 / 2
cap_area = math.pi * (CAP_D / 2) ** 2 * 1.4
lash_area = N_LASH * 13 * math.pi * (ROLL_D + 4)
straw_top = area_skin + roll_area + rib_area + cap_area + lash_area
R["straw_visible_area_cm2"] = straw_top / 100
R["texel_straw_2048_pack0.70_px_per_cm"] = ppcm(straw_top / 100, 2048, 0.70)
# underside at half density shares the atlas: effective area = top + inner/4
R["texel_straw_2048_with_underside_quarter_px_per_cm"] = ppcm((straw_top + area_skin / 4) / 100, 2048, 0.70)
# cloth
BAND_W, BAND_L = 17.0, 2 * math.pi * 0.31 * R_cone * 1.03 + 60  # ring at f~0.31, plus knot allowance
TAIL_W, TAIL_L = (28.0, 34.0), (270.0, 240.0)
cloth_area = 2 * (BAND_W * BAND_L + sum(w * l for w, l in zip(TAIL_W, TAIL_L)))  # two faces
R["cloth_area_both_faces_cm2"] = cloth_area / 100
R["texel_cloth_2048_pack0.65_px_per_cm"] = ppcm(cloth_area / 100, 2048, 0.65)
R["texel_cloth_1024_pack0.65_px_per_cm"] = ppcm(cloth_area / 100, 1024, 0.65)

# ---------------------------------------------------------------- mass
# bamboo kasa: 150 g @ 45 cm, 120 g @ 40 cm (takuhatsu, varnished); 250 g @ 46 cm (ajiro incl. rattan gotoku)
m_lo = 150 * (D_OUT_MM / 450) ** 2
m_hi = (250 - 30) * (D_OUT_MM / 460) ** 2   # minus a ~30 g head ring (the kameya 頭台 is 30 g)
lacquer = 0.15                              # ESTIMATE: +15 % for a lacquer / soot-oil coat
cotton_gsm = 150.0                          # ESTIMATE medium cotton
band_g = cloth_area / 2 / 1e6 * cotton_gsm * 1.0
R["mass_body_g_range"] = [m_lo * (1 + lacquer), m_hi * (1 + lacquer)]
R["mass_band_g"] = band_g
R["mass_total_g_mid"] = 0.5 * sum(R["mass_body_g_range"]) + band_g

# ---------------------------------------------------------------- bounds, LOD rule
# vertices: rim outer at z = 0 (roll centre plane), roll bottom -r_roll, apex top h + cap 6 mm, tails to -95 mm at r ~ 200
zmin = -95.0; zmax = h + 6.0
zc = 0.5 * (zmin + zmax)
cands = [(D_OUT_MM / 2, 0.0), (D_OUT_MM / 2 - r_roll, -r_roll), (0.0, zmax), (200.0, zmin), (230.0, -60.0)]
Rb = max(math.hypot(r, z - zc) for r, z in cands)
R["aabb_z_mm"] = [zmin, zmax]
R["bounds_radius_mm_est"] = Rb
k = Rb / 50.0
ss = [1.0, round(0.10 * k, 4), round(0.035 * k, 4)]
R["lod_screen_sizes"] = ss
half_v = math.atan(math.tan(math.radians(45)) / (16 / 9))
R["lod_switch_distance_m"] = [Rb / 1000 / (x * math.tan(half_v)) for x in ss[1:]]
R["px_across_at_switch_1080p"] = [x * 1080 for x in ss[1:]]
R["px_per_mm_at_switch_1080p"] = [x * 1080 / (2 * Rb) for x in ss[1:]]
R["feature_px_at_switch"] = {nm: [w * p for p in R["px_per_mm_at_switch_1080p"]]
                             for nm, w in (("rib_2.5mm", 2.5), ("roll_14mm", 14.0), ("lashing_13mm", 13.0),
                                           ("band_17mm", 17.0), ("tail_28mm", 28.0), ("hoop_1.5mm", 1.5))}

# chordal error of the rim circle at the reference framing and at the switches
def seg_for_sag(radius, sag):
    return math.ceil(math.pi / math.acos(1 - sag / radius))
R["rim_segments_for_0.5px_at_reference"] = seg_for_sag(D_OUT_MM / 2, 0.5 * mm_px)
R["rim_segments_for_0.5px_at_lod1_switch"] = seg_for_sag(D_OUT_MM / 2, 0.5 / R["px_per_mm_at_switch_1080p"][0])
R["rim_segments_for_0.5px_at_lod2_switch"] = seg_for_sag(D_OUT_MM / 2, 0.5 / R["px_per_mm_at_switch_1080p"][1])
R["rim_segments_for_0.1mm"] = seg_for_sag(D_OUT_MM / 2, 0.1)

# ---------------------------------------------------------------- collision: circumscribed pyramid-frustum hull
n = 15
Rv = (D_OUT_MM / 2) / math.cos(math.pi / n)
R["hull_body"] = {"ring_vertices": n, "rings": 2, "apex": 1, "total_vertices": 2 * n + 1,
                  "vertex_radius_mm": Rv, "overshoot_mm": Rv - D_OUT_MM / 2,
                  "volume_ratio_to_cone_envelope": (n * math.tan(math.pi / n)) / math.pi}

# ---------------------------------------------------------------- head seat (socket)
# head: horizontal ellipse scaled to a 57 cm circumference with FAA/ANSUR length:breadth 19.7:15.2 (men p50)
L_, B_ = 19.7, 15.2
def ell_perim(a, b):
    return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
kk = 57.0 / ell_perim(L_ / 2, B_ / 2)
a_h, b_h = L_ / 2 * kk, B_ / 2 * kk
c_h = 9.0                              # ESTIMATE: vertex above the circumference plane (sellion-top 11.2 cm, men p50)
m = math.tan(math.radians(pitch))
SKIN_T_MM = 4.0                        # ESTIMATE skin thickness under the outer surface
def seat(a):
    # cone generator z = z0 - m r tangent to ellipse r^2/a^2 + z^2/c^2 = 1  -> z0 = sqrt(a^2 m^2 + c^2)
    z0 = math.sqrt(a * a * m * m + c_h * c_h)
    r_t = a * a * m / z0
    z_t = c_h * c_h / z0
    return z0, r_t, z_t
z0a, rta, zta = seat(a_h)   # long axis touches first (it is wider)
R["head"] = {"circumference_cm": 57.0, "ellipse_semi_axes_cm": [a_h, b_h], "vertex_above_circ_plane_cm": c_h,
             "inner_apex_above_head_centre_cm": z0a, "contact_radius_cm": rta, "contact_height_cm": zta,
             "vertex_below_inner_apex_cm": z0a - c_h}
# in the hat frame: z = 0 at the rim roll centre plane, outer apex at h.  Inner apex lower by skin t / cos(pitch)
inner_apex_mm = h - SKIN_T_MM / math.cos(math.radians(pitch))
vertex_z_mm = inner_apex_mm - (z0a - c_h) * 10
R["socket_HEAD_mm"] = {"x": 0.0, "y": 0.0, "z": vertex_z_mm,
                       "note": "head vertex seat on the axis; rim roll centre plane is z=0"}
R["rim_below_vertex_mm"] = vertex_z_mm
R["rim_vs_sellion_mm"] = vertex_z_mm - 112.0   # sellion is 112 mm below the vertex (FAA men p50)
# with a real 7 cm head ring (kameya 頭台 18 cm x 7 cm) the hat would ride ~ this much higher
json.dump(R, open(OUT + "/bhstudy_calc.json", "w"), indent=1)
print(json.dumps(R, indent=1))
