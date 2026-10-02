"""Play-test log scan: errors / ensures / warnings in a -game log of dj_ninja_playtest.py, overall and per test window
(the probe's `DJ_PT_MARK <name> begin|end` markers; `route x` / `attempt x` markers open a window that the next marker
closes). Lines are normalised (timestamps, frame numbers, digits, object suffixes) and counted.

    py -3 -B pt_scan.py <log> <out.json>
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CATS = {
    "ensure": re.compile(r"Ensure condition failed|ensureMsgf|\bensure\(|=== Handled ensure", re.I),
    "assert": re.compile(r"Assertion failed|Fatal error", re.I),
    "script": re.compile(r"Script Stack|Accessed None|Script Msg|LogScript: (Warning|Error)", re.I),
    "python": re.compile(r"LogPython: Error|Traceback \(most recent", re.I),
    "ninja_warn": re.compile(r"LogNinja\w*: (Warning|Error)|LogDojoNinja: (Warning|Error)"),
    "error": re.compile(r"(?<!Display): Error:|\]Log\w+: Error:"),
    "warning": re.compile(r"\]Log\w+: Warning:"),
}
NOISE = re.compile(r"Failed to load '(aqProf|VtuneApi|VtuneApi32e|WinPixGpuCapturer)\.dll'|UnifiedErrorTest|"
                   r"FError that has been|Error with (param|context)|Error test:", re.I)


def norm(ln):
    ln = re.sub(r"^\[[^\]]*\]\[[^\]]*\]", "", ln)
    ln = re.sub(r"_C_\d+|_\d+\b", "_#", ln)
    ln = re.sub(r"\d+(\.\d+)?", "#", ln)
    return ln.strip()[:220]


def main():
    log, out = Path(sys.argv[1]), Path(sys.argv[2])
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    win = "startup"
    tot = {k: Counter() for k in CATS}
    per = defaultdict(lambda: {k: Counter() for k in CATS})
    ninja_info = Counter()
    for ln in lines:
        m = re.search(r"DJ_PT_MARK (.+)$", ln)
        if m:
            t = m.group(1).strip()
            if t.endswith(" begin"):
                win = t[:-6]
            elif t.endswith(" end"):
                win = "between"
            else:
                win = t
            continue
        if NOISE.search(ln):
            continue
        if re.search(r"LogNinja\w*:|LogDojoNinja:", ln):
            ninja_info[norm(ln)] += 1
        for k, rx in CATS.items():
            if rx.search(ln):
                n = norm(ln)
                tot[k][n] += 1
                per[win][k][n] += 1
    res = {"log": str(log), "lines": len(lines),
           "totals": {k: sum(v.values()) for k, v in tot.items()},
           "unique": {k: v.most_common(25) for k, v in tot.items() if v},
           "windows": {w: {k: sum(c.values()) for k, c in d.items() if c} for w, d in per.items()},
           "window_lines": {w: {k: c.most_common(8) for k, c in d.items() if c} for w, d in per.items()
                            if w not in ("startup",)},
           "ninja_log": ninja_info.most_common(60)}
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["totals"]), "windows with lines:", {w: v for w, v in res["windows"].items() if v})


if __name__ == "__main__":
    main()
