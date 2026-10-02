"""perf2: the clean-profile table from main/main_<pawn>_<n>_summary.json (3 windows per view per pawn, one per process).
Per view x pawn: FrameTime / GameThread / RenderThread / GPU mean, median, p95 averaged over the 3 windows (min-max of
the p95s), plus the Python frame-delta p95 (the play-test stage's method) for comparison. -> main/MAIN_TABLE.md/.json"""
import json
import statistics as S
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "main"
rows = {}
for pawn in ("ninja", "gasp"):
    for n in (1, 2, 3):
        for o in json.loads((D / f"main_{pawn}_{n}_summary.json").read_text(encoding="utf-8")):
            rows.setdefault((o["view"], pawn), []).append(o)
VIEWS = ["CAM_PlayerEyeSand", "CAM_AK_CW_WestAisle", "CAM_RiverRapids", "PAWN"]
NAMES = {"ninja": "ninja (GM_DojoNinja)", "gasp": "GASP (GM_Dojo)"}
out = []
L = ["| view | pawn | FrameTime mean / median / p95 (p95 min-max) | GameThread mean / median / p95 | RenderThread mean (busy) | GPU mean / median / p95 | python dt p95 | vs 16.7 |",
     "|---|---|---|---|---|---|---|---|"]
for v in VIEWS:
    for pawn in ("ninja", "gasp"):
        w = rows[(v, pawn)]

        def avg(key, k):
            return round(S.mean(o["main_ms"][key][k] for o in w), 2)
        r = {"view": v, "pawn": pawn, "windows": len(w),
             "frame": {k: avg("FrameTime", k) for k in ("mean", "median", "p95")},
             "frame_p95_min_max": [min(o["main_ms"]["FrameTime"]["p95"] for o in w), max(o["main_ms"]["FrameTime"]["p95"] for o in w)],
             "game": {k: avg("GameThreadTime", k) for k in ("mean", "median", "p95")},
             "render_mean": round(S.mean(o["main_ms"]["RenderThread"]["mean"] for o in w), 2),
             "render_busy_mean": round(S.mean(o["main_ms"]["RenderThread_busy_mean"] for o in w), 2),
             "gpu": {k: avg("GPUTime", k) for k in ("mean", "median", "p95")},
             "python_p95": round(S.mean(o["python"]["p95_ms"] for o in w), 2),
             "python_mean": round(S.mean(o["python"]["mean_ms"] for o in w), 2)}
        r["meets_16_7"] = r["frame_p95_min_max"][1] <= 16.7
        out.append(r)
        f, g, gp = r["frame"], r["game"], r["gpu"]
        L.append(f"| {v} | {NAMES[pawn]} | {f['mean']} / {f['median']} / **{f['p95']}** ({r['frame_p95_min_max'][0]}-{r['frame_p95_min_max'][1]}) | "
                 f"{g['mean']} / {g['median']} / {g['p95']} | {r['render_mean']} ({r['render_busy_mean']}) | {gp['mean']} / {gp['median']} / {gp['p95']} | "
                 f"{r['python_p95']} | {'met' if r['meets_16_7'] else 'MISS'} |")
L.append("")
L.append("| view | ninja - GASP: FrameTime mean | p95 | GameThread mean | GPU mean |")
L.append("|---|---|---|---|---|")
for v in VIEWS:
    a = next(r for r in out if r["view"] == v and r["pawn"] == "ninja")
    b = next(r for r in out if r["view"] == v and r["pawn"] == "gasp")
    L.append(f"| {v} | {a['frame']['mean'] - b['frame']['mean']:+.2f} | {a['frame']['p95'] - b['frame']['p95']:+.2f} | "
             f"{a['game']['mean'] - b['game']['mean']:+.2f} | {a['gpu']['mean'] - b['gpu']['mean']:+.2f} |")
(D / "MAIN_TABLE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
(D / "MAIN_TABLE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
