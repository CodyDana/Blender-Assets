# Probe the product photo: garment colour (median, warmth), scale estimate, fabric patch statistics.
# Blender 5.2 headless:  blender -b --factory-startup --python sv2_photo_probe.py
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import sv2_imgmetrics as M

REF = "C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/logs/sv2_photo_probe.json"
im = M.load(REF)                       # sRGB 0..255, top-down
L = M.lum(im)
m = L < 115                            # garment mask (the review's threshold)
ys, xs = np.nonzero(m)
R = {"size": [im.shape[1], im.shape[0]], "garment_px": int(m.sum()),
     "bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
g = im[m]
R["garment_median_rgb_srgb"] = [float(np.median(g[:, c])) for c in range(3)]
R["garment_median_lum_srgb"] = float(np.median(L[m]))
R["garment_p10_p90_lum_srgb"] = [float(np.percentile(L[m], 10)), float(np.percentile(L[m], 90))]
lin = M.s2l(g / 255.0)
mean_lin = lin.mean(0)
R["garment_mean_rgb_linear"] = [float(v) for v in mean_lin]
R["warmth_R_over_B_linear"] = float(mean_lin[0] / mean_lin[2])
R["warmth_R_over_G_linear"] = float(mean_lin[0] / mean_lin[1])
# scale: the review puts the collar top of a scaled copy at ~178.8 cm with the hem on the floor
h_px = int(ys.max() - ys.min() + 1)
R["mm_per_px_estimate"] = 1788.0 / h_px
R["mm_per_px_note"] = "garment height in px vs ~1.788 m (collar top of an exact copy on the 186 cm male, hem on floor)"
# fabric: flattest 32x32 windows (the gap tool's method) + fixed windows
pat = M.flat_patches(L, m, n=32, k=8, mm_per_px=1788.0 / (int(ys.max() - ys.min() + 1)))
R["flat_patches"] = pat
R["flat_patches_agg"] = M.agg(pat)
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "flat_patches"}, indent=1))
