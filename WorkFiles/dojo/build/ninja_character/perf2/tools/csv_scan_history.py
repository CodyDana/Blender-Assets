"""perf2: read-only scan of DojoLab's existing CSV profiles of 2026-10-01 (the finish stage) to locate the +2.9 ms
render-thread step: per CSV, FrameTime / RenderThreadTime / GPUTime mean and the exclusive render-thread stats."""
import csv, json, statistics as S, sys
from pathlib import Path
CSVD = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Saved\Profiling\CSV")
OUT = Path(sys.argv[1])
pat = sys.argv[2] if len(sys.argv) > 2 else "Profile(20261001_1*"
res = []
for f in sorted(CSVD.glob(pat)):
    allr = list(csv.reader(f.open(encoding="utf-8", errors="replace")))
    hdrs = [r for r in allr if r and r[0] == "EVENTS"]
    hdr = max(hdrs, key=len) if hdrs else allr[0]
    rows = [r + [""] * (len(hdr) - len(r)) for r in allr[1:] if r and r[0] != "EVENTS" and not r[0].startswith("[") and len(r) <= len(hdr)][3:]
    col = {h: i for i, h in enumerate(hdr)}
    def m(h):
        v = [float(r[col[h]]) for r in rows if h in col and r[col[h]] not in ("",)]
        return round(S.mean(v), 3) if v else None
    o = {"csv": f.name, "frames": len(rows), "FrameTime": m("FrameTime"), "RT": m("RenderThreadTime"), "GT": m("GameThreadTime"), "GPU": m("GPUTime")}
    o["rt_excl"] = {h.split("/", 2)[2]: m(h) for h in hdr if h.startswith("Exclusive/RenderThread/")}
    res.append(o)
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
for o in res:
    top = sorted(((k, v) for k, v in o["rt_excl"].items() if v), key=lambda kv: -kv[1])[:6]
    print(o["csv"][8:23], o["frames"], o["FrameTime"], o["RT"], o["GT"], o["GPU"], " ".join(f"{k}={v}" for k, v in top))
