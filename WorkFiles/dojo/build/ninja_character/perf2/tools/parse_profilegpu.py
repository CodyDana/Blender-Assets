"""perf2: parse the ProfileGPU dump (Graphics pipeline table) from a -game log into a tree list: depth, name,
exclusive ms, inclusive ms, draws; writes <out>.json and prints the top inclusive passes (depth <= 3) and top exclusive.
Also extracts the view resolution lines (e.g. "Scene 1920x1080", TSR input -> output) for the screen-percentage check.
usage: parse_profilegpu.py <log> <out.json>"""
import json
import re
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
start = next(i for i, l in enumerate(lines) if "GPU Profile for Frame" in l and "Graphics pipeline" in l)
rows = []
for l in lines[start:]:
    if "LogRHI" not in l:
        if rows:
            break
        continue
    body = l.split("Display:", 1)[-1]
    cells = body.split("┃")
    if len(cells) < 4:
        continue
    ex, inc, name = cells[1], cells[2], cells[3]
    m1, m2 = re.search(r"([\d.]+) ms", ex), re.search(r"([\d.]+) ms", inc)
    if not (m1 and m2):
        continue
    raw = name.rstrip()
    stripped = raw.lstrip(" │├└─")
    depth = (len(raw) - len(stripped)) // 3
    d = inc.split("│")
    rows.append({"depth": depth, "name": stripped.strip(), "excl_ms": float(m1.group(1)), "incl_ms": float(m2.group(1)),
                 "draws": int(d[0]) if d[0].strip().isdigit() else None})
res = [l.split("Display:", 1)[-1].strip() for l in lines[start:start + 4000] if re.search(r"\d{3,4}x\d{3,4}", l)][:20]
out = {"rows": rows, "resolution_lines": res}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("root", rows[0])
for r in sorted([r for r in rows if r["depth"] in (3, 4)], key=lambda r: -r["incl_ms"])[:40]:
    print(f"{r['depth']} {r['incl_ms']:7.3f} {r['excl_ms']:7.3f} {r['name'][:110]}")
print("--- top exclusive")
for r in sorted(rows, key=lambda r: -r["excl_ms"])[:15]:
    print(f"{r['excl_ms']:7.3f} {r['name'][:110]}")
print("--- res"); print("\n".join(res[:10]))
