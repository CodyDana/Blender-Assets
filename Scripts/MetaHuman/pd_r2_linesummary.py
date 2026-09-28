"""pd_r2_linesummary.py -- ramus-line numbers for the round-2 report (Blender's Python for numpy; the PNGs must first
be converted with `py Scripts/MetaHuman/pd_r2_linemetric.py convert <png...>`).

Measures the posterior-jaw-ramus line (pd_r2_linemetric.py valley depth, luma units 0-255; skin-texture floor about
7-9) on: the round-2 verify captures (before_ = FaceC, after_ = saved MH_PlayerDefault), the explore captures of the
unmodified conform face (R0) and Epic's Kelvin preset (explore2, same cameras), for the studio / ambient / eval /
bounce / headlight rigs. Splits JawClose into the upper ramus (below the ear, rows 250-400) and the lower ramus
(down to the jaw angle, rows 420-530), and the 3/4 view into rows 740-805 / 810-890.
Writes WorkFiles/MetaHuman/player_default/r2_line_summary.json.
"""
import json
import subprocess
import sys
from pathlib import Path

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
CAP, X1, X2 = OUT / "captures", OUT / "r2_explore_captures", OUT / "r2_explore2_captures"
PY = r"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
LM = str(Path(__file__).resolve().parent / "pd_r2_linemetric.py")

SETS = {
    "FaceC (before)": {"JawClose": {r: CAP / f"before_JawClose{s}.png" for r, s in
                                    (("studio", ""), ("ambient", "_ambient"), ("eval", "_eval"), ("bounce", "_bounce"),
                                     ("headlight", "_headlight"))},
                       "Face_ThreeQuarter": {r: CAP / f"before_Face_ThreeQuarter{s}.png" for r, s in
                                             (("studio", ""), ("ambient", "_ambient"), ("eval", "_eval"),
                                              ("bounce", "_bounce"), ("headlight", "_headlight"))}},
    "PlayerDefault (after)": {"JawClose": {r: CAP / f"after_JawClose{s}.png" for r, s in
                                           (("studio", ""), ("ambient", "_ambient"), ("eval", "_eval"),
                                            ("bounce", "_bounce"), ("headlight", "_headlight"))},
                              "Face_ThreeQuarter": {r: CAP / f"after_Face_ThreeQuarter{s}.png" for r, s in
                                                    (("studio", ""), ("ambient", "_ambient"), ("eval", "_eval"),
                                                     ("bounce", "_bounce"), ("headlight", "_headlight"))}},
    "conform face R0 (explore 1)": {"JawClose": {"studio": X1 / "x_R0_JawClose_studio.png",
                                                 "ambient": X1 / "x_R0_JawClose_ambient.png"},
                                    "Face_ThreeQuarter": {"studio": X1 / "x_R0_Face_ThreeQuarter_studio.png",
                                                          "ambient": X1 / "x_R0_Face_ThreeQuarter_ambient.png"}},
    "Epic Kelvin (explore 2)": {"JawClose": {"studio": X2 / "k_Kelvin_JawClose_studio.png",
                                             "ambient": X2 / "k_Kelvin_JawClose_ambient.png"}},
}


def seg(trace, lo, hi):
    d = [t[2] for t in trace if lo <= t[0] <= hi]
    return round(sum(d) / len(d), 1) if d else None


def main():
    pngs = sorted({str(p) for s in SETS.values() for v in s.values() for p in v.values() if Path(p).exists()})
    subprocess.run([sys.executable, LM, "convert", *pngs], check=True, capture_output=True)
    pairs = [f"{view}={p}" for s in SETS.values() for view, v in s.items() for p in v.values() if Path(p).exists()]
    tmp = OUT / "r2_line_raw.json"
    subprocess.run([PY, LM, "measure", str(tmp), *pairs], check=True, capture_output=True)
    raw = json.loads(tmp.read_text(encoding="utf-8"))
    out = {"units": "valley depth in luma (0-255), mean over rows; skin-texture floor ~7-9 (pd_r2_linemetric ctl)",
           "sets": {}}
    for name, views in SETS.items():
        for view, rigs in views.items():
            for rig, p in rigs.items():
                r = raw.get(Path(p).name)
                if r is None:
                    continue
                row = {"all": r["depth_mean"], "file": str(p)}
                if view == "JawClose":
                    row["upper_ramus"] = seg(r["trace"], 250, 400)
                    row["lower_ramus"] = seg(r["trace"], 420, 530)
                else:
                    row["upper_rows_740_805"] = seg(r["trace"], 740, 805)
                    row["lower_rows_810_890"] = seg(r["trace"], 810, 890)
                out["sets"].setdefault(name, {}).setdefault(view, {})[rig] = row
    (OUT / "r2_line_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for name, views in out["sets"].items():
        for view, rigs in views.items():
            print(name, view, {k: {kk: vv for kk, vv in v.items() if kk != "file"} for k, v in rigs.items()})


if __name__ == "__main__":
    main()
