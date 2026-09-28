"""SMOKEBOMB_STUDY.md: every DERIVED number in the study, from the reference measurements and the design choices.

Pure numpy (runs in Blender's bundled python.exe).  Reads the measurement JSONs next to this file; writes
sbstudy_calc.json.  Run:
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" sbstudy_calc.py
"""
import json, math, os, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
limb = json.load(open(os.path.join(HERE, "sbstudy_limb_steps.json")))
out = {}

# ------------------------------------------------------------------ design choices (ESTIMATE, study section 4)
D = 70.0            # mm, mean outline diameter over the outer tape
W = 10.0            # mm, tape width
T = 0.50            # mm, tape thickness (one layer)
R = D / 2.0


def V(r):
    return 4.0 / 3.0 * math.pi * r ** 3 / 1000.0      # cm3


# ------------------------------------------------------------------ 1. scale
r_px = limb["r_px"]["mean"]
mm_per_px = R / r_px
out["scale"] = {"mean_outline_radius_px": r_px, "mm_per_px": round(mm_per_px, 5), "px_per_mm": round(1 / mm_per_px, 3),
                "frame_1254px_mm": round(1254 * mm_per_px, 2)}
e = limb["ellipse_fit"]
out["outline"] = {"ellipse_semi_axes_mm": [round(a * mm_per_px, 2) for a in e["semi_axes_px"]],
                  "ellipse_axes_mm": [round(2 * a * mm_per_px, 2) for a in e["semi_axes_px"]],
                  "axis_ratio": e["axis_ratio"],
                  "major_axis_deg_ccw_from_image_right": e["major_axis_angle_deg_ccw_from_x"],
                  "radius_min_max_mm": [round(limb["r_px"]["min"] * mm_per_px, 2), round(limb["r_px"]["max"] * mm_per_px, 2)],
                  "highpass30_sigma_mm": round(limb["highpass30deg_sigma_px"] * mm_per_px, 3),
                  "highpass30_p05_p95_mm": [round(v * mm_per_px, 3) for v in limb["highpass30deg_p05_p95_px"]],
                  "limb_step_median_p75_max_mm": [round(limb["abs_step_px"][k] * mm_per_px, 3) for k in ("median", "p75", "max")],
                  "limb_steps_counted": limb["abs_step_px"]["n"]}
# band widths read off the profiles (sbstudy_profiles.json / the gridded views): 110-160 px
out["band_width_from_reference"] = {"px_range": [110, 160],
                                    "mm_range": [round(110 * mm_per_px, 1), round(160 * mm_per_px, 1)],
                                    "w_over_D": [round(110 / (2 * r_px), 3), round(160 / (2 * r_px), 3)],
                                    "design_w_over_D": round(W / D, 4)}
# weave periods (sbstudy_weave_fft.json): fine rib 4.0-4.9 px, cross threads ~10.4 px, slub banding 17.8-26.6 px
out["weave_mm"] = {"rib_period_mm": [round(4.0 * mm_per_px, 3), round(4.9 * mm_per_px, 3)],
                   "rib_ends_per_cm": [round(10 / (4.9 * mm_per_px), 1), round(10 / (4.0 * mm_per_px), 1)],
                   "cross_thread_period_mm": round(10.4 * mm_per_px, 3),
                   "slub_band_period_mm": [round(17.8 * mm_per_px, 2), round(26.6 * mm_per_px, 2)]}

# ------------------------------------------------------------------ 2. tape on a sphere
r_mid = R - T / 2
half = W / 2 / r_mid
rows = []
for beta_deg in (1, 2, 4, 6, 10, 20):
    kg = math.tan(math.radians(beta_deg)) / r_mid        # geodesic curvature of a small circle beta off a great circle
    rows.append({"offset_deg": beta_deg, "kg_per_mm": round(kg, 5), "edge_strain_pct": round(W * kg / 2 * 100, 2)})
out["tape_on_sphere"] = {"great_circle_edge_shortening_pct": round((1 - math.cos(half)) * 100, 3),
                         "small_circle_edge_strain": rows}

# ------------------------------------------------------------------ 3. coverage, tape length, layers
cov = []
for mean_layers in (2, 3, 4, 5, 6):
    Dm = D - T * mean_layers                  # mid diameter of the tape shell
    n = mean_layers * Dm / W                  # band area pi*Dm*w over sphere area pi*Dm^2
    length_m = n * math.pi * Dm / 1000
    cov.append({"mean_layers": mean_layers, "passes": round(n, 1), "tape_length_m": round(length_m, 2),
                "uncovered_pct_if_random": round(((1 - W / Dm) ** n) * 100, 2),
                "shell_thickness_mm": round(mean_layers * T, 2), "core_diameter_mm": round(D - 2 * mean_layers * T, 2)})
out["winding"] = cov

# ------------------------------------------------------------------ 4. mass (design: 4 mean layers)
L = 4
r_tape_in = R - L * T
shell_t = 1.0
r_fill = r_tape_in - shell_t
v_fill, v_shell, v_tape_region = V(r_fill), V(r_tape_in) - V(r_fill), V(R) - V(r_tape_in)
tape_len = cov[2]["tape_length_m"]
mass = {}
for label, tape_gsm, shell_rho, fill_rho in (("low", 200, 0.7, 0.56), ("design", 250, 0.8, 0.70), ("high", 300, 0.9, 0.80)):
    m_tape = tape_gsm * (W / 1000) * tape_len
    m_shell = v_shell * shell_rho
    m_fill = v_fill * fill_rho
    mass[label] = {"tape_g": round(m_tape, 1), "shell_g": round(m_shell, 1), "fill_g": round(m_fill, 1),
                   "total_g": round(m_tape + m_shell + m_fill, 1),
                   "inputs": {"tape_g_per_m2": tape_gsm, "shell_g_cm3": shell_rho, "fill_g_cm3": fill_rho}}
out["mass"] = {"radii_mm": {"outer": R, "tape_inner": r_tape_in, "fill": r_fill},
               "volumes_cm3": {"fill": round(v_fill, 2), "washi_shell": round(v_shell, 2),
                               "tape_region": round(v_tape_region, 2), "ball": round(V(R), 2)},
               "tape_length_m": tape_len, "cases": mass,
               "design_overall_density_g_cm3": round(mass["design"]["total_g"] / V(R), 3),
               "compare_density_g_cm3": {"baseball": [round(142 / V(37.5), 3), round(149 / V(36.5), 3)],
                                         "tennis": [round(56.0 / V(34.3), 3), round(59.4 / V(32.7), 3)]}}

# ------------------------------------------------------------------ 5. texel density
area_surface = 4 * math.pi * R ** 2
exposed_edge_mm = 1700.0              # ESTIMATE: ~850 mm of exposed tape edge on the front hemisphere, doubled
area_walls = exposed_edge_mm * T
tex = []
for size in (2048, 4096):
    for pack in (0.70, 0.75, 0.80):
        ppmm = size * math.sqrt(pack / (area_surface + area_walls))
        tex.append({"map": size, "packing": pack, "px_per_mm": round(ppmm, 2), "px_per_cm": round(ppmm * 10, 1)})
ppmm75 = tex[1]["px_per_mm"]
out["texel"] = {"surface_mm2": round(area_surface, 0), "walls_mm2": area_walls, "cases": tex,
                "reference_view_px_per_mm": round(1 / mm_per_px, 2),
                "rib_period_texels_2048_75pct": [round(ppmm75 * 4.0 * mm_per_px, 2), round(ppmm75 * 4.9 * mm_per_px, 2)],
                "cross_thread_texels_2048_75pct": round(ppmm75 * 10.4 * mm_per_px, 2)}

# ------------------------------------------------------------------ 6. LOD screen sizes (pack rule) and what they mean
tan_half_v = math.tan(math.radians(90.0) / 2) / (16 / 9)
lods = {}
for rb in (35.0, 35.5, 36.0):
    f = rb / 50.0
    s = [1.0, round(0.10 * f, 4), round(0.035 * f, 4)]
    d = [round((rb / 1000) / (x * tan_half_v), 4) for x in s[1:]]
    lods[str(rb)] = {"screen_sizes": s, "switch_m": d,
                     "ball_px_1080p_at_switch": [round(x * 1080, 1) for x in s[1:]],
                     "px_per_mm_at_switch": [round(x * 1080 / (2 * rb), 3) for x in s[1:]],
                     "tape_step_px_at_switch": [round(T * x * 1080 / (2 * rb), 2) for x in s[1:]]}
out["lods"] = lods
fp = {}
for dist in (0.35, 0.45, 0.60):
    s = (R / 1000) / (dist * tan_half_v)
    fp[str(dist)] = {"screen_size": round(s, 3), "px_across_1080p": round(s * 1080, 0), "px_per_mm": round(s * 1080 / D, 2)}
out["first_person_90hfov"] = fp
ch = []
for a in (2.5, 3.5, 4.5, 6.0, 8.0, 11.0, 14.0):
    sag = R * (1 - math.cos(a / (2 * R)))
    ch.append({"segment_mm": a, "sagitta_mm": round(sag, 4), "sagitta_px_reference_view": round(sag / mm_per_px, 2),
               "segments_around": round(2 * math.pi * R / a, 0)})
out["chordal"] = ch


def tris(seg, walls_rows, ramp_rows):
    surf = area_surface / (math.sqrt(3) / 4 * seg ** 2)
    wall = exposed_edge_mm / seg * 2 * walls_rows
    ramp = 0.5 * exposed_edge_mm / seg * 2 * ramp_rows
    return {"surface": round(surf), "walls": round(wall), "ramps": round(ramp), "total": round(surf + wall + ramp)}


out["triangles_estimate"] = {
    "LOD0_seg3.5_walls2_ramp1": tris(3.5, 2, 1),
    "LOD0_seg4.0_walls2_ramp1": tris(4.0, 2, 1),
    "LOD0_seg4.5_walls1_ramp1": tris(4.5, 1, 1),
    "LOD1_seg8_nowalls": tris(8.0, 0, 0),
    "LOD1_seg10_nowalls": tris(10.0, 0, 0),
    "LOD2_seg16_nowalls": tris(16.0, 0, 0),
    "note": "surface = sphere area / equilateral triangle of side seg; walls = exposed edge / seg * 2 tris * rows; "
            "ramps under half the edges; LOD1/2 turn walls into slopes but keep piece boundaries, which adds a floor "
            "of a few triangles per exposed piece on top of these figures",
}


# ------------------------------------------------------------------ 7. collision hull: circumscribed polyhedra
def ico():
    p = (1 + 5 ** 0.5) / 2
    v = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
         (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    return np.array(v, float)


def dodeca():
    p = (1 + 5 ** 0.5) / 2
    q = 1 / p
    v = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    v += [(0, s * q, t * p) for s in (-1, 1) for t in (-1, 1)]
    v += [(s * q, t * p, 0) for s in (-1, 1) for t in (-1, 1)]
    v += [(s * p, 0, t * q) for s in (-1, 1) for t in (-1, 1)]
    return np.array(v, float)


def unit(P):
    return P / np.linalg.norm(P, axis=1)[:, None]


def hull_planes(P):
    planes = []
    for i, j, k in itertools.combinations(range(len(P)), 3):
        nrm = np.cross(P[j] - P[i], P[k] - P[i])
        ln = np.linalg.norm(nrm)
        if ln < 1e-9:
            continue
        nrm /= ln
        d = nrm @ P[i]
        s = P @ nrm - d
        if np.all(s <= 1e-7):
            pass
        elif np.all(s >= -1e-7):
            nrm, d = -nrm, -d
        else:
            continue
        if not any(np.allclose(nrm, u[0], atol=1e-6) and abs(d - u[1]) < 1e-6 for u in planes):
            planes.append((nrm, d))
    return planes


def geodesic_f2():
    P = unit(ico())
    edge = min(np.linalg.norm(P[0] - P[j]) for j in range(1, 12))
    mids = [(P[i] + P[j]) / 2 for i, j in itertools.combinations(range(12), 2)
            if abs(np.linalg.norm(P[i] - P[j]) - edge) < 1e-6]
    return unit(np.vstack([P, np.array(mids)]))


r_max = 36.0     # mm: the outer tape plus the pole stack; the build measures its own and scales the hull to it
g = np.linspace(-r_max * 1.45, r_max * 1.45, 201)
X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
cell = (g[1] - g[0]) ** 3
hulls = {}
for name, P in {"icosahedron_12v": unit(ico()), "ico_plus_dodeca_32v": unit(np.vstack([ico(), dodeca()])),
                "geodesic_f2_42v": geodesic_f2()}.items():
    F = hull_planes(P)
    inr = min(d for _, d in F)
    k = r_max / inr
    inside = np.ones(len(pts), bool)
    for nrm, d in F:
        inside &= (pts @ nrm) <= d * k + 1e-9
    vol = inside.sum() * cell / 1000.0
    hulls[name] = {"vertices": len(P), "faces": len(F), "vertex_radius_mm": round(k, 3),
                   "max_gap_over_rmax_mm": round(k - r_max, 3), "volume_cm3": round(vol, 1),
                   "volume_over_sphere_rmax": round(vol / V(r_max), 3), "volume_over_ball_R35": round(vol / V(R), 3)}
out["hulls"] = {"r_max_mm": r_max, "cases": hulls}
json.dump(out, open(os.path.join(HERE, "sbstudy_calc.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
