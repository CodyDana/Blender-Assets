"""bhstudy_measure_ref.py - coarse metrology of References/BlackHat/blackhat_guide.png for BLACKHAT_STUDY.md.

Run headless:
  blender -b --factory-startup --python bhstudy_measure_ref.py
Reads the reference only; writes numbers to bhstudy_measure_ref.json and viewing aids to views/ (never shipped).
"""
import json, os, hashlib
import numpy as np
import OpenImageIO as oiio

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
REF = ROOT + "/References/BlackHat/blackhat_guide.png"
OUT = ROOT + "/WorkFiles/blackhat/study_calc"
VIEWS = OUT + "/views"
os.makedirs(VIEWS, exist_ok=True)

buf = oiio.ImageBuf(REF)
spec = buf.spec()
px = buf.get_pixels(oiio.FLOAT)  # stored sRGB / 255 (no colour conversion)
H, W, C = px.shape
rgb = px[..., :3].astype(np.float64)
sha = hashlib.sha256(open(REF, "rb").read()).hexdigest()

luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
mask = luma < 0.93

def save(name, img):
    img = np.clip(img, 0, 1).astype(np.float32)
    if img.ndim == 2:
        img = np.repeat(img[..., None], 3, axis=2)
    h, w = img.shape[:2]
    s = oiio.ImageSpec(w, h, 3, oiio.UINT8)
    o = oiio.ImageBuf(s)
    o.set_pixels(oiio.ROI(0, w, 0, h, 0, 1, 0, 3), img)
    o.write(VIEWS + "/" + name)

def crop_up(x0, y0, x1, y1, k=4, gain=3.0):
    c = rgb[y0:y1, x0:x1]
    c = np.clip(c * gain, 0, 1)
    c = np.repeat(np.repeat(c, k, axis=0), k, axis=1)
    return c

res = {"file": REF, "sha256": sha, "pixels": [W, H], "channels": C}

ys, xs = np.nonzero(mask)
res["silhouette_bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

# per-column top / bottom of the mask
cols = {}
top = np.full(W, -1); bot = np.full(W, -1)
for x in range(W):
    c = np.nonzero(mask[:, x])[0]
    if len(c):
        top[x] = c.min(); bot[x] = c.max()
res["apex_col"] = int(np.argmin(np.where(top >= 0, top, 10**6)))
res["apex_top_y"] = int(top[res["apex_col"]])
# per-row left / right
left = np.full(H, -1); right = np.full(H, -1)
for y in range(H):
    r = np.nonzero(mask[y, :])[0]
    if len(r):
        left[y] = r.min(); right[y] = r.max()
yl = int(np.argmin(np.where(left >= 0, left, 10**6)))
res["leftmost"] = [int(left[yl]), yl]
# rows where the leftmost x is within 2 px of the min
lrows = np.nonzero((left >= 0) & (left <= left[yl] + 2))[0]
res["leftmost_rows"] = [int(lrows.min()), int(lrows.max())]
# right rim extreme: tails hang lower right, so restrict to rows above 380
rr = np.where((right >= 0) & (np.arange(H) < 380), right, -1)
yr = int(np.argmax(rr))
res["rightmost_above380"] = [int(rr[yr]), yr]
rrows = np.nonzero(rr >= rr[yr] - 2)[0]
res["rightmost_rows"] = [int(rrows.min()), int(rrows.max())]

# bottom profile (the front rim) for columns in the left 3/4 (tails on right)
res["bottom_profile"] = {str(x): int(bot[x]) for x in range(0, W, 10) if bot[x] >= 0}
res["top_profile"] = {str(x): int(top[x]) for x in range(0, W, 10) if top[x] >= 0}

# colour stats inside the hat body (exclude tails region roughly x>470,y>300 and rim band) - coarse
body = mask.copy()
body[:, 470:] &= np.arange(H)[:, None] < 300
lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
sel = body & (luma < 0.9)
L = luma[sel]
res["body_stored_luma_pct"] = {p: round(float(np.percentile(L, p)), 4) for p in (1, 5, 25, 50, 75, 95, 99)}
lr = lin[sel]
res["body_linear_rgb_p50"] = [round(float(np.median(lr[:, i])), 5) for i in range(3)]
res["body_linear_rgb_mean"] = [round(float(lr[:, i].mean()), 5) for i in range(3)]
mr = lr.mean(axis=0)
res["body_hue_ratio"] = [1.0, round(float(mr[1] / mr[0]), 3), round(float(mr[2] / mr[0]), 3)]

# tails region stats
tail = mask & (np.arange(W)[None, :] > 480) & (np.arange(H)[:, None] > 360)
T = luma[tail]
res["tail_region_stored_luma_pct"] = {p: round(float(np.percentile(T, p)), 4) for p in (5, 50, 95)}
lt = lin[tail].mean(axis=0)
res["tail_hue_ratio"] = [1.0, round(float(lt[1] / lt[0]), 3), round(float(lt[2] / lt[0]), 3)]
res["tail_bbox"] = [int(np.nonzero(tail)[1].min()), int(np.nonzero(tail)[0].min()),
                    int(np.nonzero(tail)[1].max()), int(np.nonzero(tail)[0].max())]

# backdrop
bg = ~mask
res["backdrop_stored_luma_p50"] = round(float(np.median(luma[bg])), 4)
res["backdrop_stored_luma_p01"] = round(float(np.percentile(luma[bg], 1)), 4)

json.dump(res, open(OUT + "/bhstudy_measure_ref.json", "w"), indent=1)

# viewing aids
save("full_gain3.png", np.clip(rgb * 3.0, 0, 1))
save("mask.png", mask.astype(float))
save("crop_crown_x4.png", crop_up(270, 130, 420, 230, 4, 3))
save("crop_rimfront_x3.png", crop_up(60, 330, 460, 450, 3, 3))
save("crop_rimleft_x4.png", crop_up(0, 250, 160, 380, 4, 3))
save("crop_rimright_x4.png", crop_up(520, 250, 670, 400, 4, 3))
save("crop_knot_x3.png", crop_up(400, 170, 600, 330, 3, 3))
save("crop_tails_x2.png", crop_up(450, 250, 670, 540, 2, 3))
save("crop_weave_x6.png", crop_up(200, 260, 300, 340, 6, 4))
print(json.dumps(res, indent=1))
