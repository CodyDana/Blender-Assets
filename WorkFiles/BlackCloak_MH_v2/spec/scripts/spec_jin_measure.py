"""Measure the Jin_Cloak LOOK reference (never used as a texture/trace): face landmarks, funnel collar rim vs face,
funnel widths, clasp, fold-fan crossings around the clasp, silhouette half-widths. Output spec/out/spec_jin_measure.json
+ an annotated overlay. Coordinates are full-res px (2420x3632), y down."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
from spec_imgutil import *
import numpy as np
O = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
a = load(os.path.join(O, "spec_jin_full.png"))[..., :3] * 255.0
H, W = a.shape[:2]
R, G, B = a[..., 0], a[..., 1], a[..., 2]
L = luma(a / 255.0) * 255
skin = (np.abs(R - 196) < 18) & (np.abs(G - 186) < 18) & (np.abs(B - 179) < 20) & (R - B > 8)
bg = (np.abs(R - 197) < 10) & (np.abs(G - 197) < 10) & (np.abs(B - 197) < 10)
cloakfill = (L > 30) & (L < 60) & (R - G < 12) & (R - G >= 2)
ink = L < 22
res = {}
# ---- face region: largest skin area in the top 1000 rows
ys, xs = np.nonzero(skin[:1100])
res["skin_bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
# eyes: dark pixels inside the skin bbox rows 450-640, within the face columns
fx0, fx1 = 950, 1330
eye = (L < 90)
band = eye[450:640, fx0:fx1]
ry, rx = np.nonzero(band)
# split by x at the face centre
cx_face = 1130
le = rx + fx0 < cx_face; ri = ~le
def cen(mask):
    return [float(rx[mask].mean() + fx0), float(ry[mask].mean() + 450)]
res["eye_left_img"] = cen(le); res["eye_right_img"] = cen(ri)
ipd = res["eye_right_img"][0] - res["eye_left_img"][0]
eye_y = 0.5 * (res["eye_left_img"][1] + res["eye_right_img"][1])
res["ipd_px"] = ipd; res["eye_y"] = eye_y
# nose tip: the darkest short row segment in column band 1100..1150 between y 640..740
colL = L[640:745, 1095:1155].mean(1)
res["nose_tip_y"] = float(640 + int(np.argmin(colL)))
# collar rim: for each column across the face, lowest skin row above y=900 (first non-skin after skin going down)
rim = {}
for x in range(960, 1320, 10):
    col = skin[400:1000, x]
    idx = np.nonzero(col)[0]
    if len(idx): rim[x] = int(idx.max() + 400)
res["collar_rim_under_face"] = rim
cx = int(round((res["eye_left_img"][0] + res["eye_right_img"][0]) / 2))
res["face_centre_x"] = cx
rim_c = np.median([v for k, v in rim.items() if abs(k - cx) <= 30])
res["collar_rim_y_at_centre"] = float(rim_c)
en = res["nose_tip_y"] - eye_y
res["ratios"] = {
    "eye_to_nosetip_over_ipd": en / ipd,
    "eye_to_rim_centre_over_eye_to_nosetip": (rim_c - eye_y) / en,
    "rim_below_nosetip_over_ipd": (rim_c - res["nose_tip_y"]) / ipd,
}
# face width at the rim / at the eye line (skin extent)
def skin_extent(y):
    xs = np.nonzero(skin[y, 700:1600])[0]
    return [int(xs.min() + 700), int(xs.max() + 700)] if len(xs) else None
res["skin_extent_eye_row"] = skin_extent(int(eye_y)); res["skin_extent_nose_row"] = skin_extent(int(res["nose_tip_y"]) - 5)
# ---- clasp: dark disc near (563,1320): radius from the ink ring crossing along 8 directions
cxp, cyp = 563, 1320
rads = []
for ang in range(0, 360, 15):
    t = math.radians(ang); best = None
    prof = [L[int(cyp + r * math.sin(t)), int(cxp + r * math.cos(t))] for r in range(30, 110)]
    # outer ring = the darkest ink ring (outline) - take the last minimum below 25
    ids = [i for i, v in enumerate(prof) if v < 25]
    if ids: rads.append(30 + ids[-1])
res["clasp_centre_img"] = [cxp, cyp]; res["clasp_radius_px_samples"] = rads
res["clasp_radius_px_median"] = float(np.median(rads)) if rads else None
# ---- fold fan: along arcs around the clasp, find ink-line crossings; angle 0 = +x (viewer-right), 90 = straight down
fan = {}
for r in (250, 400, 600, 800, 1000, 1300, 1600, 2000):
    xs_, hits = [], []
    prev = False; start = None
    for k in range(0, 1801):
        ang = -60 + k * 0.1   # -60 (up-right) .. 120 (down-left)
        t = math.radians(ang)
        x = int(round(cxp + r * math.cos(t))); y = int(round(cyp + r * math.sin(t)))
        if not (0 <= x < W and 0 <= y < H): cur = False
        else: cur = bool(ink[y, x]) and bool(cloakfill[max(0,y-12):y+13, max(0,x-12):x+13].any())
        if cur and not prev: start = ang
        if not cur and prev: hits.append(round((start + ang) / 2, 1))
        prev = cur
    fan[r] = hits
res["fan_crossings_deg_by_radius_px"] = fan
# ---- silhouette half-widths of the dark cloak vs the grey background per row (only where both edges are in frame)
sil = {}
dark = L < 90
for y in range(900, 3600, 100):
    row = dark[y]
    xs = np.nonzero(row)[0]
    sil[y] = [int(xs.min()), int(xs.max())] if len(xs) else None
res["dark_extent_rows"] = sil
json.dump(res, open(os.path.join(O, "spec_jin_measure.json"), "w"), indent=1)
# overlay
ov = a.copy() / 255.0
ov[skin] = ov[skin] * 0.5 + np.array([0, 0.5, 0])
for x, y in rim.items(): ov[y-4:y+5, x-4:x+5] = (1, 0, 0)
for e in (res["eye_left_img"], res["eye_right_img"]): ov[int(e[1])-6:int(e[1])+7, int(e[0])-6:int(e[0])+7] = (0, 0, 1)
ov[int(res["nose_tip_y"]) - 2:int(res["nose_tip_y"]) + 3, cx - 60:cx + 60] = (1, 1, 0)
for r, hs in fan.items():
    for ang in hs:
        t = math.radians(ang); x = int(cxp + r * math.cos(t)); y = int(cyp + r * math.sin(t))
        if 0 <= x < W and 0 <= y < H: ov[max(0,y-8):y+9, max(0,x-8):x+9] = (1, 0.5, 0)
save(ov[::3, ::3], os.path.join(O, "spec_jin_measure_overlay.png"))
print(json.dumps({k: v for k, v in res.items() if k not in ("collar_rim_under_face", "dark_extent_rows")}, indent=1))
