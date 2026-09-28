"""Luminance / chroma statistics of candidate regions: umbra band, central diamond, dark panels, bevels."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
lum = a.mean(2)
wc = (a[:, :, 0] - a[:, :, 2]) / (a.sum(2) + 1e-3)
regions = {
    "umbra_right_neck (x880-920,y596-606)": (slice(596, 607), slice(880, 921)),
    "umbra_left_arm (x400-440,y590-600)": (slice(588, 600), slice(400, 441)),
    "central_diamond (x660-720,y620-690)": (slice(620, 691), slice(660, 721)),
    "right_panel (x1050-1150,y635-650)": (slice(635, 651), slice(1050, 1151)),
    "left_panel (x200-330,y660-680)": (slice(660, 681), slice(200, 331)),
    "bottom_panel (x700-715,y1000-1100)": (slice(1000, 1101), slice(700, 716)),
    "right_upper_bevel (x880-920,y620-640)": (slice(620, 641), slice(880, 921)),
    "right_lower_bevel (x880-920,y660-680)": (slice(660, 681), slice(880, 921)),
    "top_arm_left_bevel (x640-660,y200-300)": (slice(200, 301), slice(640, 661)),
    "bg_far (x200-400,y200-400)": (slice(200, 401), slice(200, 401)),
}
for k, (ys, xs) in regions.items():
    L = lum[ys, xs]; C = wc[ys, xs]; rgb = a[ys, xs].reshape(-1, 3)
    print("%-42s lum p5/50/95 %.3f %.3f %.3f  warmchroma p50 %.3f  rgb50 %s" % (
        k, *np.percentile(L, [5, 50, 95]), np.median(C), np.round(np.median(rgb, 0), 3)))
