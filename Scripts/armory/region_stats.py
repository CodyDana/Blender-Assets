"""Mean display colour (sRGB 0-1) and luminance of named regions, reference vs a render of the same framing.
Regions are fractions of the frame (x0, y0, x1, y1), picked on reference 2's layout (1448 x 1086, C1 view).
Run: blender -b --factory-startup --python Scripts/armory/region_stats.py -- <reference.png> <render.png> [more renders]

Calibration pass 1 (2026-09-28): the first image is the reference. A region may carry its own box for the reference
(REF_BOX) where the reference's feature sits elsewhere in the frame than the model's (the lantern, the niche, the
window ...); a region named in HI reports the brightest 10 % of its pixels (a thin line: the case glass edge). Each cell
also gives the share of clipped pixels (any channel >= 0.98) as c<n>%.
"""
import sys

import bpy
import numpy as np

REGIONS = {
    "floor_shadow_left": (0.14, 0.60, 0.24, 0.70),
    "floor_sunpatch_centre": (0.30, 0.44, 0.40, 0.52),
    "floor_front": (0.20, 0.76, 0.30, 0.82),
    "left_upper_wall": (0.02, 0.02, 0.10, 0.12),
    "left_window": (0.00, 0.13, 0.07, 0.25),
    "left_lower_alcove": (0.03, 0.32, 0.12, 0.45),
    "painting": (0.46, 0.08, 0.54, 0.20),
    "rear_alcove_left": (0.30, 0.10, 0.36, 0.20),
    "front_plinth": (0.40, 0.70, 0.60, 0.76),
    "whole": (0.0, 0.0, 1.0, 1.0),
    # calibration pass 1: the model's feature boxes (C1 at 1448 x 1086); REF_BOX has the reference's where it differs
    "lantern_paper": (0.075, 0.83, 0.12, 0.93),          # the left floor lantern's front pane
    "case_deck_front": (0.41, 0.56, 0.59, 0.65),          # the front case's deck (the reference's: with its items)
    "case_glass_edge": (0.365, 0.50, 0.385, 0.65),        # the front case's front-left post / pane edge (HI)
    "niche_back": (0.057, 0.25, 0.073, 0.36),             # a west-wall niche's back panel
    "painting_centre": (0.47, 0.11, 0.53, 0.19),
    "platform_deck": (0.40, 0.25, 0.44, 0.268),           # the platform floor left of the stair head
    "side_window": (0.082, 0.066, 0.097, 0.095),          # a west window's field left of its plum (the reference: its left window)
    "rear_lattice": (0.325, 0.085, 0.365, 0.12),          # the lattice over the west rear alcove
    # calibration pass 2: reference 2's "floor_front" box is a sky SHEEN on dark walnut, so the floor is also read as
    # like-for-like tones: plain floor out of the sun, the darkest half (the boards' own tone) and the brightest 10 %
    # (the sun patches) of a wide floor box
    "floor_shade": (0.64, 0.80, 0.74, 0.86),
    "floor_lo50": (0.18, 0.55, 0.36, 0.85),
    "floor_hi10": (0.18, 0.55, 0.36, 0.85),
    "lantern_hi10": (0.075, 0.83, 0.12, 0.93),
}
REF_BOX = {
    "lantern_paper": (0.075, 0.83, 0.12, 0.93),
    "case_deck_front": (0.40, 0.60, 0.60, 0.68),
    "case_glass_edge": (0.375, 0.60, 0.395, 0.69),
    "niche_back": (0.012, 0.33, 0.04, 0.44),
    "platform_deck": (0.40, 0.238, 0.44, 0.252),
    "side_window": (0.00, 0.13, 0.06, 0.25),
    "rear_lattice": (0.30, 0.045, 0.35, 0.095),
    "floor_shade": (0.62, 0.74, 0.70, 0.80),
    "floor_lo50": (0.20, 0.55, 0.36, 0.78),
    "floor_hi10": (0.20, 0.55, 0.36, 0.78),
    "lantern_hi10": (0.075, 0.83, 0.12, 0.93),
}
HI = {"case_glass_edge", "floor_hi10", "lantern_hi10"}
LO = {"floor_lo50"}   # the darkest half


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]   # top row first
    return px


def cell(px, box, hi, lo=False):
    x0, y0, x1, y1 = box
    h, w, _ = px.shape
    r = px[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].reshape(-1, 3)
    lum = 0.2126 * r[:, 0] + 0.7152 * r[:, 1] + 0.0722 * r[:, 2]
    if hi:   # the brightest 10 %
        keep = lum >= np.percentile(lum, 90)
        r, lum = r[keep], lum[keep]
    if lo:   # the darkest half
        keep = lum <= np.percentile(lum, 50)
        r, lum = r[keep], lum[keep]
    m = r.mean(0)
    clip = float((r.max(1) >= 0.98).mean()) * 100
    return f"rgb({m[0]:.2f},{m[1]:.2f},{m[2]:.2f}) L{float(lum.mean()):.2f} c{clip:.0f}%"


if __name__ == "__main__":
    paths = sys.argv[sys.argv.index("--") + 1:]
    imgs = [load(p) for p in paths]
    # pass 2: the header names each column by its last two path parts (the judge could not tell live from test)
    print("region".ljust(24) + "".join("/".join(p.replace("\\", "/").split("/")[-3:])[-38:].ljust(40) for p in paths))
    for name, box in REGIONS.items():
        row = name.ljust(24)
        for i, px in enumerate(imgs):
            row += cell(px, REF_BOX.get(name, box) if i == 0 else box, name in HI, name in LO).ljust(40)
        print(row)
