"""Round 3: re-measure the rake groove spacing on dojo1_reference2's near foreground (and the round-2 Unreal capture)
by mapping image rows to ground Y through each fitted camera, resampling to even Y and taking the spectrum.
System Python (PIL + numpy). Writes WorkFiles/dojo/build/round3/ground_materials/rake_measure.json."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/dojo/build/round3/ground_materials"


def lum(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def spectrum(prof, dy):
    prof = prof - np.polyval(np.polyfit(np.arange(len(prof)), prof, 2), np.arange(len(prof)))
    w = np.hanning(len(prof))
    F = np.abs(np.fft.rfft(prof * w)) ** 2
    fr = np.fft.rfftfreq(len(prof), dy)
    return fr, F


def peaks(fr, F, lo_m, hi_m, n=4):
    sel = (fr > 1.0 / hi_m) & (fr < 1.0 / lo_m)
    idx = np.where(sel)[0]
    order = idx[np.argsort(F[idx])[::-1]]
    out, taken = [], []
    for i in order:
        if any(abs(i - j) < 3 for j in taken):
            continue
        taken.append(i)
        out.append({"period_m": round(1.0 / fr[i], 4), "power_rel": round(float(F[i] / F[idx].max()), 3)})
        if len(out) >= n:
            break
    return out


def ref_rows_to_y(rows):
    # round-1 fit: level camera, f 991 px, horizon row 180, eye 9.7 m, eye at Y -11.6
    f, h, r0, ey = 991.0, 9.7, 180.0, -11.6
    return ey + f * h / (rows - r0)


def ue_rows_to_y(rows, cam, W, H):
    (cx, cy, cz), (lx, ly, lz), hfov = cam["loc"], cam["look_at"], cam["hfov_deg"]
    f = (W / 2) / math.tan(math.radians(hfov / 2))
    pitch = math.atan2(cz - lz, ly - cy)
    th = pitch + np.arctan((rows - H / 2) / f)
    return cy + cz / np.tan(th)


def column_profile(L, rows, x0, x1):
    return L[rows.astype(int), x0:x1].mean(axis=1)


def analyse(L, rows_to_y, row_lo, row_hi, x0, x1, dy=0.004):
    rows = np.arange(row_lo, row_hi)
    ys = rows_to_y(rows.astype(float))
    prof = column_profile(L, rows, x0, x1)
    o = np.argsort(ys)
    yy = np.arange(ys[o][0], ys[o][-1], dy)
    pi = np.interp(yy, ys[o], prof[o])
    fr, F = spectrum(pi, dy)
    px_per_m = (row_hi - row_lo) / (ys.max() - ys.min())
    return {"rows": [row_lo, row_hi], "x": [x0, x1], "y_m": [round(float(ys.min()), 2), round(float(ys.max()), 2)],
            "px_per_m_vertical": round(float(px_per_m), 1), "nyquist_m": round(2.0 / px_per_m, 4),
            "peaks_0p02_0p5m": peaks(fr, F, 0.02, 0.5)}


def along_crest(L, row, x0, x1, px_per_m):
    """Horizontal spectrum along a band of rows (the bead texture along each crest)."""
    prof = L[row - 2:row + 3, x0:x1].mean(axis=0)
    fr, F = spectrum(prof, 1.0 / px_per_m)
    return peaks(fr, F, 0.02, 0.3)


def main():
    res = {}
    L = lum(ROOT / "References/Dojo/dojo1_reference2.png")
    res["ref2"] = {
        "near_left": analyse(L, ref_rows_to_y, 760, 900, 300, 600),
        "near_right": analyse(L, ref_rows_to_y, 760, 900, 860, 1150),
        "mid_left": analyse(L, ref_rows_to_y, 620, 760, 330, 600),
        "mid_right": analyse(L, ref_rows_to_y, 620, 760, 860, 1150),
        "far_left": analyse(L, ref_rows_to_y, 500, 620, 350, 600),
        "along_crest_row860_left_hpx_per_m": 991.0 / (991.0 * 9.7 / (860 - 180)),
        "along_crest_row860_left": along_crest(L, 860, 250, 620, 991.0 / (991.0 * 9.7 / (860 - 180))),
        "along_crest_row860_right": along_crest(L, 860, 830, 1180, 991.0 / (991.0 * 9.7 / (860 - 180))),
    }
    lay = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text())
    cam = next(c for c in lay["cameras"] if c["name"] == "CAM_EstablishingRef2")
    p = ROOT / "WorkFiles/dojo/build/unreal/showcase/captures/CAM_EstablishingRef2.png"
    L2 = lum(p)
    H, W = L2.shape
    r2y = lambda r: ue_rows_to_y(r, cam, W, H)
    res["ue_r2_CAM_EstablishingRef2"] = {
        "near_left": analyse(L2, r2y, 880, 1080, 60, 420),
        "mid_left": analyse(L2, r2y, 700, 880, 60, 480),
        "near_right": analyse(L2, r2y, 880, 1080, 1030, 1390),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rake_measure.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if "--ours" not in __import__("sys").argv:
    main()


def ours_check():
    """r3: the same analysis on our Blender render of the UE framing (studio rig): the built spacing, as seen."""
    lay = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text())
    cam = next(c for c in lay["cameras"] if c["name"] == "CAM_EstablishingRef2")
    L3 = lum(OUT / "renders/studio/CAM_EstablishingRef2.png")
    H, W = L3.shape
    s = W / 1448.0
    r2y = lambda r: ue_rows_to_y(r, cam, W, H)
    res = {"near_left": analyse(L3, r2y, int(880 * s), H, int(60 * s), int(420 * s), dy=0.002),
           "mid_left": analyse(L3, r2y, int(700 * s), int(880 * s), int(60 * s), int(480 * s), dy=0.002)}
    p = OUT / "rake_measure.json"
    d = json.loads(p.read_text())
    d["ours_r3_studio_CAM_EstablishingRef2"] = res
    p.write_text(json.dumps(d, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__" and "--ours" in __import__("sys").argv:
    ours_check()
