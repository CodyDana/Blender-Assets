"""Senbon game/tech study calculator (GAME + TECH STUDY role, 2026-10-03).

Pure stdlib; run with the system Python:  py -3 -B WorkFiles/senbon/tech/senbon_tech_calc.py
Writes WorkFiles/senbon/tech/senbon_tech_calc.json next to itself and prints the tables used in
WorkFiles/senbon/SENBON_BUILD_PLAN.md. Nothing here reads or writes any asset.

Conventions (same as Scripts/props/props_lib/spec.py, restated so this file stays standalone):
- pack LOD screen sizes 1.0 / 0.10 / 0.035 at a 50 mm bounds radius, scaled by radius / 50 mm;
- Unreal screen size = projected bounds-sphere DIAMETER / smaller frame dimension, taken at 90 deg hFOV on 16:9;
- pixel footprint of a 1 px column at distance d: 2 d tan(hFOV/2) / width_px (90 deg -> d / 960 at 1920 wide).
"""
import json
import math
import os

PACK_SIZES = (1.0, 0.10, 0.035)
PACK_R_MM = 50.0
STEEL_G_CM3 = 7.85


def screen_sizes(radius_mm):
    f = radius_mm / PACK_R_MM
    return [1.0] + [round(s * f, 4) for s in PACK_SIZES[1:]]


def switch_distance_m(size, radius_m, hfov=90.0, aspect=16 / 9):
    half_v = math.atan(math.tan(math.radians(hfov) / 2) / aspect)
    return radius_m / (size * math.tan(half_v))


def mm_per_px(d_m, width_px=1920, hfov=90.0):
    return 2.0 * d_m * 1000.0 * math.tan(math.radians(hfov) / 2) / width_px


def width_px(diam_mm, d_m, width_px_=1920, hfov=90.0):
    return diam_mm / mm_per_px(d_m, width_px_, hfov)


def dist_for_width(diam_mm, px, width_px_=1920, hfov=90.0):
    # diam / (2 d tan / W) = px  ->  d = diam W / (2 px tan) (mm -> m)
    return diam_mm * width_px_ / (2.0 * px * math.tan(math.radians(hfov) / 2)) / 1000.0


def facet_dev_mm(r_mm, n):
    """Silhouette deviation of an n-gon inscribed in the true circle (worst case, flat mid-face)."""
    return r_mm * (1.0 - math.cos(math.pi / n))


def tris_round(n, stations, tip="apex", butt="flat"):
    """Closed round needle: n sides, `stations` rings along the shaft (incl. butt ring and taper rings),
    a tip that is an apex vertex (n tris) or a tiny flat (n-2 tris + an extra ring 2n), a flat butt (n-2)
    or a butt cone (n)."""
    t = 2 * n * (stations - 1)
    t += n if tip == "apex" else (n - 2) + 2 * n
    t += (n - 2) if butt == "flat" else n
    return t


def needle_volume_mm3(d_mm, length_mm, taper_mm, tail_taper_mm=0.0, tail_end_d_mm=None):
    """Cylinder with a conical point of length taper_mm (to a point) and an optional conical tail taper."""
    r = d_mm / 2.0
    a = math.pi * r * r
    body = a * (length_mm - taper_mm - tail_taper_mm)
    point = a * taper_mm / 3.0
    tail = 0.0
    if tail_taper_mm > 0.0:
        r2 = (tail_end_d_mm if tail_end_d_mm is not None else d_mm) / 2.0
        tail = math.pi * tail_taper_mm / 3.0 * (r * r + r * r2 + r2 * r2)
    return body + point + tail


def com_from_butt_mm(d_mm, length_mm, taper_mm):
    r = d_mm / 2.0
    a = math.pi * r * r
    lb = length_mm - taper_mm
    vb, xb = a * lb, lb / 2.0
    vp, xp = a * taper_mm / 3.0, lb + taper_mm / 4.0      # cone centroid at 1/4 of its height from the base
    return (vb * xb + vp * xp) / (vb + vp)


def main():
    out = {}
    lengths = [120.0, 150.0, 180.0, 210.0]
    diams = [1.5, 2.0, 2.5, 3.0, 4.0]

    # 1. screen sizes and switch distances (bounds radius = half length, the section adds < 0.01 mm)
    lod = {}
    for L in lengths:
        R = math.hypot(L / 2.0, 1.5)
        s = screen_sizes(R)
        lod[str(int(L))] = {
            "bounds_radius_mm": round(R, 3),
            "screen_sizes": s,
            "switch_m": [None] + [round(switch_distance_m(x, R / 1000.0), 3) for x in s[1:]],
        }
    out["lod_switch"] = lod

    # 2. on-screen width of the shaft
    dists = [0.2, 0.3, 0.5, 0.89, 1.0, 1.5, 2.0, 2.54, 3.0, 5.0, 10.0, 20.0]
    widths = {}
    for D in diams:
        widths[str(D)] = {
            "1080p_90": {str(d): round(width_px(D, d), 2) for d in dists},
            "4k_90": {str(d): round(width_px(D, d, 3840), 2) for d in dists},
            "1080p_70": {str(d): round(width_px(D, d, 1920, 70.0), 2) for d in dists},
            "dist_1px_m": {"1080p_90": round(dist_for_width(D, 1), 2), "4k_90": round(dist_for_width(D, 1, 3840), 2),
                           "1080p_70": round(dist_for_width(D, 1, 1920, 70.0), 2)},
            "dist_half_px_m": {"1080p_90": round(dist_for_width(D, 0.5), 2), "4k_90": round(dist_for_width(D, 0.5, 3840), 2)},
        }
    out["shaft_width_px"] = widths

    # 3. facet silhouette deviation in px at the views that matter (shaft d = 2.5 mm, r = 1.25 mm)
    views = {"inspect_4k_0.2m": (0.2, 3840), "fp_1080p_0.3m": (0.3, 1920), "fp_4k_0.3m": (0.3, 3840),
             "lod1_switch_1080p_0.89m": (0.89, 1920), "lod1_switch_4k_0.89m": (0.89, 3840),
             "lod2_switch_1080p_2.54m": (2.54, 1920), "lod2_switch_4k_2.54m": (2.54, 3840)}
    facets = {}
    for r in (0.75, 1.0, 1.25, 1.5, 2.0):
        row = {}
        for n in (3, 4, 6, 8, 10, 12, 16):
            dev = facet_dev_mm(r, n)
            row[str(n)] = {"dev_mm": round(dev, 4),
                           **{k: round(dev / mm_per_px(d, w), 3) for k, (d, w) in views.items()}}
        facets["r=%.2f" % r] = row
    out["facet_deviation_px"] = facets

    # 4. triangle counts for candidate LOD parameter sets (round section)
    out["triangles"] = {
        "LOD0 n12 s10 apex flat": tris_round(12, 10),
        "LOD0 n12 s12 tipflat flat": tris_round(12, 12, tip="flat"),
        "LOD0 n16 s12 apex flat": tris_round(16, 12),
        "LOD1 n8 s6 apex flat": tris_round(8, 6),
        "LOD1 n8 s5 apex flat": tris_round(8, 5),
        "LOD2 n6 s3 apex flat": tris_round(6, 3),
        "LOD2 n4 s3 apex flat": tris_round(4, 3),
        "LOD2 n3 s3 apex flat": tris_round(3, 3),
    }

    # 5. mass and centre of mass (steel 7.85 g/cm3), cylinder + conical point
    mass = {}
    for L in (150.0, 180.0):
        for D in (2.0, 2.5, 3.0, 4.0):
            for tp in (25.0, 40.0):
                v = needle_volume_mm3(D, L, tp)
                key = "L%d_D%.1f_point%d" % (L, D, tp)
                c = com_from_butt_mm(D, L, tp)
                mass[key] = {"volume_mm3": round(v, 1), "mass_g": round(v * STEEL_G_CM3 / 1000.0, 2),
                             "com_from_butt_mm": round(c, 2), "com_behind_middle_mm": round(L / 2 - c, 2)}
    out["mass"] = mass
    out["spike_for_comparison"] = {"length_mm": 150.0, "section_mm": "6 x 6 square", "mass_g": 35.3,
                                   "lod_tris": [92, 60, 28], "maps": "2048 x 512", "px_per_cm": 135.0}

    # 6. texture strip for a single unrolled shaft at the pack's bar density (135 px/cm = 13.5 px/mm)
    tex = {}
    for D in (2.0, 2.5, 3.0, 4.0):
        circ = math.pi * D
        tex[str(D)] = {"circumference_mm": round(circ, 2), "island_px_at_13.5px_per_mm": round(circ * 13.5, 1),
                       "with_8px_border_each_side": round(circ * 13.5 + 16, 1)}
    for L in (150.0, 180.0, 210.0):
        tex["length_%d_px_per_mm_on_2048" % L] = round((2048 - 16) / L, 2)
    out["texture"] = tex

    # 7. in-flight travel per frame
    out["flight"] = {"%d_mps" % v: {"cm_per_frame_60fps": round(v * 100 / 60.0, 1),
                                    "cm_per_frame_30fps": round(v * 100 / 30.0, 1)} for v in (15, 20, 30, 40)}

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "senbon_tech_calc.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
