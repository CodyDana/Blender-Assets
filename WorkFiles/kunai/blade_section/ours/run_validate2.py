"""Validation of the FIXED procedure (de-blurred matcap) on renders of our kunai with known sections.

For each render: RATIO estimator (albedo-free, roll from the measured ridge offset) with
  K10  : kernel-smoothed matcap, sigma 0.10 (the measurers' style: A 0.12, B 4-deg bins)  -> the bias we found
  DB   : de-blurred matcap (forward model: pixel box + PSF), orthographic
  DBP  : de-blurred + perspective-corrected lookup (known focal; the photo's is unknown)
at three image scales: 1.0 (probe tube 7.8 px), 0.7 (tube 5.4 px = the photo's ring tube), 0.5 (3.9 px).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP  # noqa: E402
from run_validate import FV, x_of_fvis, analytic  # noqa: E402

HERE = Path(__file__).parent


def resize(a, scale):
    if scale == 1.0:
        return a
    h, w = a.shape
    return np.asarray(Image.fromarray(a.astype(np.float32), mode="F").resize((round(w * scale), round(h * scale)),
                                                                             Image.BOX))


def analyse(png, k, scale, methods=("K10", "DB", "DBP"), sig_psf=0.35):
    meta = json.loads(Path(str(png) + ".json").read_text())
    lum0, alpha0 = SP.load_lum(png)
    lum, alpha = resize(lum0, scale), resize(alpha0, scale)
    blade = SP.blade_from_meta(meta, scale=scale, visible_x=x_of_fvis(1.0))
    pr = meta["probe"]
    centre = np.array(pr["centre_px"]) * scale
    cl = [[p[0] * scale, p[1] * scale] for p in pr["centreline_px"]]
    tube = pr["tube_r_px"] * scale
    sig = sig_psf * max(scale, 0.5)
    fn, box = SP.ring_d_centreline(centre, cl, tube)
    dmax = 1.0 - (0.5 + 2 * sig) / tube
    pix = SP.probe_pixels(fn, box, dmax)
    W, H = lum.shape[1], lum.shape[0]
    f_px = meta["args"]["focal"] / 36.0 * W
    mcs = {}
    if "K10" in methods:
        S = SP.probe_samples_centreline(lum, centre, cl, tube)
        k10 = SP.Matcap(S, 0.10)
        mcs["K10"] = lambda n2, at=None, m=k10: m(n2)
    if "DB" in methods:
        mcs["DB"] = SP.DeblurMatcap(lum, fn, pix, sig_psf=sig)
    if "DBP" in methods:
        mcs["DBP"] = SP.DeblurMatcap(lum, fn, pix, sig_psf=sig, persp=(f_px, W / 2, H / 2))
    xs = [x_of_fvis(f) for f in FV]
    rows = []
    for f, x in zip(FV, xs):
        s = blade.s_of_x(x)
        q, *_ = SP.ridge_offset(lum, blade, s, alpha=alpha)
        an = analytic(x, k)
        row = {"frac_vis": f, "x_mm": round(x, 2), "true_face_slope": round(an["face_slope"], 4), "q": round(q, 4)}
        for name, mc in mcs.items():
            res = SP.run2(lum, blade, mc, [s], lambda _s: q, alpha=alpha, gain1=(name == "DB"))[0]
            row[name] = res["ratio_r"]
            row[name + "_band"] = res["ratio_band10"]
            if name == "DB":
                row["DB_gain1_r"] = res["gain1_r"]
                row["DB_gain1_roll"] = res["gain1_roll"]
                row["DB_gain_fitted"] = round(res["gain_fitted"], 3)
                row["L_srgb"] = [round(res["L_top_srgb"], 1), round(res["L_bot_srgb"], 1)]
        rows.append(row)
    return rows


def summarise(rows, key, front_only=True):
    rr = [r for r in rows if (r["frac_vis"] >= 0.3 or not front_only)]
    ratios = [r[key] / r["true_face_slope"] for r in rr if r.get(key) is not None]
    return float(np.median(ratios))


if __name__ == "__main__":
    cases = [("v1_z1", 1.0), ("v7_z1_roll6", 1.0), ("v4_z1_probe035", 1.0), ("v3_z2", 2.0), ("v6_z2_roll6", 2.0),
             ("v2_z35", 3.5), ("v8_z35_roll0", 3.5), ("v5_z35_probe035", 3.5)]
    out = {}
    for name, k in cases:
        for scale in (1.0, 0.7, 0.5):
            key = f"{name}@{scale}"
            rows = analyse(HERE / "validate" / f"{name}.png", k, scale)
            out[key] = {"rows": rows, "median_recovered_over_true_front": {m: summarise(rows, m) for m in
                                                                          ("K10", "DB", "DBP", "DB_gain1_r")}}
            print("==", key, {m: round(v, 3) for m, v in out[key]["median_recovered_over_true_front"].items()})
            for r in rows:
                print("   f%.2f x%6.1f true %.3f | K10 %.3f | DB %.3f %s | DBP %.3f | G1 %.3f roll %.1f g %.2f | q %.4f L %s"
                      % (r["frac_vis"], r["x_mm"], r["true_face_slope"], r["K10"], r["DB"], r["DB_band"], r["DBP"],
                         r["DB_gain1_r"], r["DB_gain1_roll"], r["DB_gain_fitted"], r["q"], r["L_srgb"]))
    (HERE / "validate" / "validation2_results.json").write_text(json.dumps(out, indent=1))
