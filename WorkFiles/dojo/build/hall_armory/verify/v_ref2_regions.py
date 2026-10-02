# VERIFIER: Ref2Match split into the backdrop above the hall roofline and the hall + courtyard below it
import json, numpy as np
from PIL import Image
B = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/"
ld = lambda p: np.asarray(Image.open(B + p).convert("RGB")).astype(np.int16)
A, Bf, N = ld("hall_armory/fix/caps/final/CAM_Ref2Match.png"), ld("landscape/fix/caps/CAM_Ref2Match.png"), ld("hall_armory/fix/caps/noise/CAM_Ref2Match.png")
def dil(m, k=3):
    o = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o
d = np.abs(A - Bf).max(2); noise = dil(np.abs(A - N).max(2) > 24)
box = np.zeros(d.shape, bool); box[615:733, 823:1096] = True
# hall roofline per column: the first row (from the top) where the hall/outbuilding roof starts = the darkest tile band;
# simpler and conservative: a fixed split at row 500 (the main ridge is at ~ row 340 only between x 660..1260, the
# outbuilding ridges at ~480): report both
out = {}
for name, rows in (("backdrop_rows_0_500", slice(0, 500)), ("hall_courtyard_rows_500_1440", slice(500, 1440))):
    ch = (d > 24)[rows] & ~box[rows]; st = ch & ~noise[rows]
    out[name] = {"changed_px": int(ch.sum()), "static_changed_px": int(st.sum()),
                 "static_pct_of_frame": round(100 * st.sum() / d.size, 4), "static_pct_of_region": round(100 * st.mean(), 3)}
# directly above the hall ridge between the hips (x 660..1260, rows 0..345): the area the owner's silhouette sees
ch = (d > 24)[0:345, 660:1260] & ~noise[0:345, 660:1260]
out["above_main_roof_x660_1260_rows0_345"] = {"static_changed_px": int(ch.sum()), "pct_of_region": round(100 * ch.mean(), 2)}
# luma means of the backdrop
lA, lB = A.mean(2), Bf.mean(2)
out["backdrop_mean_luma_before_after"] = [round(float(lB[:500].mean()), 2), round(float(lA[:500].mean()), 2)]
out["hall_courtyard_mean_luma_before_after"] = [round(float(lB[500:].mean()), 2), round(float(lA[500:].mean()), 2)]
out["mean_abs_diff_hall_courtyard_outside_box"] = round(float(np.abs(A - Bf)[500:][~box[500:]].mean()), 3)
json.dump(out, open(B + "hall_armory/verify/json/ref2_regions.json", "w"), indent=1)
print(json.dumps(out, indent=1))
