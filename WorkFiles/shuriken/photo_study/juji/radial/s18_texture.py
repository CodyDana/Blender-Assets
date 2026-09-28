"""Texture test: is the near-black band on up-facing edges smooth like the lid (a shadow) or grainy like the
metal? High-pass residual (lum - gaussian(lum, 2)) RMS over sample boxes, absolute and relative to the mean."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
lum = a.mean(2)
hp = lum - jlib.gblur(lum, 2.0)
# horizontal-direction-only high pass too (the band runs horizontally; avoid the band's own vertical gradient)
hpx = lum - jlib.gblur(lum[None], 1.0)[0] if False else lum - np.apply_along_axis(lambda r: np.convolve(np.pad(r, 4, mode='edge'), np.ones(9) / 9, 'valid'), 1, lum)
boxes = {
    "lid far (x300-400,y250-350)": (slice(250, 350), slice(300, 400)),
    "lid penumbra above right neck (x860-940,y578-584)": (slice(578, 585), slice(860, 941)),
    "BAND right neck (x860-940,y597-606)": (slice(597, 607), slice(860, 941)),
    "BAND left neck (x400-520,y604-613)": (slice(604, 614), slice(400, 521)),
    "object olive upper bevel right neck (x860-940,y620-640)": (slice(620, 641), slice(860, 941)),
    "object dark upper bevel left neck (x400-520,y625-645)": (slice(625, 646), slice(400, 521)),
    "object tan lower bevel right neck (x860-940,y660-680)": (slice(660, 681), slice(860, 941)),
    "object central diamond (x670-710,y630-670)": (slice(630, 671), slice(670, 711)),
    "object right panel (x1060-1140,y635-650)": (slice(635, 651), slice(1060, 1141)),
}
print("%-58s  mean   hpRMS  hpxRMS  hpx/mean" % "region")
for k, (ys, xs) in boxes.items():
    L = lum[ys, xs]; r = hp[ys, xs]; rx = hpx[ys, xs]
    print("%-58s  %.3f  %.4f  %.4f  %.3f" % (k, L.mean(), np.sqrt((r ** 2).mean()), np.sqrt((rx ** 2).mean()), np.sqrt((rx ** 2).mean()) / L.mean()))
