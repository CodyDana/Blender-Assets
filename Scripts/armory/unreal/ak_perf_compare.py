"""Compare two ak_perf runs (plain Python + Pillow): perf/<before>/ vs perf/<after>/.

Per mode and per view segment present in both: frame / game / render / RHI / GPU ms, draw calls, shadow-depth draws,
fps. Per camera shot (the HighResShot each run takes of every non-spawn view in AK_PERF_VIEWS, in probe order): whole-
frame mean luminance (Rec. 709 on the sRGB values, as ak_image_stats) before / after, the change in %, and the mean
absolute per-pixel difference. Writes perf/<after>/compare_vs_<before>.json and prints a table.
Usage: py -3 ak_perf_compare.py <before label> <after label>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PERF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\perf")
KEYS = ("frame_ms", "game_ms", "render_ms", "rhi_ms", "gpu_ms", "draw_calls")


def seg_table(run, mode):
    p = PERF / run / mode / "perf.json"
    if not p.exists():
        return {}
    r = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for s in r["segments"]:
        c = s.get("csv") or {}
        e = {k: (c.get(k) or {}).get("mean") for k in KEYS}
        e["fps"] = s.get("py_fps")
        e["shadowdepth_draws"] = (c.get("other_stats") or {}).get("DrawCall/ShadowDepths")
        e["gpu_lights_ms"] = dict(c.get("gpu_passes_top") or []).get("Lights")
        out[s["name"]] = e
    return out


def shots(run, mode):
    d = PERF / run / mode
    p = d / "probe.json"
    if not p.exists():
        return {}
    views = [s["view"] for s in json.loads(p.read_text(encoding="utf-8")).get("shots", [])]
    files = sorted((d / "shots").glob("HighresScreenshot*.png"), key=lambda f: f.stat().st_mtime)
    return dict(zip(views, files))


def lum(f):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def main():
    b, a = sys.argv[1], sys.argv[2]
    res = {"before": b, "after": a, "modes": {}}
    for mode in ("game", "pie"):
        sb, sa = seg_table(b, mode), seg_table(a, mode)
        if not sb or not sa:
            continue
        m = {"segments": {}, "shots": {}}
        for name in sb:
            if name in sa:
                m["segments"][name] = {"before": sb[name], "after": sa[name]}
        hb, ha = shots(b, mode), shots(a, mode)
        for v in hb:
            if v in ha:
                lb, la = lum(hb[v]), lum(ha[v])
                if lb.shape != la.shape:
                    m["shots"][v] = {"error": f"size {lb.shape} vs {la.shape}"}
                    continue
                m["shots"][v] = {"mean_before": round(float(lb.mean()), 4), "mean_after": round(float(la.mean()), 4),
                                 "change_pct": round(100.0 * (float(la.mean()) / max(float(lb.mean()), 1e-6) - 1.0), 2),
                                 "abs_diff_mean": round(float(np.abs(la - lb).mean()), 4),
                                 "pixels_diff_gt_0.05_pct": round(100.0 * float((np.abs(la - lb) > 0.05).mean()), 3),
                                 "files": [str(hb[v]), str(ha[v])]}
        res["modes"][mode] = m
        print(f"== {mode}")
        for name, e in m["segments"].items():
            x, y = e["before"], e["after"]
            print(f"  {name:<24} " + "  ".join(f"{k} {x.get(k)} -> {y.get(k)}" for k in
                                                ("fps", "frame_ms", "render_ms", "gpu_ms", "draw_calls", "shadowdepth_draws")))
        for v, e in m["shots"].items():
            print(f"  shot {v}: {e}")
    (PERF / a / f"compare_vs_{b}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


main()
