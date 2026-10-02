"""perf2: column-mean diff of two (or two groups of) DojoLab CSV profiles; prints the columns that changed most.
usage: csv_diff.py "A1.csv,A2.csv" "B1.csv,B2.csv" [min_abs]"""
import csv, statistics as S, sys
from pathlib import Path
CSVD = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab\Saved\Profiling\CSV")


def load(name):
    p = Path(name) if Path(name).is_absolute() else CSVD / name
    allr = list(csv.reader(p.open(encoding="utf-8", errors="replace")))
    hdr = max([r for r in allr if r and r[0] == "EVENTS"], key=len)
    rows = [r for r in allr[1:] if r and r[0] != "EVENTS" and not r[0].startswith("[") and len(r) <= len(hdr)][3:]
    out = {}
    for i, h in enumerate(hdr):
        v = []
        for r in rows:
            if i < len(r) and r[i] not in ("",):
                try:
                    v.append(float(r[i]))
                except ValueError:
                    pass
        if v:
            out[h] = S.mean(v)
    return out


def group(arg):
    ms = [load(n) for n in arg.split(",")]
    keys = set().union(*ms)
    return {k: S.mean([m.get(k, 0.0) for m in ms]) for k in keys}


if __name__ == "__main__":
    a, b = group(sys.argv[1]), group(sys.argv[2])
    lim = float(sys.argv[3]) if len(sys.argv) > 3 else 0.15
    rows = [(k, a.get(k, 0.0), b.get(k, 0.0)) for k in set(a) | set(b)]
    rows = [r for r in rows if abs(r[2] - r[1]) >= lim and not r[0].startswith(("Memory", "Physical", "Virtual", "Extended", "System", "RenderTarget", "Transient", "ShadowCache", "CPUUsage"))]
    for k, x, y in sorted(rows, key=lambda r: -abs(r[2] - r[1]))[:70]:
        print(f"{k:70s} {x:10.3f} {y:10.3f} {y - x:+10.3f}")
