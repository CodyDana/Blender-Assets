"""Warning / error TYPES in UE logs: category + message with numbers, paths-in-quotes and hex collapsed.
usage: py -3 -B v_logtypes.py out.json baseline.log [baseline2.log ...] -- new.log [new2.log ...]"""
import json
import re
import sys
from collections import Counter

RX = re.compile(r"^\[[^\]]*\]\[\s*\d+\](Log\w+): (Warning|Error): (.*)$|^(Log\w+): (Warning|Error): (.*)$")


def norm(m):
    m = re.sub(r"0x[0-9A-Fa-f]+", "#", m)
    m = re.sub(r"\d+(\.\d+)?", "#", m)
    m = re.sub(r"'[^']*'", "'*'", m)
    m = re.sub(r'"[^"]*"', '"*"', m)
    m = re.sub(r"[A-Za-z]:[\\/][^ ]*", "<path>", m)
    m = re.sub(r"/(Game|Script|Engine)/[^ ]*", "<obj>", m)
    return m[:140]


def types(path):
    c = Counter()
    for line in open(path, encoding="utf-8", errors="replace"):
        x = RX.match(line.rstrip())
        if not x:
            continue
        g = [y for y in x.groups() if y is not None]
        cat, lvl, msg = g[0], g[1], g[2]
        if cat == "LogPython" or "VPROBE" in msg:
            continue
        c[f"{lvl} {cat}: {norm(msg)}"] += 1
    return c


out = sys.argv[1]
i = sys.argv.index("--")
base, new = sys.argv[2:i], sys.argv[i + 1:]
B, N = Counter(), Counter()
for p in base:
    B.update(types(p))
for p in new:
    N.update(types(p))
newtypes = {k: v for k, v in N.items() if k not in B}
rep = {"baseline": base, "new": new, "baseline_types": len(B), "new_log_types": len(N),
       "errors_new_logs": sum(v for k, v in N.items() if k.startswith("Error")),
       "types_only_in_new": dict(sorted(newtypes.items())), "types_gone": sorted(k for k in B if k not in N)[:80]}
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("baseline_types", "new_log_types", "errors_new_logs")}))
for k, v in sorted(newtypes.items()):
    print(v, k)
