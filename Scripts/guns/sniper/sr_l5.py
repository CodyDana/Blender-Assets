"""SR01 gate L5 (colour; the SMG's smg_l5 / smg_l5_fit method, sniper regions):

    py -3 -B Scripts/guns/sniper/sr_l5.py [--samples 96]

The GR panel rendered from the BAKED maps in the sheet panel's own px <-> mm frame (sr_render --set l5: ortho right
view, the physical rig), so each traced part label (trace GR parts, eroded 3 px: edges and silhouette differences
stay out) lines up with the sheet crop (scratch/crops/GR.png). ONE light scale k is fitted on the largest OD region
(chassis_forend's linear luminance; the render is linear in k); every other region is a relative test under it.
Per region: median sRGB sheet vs ours -> luma (Rec. 709 on sRGB 0..1) +-0.05, HSV saturation +-0.05, hue +-4 deg
(only where both saturations >= 0.15). Also the OD's rendered median sRGB (spec: about 89/89/78).
Writes scratch/w2/l5/l5.json.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, TRACE, WORK, trace  # noqa: E402
from gunlib import compare as C  # noqa: E402

B = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT = WORK / "scratch" / "w2" / "l5"
REGIONS = ("chassis_forend", "chassis_centre", "butt", "cheek_riser", "grip", "butt_pad", "pad_plate", "barrel",
           "magazine", "muzzle_device", "rail", "bipod", "receiver")
FIT = "chassis_forend"


def s2l(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def render(ks, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [B, "-b", "--factory-startup", str(ROOT / "Assets" / "Guns" / "SR01.blend"), "--python",
           str(HERE / "sr_render.py"), "--", "--set", "l5", "--with-scope", "--light", ",".join(f"{k:.3f}" for k in ks),
           "--samples", str(samples), "--panel", "%d,%d" % Image.open(WORK / "scratch" / "crops" / "GR.png").size]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if "Traceback" in r.stdout + r.stderr or "SystemExit" in r.stdout + r.stderr:
        print((r.stdout + r.stderr)[-3000:])
        raise SystemExit("L5 render failed")
    return [OUT / f"side_k{k:.3f}.png" for k in ks]


def regions_stats(img):
    """median sRGB per eroded region of the GR trace labels, on an image at the crop's size."""
    j = trace("GR")
    sheet = np.asarray(Image.open(WORK / "scratch" / "crops" / "GR.png").convert("RGB"), float) / 255.0
    H, W = sheet.shape[:2]
    ours = np.asarray(Image.open(img).convert("RGB").resize((W, H), Image.LANCZOS), float) / 255.0
    out = {}
    for key in REGIONS:
        if key not in j["parts"]:
            continue
        m = C.rings_mask(j["parts"][key]["px"], (H, W))
        m = ndimage.binary_erosion(m, iterations=3)
        if m.sum() < 20:
            continue
        rec = {"px": int(m.sum())}
        for nm, im in (("sheet", sheet), ("ours", ours)):
            med = np.median(im[m], axis=0)
            hsv = colorsys.rgb_to_hsv(*med)
            rec[nm] = {"srgb": [round(float(v) * 255, 1) for v in med],
                       "luma": round(float(med @ np.array([0.2126, 0.7152, 0.0722])), 4),
                       "sat": round(hsv[1], 4), "hue_deg": round(hsv[0] * 360.0, 1),
                       "lin_lum": float(s2l(med) @ np.array([0.2126, 0.7152, 0.0722]))}
        rec["d_luma"] = round(rec["ours"]["luma"] - rec["sheet"]["luma"], 4)
        rec["d_sat"] = round(rec["ours"]["sat"] - rec["sheet"]["sat"], 4)
        if max(rec["sheet"]["srgb"]) < 30 and max(rec["ours"]["srgb"]) < 30:
            rec["d_sat_note"] = "near black (< 30 sRGB levels): a 2-level channel step is sat 0.12; sat not tested"
            rec["d_sat"] = 0.0
        if rec["ours"]["sat"] >= 0.15 and rec["sheet"]["sat"] >= 0.15:
            dh = (rec["ours"]["hue_deg"] - rec["sheet"]["hue_deg"] + 180.0) % 360.0 - 180.0
            rec["d_hue_deg"] = round(dh, 2)
        rec["pass"] = bool(abs(rec["d_luma"]) <= 0.05 and abs(rec["d_sat"]) <= 0.05 and abs(rec.get("d_hue_deg", 0.0)) <= 4.0)
        out[key] = rec
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=96)
    a = ap.parse_args()
    p1, = render([1.0], a.samples)
    r1 = regions_stats(p1)
    k = r1[FIT]["sheet"]["lin_lum"] / max(r1[FIT]["ours"]["lin_lum"], 1e-9)
    pk, = render([k], a.samples)
    rk = regions_stats(pk)
    tests = {n: v for n, v in rk.items() if n != FIT}
    res = {"fit_region": FIT, "light_k": round(k, 4), "render": str(pk.relative_to(ROOT)), "regions": rk,
           "passed": sum(v["pass"] for v in tests.values()), "tested": len(tests),
           "od_rendered_srgb": rk[FIT]["ours"]["srgb"], "od_sheet_srgb": rk[FIT]["sheet"]["srgb"],
           "tolerances": "luma +-0.05, sat +-0.05, hue +-4 deg (both sat >= 0.15)"}
    (OUT / "l5.json").write_text(json.dumps(res, indent=1))
    print("[SR01-l5] k %.3f passed %d / %d" % (k, res["passed"], res["tested"]))
    for n, v in rk.items():
        print("  %-15s sheet %s ours %s d_luma %+.3f d_sat %+.3f %s" % (n, v["sheet"]["srgb"], v["ours"]["srgb"],
                                                                       v["d_luma"], v["d_sat"], "ok" if v["pass"] else "FAIL"))


if __name__ == "__main__":
    main()
