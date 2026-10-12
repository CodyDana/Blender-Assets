"""SMG01 W4 resume (spec R45): do the painted maps READ in a render, or is the surface clay? (plain Python; renders via
headless Blender, smg_maps_vs_clay_bl.py on the W2 blend scratch/SMG01_w2_final.blend + the shipped textures).

    py -3 -B Scripts/guns/smg/smg_maps_vs_clay.py [--samples 96] [--no-render]

The seven texrender close-ups (g1-g7, 35 cm) are rendered four times: {tex, flat} x {rough, studio}. 'flat' is the same
game material with its maps unplugged and set to the shipped maps' per-set medians (BC sRGB, roughness; metallic 0):
a constant per-set clay of the same mean colour. Per close-up: the mean and P90 of |tex - flat| (sRGB levels, luma)
over the object's pixels. If the maps read, the textured render differs visibly from the clay. Writes
review/diag/maps_vs_clay.json (+ side-by-side crops in scratch/maps_vs_clay/).
Reported, not a realism verdict (W4 resume, gates/review_fixes.json R1): the studio-rig mean of the 7 close-ups
against the first W4 pass's (2.73 levels, min P90 4.9; W3 painted less still, polymer BC std 2.3). 'pass' = the maps
read more than the first pass's did (ratio > 1). A stronger setting (sheen fields 0.45 / 0.25: 3.88, x 1.42) was tried
and rejected by eye: at hero distance under the studio light it read as camouflage clouds on the receiver.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, REVIEW  # noqa: E402

import gunlib  # noqa: E402

TEX = ROOT / "Exports" / "Guns" / "SMG01" / "Textures"
OUT = SCRATCH / "maps_vs_clay"
BLEND = SCRATCH / "SMG01_w2_final.blend"
NAMES = ["g1_receiver_rails", "g2_grip_trigger_sel", "g3_magazine_well", "g4_stock_extended", "g5_stock_folded",
         "g6_front_end", "g7_rear_sight"]
# the first W4 fix pass's maps (before the R45 visible-variation pass), measured with this tool on the same UV layout
# (--tex <those maps> --tag firstpass_, 2026-10-12): mean |tex - flat| per close-up; mean of means rough 2.82 / studio
# 2.73, min P90 4.8 / 4.9
BEFORE = {"rough": {"g1_receiver_rails": 3.43, "g2_grip_trigger_sel": 1.81, "g3_magazine_well": 2.23,
                    "g4_stock_extended": 2.67, "g5_stock_folded": 3.07, "g6_front_end": 3.2, "g7_rear_sight": 3.31},
          "studio": {"g1_receiver_rails": 3.15, "g2_grip_trigger_sel": 1.77, "g3_magazine_well": 3.54,
                     "g4_stock_extended": 2.47, "g5_stock_folded": 3.13, "g6_front_end": 2.55, "g7_rear_sight": 2.5}}


def consts(tex):
    out = {}
    for st in ("Metal", "Furniture", "Mag"):
        bc = np.asarray(Image.open(tex / f"T_SMG01_{st}_BC.png").convert("RGB"))
        orm = np.asarray(Image.open(tex / f"T_SMG01_{st}_ORM.png").convert("RGB")).astype(float) / 255.0
        out[st] = {"bc_srgb": [float(v) for v in np.median(bc.reshape(-1, 3), 0)],
                   "rough": round(float(np.median(orm[..., 1])), 4)}
    return out


def render(var, rig, cp, samples, tex, tag):
    od = OUT / f"{tag}{var}_{rig}"
    log = OUT / f"{tag}{var}_{rig}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(BLEND), "--factory-startup", "--python",
                        str(HERE / "smg_maps_vs_clay_bl.py"), "--", "--variant", var, "--rig", rig, "--consts", str(cp),
                        "--out", str(od), "--samples", str(samples), "--tex", str(tex)], stdout=f,
                       stderr=subprocess.STDOUT, check=False)
    t = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in t or "TEXRENDER_DONE" not in t:
        raise SystemExit(f"render failed: {log}")
    return od / "closeups"


def luma(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)
    return a @ np.array([0.2126, 0.7152, 0.0722])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--tex", default=str(TEX), help="maps folder (default: the shipped maps)")
    ap.add_argument("--tag", default="", help="a trial on other maps: scratch outputs prefixed, result in "
                                                "scratch/maps_vs_clay/<tag>result.json (the review file untouched)")
    a = ap.parse_args()
    tex = Path(a.tex)
    OUT.mkdir(parents=True, exist_ok=True)
    cp = OUT / f"{a.tag}consts.json"
    C = consts(tex)
    cp.write_text(json.dumps(C, indent=1))
    res = {"date": datetime.datetime.now().isoformat(timespec="seconds"), "consts_flat": C, "rigs": {},
           "before_first_W4_pass_mean": BEFORE, "method": __doc__.strip().splitlines()[0]}
    for rig in ("rough", "studio"):
        dirs = {v: (OUT / f"{a.tag}{v}_{rig}" / "closeups") if a.no_render else
                render(v, rig, cp, a.samples, tex, a.tag) for v in ("tex", "flat")}
        rows = {}
        for n in NAMES:
            t, f = luma(dirs["tex"] / f"{n}.png"), luma(dirs["flat"] / f"{n}.png")
            # the backdrop: the median of the frame's border (the corner pixel itself can carry a denoiser edge)
            bt = np.median(np.concatenate([t[0], t[-1], t[:, 0], t[:, -1]]))
            bf = np.median(np.concatenate([f[0], f[-1], f[:, 0], f[:, -1]]))
            bg = (np.abs(t - bt) < 2.0) & (np.abs(f - bf) < 2.0)
            d = np.abs(t - f)[~bg]
            rows[n] = {"mean": round(float(d.mean()), 2), "p90": round(float(np.percentile(d, 90)), 1),
                       "object_px": int((~bg).sum()), "tex_object_luma": round(float(t[~bg].mean()), 1)}
            box = (0, 0, t.shape[1], t.shape[0])
            A = Image.open(dirs["tex"] / f"{n}.png").convert("RGB").crop(box)
            B = Image.open(dirs["flat"] / f"{n}.png").convert("RGB").crop(box)
            S = Image.new("RGB", (A.width, 2 * A.height))
            S.paste(A, (0, 0))
            S.paste(B, (0, A.height))
            S.thumbnail((1200, 1400))
            S.save(OUT / f"{a.tag}pair_{rig}_{n}.png")
        res["rigs"][rig] = {"closeups": rows, "mean_of_means": round(float(np.mean([r["mean"] for r in rows.values()])),
                                                                     2),
                            "min_p90": min(r["p90"] for r in rows.values())}
    st = res["rigs"]["studio"]
    before = float(np.mean(list(BEFORE["studio"].values())))
    res["gate"] = {"rule": "reported: studio rig mean of the 7 close-ups' mean |tex - flat| vs the first W4 pass's "
                           "(%.2f); pass = ratio > 1 (the maps read more than before; the judges decide realism)" % before,
                   "value": {"mean_of_means": st["mean_of_means"], "first_pass": round(before, 2),
                             "ratio": round(st["mean_of_means"] / before, 3), "min_p90": st["min_p90"]},
                   "tried_and_rejected": {"sheen_fields": [0.45, 0.25], "studio_mean_of_means": 3.88, "ratio": 1.42,
                                          "why": "read as camouflage clouds on the receiver at hero distance"}}
    res["pass"] = bool(st["mean_of_means"] > before)
    res["maps"] = str(tex)
    if a.tag:
        (OUT / f"{a.tag}result.json").write_text(json.dumps(res, indent=1))
    else:
        (REVIEW / "diag").mkdir(parents=True, exist_ok=True)
        (REVIEW / "diag" / "maps_vs_clay.json").write_text(json.dumps(res, indent=1))
    print("[maps-vs-clay]", json.dumps({k: v["mean_of_means"] for k, v in res["rigs"].items()}), "pass", res["pass"])


if __name__ == "__main__":
    main()
