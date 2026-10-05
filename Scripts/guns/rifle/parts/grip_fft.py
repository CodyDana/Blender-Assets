"""Grip checkering by FFT, round 2 (plain Python): the power spectrum SUMMED over windows of the field (c6: 5 windows of
40 px, c1: 4 of 28 px), the strongest peak per groove family (A: wave angle -90..0, B: -180..-90 in image axes), for
the reference panel and our ROUGH LOOK crop of a grip_loop tag placed back into panel px; directions converted to frame
M through the solved part cameras (deg from vertical, + = down toward the rear) and periods to mm.

    py -3 -B Scripts/guns/rifle/parts/grip_fft.py --tag r2        -> review/detail/grip/<tag>_fft.json

Round 1 took medians of per-window peaks (32 px Hann windows, grip_measure.lattice); summing the power first is steadier
on the drawn field, whose B family carries ~1/20 of A's power.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rifle_common import SHEET, SCRATCH, REVIEW  # noqa: E402

OUT = REVIEW / "detail" / "grip"
BOXES = {"c6": (1153, 629, 1379, 991), "c1": (9, 629, 298, 991)}
WIN = {"c6": ([(145, 200), (140, 175), (155, 225), (150, 210), (135, 185)], 40),
       "c1": ([(60, 250), (55, 270), (50, 285), (62, 240)], 28)}


def analyse(P, cents, n, N=512):
    Fs = 0
    for cx, cy in cents:
        Q = P[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
        Q = Q - Q.mean()
        w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
        Z = np.zeros((N, N))
        Z[:n, :n] = Q * w
        Fs = Fs + np.abs(np.fft.fftshift(np.fft.fft2(Z))) ** 2
    c = N // 2
    yy, xx = (np.mgrid[0:N, 0:N] - c) / N
    r = np.hypot(xx, yy)
    ang = np.degrees(np.arctan2(yy, xx))
    m = (r > 1 / 7) & (r < 1 / 2.2) & (yy < 0)
    out = {}
    for name, band in (("A", (-90, 0)), ("B", (-180, -90))):
        G = np.where(m & (ang > band[0]) & (ang < band[1]), Fs, 0)
        iy, ix = np.unravel_index(int(np.argmax(G)), G.shape)
        out[name] = {"period_px": round(float(1 / r[iy, ix]), 3), "wave_deg": round(float(ang[iy, ix]), 2),
                     "amp": round(float(np.sqrt(G[iy, ix]) / 1e3), 2)}
    out["amp_ratio"] = round(max(out["A"]["amp"], out["B"]["amp"]) / min(out["A"]["amp"], out["B"]["amp"]), 2)
    return out


def to_M(cam, fam):
    R = np.array(cam["R_rows_right_up_fwd_M"])
    a = math.radians(fam["wave_deg"] + 90)
    d = np.array([math.cos(a), math.sin(a)])
    dM = d[0] * R[0] - d[1] * R[1]
    x, z = dM[0], dM[2]
    if z > 0:
        x, z = -x, -z
    return {"deg_from_vertical_down_toward_rear": round(math.degrees(math.atan2(-x, -z)), 1),
            "spacing_mm": round(fam["period_px"] / cam["px_per_mm"], 3)}


def main(tag):
    sheet = np.asarray(Image.open(SHEET).convert("L"), float)
    res = {"tag": tag, "method": __doc__.strip().splitlines()[0]}
    for key, box in BOXES.items():
        P = sheet[box[1]:box[3] + 1, box[0]:box[2] + 1]
        crops = json.loads((OUT / f"{tag}_crops.json").read_text())
        x0, y0, x1, y1 = crops[key]["window_px"]
        o = Image.open(OUT / f"{tag}_ours_{key}.png").convert("L").resize((x1 - x0, y1 - y0), Image.LANCZOS)
        Q = np.full(P.shape, 128.0)
        Q[y0:y1, x0:x1] = np.asarray(o, float)
        cam = json.loads((SCRATCH / "detail" / "cameras" / f"grip__{key}.json").read_text())["camera"]
        cents, n = WIN[key]
        r, q = analyse(P, cents, n), analyse(Q, cents, n)
        d = {"ref": r, "ours": q, "ref_M": {k: to_M(cam, r[k]) for k in "AB"}, "ours_M": {k: to_M(cam, q[k]) for k in "AB"}}
        d["period_ratio"] = {k: round(q[k]["period_px"] / r[k]["period_px"], 3) for k in "AB"}
        d["direction_diff_deg"] = {k: round(q[k]["wave_deg"] - r[k]["wave_deg"], 2) for k in "AB"}
        res[key] = d
    (OUT / f"{tag}_fft.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    main(ap.parse_args().tag)
