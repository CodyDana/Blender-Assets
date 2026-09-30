"""Round 3: rake spacing and moire on the DojoLab captures (plain Python, read-only).

Spacing: the ground track's method (Scripts/dojo/ground/r3/measure_rake_r3.py, functions copied so importing it does not
rewrite its JSON): image rows of CAM_EstablishingRef2 mapped to ground Y through the camera, resampled to even Y, the
spectrum's peaks. Moire: in the far sand band of CAM_EstablishingRef2 / CAM_PlayerEyeSand / CU_SandEye, the row-mean
luminance's periodic component at 6-80 px (the beat a regular fine pattern throws when the pixels undersample it),
as the rms of the band-passed profile / mean (r2 capture vs r3), plus the strongest such period in px.
Run: py -3 WorkFiles/dojo/build/unreal/round3/rake_r3_ue.py <capture_dir>
Out: <capture_dir>/rake_moire.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
CAP = Path(sys.argv[1])
R2 = ROOT / "WorkFiles/dojo/build/unreal/round3/start_backup/r2_captures"
LAY = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
CAMS = {c["name"]: c for c in LAY["cameras"]}


def lum(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def spectrum(prof, dy):
    prof = prof - np.polyval(np.polyfit(np.arange(len(prof)), prof, 2), np.arange(len(prof)))
    F = np.abs(np.fft.rfft(prof * np.hanning(len(prof)))) ** 2
    return np.fft.rfftfreq(len(prof), dy), F


def peaks(fr, F, lo_m, hi_m, n=4):
    idx = np.where((fr > 1.0 / hi_m) & (fr < 1.0 / lo_m))[0]
    out, taken = [], []
    for i in idx[np.argsort(F[idx])[::-1]]:
        if any(abs(i - j) < 3 for j in taken):
            continue
        taken.append(i)
        out.append({"period_m": round(1.0 / fr[i], 4), "power_rel": round(float(F[i] / F[idx].max()), 3)})
        if len(out) >= n:
            break
    return out


def rows_to_y(rows, cam, W, H):
    (cx, cy, cz), (lx, ly, lz), hfov = cam["loc"], cam["look_at"], cam["hfov_deg"]
    f = (W / 2) / math.tan(math.radians(hfov / 2))
    th = math.atan2(cz - lz, ly - cy) + np.arctan((rows - H / 2) / f)
    return cy + cz / np.tan(th)


def spacing(L, cam, r0, r1, x0, x1, dy=0.002):
    H, W = L.shape
    rows = np.arange(r0, r1)
    ys = rows_to_y(rows.astype(float), cam, W, H)
    prof = L[rows, x0:x1].mean(axis=1)
    o = np.argsort(ys)
    yy = np.arange(ys[o][0], ys[o][-1], dy)
    fr, F = spectrum(np.interp(yy, ys[o], prof[o]), dy)
    return {"rows": [r0, r1], "y_m": [round(float(ys.min()), 2), round(float(ys.max()), 2)],
            "px_per_m": round(float((r1 - r0) / (ys.max() - ys.min())), 1), "peaks": peaks(fr, F, 0.02, 0.5)}


def moire(L, r0, r1, x0, x1):
    prof = L[r0:r1, x0:x1].mean(axis=1)
    fr, F = spectrum(prof, 1.0)
    band = (fr > 1 / 80.0) & (fr < 1 / 6.0)
    detr = prof - np.polyval(np.polyfit(np.arange(len(prof)), prof, 2), np.arange(len(prof)))
    spec = np.fft.rfft(detr)
    spec[~band] = 0
    bp = np.fft.irfft(spec, len(prof))
    i = np.where(band)[0][np.argmax(F[band])]
    return {"rows": [r0, r1], "x": [x0, x1], "rms_rel": round(float(bp.std() / prof.mean()), 4),
            "strongest_period_px": round(float(1.0 / fr[i]), 1)}


# far-sand bands (rows, x) per camera: sand only, clear of the path and the building bases
MOIRE = {"CAM_EstablishingRef2": [(620, 700, 20, 270)],
         "CAM_PlayerEyeSand": [(760, 900, 60, 900)],
         "CU_SandEye": [(300, 540, 40, 800)]}


def main():
    res = {"spacing": {}, "moire": {}}
    L = lum(CAP / "CAM_EstablishingRef2.png")
    cam = CAMS["CAM_EstablishingRef2"]
    res["spacing"]["r3"] = {"near_left": spacing(L, cam, 880, 1080, 60, 420), "mid_left": spacing(L, cam, 700, 880, 60, 480)}
    L2 = lum(R2 / "CAM_EstablishingRef2.png")
    res["spacing"]["r2"] = {"near_left": spacing(L2, cam, 880, 1080, 60, 420), "mid_left": spacing(L2, cam, 700, 880, 60, 480)}
    for c, bands in MOIRE.items():
        for tag, folder in (("r3", CAP), ("r2", R2)):
            p = folder / f"{c}.png"
            if p.exists():
                Lc = lum(p)
                res["moire"].setdefault(c, {})[tag] = [moire(Lc, *b) for b in bands]
    (CAP / "rake_moire.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


main()
