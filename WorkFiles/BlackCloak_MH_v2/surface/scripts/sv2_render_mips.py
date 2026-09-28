# Contrast of the rendered flat swatch when box-averaged to coarser pixel sizes (game distance): std/mean of linear
# luminance of the high-passed (< 45 mm) field, at 2.73 / 5.5 / 8.2 / 11 mm per pixel.
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, sv2_imgmetrics as M
S = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/"
im = M.load(S + "renders/final_swatch_1x.png")[40:340, 40:340]
L = M.s2l(M.lum(im) / 255.0)
mm = json.load(open(S + "logs/sv2_photo_probe.json"))["mm_per_px_estimate"]
out = {}
for f in (1, 2, 3, 4):
    h = (L.shape[0] // f) * f
    a = L[:h, :h].reshape(h // f, f, h // f, f).mean((1, 3))
    k = max(3, int(round(45 / (mm * f))) | 1)
    hp = a - M.blur2d(a, k)
    out["%.1fmm_per_px" % (mm * f)] = {"texel_equiv_mip": round(float(np.log2(mm * f / 0.2197)), 2),
                                       "hp45_std_over_mean": round(float(hp[k:-k, k:-k].std() / a.mean()), 4)}
json.dump(out, open(S + "logs/final_render_mips.json", "w"), indent=1)
print("RMIPS", json.dumps(out))
