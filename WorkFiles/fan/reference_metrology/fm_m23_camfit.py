"""Stage 23: fan2 camera fit. Pinhole, principal point at the image centre, sensor upright (no pitch), fan plane tilted by alpha
about its horizontal axis through the rivet (top away from the camera), roll free. Data: subpixel outer-edge radius r(phi) about
the rivet image for phi in [12,170]. Ladder over camera distance D (in L = rivet-to-leaf-edge radius); alpha, image scale
s = f/D (px per L at the rivet depth) and roll fitted. Also the predicted image-angle pitch non-uniformity (25 equal gaps)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json"))); rx, ry = S2["2"]["rivet_bright_centroid"]
rs = np.load(os.path.join(OUT, "fm_rout_sub2.npy")); th, rout = rs[:, 0], rs[:, 1]
m = (th > 12) & (th < 170) & ~np.isnan(rout); th, rout = th[m], rout[m]
def model(D, alpha, s, roll, t):
    f = s*D; a = np.radians(alpha); X0 = (rx-400)/f*D; Y0 = -(ry-400)/f*D
    ro = np.radians(roll); ct, st = np.cos(t+ro), np.sin(t+ro)
    X = X0 + ct; Y = Y0 + st*np.cos(a); Z = D + st*np.sin(a)
    xi = 400 + f*X/Z; yi = 400 - f*Y/Z
    return np.degrees(np.arctan2(ry - yi, xi - rx)), np.hypot(xi-rx, yi-ry)
t = np.radians(np.linspace(0, 180, 721))
res = {}
for D in (1.8, 2.2, 2.6, 3.0, 3.34, 4.0, 5.0, 7.0, 10.0, 20.0):
    best = None
    for alpha in np.arange(0, 40.01, 1.0):
        for roll in (-1.0, 0.0, 1.0):
            for s in np.arange(330, 356, 1.0):
                phi, r = model(D, alpha, s, roll, t); o = np.argsort(phi)
                e = float(np.sqrt(np.mean((rout - np.interp(th, phi[o], r[o]))**2)))
                if best is None or e < best[0]: best = (e, alpha, roll, s)
    # refine alpha / s finely around best
    e0, a0, r0, s0 = best
    for alpha in np.arange(max(0, a0-1), a0+1.01, 0.1):
        for s in np.arange(s0-1, s0+1.01, 0.1):
            phi, r = model(D, alpha, s, r0, t); o = np.argsort(phi)
            e = float(np.sqrt(np.mean((rout - np.interp(th, phi[o], r[o]))**2)))
            if e < best[0]: best = (e, alpha, r0, s)
    e, alpha, roll, s = best
    tt = np.radians(np.linspace(8, 172, 26)); ph, _ = model(D, alpha, s, 0, tt)
    pitch = np.diff(ph); thirds = [round(float(np.mean(x)), 3) for x in np.array_split(pitch, 3)]
    res[D] = dict(rms_px=round(e, 3), alpha_deg=round(float(alpha), 2), roll_deg=roll, s_px_per_L=round(float(s), 2),
                  f_px=round(float(s*D), 1), f_mm_on_36mm_800px=round(float(s*D*36/800), 1), hfov_deg=round(float(2*np.degrees(np.arctan(400/(s*D)))), 1),
                  pred_pitch_thirds=thirds)
res['circle_at_rivet_rms_px'] = round(float(np.std(rout)), 3)
json.dump(res, open(os.path.join(OUT, "fm_s23_camfit.json"), "w"), indent=0)
for k, v in res.items(): print("CAM", k, v)
