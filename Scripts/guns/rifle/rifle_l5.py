"""AR-01 gate L5 (colour, GUN_BUILDING_STUDY 7.3 / STONE_BUILDING_STUDY 6.2 SG11 tolerances), plain Python:

    py -3 -B Scripts/guns/rifle/rifle_l5.py --render WorkFiles/guns/rifle/review/tex/tex_side.png [--calibrate]

The render is the side view from the BAKED MAPS in the sheet's own px <-> mm frame (rifle_texrender --set side, 3x), so
each part's pixels line up with the sheet's LEFT-labelled panel (L2 side IoU 0.976). Per part region (the traced
part labels, trace/LEFT_parts_index.png, eroded 3 px so edges and the silhouette difference stay out): median sRGB
of the sheet vs ours -> luma (Rec. 709 on sRGB 0..1), HSV saturation, R/B and hue (hue only where both saturations
are >= 0.15). Tolerances: luma +-0.05, saturation +-0.05, R/B +-0.1, hue +-4 deg.

Matched light: the sheet's light is unknown and its samples are lit values (spec materials.sheet_samples_srgb: "hue and
relative value only"), so ONE global light scale is fitted on the largest steel region (the receiver: its linear
luminance ratio, --calibrate prints it) and every other region is then a relative test under that one light.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "WorkFiles" / "guns" / "rifle"
TRACE = WORK / "trace"
SHEET = ROOT / "References" / "Guns" / "Rifle" / "rifle_sheetAB.webp"
REGIONS = {"receiver": 10, "dust_cover": 9, "magazine": 1, "butt_plate": 6, "stock": 4, "pistol_grip": 5,
           "handguard_lower": 3, "handguard_upper": 2, "gas_block": 13, "barrel": 15}
TOL = {"luma": 0.05, "sat": 0.05, "rb": 0.10, "hue_deg": 4.0}


def erode(m, n):
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        m = e
    return m


def stats(px):
    med = np.median(px, axis=0) / 255.0
    luma = float(0.2126 * med[0] + 0.7152 * med[1] + 0.0722 * med[2])
    h, s, v = colorsys.rgb_to_hsv(*med)
    return {"median_srgb": [round(float(x) * 255, 1) for x in med], "luma": round(luma, 4), "sat": round(s, 4),
            "hue_deg": round(h * 360.0, 2), "rb": round(float(med[0] / max(med[2], 1e-4)), 4)}


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--light", type=float, default=1.0, help="the light scale the render used (recorded)")
    ap.add_argument("--json", default=str(WORK / "scratch" / "game" / "l5.json"))
    ap.add_argument("--calib", default="receiver", help="regions the light fit used (not graded)")
    a = ap.parse_args()
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    x0, y0, x1, y1 = j["panel_box_sheet_px"]
    sheet = np.asarray(Image.open(SHEET).convert("RGB"), float)[y0:y1 + 1, x0:x1 + 1]
    lab = np.asarray(Image.open(TRACE / "LEFT_parts_index.png"))
    ours = np.asarray(Image.open(a.render).convert("RGB"), float)
    H, W = lab.shape
    ss = ours.shape[0] // H
    ours = ours[:H * ss, :W * ss].reshape(H, ss, W, ss, 3).mean((1, 3))
    bg = np.all(np.abs(ours - 126.0) < 2.5, axis=2)
    out = {"render": str(Path(a.render).name), "light_scale": a.light, "tolerances": TOL, "regions": {}}
    for name, idx in REGIONS.items():
        m = erode(lab == idx, 3) & ~bg
        if m.sum() < 30:
            continue
        s_, o_ = stats(sheet[m]), stats(ours[m])
        d = {"luma": round(o_["luma"] - s_["luma"], 4), "sat": round(o_["sat"] - s_["sat"], 4),
             "rb": round(o_["rb"] - s_["rb"], 4)}
        chroma = s_["sat"] >= 0.15 and o_["sat"] >= 0.15
        if chroma:
            d["hue_deg"] = round(((o_["hue_deg"] - s_["hue_deg"]) + 180.0) % 360.0 - 180.0, 2)
        ok = abs(d["luma"]) <= TOL["luma"] and abs(d["sat"]) <= TOL["sat"] and abs(d["rb"]) <= TOL["rb"] and \
            (not chroma or abs(d["hue_deg"]) <= TOL["hue_deg"])
        out["regions"][name] = {"pixels": int(m.sum()), "sheet": s_, "ours": o_, "delta": d, "pass": bool(ok)}
    rec = out["regions"].get("receiver")
    if rec:
        ls = lin(np.array(rec["sheet"]["median_srgb"]) / 255.0) @ np.array([0.2126, 0.7152, 0.0722])
        lo = lin(np.array(rec["ours"]["median_srgb"]) / 255.0) @ np.array([0.2126, 0.7152, 0.0722])
        out["calibration"] = {"region": "receiver", "linear_luminance_ratio_sheet_over_ours": round(float(ls / lo), 4),
                              "suggested_light_scale": round(float(a.light * ls / lo), 4)}
    calib = set(a.calib.split(","))
    out["calibration_regions"] = sorted(calib)
    tested = {k: v for k, v in out["regions"].items() if k not in calib}
    out["pass"] = all(v["pass"] for v in tested.values())
    out["failed"] = [k for k, v in tested.items() if not v["pass"]]
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    if a.calibrate:
        print("L5_LIGHT", out["calibration"]["suggested_light_scale"])
    for k, v in out["regions"].items():
        print("[L5] %-16s sheet %-22s ours %-22s d %s %s" % (k, v["sheet"]["median_srgb"], v["ours"]["median_srgb"],
                                                             v["delta"], "PASS" if v["pass"] else "FAIL"))
    print("[L5]", "PASS" if out["pass"] else "FAIL", out["failed"])


if __name__ == "__main__":
    main()
