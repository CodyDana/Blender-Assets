"""perf2: lever gains from levers/lever_<n>_summary.json. Each lever window L has its base window B right before it (same
view, same pawn placement); gain = B - L (positive = faster), for FrameTime mean / p95, GameThread, RenderThread busy and
GPU; averaged over the sessions (lever_1 forward order, lever_2 reversed order). Casts: the effect window of each jutsu,
base vs Niagara RT cvars off, against the plain PES base. -> levers/LEVER_TABLE.md/.json"""
import json
import statistics as S
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "levers"
sess = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(D.glob("lever_*_summary.json"))]


def met(o):
    m = o["main_ms"]
    return {"ft": m["FrameTime"]["mean"], "p95": m["FrameTime"]["p95"], "gt": m["GameThreadTime"]["mean"],
            "rt": m["RenderThread_busy_mean"], "gpu": m["GPUTime"]["mean"], "gpu_p95": m["GPUTime"]["p95"],
            "lights": o["counts"].get("LightCount/All"), "unbatched": o["counts"].get("LightCount/Unbatched"),
            "rt_gather": o["rt_excl"].get("RayTracing_FinishGatherInstances", 0.0),
            "render_lighting": o["rt_excl"].get("RenderLighting", 0.0)}


gains = {}
casts = {}
bases_pes = []
for rows in sess:
    by_i = {o["i"]: o for o in rows}
    for o in rows:
        lab = o["label"]
        if lab.startswith("base_"):
            if o["view"] == "CAM_PlayerEyeSand":
                bases_pes.append(met(o))
            continue
        if lab.startswith(("cast_", "pcast_")):
            casts.setdefault(lab, []).append(met(o))
            continue
        b = by_i.get(o["i"] - 1)
        if b is None or not b["label"].startswith("base_"):
            continue
        mb, ml = met(b), met(o)
        gains.setdefault(lab, []).append({k: (round(mb[k] - ml[k], 3) if isinstance(mb[k], (int, float)) and isinstance(ml[k], (int, float)) else None)
                                          for k in mb} | {"base": mb, "lever": ml})


def mean_of(lst, k):
    v = [g[k] for g in lst if g.get(k) is not None]
    return round(S.mean(v), 2) if v else None


out = {"levers": {}, "casts": {}, "pes_base": {k: mean_of(bases_pes, k) for k in ("ft", "p95", "gt", "rt", "gpu")}}
L = ["| lever (view) | n | FrameTime mean gain | p95 gain | GameThread gain | RT busy gain | GPU gain | base FT mean -> lever | lights (all / unbatched) base -> lever |",
     "|---|---|---|---|---|---|---|---|---|"]
for lab, g in gains.items():
    r = {k: mean_of(g, k) for k in ("ft", "p95", "gt", "rt", "gpu")}
    r["n"] = len(g)
    r["base_ft"] = round(S.mean(x["base"]["ft"] for x in g), 2)
    r["lever_ft"] = round(S.mean(x["lever"]["ft"] for x in g), 2)
    r["lights"] = [g[0]["base"]["lights"], g[0]["base"]["unbatched"], g[0]["lever"]["lights"], g[0]["lever"]["unbatched"]]
    r["spread_ft"] = [min(x["ft"] for x in g), max(x["ft"] for x in g)]
    out["levers"][lab] = r
    L.append(f"| {lab} | {r['n']} | {r['ft']:+.2f} ({r['spread_ft'][0]:+.2f}..{r['spread_ft'][1]:+.2f}) | {r['p95']:+.2f} | {r['gt']:+.2f} | {r['rt']:+.2f} | {r['gpu']:+.2f} | "
             f"{r['base_ft']} -> {r['lever_ft']} | {r['lights'][0]} / {r['lights'][1]} -> {r['lights'][2]} / {r['lights'][3]} |")
L += ["", f"PES base (all base windows at PlayerEyeSand, ninja in view): {out['pes_base']}", "",
      "| jutsu window (PES, ninja) | n | FrameTime mean | p95 | GameThread | RT busy | GPU | RayTracing_FinishGatherInstances |",
      "|---|---|---|---|---|---|---|---|"]
for lab, g in sorted(casts.items()):
    r = {k: mean_of(g, k) for k in ("ft", "p95", "gt", "rt", "gpu", "rt_gather")}
    r["n"] = len(g)
    out["casts"][lab] = r
    L.append(f"| {lab} | {r['n']} | {r['ft']} | {r['p95']} | {r['gt']} | {r['rt']} | {r['gpu']} | {r['rt_gather']} |")
(D / "LEVER_TABLE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
(D / "LEVER_TABLE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
