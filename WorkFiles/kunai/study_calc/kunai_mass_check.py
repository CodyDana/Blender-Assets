"""Kunai study cross-check (References/Kunai/KUNAI_STUDY.md section 4).

Numeric volume, mass and centre of mass of the BUILD-TO winged kunai, by rasterising the
top-view outline on a 0.05 mm grid and integrating a section-thickness field over it.
Pure numpy; run with Blender's bundled Python:

    "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" kunai_mass_check.py

Frame (mm): X along the long axis, +X toward the tip; Y across, in the blade plane; Z through
the thickness.  X = 0 is the fork plane (where the main blade, the two prongs and the grip meet).

Every number below is a build-to value from the study; the study marks each one SOURCED,
DERIVED or ESTIMATE.  This file only does the arithmetic.  Writes kunai_mass_check.json.
"""
import json
import math
import os

import numpy as np

# ------------------------------------------------------------------ build-to values (mm)
OAL = 280.0
BLADE_L = 140.0            # fork plane to tip
BLADE_BASE_HALF = 8.0      # main blade half-width at the fork plane
BLADE_MAX_HALF = 18.0      # 36 mm max width
BLADE_MAX_AT = 35.0        # widest point, 0.25 of the blade length
LEAF_BULGE = 0.25          # convexity of the fore edge, h = H (1-u)(1+b u)
RIDGE_BASE = 5.0           # diamond ridge thickness, fork to widest point
RIDGE_TIP = 1.6            # ridge thickness at RIDGE_TIP_AT
RIDGE_TIP_AT = 135.0
SHOULDER = 1.5             # section thickness where the diamond face meets the knife grind
LAND = 0.15                # pack knife grind: land
GRIND_DEG = 35.0           # pack knife grind: degrees per side

PRONG_ANGLE_DEG = 38.0     # prong axis off the main axis
PRONG_L = 60.0             # along the prong axis, root centre to tip
PRONG_ROOT_OFF = 13.0      # |Y| of the prong root centre on the fork plane
PRONG_ROOT_HALF = 7.0      # 14 mm root width
PRONG_RIDGE_ROOT = 5.0
PRONG_RIDGE_TIP = 1.6

STOCK = 5.0                # flat stock: web, tang, ring
TANG_HALF = 8.0            # 16 mm tang bar under the wrap (fits inside the 18 mm core: diagonal 16.8 mm)
GRIP_X0, GRIP_X1 = -102.0, -6.0   # wrapped length 96 mm
TANG_X0 = -110.0           # tang runs into the ring
GRIP_D = 20.0              # wrapped grip diameter
CORE_D = 18.0              # wood or filler core under a 1 mm tape wrap

RING_OD, RING_ID = 32.0, 20.0
RING_CX = -OAL / 2 + RING_OD / 2   # ring outer end at -140

STEEL = 7.85e-3            # g/mm3
WOOD = (0.6e-3, 0.8e-3)    # g/mm3 range for a wooden core
COTTON = (0.6e-3, 0.9e-3)  # g/mm3 range for a wound cotton tape wrap

STEP = 0.05


def leaf_half(x):
    """Main blade half-width at x (0 <= x <= BLADE_L)."""
    x = np.asarray(x, dtype=float)
    h = np.zeros_like(x)
    a = (x >= 0) & (x <= BLADE_MAX_AT)
    h[a] = BLADE_BASE_HALF + (BLADE_MAX_HALF - BLADE_BASE_HALF) * x[a] / BLADE_MAX_AT
    b = (x > BLADE_MAX_AT) & (x <= BLADE_L)
    u = (x[b] - BLADE_MAX_AT) / (BLADE_L - BLADE_MAX_AT)
    h[b] = BLADE_MAX_HALF * (1 - u) * (1 + LEAF_BULGE * u)
    return h


def blade_ridge(x):
    t = np.where(x <= BLADE_MAX_AT, RIDGE_BASE,
                 RIDGE_BASE + (RIDGE_TIP - RIDGE_BASE) * (x - BLADE_MAX_AT) / (RIDGE_TIP_AT - BLADE_MAX_AT))
    return np.clip(t, RIDGE_TIP, RIDGE_BASE)


def section(s, half, ridge, ground=True):
    """Diamond section with a knife grind: thickness at distance s inside the cutting edge."""
    face = SHOULDER + (ridge - SHOULDER) * np.clip(s / np.maximum(half, 1e-9), 0, 1)
    face = np.maximum(face, np.minimum(ridge, SHOULDER))
    if not ground:
        return face
    grind = LAND + 2 * s * math.tan(math.radians(GRIND_DEG))
    return np.minimum(face, grind)


def main():
    xs = np.arange(-OAL / 2 - 1, OAL / 2 + 1, STEP) + STEP / 2
    ys = np.arange(-60, 60, STEP) + STEP / 2
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    cell = STEP * STEP

    parts = {}
    # main blade
    h = leaf_half(X)
    inside = (X >= 0) & (X <= BLADE_L) & (np.abs(Y) <= h)
    s = h - np.abs(Y)
    for ground in (True, False):
        t = np.where(inside, section(s, h, blade_ridge(X), ground), 0.0)
        parts[("blade", ground)] = t
    blade_area = inside.sum() * cell

    # prongs (each symmetric about its own axis; half-width tapers to the tip, slight convexity)
    th = math.radians(PRONG_ANGLE_DEG)
    prong_t = {True: np.zeros_like(X), False: np.zeros_like(X)}
    prong_area = 0.0
    for sign in (1, -1):
        dx, dy = math.cos(th), sign * math.sin(th)
        rx, ry = 0.0, sign * PRONG_ROOT_OFF
        u = (X - rx) * dx + (Y - ry) * dy
        v = -(X - rx) * dy + (Y - ry) * dx
        f = u / PRONG_L
        w = PRONG_ROOT_HALF * (1 - f) * (1 + LEAF_BULGE * f)
        ins = (u >= 0) & (u <= PRONG_L) & (np.abs(v) <= w)
        prong_area += ins.sum() * cell
        ridge = PRONG_RIDGE_ROOT + (PRONG_RIDGE_TIP - PRONG_RIDGE_ROOT) * np.clip(f, 0, 1)
        for ground in (True, False):
            t = np.where(ins, section(w - np.abs(v), w, ridge, ground), 0.0)
            prong_t[ground] = np.maximum(prong_t[ground], t)
    for ground in (True, False):
        parts[("prongs", ground)] = prong_t[ground]

    # fork web: flat stock joining the tang, the blade base and the prong roots
    n = (-math.sin(th), math.cos(th))
    outer_root = (0.0 + PRONG_ROOT_HALF * n[0], PRONG_ROOT_OFF + PRONG_ROOT_HALF * n[1])
    inner_root = (0.0 - PRONG_ROOT_HALF * n[0], PRONG_ROOT_OFF - PRONG_ROOT_HALF * n[1])
    poly = [(-6.0, TANG_HALF), outer_root, inner_root,
            (inner_root[0], -inner_root[1]), (outer_root[0], -outer_root[1]), (-6.0, -TANG_HALF)]
    web = point_in_poly(X, Y, poly)
    parts[("web", True)] = parts[("web", False)] = np.where(web, STOCK, 0.0)

    # tang bar (under the wrap and the bare neck) and ring, flat stock
    tang = (X >= TANG_X0) & (X <= -6.0) & (np.abs(Y) <= TANG_HALF)
    parts[("tang", True)] = parts[("tang", False)] = np.where(tang, STOCK, 0.0)
    r = np.hypot(X - RING_CX, Y)
    ring = (r <= RING_OD / 2) & (r >= RING_ID / 2)
    parts[("ring", True)] = parts[("ring", False)] = np.where(ring, STOCK, 0.0)

    out = {"frame": "mm; X long axis, +X to the tip; fork plane X=0; ring outer end X=-140",
           "inputs": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}}
    for ground in (True, False):
        # union: the thickest part wins where parts overlap (web over blade base, tang into ring)
        field = np.zeros_like(X)
        for name in ("blade", "prongs", "web", "tang", "ring"):
            field = np.maximum(field, parts[(name, ground)])
        vol = field.sum() * cell
        mx = (field * X).sum() * cell / vol
        key = "ground" if ground else "unground"
        per = {}
        claimed = np.zeros_like(X, dtype=bool)
        for name in ("ring", "tang", "web", "prongs", "blade"):
            m = (parts[(name, ground)] > 0) & ~claimed
            per[name] = round(float((field * m).sum() * cell), 1)
            claimed |= m
        out[key] = {"steel_volume_mm3": round(float(vol), 1),
                    "steel_mass_g": round(float(vol * STEEL), 2),
                    "steel_com_x_mm": round(float(mx), 2),
                    "volume_by_part_mm3": per,
                    "plan_area_mm2": round(float((field > 0).sum() * cell), 1)}
    out["areas_mm2"] = {"blade": round(float(blade_area), 1), "prongs_both": round(float(prong_area), 1),
                        "ring": round(math.pi / 4 * (RING_OD ** 2 - RING_ID ** 2), 1)}

    # grip: wrap and core, separate from the steel
    L = GRIP_X1 - GRIP_X0
    tang_in = 2 * TANG_HALF * STOCK * L
    core = math.pi / 4 * CORE_D ** 2 * L - tang_in
    wrap = math.pi / 4 * (GRIP_D ** 2 - CORE_D ** 2) * L
    gx = (GRIP_X0 + GRIP_X1) / 2
    grip = {"wrapped_length_mm": L, "core_mm3": round(core, 1), "wrap_mm3": round(wrap, 1),
            "core_g": [round(core * d, 1) for d in WOOD], "wrap_g": [round(wrap * d, 1) for d in COTTON],
            "centre_x_mm": gx}
    grip["total_g"] = [round(grip["core_g"][i] + grip["wrap_g"][i], 1) for i in (0, 1)]
    out["grip_nonsteel"] = grip

    g = out["ground"]
    mid = sum(grip["total_g"]) / 2
    tot = g["steel_mass_g"] + mid
    com = (g["steel_mass_g"] * g["steel_com_x_mm"] + mid * gx) / tot
    out["assembled"] = {"mass_g_mid": round(tot, 1),
                        "mass_g_range": [round(g["steel_mass_g"] + grip["total_g"][0], 1),
                                         round(g["steel_mass_g"] + grip["total_g"][1], 1)],
                        "com_x_mm_mass_weighted": round(com, 2)}
    # what a uniform-density centroid of the RENDER mesh would give (the wrong pivot): the grip
    # rendered as a solid 20 mm cylinder counted at steel density
    grip_solid = math.pi / 4 * GRIP_D ** 2 * L - tang_in
    wrong = (g["steel_volume_mm3"] * g["steel_com_x_mm"] + grip_solid * gx) / (g["steel_volume_mm3"] + grip_solid)
    out["assembled"]["com_x_mm_if_render_volume_uniform"] = round(wrong, 2)

    # bounds: Unreal's sphere radius from the box centre
    out["bounds"] = {"x": [-OAL / 2, OAL / 2],
                     "prong_tip": [round(PRONG_L * math.cos(th), 2),
                                   round(PRONG_ROOT_OFF + PRONG_L * math.sin(th), 2)],
                     "span_mm": round(2 * (PRONG_ROOT_OFF + PRONG_L * math.sin(th)), 2),
                     "box_centre_x": 0.0,
                     "sphere_radius_mm": round(math.hypot(OAL / 2, GRIP_D / 2 * 0), 2)}
    out["bounds"]["lod_screen_sizes_scaled"] = [1.0] + [round(s * (OAL / 2) / 50.0, 4) for s in (0.10, 0.035)]

    # crotch: where the prong inner edge meets the blade edge (search along the inner edge)
    best = None
    for i in range(0, 6001):
        uu = i * PRONG_L / 6000
        f = uu / PRONG_L
        w = PRONG_ROOT_HALF * (1 - f) * (1 + LEAF_BULGE * f)
        px = uu * math.cos(th) + w * math.sin(th)
        py = PRONG_ROOT_OFF + uu * math.sin(th) - w * math.cos(th)
        if px >= 0 and py > float(leaf_half(np.array([px]))[0]):
            best = (round(px, 2), round(py, 2))
            break
    out["crotch_mm"] = best

    # Honshu density check: leaf 179 x 41.5 mm (the set's middle width), 4.6 -> 1.6 mm taper, flat
    Lb, Wb = 179.0, 41.5
    xb = np.linspace(0, Lb, 20001)
    hb = np.where(xb <= 0.25 * Lb, Wb / 2 * (0.45 + 0.55 * xb / (0.25 * Lb)),
                  Wb / 2 * (1 - (xb - 0.25 * Lb) / (0.75 * Lb)) * (1 + LEAF_BULGE * (xb - 0.25 * Lb) / (0.75 * Lb)))
    tb = 4.6 + (1.6 - 4.6) * xb / Lb
    vb = np.trapezoid(2 * hb * tb, xb) if hasattr(np, "trapezoid") else np.trapz(2 * hb * tb, xb)
    out["honshu_blade_check"] = {"blade_area_mm2": round(float(np.trapezoid(2 * hb, xb)), 1),
                                 "blade_volume_mm3_flat": round(float(vb), 1),
                                 "blade_mass_g_flat": round(float(vb * STEEL), 1),
                                 "sourced_total_g": 227,
                                 "remainder_g": round(227 - float(vb * STEEL), 1)}

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kunai_mass_check.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


def point_in_poly(X, Y, poly):
    inside = np.zeros_like(X, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > Y) != (y2 > Y)) & (X < (x2 - x1) * (Y - y1) / ((y2 - y1) if y2 != y1 else 1e-12) + x1)
        inside ^= cond
    return inside


if __name__ == "__main__":
    main()
