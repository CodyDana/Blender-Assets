"""Parse one ak_perf run folder (plain Python, no Unreal): perf/<label>/<mode>/{perf.log, csv/*.csv, probe.json}
-> perf/<label>/<mode>/perf.json, and perf/<label>/summary.json over the modes present.

Per segment (CSV profiler, in the order the probe ran them): mean / p95 frame ms, game, render, RHI and GPU ms, draw
calls, primitives drawn, the top GPU passes (GPU/* columns, r.GPUCsvStatsEnabled=1). From the log: PSO hitches ("Waited
for PSO creation" lines and the LogPSOHitching summary), VSM overflow warnings, the ProfileGPU and 'stat dumpframe'
blocks (saved as text next to perf.json; the top ProfileGPU passes by ms are parsed when the format allows).
Usage: py -3 ak_perf_parse.py <run folder>   (the folder holding game/ and/or pie/)
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

CORE = {"frame_ms": "FrameTime", "game_ms": "GameThreadTime", "render_ms": "RenderThreadTime",
        "rhi_ms": "RHIThreadTime", "gpu_ms": "GPUTime", "draw_calls": "RHI/DrawCalls",
        "primitives": "RHI/PrimitivesDrawn"}


def read_csv(path):
    rows = list(csv.reader(path.read_text(encoding="utf-8", errors="replace").splitlines()))
    if not rows:
        return None, []
    # the profiler repeats the header at the end ([HasHeaderRowAtEnd]); stats that appear mid-capture are only in that
    # last header, so it is the authoritative column list
    heads = [r for r in rows if r and r[0] == "EVENTS"]
    head = heads[-1] if heads else rows[0]
    fi =head.index("FrameTime") if "FrameTime" in head else None
    data = []
    for r in rows[1:]:   # column 0 is EVENTS (text or empty); metadata rows start with '['
        if not r or r[0].startswith("[") or r[0] == "EVENTS" or len(r) < len(head) - 2:
            continue
        try:
            if fi is not None:
                float(r[fi])
        except (ValueError, IndexError):
            continue
        data.append(r)
    return head, data


def col(head, data, name):
    if name not in head:
        return []
    i = head.index(name)
    out = []
    for r in data:
        try:
            out.append(float(r[i]))
        except (ValueError, IndexError):
            pass
    return out


def stats(v):
    if not v:
        return None
    s = sorted(v)
    return {"mean": round(statistics.fmean(s), 2), "p95": round(s[int(0.95 * (len(s) - 1))], 2),
            "max": round(s[-1], 2)}


def parse_csv(path):
    head, data = read_csv(path)
    if not head:
        return {"file": path.name, "error": "empty"}
    res = {"file": path.name, "frames": len(data)}
    for k, n in CORE.items():
        res[k] = stats(col(head, data, n))
    gpu = []
    for n in head:
        if n.startswith("GPU/") and n != "GPU/Total":
            v = col(head, data, n)
            if v:
                gpu.append((n[4:], round(statistics.fmean(v), 3)))
    gpu.sort(key=lambda x: -x[1])
    res["gpu_passes_top"] = gpu[:20]
    other = {}
    for n in head:
        if re.match(r"^(Lumen|LightCount|Shadows|Nanite|RayTracing|Ray Tracing|PSO|DrawCall|Exclusive/RenderThread|Exclusive/GameThread)/", n) \
                or n in ("RenderThreadTime_CriticalPath", "GameThreadTime_CriticalPath", "MaxFrameTime", "CPUUsage_Process"):
            v = col(head, data, n)
            if v and statistics.fmean(v) > 0:
                other[n] = round(statistics.fmean(v), 3)
    res["other_stats"] = dict(sorted(other.items(), key=lambda kv: -kv[1])[:60])
    if res.get("frame_ms"):
        res["fps"] = round(1000.0 / res["frame_ms"]["mean"], 1)
    return res


def block(text, begin, end):
    out = []
    for m in re.finditer(re.escape(begin) + r" (\S+)(.*?)" + re.escape(end) + r" \1", text, re.S):
        out.append((m.group(1), m.group(2)))
    return out


def profilegpu_top(txt, n=30):
    """UE 5.8 ProfileGPU table (LogRHI, box-drawing columns): rows '| exclusive ... X ms | inclusive ... Y ms | <indent>Name |'
    (3 spaces of indent per level). Returns the GRAPHICS pipeline frame total and the direct children of 'Scene' (the
    render passes) by inclusive ms, plus the direct children of each heavy pass (>= 0.5 ms)."""
    rows, on = [], False
    for line in txt.splitlines():
        if "GPU Profile for Frame" in line:
            on = "Graphics pipeline" in line
            continue
        if not on or "┃" not in line:
            continue
        parts = line.split("┃")
        if len(parts) < 5:
            continue
        m = re.search(r"([0-9]+\.[0-9]+) ms", parts[2])
        if not m:
            continue
        raw = parts[3].rstrip()
        draws = re.match(r"\s*(\d+)", parts[2])
        rows.append([float(m.group(1)), len(raw) - len(raw.lstrip(" ")), raw.strip()[:110],
                     int(draws.group(1)) if draws else None])
    if not rows:
        return {}
    frame = next((r for r in rows if r[2].startswith("Frame ")), rows[0])
    si = next((i for i, r in enumerate(rows) if r[2] == "Scene"), None)
    out = {"frame_gpu_ms": frame[0], "frame_draws": frame[3], "passes": []}
    if si is None:
        return out
    ind = rows[si][1]
    kids = []
    for r in rows[si + 1:]:
        if r[1] <= ind:
            break
        if r[1] == ind + 3:
            kids.append({"ms": r[0], "name": r[2], "draws": r[3], "children": []})
        elif r[1] == ind + 6 and kids and kids[-1]["ms"] >= 0.5 and r[0] >= 0.05:
            kids[-1]["children"].append({"ms": r[0], "name": r[2], "draws": r[3]})
    out["scene_ms"] = rows[si][0]
    out["passes"] = sorted(kids, key=lambda k: -k["ms"])[:n]
    for k in out["passes"]:
        k["children"] = sorted(k["children"], key=lambda c: -c["ms"])[:8]
    return out


def statcounters(txt):
    """Counters of interest from the 'stat dumpframe' block (cycle stats carry ms; counters print as plain numbers)."""
    out = {}
    for key in ("Mesh draw calls", "Lights", "Processed primitives", "Frustum Culled primitives", "Occluded primitives",
                "Visible static mesh elements", "Visible dynamic primitives", "Shadow", "Draw calls", "Triangles drawn",
                "InitViews", "Render Lighting", "Shadow Depths", "Lumen"):
        for m in re.finditer(r"LogStats:\s+([0-9.]+)ms \(\s*(\d+)\)\s+-\s+(" + re.escape(key) + r"[^-]*?) - ", txt):
            out.setdefault(m.group(3).strip(), (float(m.group(1)), int(m.group(2))))
    return out


def parse_mode(d):
    log = (d / "perf.log").read_text(encoding="utf-8", errors="replace") if (d / "perf.log").exists() else ""
    probe = json.loads((d / "probe.json").read_text(encoding="utf-8")) if (d / "probe.json").exists() else {}
    res = {"mode": d.name, "probe_passed": probe.get("passed"), "errors": probe.get("errors", [])[:5],
           "notes": probe.get("notes", []), "t_world_s": probe.get("t_world_s")}
    pso_lines = re.findall(r"Waited for PSO creation for ([0-9.]+)ms", log)
    hitch = re.findall(r"LogPSOHitching: Encountered (\d+) PSO creation hitches so far \((\d+) graphics, (\d+) compute\)\. (\d+) of them were precached", log)
    res["pso"] = {"waited_lines": len(pso_lines), "waited_ms_total": round(sum(float(x) for x in pso_lines), 1),
                  "hitch_summaries": [{"total": int(a), "graphics": int(b), "compute": int(c), "precached": int(e)}
                                      for a, b, c, e in hitch]}
    res["vsm_overflow_warnings"] = len(re.findall(r"Non-Nanite Marking Job Queue overflow", log))
    res["gpu_timeouts"] = len(re.findall(r"GPU timeout", log))
    res["log_errors"] = len(re.findall(r"Error:", log))
    # pso hitches after the warm-up (steady state) vs before
    wpos = log.find("AK_PERF_WARM_END")
    res["pso"]["waited_lines_after_warmup"] = len(re.findall(r"Waited for PSO creation", log[wpos:])) if wpos >= 0 else None
    csvs = sorted((d / "csv").glob("*.csv"), key=lambda p: p.stat().st_mtime) if (d / "csv").exists() else []
    segs = probe.get("segments", [])
    res["segments"] = []
    for i, s in enumerate(segs):
        e = dict(s)
        if i < len(csvs):
            e["csv"] = parse_csv(csvs[i])
        res["segments"].append(e)
    if len(csvs) != len(segs):
        res["notes"].append(f"{len(csvs)} CSV files for {len(segs)} segments")
    for view, txt in block(log, "AK_PERF_PROFILE_BEGIN", "AK_PERF_PROFILE_END"):
        (d / f"profile_{view}.txt").write_text(txt, encoding="utf-8")
        res.setdefault("profilegpu", {})[view] = profilegpu_top(txt)
        res.setdefault("stat_dumpframe", {})[view] = statcounters(txt)
    res["resolution"] = sorted(set(re.findall(r"TemporalSuperResolution\(sg\.AntiAliasingQuality=\d\) (\d+x\d+ -> \d+x\d+)", log)))
    res["viewport"] = probe.get("viewport")
    res["inventory"] = probe.get("inventory")
    res["cvars"] = probe.get("cvars_start")
    return res


def main():
    run = Path(sys.argv[1])
    summary = {"run": str(run), "modes": {}}
    for m in ("game", "pie"):
        d = run / m
        if not d.exists():
            continue
        r = parse_mode(d)
        (d / "perf.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        summary["modes"][m] = {
            "pso": r["pso"], "vsm_overflow_warnings": r["vsm_overflow_warnings"],
            "segments": [{"name": s["name"], "py_fps": s.get("py_fps"),
                          **({k: (s["csv"].get(k) or {}).get("mean") for k in CORE} if s.get("csv") else {}),
                          "gpu_top5": (s.get("csv") or {}).get("gpu_passes_top", [])[:5]} for s in r["segments"]]}
    (run / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    for m, s in summary["modes"].items():
        print(f"== {m}  PSO waited lines {s['pso']['waited_lines']} (after warm-up {s['pso']['waited_lines_after_warmup']}), "
              f"VSM overflow {s['vsm_overflow_warnings']}")
        for g in s["segments"]:
            print(f"  {g['name']:<34} fps {g.get('py_fps')}  frame {g.get('frame_ms')}  game {g.get('game_ms')}  "
                  f"render {g.get('render_ms')}  rhi {g.get('rhi_ms')}  gpu {g.get('gpu_ms')}  draws {g.get('draw_calls')}  "
                  f"prims {g.get('primitives')}")
            print(f"      gpu top: {g['gpu_top5']}")


main()
