"""VERIFY r9: summarise the CSV profiles of the -game perf run (DojoLab/Saved/Profiling/CSV, read only), in segment
order (game_perf.json). Per segment: FrameTime / GameThread / RenderThread / RHI / GPUTime mean, median, p95; top GPU
passes by mean ms. Out: verify_r9/perf_summary.json + perf_summary.md"""
import csv
import json
import statistics as S
from pathlib import Path

VD = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/perf")
CSVD = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Saved\Profiling\CSV")
G = json.loads((VD / "game_perf.json").read_text(encoding="utf-8"))
import re
_g = (VD / "game_perf_guard.txt").read_text(encoding="utf-8-sig")
files = sorted({Path(m.group(1)) for m in re.finditer(r" csv (.+?\.csv) \d+", _g)}, key=lambda p: p.name)
assert len(files) == len(G["segments"]), (len(files), len(G["segments"]))


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


out = []
for seg, f in zip(G["segments"], files):
    rows = []
    with f.open(encoding="utf-8", errors="replace") as fh:
        allr = list(csv.reader(fh))
    hdrs = [r for r in allr if r and r[0] == "EVENTS"]
    hdr = max(hdrs, key=len)   # the header row at the END is the full one (columns are appended mid-capture)
    for r in allr:
        if not r or r[0] == "EVENTS" or r[0].startswith("[") or len(r) > len(hdr):
            continue
        rows.append(r + [""] * (len(hdr) - len(r)))
    rows = rows[3:]   # drop the first frames after csvprofile start
    col = {h: i for i, h in enumerate(hdr)}

    def vals(h):
        return [float(r[col[h]]) for r in rows if r[col[h]] not in ("", None)]

    main = {}
    for h in ("FrameTime", "GameThreadTime", "RenderThreadTime", "RHIThreadTime", "GPUTime"):
        if h in col:
            v = vals(h)
            main[h] = {"mean": round(S.mean(v), 2), "median": round(S.median(v), 2), "p95": round(pct(v, 0.95), 2)}
    gp = {h[4:]: round(S.mean(vals(h)), 3) for h in hdr if h.startswith("GPU/")}
    top = sorted(gp.items(), key=lambda kv: -kv[1])[:10]
    out.append({"segment": seg["i"], "view": seg["view"], "res": seg["res"], "screen_pct": seg["screen_pct"],
                "csv": f.name, "frames": len(rows), "main_ms": main, "gpu_top_ms": top,
                "gpu_sum_passes_ms": round(sum(gp.values()), 2), "python_tick": seg["frames"]})
(VD / "perf_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
L = ["| view | output @ screen % | frames | FrameTime mean / p95 | GPUTime mean / median / p95 | GT mean | RT mean | top GPU passes (mean ms) |",
     "|---|---|---|---|---|---|---|---|"]
for o in out:
    m = o["main_ms"]
    L.append(f"| {o['view']} | {o['res'][0]}x{o['res'][1]} @ {o['screen_pct']} | {o['frames']} | "
             f"{m['FrameTime']['mean']} / {m['FrameTime']['p95']} | {m['GPUTime']['mean']} / {m['GPUTime']['median']} / {m['GPUTime']['p95']} | "
             f"{m['GameThreadTime']['mean']} | {m['RenderThreadTime']['mean']} | "
             + ", ".join(f"{k} {v}" for k, v in o["gpu_top_ms"][:6]) + " |")
(VD / "perf_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
