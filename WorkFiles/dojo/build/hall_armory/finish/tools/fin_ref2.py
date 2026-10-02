"""FINISH stage: CAM_Ref2Match backdrop against the landscape round's capture (the verifier's regions, v_ref2_regions.py),
for the fix round's final (before this stage) and this stage's final; live noise = pixels that differ (> 24/255, dilated
3 px) between this stage's two identical capture runs. Writes finish/caps/BEFORE_AFTER_Ref2Match.jpg,
finish/caps/DIFF_CAM_Ref2Match.png and finish/json/ref2_backdrop.json."""
import json
import numpy as np
from PIL import Image, ImageDraw

B = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/"
F = B + "hall_armory/finish/"


def ld(p):
    return np.asarray(Image.open(B + p).convert("RGB")).astype(np.int16)


LAND = ld("landscape/fix/caps/CAM_Ref2Match.png")
FIX = ld("hall_armory/fix/caps/final/CAM_Ref2Match.png")
FIN = ld("hall_armory/finish/caps/final/CAM_Ref2Match.png")
NOI = ld("hall_armory/finish/caps/noise/CAM_Ref2Match.png")
FIXN = ld("hall_armory/fix/caps/noise/CAM_Ref2Match.png")


def dil(m, k=3):
    o = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


box = np.zeros(LAND.shape[:2], bool)
box[615:733, 823:1096] = True          # the open door box (the verifier's projected box)


def regions(A, noise):
    d = np.abs(A - LAND).max(2)
    out = {}
    for name, rows, cols in (("backdrop_rows_0_500", slice(0, 500), slice(None)),
                             ("above_main_roof_x660_1260_rows0_345", slice(0, 345), slice(660, 1260)),
                             ("hall_courtyard_rows_500_1440_outside_door_box", slice(500, 1440), slice(None))):
        ch = (d > 24)[rows, cols] & ~box[rows, cols]
        st = ch & ~noise[rows, cols]
        out[name] = {"changed_px": int(ch.sum()), "static_changed_px": int(st.sum()),
                     "static_pct_of_frame": round(100 * st.sum() / d[..., ].size, 3),
                     "static_pct_of_region": round(100 * st.mean(), 3),
                     "mean_abs_diff": round(float(np.abs(A - LAND)[rows, cols].mean()), 3)}
    return out, d


noise_fin = dil(np.abs(FIN - NOI).max(2) > 24)
noise_fix = dil(np.abs(FIX - FIXN).max(2) > 24)
r_fix, d_fix = regions(FIX, noise_fix)
r_fin, d_fin = regions(FIN, noise_fin)
res = {"against": "landscape/fix/caps/CAM_Ref2Match.png (the landscape round, before the hall + armory move)",
       "noise": "two identical capture runs of each state; pixels differing > 24/255 (dilated 3 px) are live noise",
       "live_noise_pct": {"fix": round(100 * noise_fix.mean(), 3), "finish": round(100 * noise_fin.mean(), 3)},
       "fix_round_final": r_fix, "finish_final": r_fin}
(open(F + "json/ref2_backdrop.json", "w")).write(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
# sheet: landscape | fix final | finish final (top 560 rows = the backdrop), and the diff maps
h = 560
tiles = [LAND[:h], FIX[:h], FIN[:h]]
sheet = np.concatenate(tiles, 0).clip(0, 255).astype(np.uint8)
im = Image.fromarray(sheet)
dr = ImageDraw.Draw(im)
for k, t in enumerate(["LANDSCAPE ROUND (before the move)", "FIX ROUND final (backdrop sank)", "FINISH final (restored)"]):
    dr.rectangle([0, k * h, 520, k * h + 34], fill=(0, 0, 0))
    dr.text((8, k * h + 8), t, fill=(255, 255, 255))
im.save(F + "caps/BEFORE_AFTER_Ref2Match.jpg", quality=90)


def diffimg(d, noise):
    img = np.zeros(d.shape + (3,), np.uint8)
    img[(d > 24) & ~noise] = (255, 40, 40)
    img[(d > 24) & noise] = (60, 90, 255)
    img[box] = img[box] // 2 + 40
    return img


Image.fromarray(np.concatenate([diffimg(d_fix, noise_fix), diffimg(d_fin, noise_fin)], 1)).save(
    F + "caps/DIFF_CAM_Ref2Match_fix_vs_finish.png")


# the forest / hill only: pixels of rows 0-500 that are vegetation or ground in EITHER image (not sky: the UDS cloud
# layer differs between the landscape round's capture and every later run, on both the fix and the finish captures)
def nonsky(A):
    r, g, b = A[..., 0], A[..., 1], A[..., 2]
    lum = (r + g + b) / 3
    return ~((b >= g - 4) & (lum > 95))     # sky / cloud: bright, blue >= green


res["forest_and_hill_only_rows_0_500"] = {}
for nm, A, noise, d in (("fix_round_final", FIX, noise_fix, d_fix), ("finish_final", FIN, noise_fin, d_fin)):
    m = (nonsky(LAND) | nonsky(A))[:500] & ~box[:500]
    ch = (d > 24)[:500] & m & ~noise[:500]
    mr = m.copy(); mr[:, :660] = False; mr[:, 1260:] = False; mr[345:] = False
    chr_ = (d > 24)[:500] & mr & ~noise[:500]
    res["forest_and_hill_only_rows_0_500"][nm] = {"region_px": int(m.sum()), "static_changed_px": int(ch.sum()),
                                                  "static_pct_of_region": round(100 * ch.sum() / max(1, m.sum()), 3),
                                                  "above_main_roof_px": int(mr.sum()),
                                                  "above_main_roof_static_pct": round(100 * chr_.sum() / max(1, mr.sum()), 3)}
(open(F + "json/ref2_backdrop.json", "w")).write(json.dumps(res, indent=1))
print(json.dumps(res["forest_and_hill_only_rows_0_500"], indent=1))
