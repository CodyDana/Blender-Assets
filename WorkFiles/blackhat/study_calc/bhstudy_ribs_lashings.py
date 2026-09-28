"""bhstudy_ribs_lashings.py - detect rib and lashing azimuths on the unwrapped front half of blackhat_guide.png.

Uses the orthographic fit from bhstudy_unwrap.json. Azimuth phi: 0 = toward the camera, + = image right.
Also tries the rib/lashing count N that best explains the detected azimuths (phase-fit), for N in 6..40.
"""
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
luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

xc = fit["centre_x_px"]; xa, ya = fit["virtual_apex_px"]
A = fit["projection"]["A_roll_centre_px"]
B = fit["projection"]["B_px"]
D = fit["projection"]["D_direct_px"]

def bil(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

step = 0.1
phis = np.arange(-80, 80 + step, step)
P = np.radians(phis)

def profile(f0, f1, n=40):
    acc = np.zeros_like(P)
    for f in np.linspace(f0, f1, n):
        X = xc + f * A * np.sin(P)
        Y = ya + f * (D + B * np.cos(P))
        acc += bil(luma, X, Y)
    return acc / n

def highpass(p, halfdeg):
    k = int(round(halfdeg / step))
    pad = np.pad(p, (k, k), mode="edge")
    c = np.cumsum(np.insert(pad, 0, 0))
    return p - (c[2 * k + 1:] - c[:-2 * k - 1]) / (2 * k + 1)

def peaks(p, min_sep_deg, top_n, thresh):
    order = np.argsort(-p)
    out = []
    for i in order:
        if p[i] < thresh:
            break
        if all(abs(phis[i] - q) >= min_sep_deg for q, _ in out):
            out.append((float(phis[i]), float(p[i])))
        if len(out) >= top_n:
            break
    return sorted(out)

res = {"model": {"xc": xc, "apex": [xa, ya], "A": A, "B": B, "D": D}}
# ribs: two bands of slant fraction, below the cloth band and above the rim
for name, (f0, f1) in {"ribs_mid": (0.45, 0.70), "ribs_low": (0.70, 0.88), "ribs_high": (0.33, 0.45)}.items():
    p = highpass(profile(f0, f1), 1.5)
    s = p.std()
    res[name] = {"f": [f0, f1], "std": float(s), "peaks_gt_3sd": peaks(p, 2.0, 40, 3 * s),
                 "peaks_gt_2sd": peaks(p, 2.0, 60, 2 * s)}
# lashings: on the roll, f ~ 0.97-1.02 (bright cord bundles)
p = highpass(profile(0.965, 1.02, 30), 3.0)
s = p.std()
res["lashings"] = {"std": float(s), "peaks_gt_1.5sd": peaks(p, 4.0, 40, 1.5 * s)}

def best_N(angles, Ns=range(6, 41)):
    a = np.radians(np.array(angles))
    out = []
    for N in Ns:
        # circular mean of N*a gives phase; resultant length R measures fit
        z = np.exp(1j * N * a).mean()
        out.append((N, float(abs(z)), float(np.degrees(np.angle(z)) / N)))
    return sorted(out, key=lambda t: -t[1])[:6]

res["rib_count_fit_mid3sd"] = best_N([q for q, _ in res["ribs_mid"]["peaks_gt_3sd"]])
res["lashing_count_fit"] = best_N([q for q, _ in res["lashings"]["peaks_gt_1.5sd"]])
json.dump(res, open(OUT + "/bhstudy_ribs_lashings.json", "w"), indent=1)
for k in ("ribs_high", "ribs_mid", "ribs_low"):
    print(k, [round(q, 1) for q, _ in res[k]["peaks_gt_3sd"]])
print("lash", [round(q, 1) for q, _ in res["lashings"]["peaks_gt_1.5sd"]])
print("ribN", res["rib_count_fit_mid3sd"])
print("lashN", res["lashing_count_fit"])
