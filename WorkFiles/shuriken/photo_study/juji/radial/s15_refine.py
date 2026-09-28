"""Refined edge positions and ridge (medial crest) line for each arm.

Frame: the watershed-mask arm axis (arm_ws_<name>.npz): origin, u (outward), n (arm's left).
For stations s (1 px), colour profiles along n are averaged over s-2..s+2.
Per side:
  t50  : half-contrast crossing between local lid colour B (28-40 px outside the watershed edge) and
         object colour O (6-14 px inside), coming from outside.
  t90  : 90 % crossing (inner end of the ramp).
  band : if a near-black run (lum < 0.12) starts within 4 px of the watershed edge and runs inward, its
         inner boundary (50 % between band level and the object level just inside it); NaN otherwise.
Ridge: the crest line between the two bevels, located as the strongest luminance step or highlight
within +-25 px of the mask midline at stations in the neck (110..330 px) and near the tip (0.86..0.97 R),
fitted with a robust straight line t_r(s) = a + b s.
All t values are in px along n from the watershed axis. Saves refine_<arm>.npz and prints summaries.
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
ab = jlib.gblur(a, 0.7)
tag = "ws"
names = ["right", "top", "left", "bottom"]
summary = {}
for nme in names:
    d = np.load(os.path.join(jlib.OUT, "arm_%s_%s.npz" % (tag, nme)))
    prof, u, n, origin = d["prof"], d["u"], d["n"], d["origin"]
    fin = np.isfinite(prof[:, 1])
    R = prof[fin, 0].max()
    S = np.arange(60, int(R) + 1, 1.0)
    T = np.arange(-140, 140.01, 0.5)
    # straightened colour strip averaged over 5 stations
    acc = np.zeros((len(S), len(T), 3))
    for ds in (-2, -1, 0, 1, 2):
        X = origin[0] + (S[:, None] + ds) * u[0] + T[None, :] * n[0]
        Y = origin[1] + (S[:, None] + ds) * u[1] + T[None, :] * n[1]
        acc += jlib.bilinear(ab, X, Y)
    C = (acc / 5).astype(np.float32)
    L = C.mean(2)
    res = {k: np.full(len(S), np.nan) for k in ("ws_L", "ws_R", "t50_L", "t50_R", "t90_L", "t90_R", "band_L", "band_R", "ridge_raw", "contrast_L", "contrast_R")}
    for i, s in enumerate(S):
        j = int(np.argmin(np.abs(prof[:, 0] - s)))
        if not np.isfinite(prof[j, 1]):
            continue
        for side, te in (("L", prof[j, 1]), ("R", prof[j, 2])):
            sg = 1.0 if side == "L" else -1.0
            res["ws_" + side][i] = te
            rel = sg * (T - te)            # >0 outside
            B = np.median(C[i][(rel >= 28) & (rel <= 40)], 0)
            O = np.median(C[i][(rel >= -14) & (rel <= -6)], 0)
            v = O - B
            den = float(v @ v)
            res["contrast_" + side][i] = math.sqrt(den)
            if den < 0.03 ** 2:
                continue
            f = (C[i] - B) @ v / den
            order = np.argsort(-rel)       # from outside inward
            ro = rel[order]; fo = f[order]
            sel = (ro <= 40) & (ro >= -20)
            ro = ro[sel]; fo = fo[sel]
            for lev, key in ((0.5, "t50_"), (0.9, "t90_")):
                k = np.argmax(fo >= lev)
                if fo[k] >= lev and k > 0:
                    tr = ro[k - 1] + (lev - fo[k - 1]) / (fo[k] - fo[k - 1]) * (ro[k] - ro[k - 1])
                    res[key + side][i] = te + sg * tr
            # black band
            Lo = L[i][order][sel]
            k0 = np.nonzero((ro <= 4) & (ro >= -4) & (Lo < 0.12))[0]
            if len(k0):
                k = k0[0]
                while k + 1 < len(ro) and Lo[k + 1] < 0.12:
                    k += 1
                t_in = ro[k]
                if t_in < -3 and k + 12 < len(ro):
                    band_level = np.median(Lo[k0[0]:k + 1])
                    obj_level = np.median(Lo[k + 3:k + 13])
                    if obj_level - band_level > 0.05:
                        half = 0.5 * (band_level + obj_level)
                        kk = k
                        while kk + 1 < len(ro) and Lo[kk + 1] < half:
                            kk += 1
                        if kk + 1 < len(ro):
                            tr = ro[kk] + (half - Lo[kk]) / (Lo[kk + 1] - Lo[kk]) * (ro[kk + 1] - ro[kk])
                            res["band_" + side][i] = te + sg * tr
        # ridge candidate: strongest luminance step within +-25 px of the midline
        mid = 0.5 * (prof[j, 1] + prof[j, 2])
        sel = np.abs(T - mid) <= 25
        Ls = L[i][sel]
        dL = np.gradient(jlib.gblur(Ls[None, :], 1.0)[0]) if False else np.gradient(np.convolve(Ls, np.ones(3) / 3, 'same'))
        k = int(np.argmax(np.abs(dL[3:-3])) + 3)
        res["ridge_raw"][i] = T[sel][k]
    # robust ridge line fit on neck + near-tip stations
    rsel = (((S >= 110) & (S <= 330)) | ((S >= 0.86 * R) & (S <= 0.97 * R))) & np.isfinite(res["ridge_raw"])
    ss, tt = S[rsel], res["ridge_raw"][rsel]
    keep = np.ones(len(ss), bool)
    for it in range(6):
        A = np.stack([np.ones(keep.sum()), ss[keep]], 1)
        (ra, rb), *_ = np.linalg.lstsq(A, tt[keep], rcond=None)
        r = tt - (ra + rb * ss)
        mad = np.median(np.abs(r[keep])) * 1.4826 + 0.3
        keep = np.abs(r) < 2.5 * mad
    ridge = ra + rb * S
    frac_in = keep.mean()
    np.savez(os.path.join(jlib.OUT, "refine_%s.npz" % nme), S=S, ridge=ridge, ridge_a=ra, ridge_b=rb, R=R,
             **res)
    summary[nme] = dict(R=R, ridge_a=ra, ridge_b_deg=math.degrees(math.atan(rb)), ridge_inlier_frac=frac_in,
                        ridge_resid_mad=float(mad))
    print(nme, {k: round(float(v), 3) for k, v in summary[nme].items()})

# report half-widths from ridge
print("\nhalf-widths from the ridge line: +side(L) / -side(R); variants ws, t50, t90, band")
for nme in names:
    z = np.load(os.path.join(jlib.OUT, "refine_%s.npz" % nme))
    S = z["S"]; rg = z["ridge"]
    print("--", nme, "R=%.1f" % z["R"])
    print("   s     wsL   wsR |  t50L  t50R |  t90L  t90R | bandL bandR | contrastL/R")
    for s in [120, 160, 200, 240, 280, 320, 360, 400, 440, 480, 520, 560, 600, 630]:
        i = int(np.argmin(np.abs(S - s)))
        f = lambda k, sg: sg * (z[k][i] - rg[i])
        print("%5d  %5.1f %5.1f | %5.1f %5.1f | %5.1f %5.1f | %5.1f %5.1f | %.3f %.3f" % (
            s, f("ws_L", 1), f("ws_R", -1), f("t50_L", 1), f("t50_R", -1), f("t90_L", 1), f("t90_R", -1),
            f("band_L", 1), f("band_R", -1), z["contrast_L"][i], z["contrast_R"][i]))
