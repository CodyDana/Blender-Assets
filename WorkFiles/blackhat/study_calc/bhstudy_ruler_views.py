"""bhstudy_ruler_views.py - rim and cone unwraps with azimuth tick marks (every 5 deg, long every 10 deg) for reading
lashing, rib and band positions by eye. Viewing aids only (views/ruler_*.png)."""
import json
import numpy as np
import OpenImageIO as oiio

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/blackhat/study_calc"
REF = ROOT + "/References/BlackHat/blackhat_guide.png"
fit = json.load(open(OUT + "/bhstudy_unwrap.json"))
px = oiio.ImageBuf(REF).get_pixels(oiio.FLOAT)
H, W = px.shape[:2]
rgb = px[..., :3].astype(np.float64)
xc = fit["centre_x_px"]; xa, ya = fit["virtual_apex_px"]
A = fit["projection"]["A_roll_centre_px"]
B = fit["projection"]["B_px"]; D = fit["projection"]["D_direct_px"]

def bil(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

def save(name, img):
    img = np.clip(img, 0, 1).astype(np.float32)
    h, w = img.shape[:2]
    o = oiio.ImageBuf(oiio.ImageSpec(w, h, 3, oiio.UINT8))
    o.set_pixels(oiio.ROI(0, w, 0, h, 0, 1, 0, 3), img)
    o.write(OUT + "/views/" + name)

def unwrap(p0, p1, f0, f1, ppd, rows):
    phis = np.linspace(p0, p1, int((p1 - p0) * ppd) + 1)
    fs = np.linspace(f0, f1, rows)
    P, F = np.meshgrid(np.radians(phis), fs)
    img = bil(rgb, xc + F * A * np.sin(P), ya + F * (D + B * np.cos(P))) * 3
    ruler = np.ones((24, len(phis), 3))
    for i, ph in enumerate(phis):
        r = ph - np.floor(ph)
        if abs(ph - round(ph)) < 0.5 / ppd and int(round(ph)) % 5 == 0:
            L = 22 if int(round(ph)) % 10 == 0 else 10
            ruler[:L, i] = (1, 0, 0) if int(round(ph)) % 30 == 0 else (0, 0, 0)
    return np.concatenate([ruler, img, ruler[::-1]], 0)

save("ruler_rim_left.png", unwrap(-88, 0, 0.90, 1.06, 12, 110))
save("ruler_rim_right.png", unwrap(0, 88, 0.90, 1.06, 12, 110))
save("ruler_cone_left.png", unwrap(-88, 0, 0.0, 1.03, 9, 520))
save("ruler_cone_right.png", unwrap(0, 88, 0.0, 1.03, 9, 520))
