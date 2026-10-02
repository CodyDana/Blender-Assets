"""perf2: join a dj_ninja_perf2 run's report (<run>.json) with the CSV profiles its runner recorded (<run>.log.guard.txt,
"csv <path> <bytes>" lines of the LAST run in that guard file; one CSV per sampled segment in order). Per segment:
FrameTime / GameThreadTime / RenderThreadTime / RHIThreadTime / GPUTime mean, median, p95 (the CSV is the engine's own
stat unit data), the render-thread and game-thread exclusive tops, the top GPU passes, light counts, draw calls.
usage: summarize.py <run.json> [more run.json ...]  -> writes <run>_summary.json next to each report."""
import csv
import json
import re
import statistics as S
import sys
from pathlib import Path


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def read_csv(f):
    allr = list(csv.reader(Path(f).open(encoding="utf-8", errors="replace")))
    hdrs = [r for r in allr if r and r[0] == "EVENTS"]
    hdr = max(hdrs, key=len)
    rows = [r + [""] * (len(hdr) - len(r)) for r in allr[1:]
            if r and r[0] != "EVENTS" and not r[0].startswith("[") and len(r) <= len(hdr)]
    rows = rows[3:]
    col = {h: i for i, h in enumerate(hdr)}

    def vals(h):
        if h not in col:
            return []
        out = []
        for r in rows:
            try:
                out.append(float(r[col[h]]))
            except ValueError:
                pass
        return out
    return hdr, vals, len(rows)


def triple(v):
    return {"mean": round(S.mean(v), 2), "median": round(S.median(v), 2), "p95": round(pct(v, 0.95), 2)} if v else None


def summarize_seg(f):
    hdr, vals, n = read_csv(f)
    m = {}
    for h in ("FrameTime", "GameThreadTime", "RenderThreadTime", "RenderThreadTime_CriticalPath", "RHIThreadTime", "GPUTime"):
        m[h] = triple(vals(h))
    rtx = {h.split("/", 2)[2]: round(S.mean(vals(h) or [0.0]), 3) for h in hdr if h.startswith("Exclusive/RenderThread/")}
    rt = m["RenderThreadTime"]
    if rt is None or rt["mean"] < 0.5:   # the column reads ~0 in later captures of a process; use the critical path
        rt = m["RenderThreadTime_CriticalPath"]
    if rt is None or rt["mean"] < 0.5:   # both ~0 in later captures: the exclusive render-thread sum (incl. waits)
        rt = {"mean": round(sum(rtx.values()), 2), "median": None, "p95": None, "from": "exclusive_sum"}
    m["RenderThread"] = rt
    m["RenderThread_busy_mean"] = round(sum(v for k, v in rtx.items() if not k.startswith("EventWait")), 2)
    gtx = {h.split("/", 2)[2]: round(S.mean(vals(h) or [0.0]), 3) for h in hdr if h.startswith("Exclusive/GameThread/")}
    gp = {h[4:]: round(S.mean(vals(h) or [0.0]), 3) for h in hdr if h.startswith("GPU/")}
    extra = {}
    for h in ("LightCount/All", "LightCount/Batched", "LightCount/Unbatched", "LightCount/UpdatedShadowMaps", "RHI/DrawCalls",
              "RHI/PrimitivesDrawn", "DrawCall/Lights", "DrawCall/ShadowDepths", "Ticks/Total",
              "AnimationParallelEvaluation/TotalTaskTime", "Exclusive/AllWorkers/RenderLighting"):
        v = vals(h)
        if v:
            extra[h] = round(S.mean(v), 2)
    return {"csv": Path(f).name, "frames": n, "main_ms": m, "rt_excl_sum": round(sum(rtx.values()), 2),
            "rt_top": sorted(rtx.items(), key=lambda kv: -kv[1])[:8],
            "gt_top": sorted(gtx.items(), key=lambda kv: -kv[1])[:8],
            "gpu_top": sorted(gp.items(), key=lambda kv: -kv[1])[:10], "gpu_sum": round(sum(gp.values()), 2),
            "rt_excl": rtx, "gt_excl": gtx, "gpu": gp, "counts": extra}


def run(rep_path):
    rep_path = Path(rep_path)
    R = json.loads(rep_path.read_text(encoding="utf-8"))
    guard = Path(str(rep_path.with_suffix("")) + ".log.guard.txt")
    g = guard.read_text(encoding="utf-8-sig")
    g = g[g.rfind("started pid="):]
    files = [m.group(1) for m in re.finditer(r" csv (.+?\.csv) \d+", g)]
    segs = [s for s in R["segments"] if s.get("csv", True)]
    if len(files) != len(segs):
        print(f"WARNING {rep_path.name}: {len(files)} csv for {len(segs)} csv segments")
    out = []
    for s, f in zip(segs, files):
        o = {"i": s["i"], "label": s.get("label"), "view": s["view"], "toggles": s.get("toggles"), "cast": s.get("cast"),
             "t_s": s["t_s"], "python": s["frames"], "pawn": R.get("pawn", "").rsplit(".", 1)[-1]}
        o.update(summarize_seg(f))
        out.append(o)
    dst = Path(str(rep_path.with_suffix("")) + "_summary.json")
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        for o in run(a):
            m = o["main_ms"]
            print(f"{o['label']:>14} {o['view'][:20]:>20} t{o['t_s']:6.1f} FT {m['FrameTime']['mean']:6.2f}/{m['FrameTime']['p95']:6.2f}"
                  f" GT {m['GameThreadTime']['mean']:5.2f} RT {m["RenderThread"]["mean"]:5.2f} busy {m["RenderThread_busy_mean"]:5.2f} GPU {m['GPUTime']['mean']:5.2f}"
                  f" | " + " ".join(f"{k}={v}" for k, v in o["rt_top"][:4]))
