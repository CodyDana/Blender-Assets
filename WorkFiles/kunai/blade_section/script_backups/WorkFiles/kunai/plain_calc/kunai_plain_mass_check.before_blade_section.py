"""Plain-kunai cross-check: the KUNAI_STUDY.md section 4 arithmetic with the prongs and the crotch removed.

Copied from WorkFiles/kunai/study_calc/kunai_mass_check.py (the study's companion script) and changed only where the
plain kunai differs: no prongs, no fork web, and the fork plane is the SHOULDER (X = 0), where the 16 mm blade base
meets the 6 mm bare neck (16 x 5 mm flat stock, X -6..0) that runs into the grip.  Same grid (0.05 mm), same blade,
tang, ring, grip and wrap numbers, same densities.  Pure numpy; run with Blender's bundled Python:

    "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" kunai_plain_mass_check.py

Writes kunai_plain_mass_check.json.  This is the study-basis reference the build's measured mesh is compared with.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study_calc"))
import kunai_mass_check as S  # noqa: E402  (the study's own functions and build-to values)


def main():
    step = S.STEP
    xs = np.arange(-S.OAL / 2 - 1, S.OAL / 2 + 1, step) + step / 2
    ys = np.arange(-25, 25, step) + step / 2
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    cell = step * step
    parts = {}
    h = S.leaf_half(X)
    inside = (X >= 0) & (X <= S.BLADE_L) & (np.abs(Y) <= h)
    s = h - np.abs(Y)
    for ground in (True, False):
        parts[("blade", ground)] = np.where(inside, S.section(s, h, S.blade_ridge(X), ground), 0.0)
    blade_area = inside.sum() * cell
    # the bare neck (the study's 6 mm between the grip and the blade base) is flat stock like the tang: it IS the
    # tang from X = -6 to the shoulder, so the tang runs from TANG_X0 to 0
    tang = (X >= S.TANG_X0) & (X <= 0.0) & (np.abs(Y) <= S.TANG_HALF)
    parts[("tang", True)] = parts[("tang", False)] = np.where(tang, S.STOCK, 0.0)
    r = np.hypot(X - S.RING_CX, Y)
    ring = (r <= S.RING_OD / 2) & (r >= S.RING_ID / 2)
    parts[("ring", True)] = parts[("ring", False)] = np.where(ring, S.STOCK, 0.0)
    out = {"frame": "mm; X long axis, +X to the tip; X=0 is the SHOULDER (blade base 16 mm meets the bare neck); "
                    "ring outer end X=-140",
           "changed_from_study": "no prongs, no fork web; the 6 mm bare neck (-6..0) is 16 x 5 flat stock, part of "
                                 "the tang; everything else is the study's (kunai_mass_check.py, imported)"}
    for ground in (True, False):
        field = np.zeros_like(X)
        for name in ("blade", "tang", "ring"):
            field = np.maximum(field, parts[(name, ground)])
        vol = field.sum() * cell
        mx = (field * X).sum() * cell / vol
        per, claimed = {}, np.zeros_like(X, dtype=bool)
        for name in ("ring", "tang", "blade"):
            m = (parts[(name, ground)] > 0) & ~claimed
            per[name] = round(float((field * m).sum() * cell), 1)
            claimed |= m
        out["ground" if ground else "unground"] = {
            "steel_volume_mm3": round(float(vol), 1), "steel_mass_g": round(float(vol * S.STEEL), 2),
            "steel_com_x_mm": round(float(mx), 2), "volume_by_part_mm3": per,
            "plan_area_mm2": round(float((field > 0).sum() * cell), 1)}
    out["areas_mm2"] = {"blade": round(float(blade_area), 1),
                        "ring": round(math.pi / 4 * (S.RING_OD ** 2 - S.RING_ID ** 2), 1)}
    # 3.10.1 review answer: the tang's end IS inside the ring, and the basis does NOT count it twice.  The field is a
    # MAXIMUM of the parts, so the overlap contributes its 5 mm once; the per-part breakdown claims the ring first and
    # gives the tang only what is left, so ring + tang + blade = the field's own total.  Both figures are recorded here.
    overlap = (tang & ring).sum() * cell * S.STOCK
    out["ring_tang_overlap"] = {
        "volume_mm3": round(float(overlap), 1),
        "counted_once": True,
        "check": {"tang_rectangle_mm3": round(float(2 * S.TANG_HALF * S.STOCK * (0.0 - S.TANG_X0)), 1),
                  "tang_after_the_ring_claimed_its_own_mm3": out["unground"]["volume_by_part_mm3"]["tang"],
                  "ring_annulus_analytic_mm3": round(math.pi / 4 * (S.RING_OD ** 2 - S.RING_ID ** 2) * S.STOCK, 1),
                  "parts_sum_mm3": round(float(sum(out["unground"]["volume_by_part_mm3"].values())), 1),
                  "field_total_mm3": out["unground"]["steel_volume_mm3"],
                  "blade_plan_area_analytic_mm2": 2957.5},
        "note": ("the tang rectangle minus what the ring already claimed = the reported tang volume, and the parts sum "
                 "to the field total: the overlap is in the total exactly once")}
    L = S.GRIP_X1 - S.GRIP_X0
    tang_in = 2 * S.TANG_HALF * S.STOCK * L
    core = math.pi / 4 * S.CORE_D ** 2 * L - tang_in
    wrap = math.pi / 4 * (S.GRIP_D ** 2 - S.CORE_D ** 2) * L
    gx = (S.GRIP_X0 + S.GRIP_X1) / 2
    grip = {"wrapped_length_mm": L, "core_mm3": round(core, 1), "wrap_mm3": round(wrap, 1),
            "core_g": [round(core * d, 1) for d in S.WOOD], "wrap_g": [round(wrap * d, 1) for d in S.COTTON],
            "centre_x_mm": gx}
    grip["total_g"] = [round(grip["core_g"][i] + grip["wrap_g"][i], 1) for i in (0, 1)]
    out["grip_nonsteel"] = grip
    g = out["ground"]
    mid = sum(grip["total_g"]) / 2
    tot = g["steel_mass_g"] + mid
    com = (g["steel_mass_g"] * g["steel_com_x_mm"] + mid * gx) / tot
    grip_solid = math.pi / 4 * S.GRIP_D ** 2 * L - tang_in
    wrong = (g["steel_volume_mm3"] * g["steel_com_x_mm"] + grip_solid * gx) / (g["steel_volume_mm3"] + grip_solid)
    out["assembled"] = {"mass_g_mid": round(tot, 1),
                        "mass_g_range": [round(g["steel_mass_g"] + grip["total_g"][0], 1),
                                         round(g["steel_mass_g"] + grip["total_g"][1], 1)],
                        "com_x_mm_mass_weighted": round(com, 2),
                        "com_x_mm_if_render_volume_uniform": round(wrong, 2)}
    out["winged_study_for_comparison"] = json.load(open(os.path.join(HERE, "..", "study_calc",
                                                                      "kunai_mass_check.json")))["assembled"]
    out["plain_replicas_in_the_study_g"] = {
        "Honshu 12 in (305 mm), one-piece 7Cr13, cord wrap [24]": 227,
        "Leones Atsu 26 cm, carbon steel, blunt [27]": 162,
        "Ninja Dojo and Store Metal Big 290 x 50 mm, zinc alloy [28]": 140,
        "Slash2Gash 12 in thrower, 5.1 mm, up to 6.2 oz [32]": round(6.2 * 28.3495, 1),
        "forged 12 in, 3/16 in, 10 oz [30] SNIPPET, unconfirmed": round(10 * 28.3495, 1)}
    path = os.path.join(HERE, "kunai_plain_mass_check.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
