"""Apply section_procedure to our validation renders (known section) and report recovered vs analytic face_slope."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP  # noqa: E402

HERE = Path(__file__).parent
FV = [0.10, 0.20, 0.30, 0.45, 0.60, 0.75, 0.90]
PH = {"crease": 40.418, "visible": 154.431, "tip": 180.883}     # photo px along the axis (measurer A)


def x_of_fvis(f):
    s = f * PH["visible"]
    if s <= PH["crease"]:
        return 35.0 * s / PH["crease"]
    return 35.0 + (s - PH["crease"]) / (PH["tip"] - PH["crease"]) * 105.0


def h_blade(x):
    if x <= 35:
        return 8.0 + 10.0 * x / 35.0
    u = (x - 35.0) / 105.0
    return 18.0 * (1 - u) * (1 + 0.25 * u)


def ridge_t(x, base=5.0, tip=1.6, tip_at=135.0):
    return base if x <= 35 else max(tip, base + (tip - base) * (x - 35.0) / (tip_at - 35.0))


def analytic(x, k=1.0, edge_t=1.5, ridge=(5.0, 1.6, 135.0)):
    h = h_blade(x)
    t = ridge_t(x, *ridge)
    return {"x_mm": round(x, 2), "half_width_mm": round(h, 3), "ridge_t_mm": round(t * k, 3),
            "face_slope": k * (0.5 * t - 0.5 * edge_t) / h, "ridge_ratio": k * 0.5 * t / h}


def analyse_render(png, zscale, scale=1.0, sigma=0.10):
    meta = json.loads(Path(str(png) + ".json").read_text())
    lum, alpha = SP.load_lum(png)
    if scale != 1.0:
        from PIL import Image
        W, H = lum.shape[1], lum.shape[0]
        w2, h2 = int(W * scale), int(H * scale)
        lum = np.asarray(Image.fromarray(lum.astype(np.float32), mode="F").resize((w2, h2), Image.BOX))
        alpha = np.asarray(Image.fromarray(alpha.astype(np.float32), mode="F").resize((w2, h2), Image.BOX))
    xs = [x_of_fvis(f) for f in FV]
    blade = SP.blade_from_meta(meta, scale=scale, visible_x=x_of_fvis(1.0))
    pr = meta["probe"]
    S = SP.probe_samples_centreline(lum, np.array(pr["centre_px"]) * scale,
                                    [[p[0] * scale, p[1] * scale] for p in pr["centreline_px"]],
                                    pr["tube_r_px"] * scale)
    mc = SP.Matcap(S, sigma)
    rows = []
    for f, x in zip(FV, xs):
        s = blade.s_of_x(x)
        q, hw, ur, mid = SP.ridge_offset(lum, blade, s, alpha=alpha)
        q_true = (blade.ridge(s) - 0.5 * (blade.top(s) + blade.bot(s))) / (0.5 * (blade.top(s) - blade.bot(s)))
        res = SP.run(lum, blade, mc, [s], lambda _s: q, alpha=alpha)[0]
        an = analytic(x, zscale)
        rows.append({"frac_vis": f, "x_mm": round(x, 2), "analytic_face_slope": round(an["face_slope"], 4),
                     "analytic_ridge_ratio": round(an["ridge_ratio"], 4), "q_meas": round(q, 4),
                     "q_true_projected": round(q_true, 4),
                     "RATIO_r": res["ratio"]["r"], "RATIO_band": res["ratio"]["r_band10"],
                     "RATIO_roll": round(res["ratio"]["roll"], 2), "GAIN1_r": res["gain1"]["r"],
                     "GAIN1_roll": res["gain1"]["roll"], "gain_fitted": round(res["gainfit_gain"], 3),
                     "L_top_srgb": round(res["L_top_srgb"], 1), "L_bot_srgb": round(res["L_bot_srgb"], 1)})
    return rows


if __name__ == "__main__":
    cases = [("v1_z1", 1.0), ("v3_z2", 2.0), ("v2_z35", 3.5), ("v4_z1_probe035", 1.0), ("v5_z35_probe035", 3.5),
             ("v6_z2_roll6", 2.0)]
    out = {}
    for name, k in cases:
        for scale in (1.0, 0.5):
            key = f"{name}@{scale}"
            rows = analyse_render(HERE / "validate" / f"{name}.png", k, scale)
            out[key] = rows
            print("==", key)
            for r in rows:
                print("  f%.2f x%6.1f  true fs %.3f | RATIO %.3f %s roll %.1f | GAIN1 %.3f roll %.1f | g %.2f | q %.4f (true %.4f) | L %.0f/%.0f"
                      % (r["frac_vis"], r["x_mm"], r["analytic_face_slope"], r["RATIO_r"], r["RATIO_band"],
                         r["RATIO_roll"], r["GAIN1_r"], r["GAIN1_roll"], r["gain_fitted"], r["q_meas"],
                         r["q_true_projected"], r["L_top_srgb"], r["L_bot_srgb"]))
    (HERE / "validate" / "validation_results.json").write_text(json.dumps(out, indent=1))
