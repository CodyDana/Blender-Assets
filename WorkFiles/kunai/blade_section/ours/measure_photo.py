"""Re-derive the photo's blade section with the VALIDATED procedure (section_procedure v3: parametric matcap
forward-fitted to the ring through the pixel footprint + PSF; RATIO estimator, roll from the measured ridge offset).

Geometry: measurer A's line fits (photo_A/measure_raw.json; B's agree within ~0.5 px).  Probe: A's ring ellipses
(photo_A/ring_fit.json), the grip sector (-75..20 deg) excluded.  PSF: 0.3 px (psf_photo.py, erf fits to the straight
front edges; the JPEG is sharpened).  Sensitivity: PSF 0.3/0.6, probe depth cut, residual space, and perspective
(unknown lens: orthographic, 300 / 200 / 135 mm full-frame equivalents, uncropped frame assumed).
"""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP  # noqa: E402
from run_validate import FV, x_of_fvis, analytic, h_blade  # noqa: E402

HERE = Path(__file__).parent
M = json.loads(Path(SP.BS + "/photo_A/measure_raw.json").read_text())
RF = json.loads(Path(SP.BS + "/photo_A/ring_fit.json").read_text())
lum, _ = SP.load_lum(SP.PHOTO_PATH)
blade = SP.blade_from_lines(M)
W, H = 500, 333


def probe(sig_psf=0.3, dcut_extra=0.0, persp_mm=None, log=True):
    fn, box = SP.ring_d_centreline if False else SP.ring_d_ellipses(RF["inner"], RF["outer"], excl_deg=(-75, 20))
    tube = 0.25 * ((RF["outer"]["a"] + RF["outer"]["b"]) - (RF["inner"]["a"] + RF["inner"]["b"]))
    dmax = 1.0 - (0.5 + 2 * sig_psf) / tube - dcut_extra
    pix = SP.probe_pixels(fn, box, dmax)
    persp = None if persp_mm is None else (persp_mm / 36.0 * W, W / 2, H / 2)
    return SP.ParamMatcap(lum, fn, pix, sig_psf=sig_psf, persp=persp, log=log), tube, dmax


def stations(mc):
    rows = []
    for f in FV:
        s = f * M["L_visible_px"]
        q, hw, ur, mid = SP.ridge_offset(lum, blade, s)
        r = SP.run2(lum, blade, mc, [s], lambda _s: q, gain1=False)[0]
        rows.append({"frac": f, "s_px": s, "q": q, "halfwidth_px": hw, "r": r["ratio_r"], "band": r["ratio_band10"],
                     "roll": r["ratio_roll"], "gain": r["gain_fitted"], "L_top_srgb": r["L_top_srgb"],
                     "L_bot_srgb": r["L_bot_srgb"], "curve": r["ratio_curve"]})
    return rows


if __name__ == "__main__":
    runs = {}
    grid = list(itertools.product((0.3, 0.6), (0.0, 0.1), (None, 300.0, 200.0, 135.0), (True, False)))
    for sig, dcx, pm, lg in grid:
        key = f"psf{sig}_dcut{dcx}_persp{pm}_log{int(lg)}"
        mc, tube, dmax = probe(sig, dcx, pm, lg)
        rows = stations(mc)
        runs[key] = {"matcap": mc.describe(), "tube_px": tube, "dmax": dmax, "rows": rows}
        print(key, "rms %.3f" % mc.rms, " ".join("%.2f:%.3f" % (r["frac"], r["r"]) for r in rows), flush=True)
    base = "psf0.3_dcut0.0_perspNone_log1"
    out = {"base": base, "runs": runs}
    # per-station summary over the sensitivity grid
    summ = []
    for i, f in enumerate(FV):
        vals = np.array([runs[k]["rows"][i]["r"] for k in runs])
        b = runs[base]["rows"][i]
        x = x_of_fvis(f)
        summ.append({"frac": f, "x_mm": round(x, 2), "face_slope_base": b["r"],
                     "face_slope_median_grid": float(np.median(vals)),
                     "p10": float(np.percentile(vals, 10)), "p90": float(np.percentile(vals, 90)),
                     "min": float(vals.min()), "max": float(vals.max()), "band10_base": b["band"],
                     "q": b["q"], "roll_deg": b["roll"], "L_top_srgb": b["L_top_srgb"], "L_bot_srgb": b["L_bot_srgb"],
                     "ours_face_slope": analytic(x)["face_slope"], "ours_ridge_ratio": analytic(x)["ridge_ratio"],
                     "ours_half_width_mm": h_blade(x)})
    out["summary"] = summ
    for s_ in summ:
        print(s_)
    (HERE / "photo_v3_results.json").write_text(json.dumps(out, indent=1))
