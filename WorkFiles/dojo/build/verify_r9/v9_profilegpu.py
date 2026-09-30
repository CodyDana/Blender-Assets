"""VERIFY r8: parse the 12 ProfileGPU dumps in game_perf.log (graphics pipeline). Per segment: the root inclusive ms and
the top events by inclusive ms at depth 2-3 under the frame (scene passes), plus every event whose name has Lumen /
Cloud / Fog / Shadow / TSR / Sky. Note: the ProfileGPU frame itself runs slower than a normal frame (profiling overhead).
Out: verify_r9/profilegpu.json"""
import json
import re
from pathlib import Path

VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r9")
txt = (VD / "game_perf.log").read_text(encoding="utf-8", errors="replace").splitlines()
segs, cur = [], None
for l in txt:
    m = re.search(r"PROFILEGPU_BEGIN (\d+) (\S+) (\S+)", l)
    if m:
        cur = {"i": int(m.group(1)), "view": m.group(2), "cfg": m.group(3), "lines": []}
        continue
    if cur is not None and re.search(r"PROFILEGPU_END \d+", l):
        segs.append(cur)
        cur = None
        continue
    if cur is not None:
        cur["lines"].append(l)
out = []
for s in segs:
    g = next((k for k, l in enumerate(s["lines"]) if "Graphics pipeline" in l), None)
    ft = None
    ev = []
    if g is not None:
        for l in s["lines"][g:]:
            mft = re.search(r"Frame Time\s*:\s*([0-9.]+)ms", l)
            if mft:
                ft = float(mft.group(1))
            cols = l.split("┃")
            if len(cols) < 5:
                continue
            incl = re.findall(r"([0-9]+\.[0-9]+) ms", cols[2])
            if not incl:
                continue
            raw = cols[3]
            name = raw.strip()
            depth = (len(raw) - len(raw.lstrip(" ")) - 1) // 3
            ev.append((depth, name, float(incl[0])))
    root = next((e[2] for e in ev if e[1] == "<root>"), None)
    scene = sorted([e for e in ev if e[0] in (2, 3)], key=lambda e: -e[2])[:15]
    keys = [e for e in ev if re.search(r"Lumen|Cloud|Fog|Shadow|TSR|TemporalSuper|SkyAtmos|SkyLight|Nanite|BasePass|Lights", e[1])
            and e[2] >= 0.2 and e[0] <= 5]
    out.append({"i": s["i"], "view": s["view"], "cfg": s["cfg"], "profile_frame_ms": ft, "root_incl_ms": root,
                "top_depth2_3": [[d, n[:80], ms] for d, n, ms in scene],
                "key_events": [[d, n[:80], ms] for d, n, ms in keys][:40]})
(VD / "profilegpu.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
for o in out:
    print(o["i"], o["view"], o["cfg"], "frame", o["profile_frame_ms"], "root", o["root_incl_ms"])
    for d, n, ms in o["top_depth2_3"][:10]:
        print(f"    d{d} {ms:6.3f} {n}")
