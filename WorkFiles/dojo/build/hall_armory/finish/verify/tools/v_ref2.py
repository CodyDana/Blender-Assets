"""VERIFIER: CAM_Ref2Match (this verification's fresh -game capture) vs the landscape round's capture
(landscape/fix/caps/CAM_Ref2Match.png). Static change = |diff| > 24/255 on any channel and NOT live noise (pixels that
differ > 24 between this verification's two identical capture runs, dilated 3 px). Regions as the earlier verifier's
v_ref2_regions.py. Out: finish/verify/json/ref2.json + caps/VDIFF_Ref2Match.png"""
import json
import numpy as np
from PIL import Image
B = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/"
V = B + "hall_armory/finish/verify/"
ld = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
LAND = ld(B + "landscape/fix/caps/CAM_Ref2Match.png")
A = ld(V + "caps/final/CAM_Ref2Match.png")
N = ld(V + "caps/noise/CAM_Ref2Match.png")
BUILDER = ld(B + "hall_armory/finish/caps/final/CAM_Ref2Match.png")
def dil(m, k=3):
    o = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o
noise = dil(np.abs(A - N).max(2) > 24)
d = np.abs(A - LAND).max(2)
box = np.zeros(d.shape, bool); box[615:733, 823:1096] = True
out = {"live_noise_pct_of_frame": round(100 * noise.mean(), 3)}
for name, rs, cs in (("above_main_roof_x660_1260_rows0_345", slice(0, 345), slice(660, 1260)),
                     ("backdrop_rows_0_500", slice(0, 500), slice(None)),
                     ("hall_courtyard_rows_500_1440_outside_door_box", slice(500, 1440), slice(None))):
    ch = (d > 24)[rs, cs] & ~box[rs, cs]
    st = ch & ~noise[rs, cs]
    out[name] = {"region_px": int(ch.size), "changed_px": int(ch.sum()), "static_changed_px": int(st.sum()),
                 "static_pct_of_region": round(100 * st.mean(), 3), "static_pct_of_frame": round(100 * st.sum() / d.size, 3),
                 "changed_pct_of_region_no_noise_mask": round(100 * ch.mean(), 3)}
db = np.abs(A - BUILDER).max(2)
out["vs_builder_finish_final_changed_pct_of_frame"] = round(100 * ((db > 24) & ~noise).mean(), 3)
out["door_box_changed_pct_of_box"] = round(100 * (d > 24)[box].mean(), 2)
json.dump(out, open(V + "json/ref2.json", "w"), indent=1)
img = np.zeros(d.shape + (3,), np.uint8)
img[(d > 24) & ~noise] = (255, 40, 40); img[(d > 24) & noise] = (60, 90, 255); img[box] = img[box] // 2 + 40
img[345, 660:1260] = (255, 255, 0); img[0:345, 660] = (255, 255, 0); img[0:345, 1259] = (255, 255, 0)
Image.fromarray(img).save(V + "caps/VDIFF_Ref2Match.png")
print(json.dumps(out, indent=1))
