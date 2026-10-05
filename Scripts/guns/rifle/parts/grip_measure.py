"""Grip close-up measurements (plain Python): the checker panel traced on c6 / c1 and the cell lattice by FFT.

    py -3 -B Scripts/guns/rifle/parts/grip_measure.py        -> review/detail/grip/measure_r1.json (+ overlays)

Panel: corners read on 5x gridded zooms of the sheet panels (gunlib.closeup.grid_zoom; +-1.5 px), back-projected
through the solved part cameras (scratch/detail/cameras/grip__<panel>.json) onto the form grip's triangles; the
numbers in grip_checker.PANEL_TS are the c1 / c6 average in the grip axis frame.
Cells: zero-padded FFT (32 px Hann window -> 512) of the luminance at windows inside the field; the peak in each
family's angular band gives the groove period (px) and direction; px -> mm with the part camera's scale and the
camera rows (c6 / c1 look at the grip side nearly square on).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rifle_common import SHEET, SCRATCH, REVIEW  # noqa: E402
from gunlib import closeup as CU  # noqa: E402
from gunlib import compare as C  # noqa: E402

OUT = REVIEW / "detail" / "grip"
BOXES = {"c6": (1153, 629, 1379, 991), "c1": (9, 629, 298, 991)}
# corner picks, panel px (u, v); order front-top, rear-top, rear-bottom, front-bottom
CORNERS = {"c6": [(110.0, 127.0), (152.0, 140.0), (180.0, 260.0), (142.0, 270.0)],
           "c1": [(85.0, 211.0), (47.0, 220.0), (20.0, 313.0), (54.0, 322.0)]}
SIDE = {"c6": +1, "c1": -1}
# FFT windows inside the field (panel px centres) and the angular bands (wave-vector deg, image axes) per family
FFT = {"c6": {"centres": [(145, 200), (140, 170), (155, 230), (130, 180), (150, 215)],
              "bands": {"A": (-80, -5), "B": (-175, -95)}, "n": 32},
       "c1": {"centres": [(60, 250), (55, 270), (48, 290), (62, 235)],
              "bands": {"A": (-175, -95), "B": (-85, -5)}, "n": 24}}


def spectrum(L, cx, cy, n=32, N=512):
    P = L[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
    P = P - P.mean()
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    Z = np.zeros((N, N))
    Z[:n, :n] = P * w
    F = np.abs(np.fft.fftshift(np.fft.fft2(Z)))
    c = N // 2
    yy, xx = (np.mgrid[0:N, 0:N] - c) / N
    return F, xx, yy


def peak(F, xx, yy, band, pmin=2.2, pmax=6.0):
    r = np.hypot(xx, yy)
    ang = np.degrees(np.arctan2(yy, xx))
    m = (r > 1 / pmax) & (r < 1 / pmin) & (ang > band[0]) & (ang < band[1])
    i = int(np.argmax(np.where(m, F, 0)))
    return {"amp": float(F.flat[i]), "period_px": float(1 / r.flat[i]), "wave_deg": float(ang.flat[i])}


def lattice(panel_rgb, centres, bands, n):
    L = np.asarray(panel_rgb, float).mean(2)
    res = {k: [] for k in bands}
    for (cx, cy) in centres:
        F, xx, yy = spectrum(L, cx, cy, n)
        for k, b in bands.items():
            res[k].append(peak(F, xx, yy, b))
    summ = {}
    for k, v in res.items():
        summ[k] = {"period_px_median": round(float(np.median([q["period_px"] for q in v])), 3),
                   "wave_deg_median": round(float(np.median([q["wave_deg"] for q in v])), 2),
                   "amp_median": round(float(np.median([q["amp"] for q in v])), 1),
                   "samples": [{kk: round(vv, 3) for kk, vv in q.items()} for q in v]}
    return summ


def lattice_compare(ref_panel, our_panel, fw):
    r = lattice(ref_panel, fw["centres"], fw["bands"], fw["n"])
    o = lattice(our_panel, fw["centres"], fw["bands"], fw["n"])
    out = {"ref": {k: {kk: v[kk] for kk in ("period_px_median", "wave_deg_median", "amp_median")} for k, v in r.items()},
           "ours": {k: {kk: v[kk] for kk in ("period_px_median", "wave_deg_median", "amp_median")} for k, v in o.items()}}
    out["period_ratio"] = {k: round(o[k]["period_px_median"] / r[k]["period_px_median"], 3) for k in r}
    out["direction_diff_deg"] = {k: round(o[k]["wave_deg_median"] - r[k]["wave_deg_median"], 2) for k in r}
    return out


def ref_poly(key):
    return np.array(CORNERS[key], float)


def poly_mask(P, shape, ss=4):
    return C.poly_cov([np.asarray(P, float)], shape, ss) > 0.5


def panel_iou(cam, shape, refp):
    from parts import grip_checker as GC
    o = GC.panel_outline_xz(seg=6)
    P3 = np.c_[o[:, 0], np.full(len(o), refp["side"] * 15.4), o[:, 1]]
    ours = cam.project(P3)
    a = poly_mask(ours, shape)
    b = poly_mask(refp["poly_px"], shape)
    return {"iou": round(C.iou(a, b), 4), "ref_px": int(b.sum()), "ours_px": int(a.sum())}


def reference():
    return {"panels": {k: {"poly_px": CORNERS[k], "side": SIDE[k], "fft_windows": FFT[k]} for k in CORNERS}}


def _ray_hit(cam, V, T, u, v):
    o = cam.c0 + ((u - cam.u0) / cam.s) * cam.R[0] + (-(v - cam.v0) / cam.s) * cam.R[1] - 500 * cam.R[2]
    d = cam.R[2]
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    e1, e2 = b - a, c - a
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - a
    uu = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    vv = (q @ d) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    m = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t > 0)
    if not m.any():
        return None
    k = int(np.argmin(np.where(m, t, 1e9)))
    return o + t[k] * d


def main():
    from parts import grip_checker as GC
    D = np.load(SCRATCH / "form_tris.npz")
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    TT = T[lab == names.index("pistol_grip")]
    rgb = CU.load_rgb(SHEET)
    out = {"date": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"), "method": __doc__.strip().splitlines()[0],
           "panels": {}}
    labels = ["front_top", "rear_top", "rear_bottom", "front_bottom"]
    for key in CORNERS:
        cam = CU.cam_from_json(json.loads((SCRATCH / "detail" / "cameras" / f"grip__{key}.json").read_text())["camera"])
        P = CU.crop(rgb, BOXES[key])
        hits = {}
        for lb, (u, v) in zip(labels, CORNERS[key]):
            h = _ray_hit(cam, V, TT, u, v)
            hits[lb] = None if h is None else {"M": [round(float(x), 2) for x in h],
                                               "ts": [round(float(x), 2) for x in GC.xz_to_ts(h[[0, 2]][None])[0]]}
        lat = lattice(P, FFT[key]["centres"], FFT[key]["bands"], FFT[key]["n"])
        # groove directions in frame M (side plane): line direction = wave + 90 deg, image (u right, v down)
        dirs = {}
        for fam, s in lat.items():
            a = math.radians(s["wave_deg_median"] + 90.0)
            dimg = np.array([math.cos(a), math.sin(a)])
            dM = dimg[0] * cam.R[0] - dimg[1] * cam.R[1]
            x, z = dM[0], dM[2]
            if z > 0:
                x, z = -x, -z
            dirs[fam] = {"deg_from_vertical_down_toward_rear": round(math.degrees(math.atan2(-x, -z)), 1),
                         "spacing_mm": round(s["period_px_median"] / cam.s, 3)}
        out["panels"][key] = {"corners_px": dict(zip(labels, CORNERS[key])), "corners_on_grip": hits,
                              "px_per_mm": round(cam.s, 4), "lattice_px": lat, "grooves_M": dirs}
        # overlay
        z = 4
        im = Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).resize((P.shape[1] * z, P.shape[0] * z), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        q = [((u + 0.5) * z, (v + 0.5) * z) for u, v in CORNERS[key]]
        d.line(q + [q[0]], fill=(0, 255, 255), width=2)
        o = GC.panel_outline_xz(seg=6)
        P3 = np.c_[o[:, 0], np.full(len(o), SIDE[key] * 15.4), o[:, 1]]
        pp = [((u + 0.5) * z, (v + 0.5) * z) for u, v in cam.project(P3)]
        d.line(pp + [pp[0]], fill=(255, 120, 0), width=2)
        for (cx, cy) in FFT[key]["centres"]:
            n = FFT[key]["n"] // 2
            d.rectangle([(cx - n) * z, (cy - n) * z, (cx + n) * z, (cy + n) * z], outline=(255, 255, 0))
        im.save(OUT / f"measure_{key}.png")
    out["adopted"] = {"PANEL_TS": GC.PANEL_TS, "PANEL_R": GC.PANEL_R, "FAM_A_DEG": GC.FAM_A_DEG,
                      "FAM_B_DEG": GC.FAM_B_DEG, "PITCH_A": GC.PITCH_A, "PITCH_B": GC.PITCH_B}
    (OUT / "measure_r1.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {"corners": v["corners_on_grip"], "grooves": v["grooves_M"]} for k, v in out["panels"].items()},
                     indent=1))


if __name__ == "__main__":
    main()
