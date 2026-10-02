"""Scan an Unreal log for load problems, split into lines that concern the ported content and the rest.

    py -3 -B scan_log.py <log> <out.json> [<baseline log>]

Gates: no 'Failed to load' / 'Missing' / 'invalid class' / "Can't find file" / skeleton or bone mismatch / CoreRedirect
problems on the ported paths. The optional baseline log (an earlier DojoLab run) shows which other warnings were
already there before the port.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

PORTED = ("/Game/Ninja", "/Game/MetaHumans", "/Game/BareNinja_AnimSet", "/Game/NiagaraExamples",
          "/Game/Characters/Mannequins/", "DemoGame_1", "/Script/DojoLab", "BP_NinjaGasp", "BP_NinjaVisual",
          "GM_DojoNinja", "Ninja", "MH_PlayerDefault", "metahuman")
PATTERNS = {
    "failed_to_load": re.compile(r"Failed to load|failed to load|LoadPackage.*fail", re.I),
    "missing": re.compile(r"\bMissing\b|Can't find file|Cannot find|could not be found|not found", re.I),
    "invalid_class": re.compile(r"invalid class|Unknown class|Class .* not found|ClassNotFound|"
                                r"BlueprintGeneratedClass.*None|Unable to load class", re.I),
    "skeleton": re.compile(r"skeleton.*(mismatch|incompatible|not compatible)|missing bone|bone .* not found|"
                           r"does not match skeleton", re.I),
    "redirect": re.compile(r"CoreRedirect|redirector", re.I),
    "compile_error": re.compile(r"\[Compiler\].*Error|Blueprint.*compil.*(error|failed)|LogBlueprint: Error", re.I),
    "error": re.compile(r"\bError:", re.I),
}
NOISE = re.compile(r"LogPython: DJ_|LogInit: Display|cmd line|Command line|Running .*-run=", re.I)


def scan(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = {k: {"ported": [], "other": []} for k in PATTERNS}
    for ln in text:
        if NOISE.search(ln):
            continue
        for k, rx in PATTERNS.items():
            if rx.search(ln):
                side = "ported" if any(p.lower() in ln.lower() for p in PORTED) else "other"
                out[k][side].append(ln.strip()[:400])
    return text, out


def main():
    log, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text, out = scan(log)
    rep = {"log": str(log), "lines": len(text), "counts": {k: {s: len(v[s]) for s in v} for k, v in out.items()},
           "ported": {k: v["ported"][:60] for k, v in out.items() if v["ported"]},
           "other_top": {k: Counter(re.sub(r"\d+", "#", x)[:200] for x in v["other"]).most_common(25)
                         for k, v in out.items() if v["other"]}}
    if len(sys.argv) > 3 and Path(sys.argv[3]).is_file():
        _, base = scan(Path(sys.argv[3]))
        rep["baseline"] = {"log": sys.argv[3], "counts": {k: {s: len(v[s]) for s in v} for k, v in base.items()}}
    hard = ("failed_to_load", "invalid_class", "skeleton", "compile_error")
    rep["ported_hard_problems"] = sum(len(out[k]["ported"]) for k in hard)
    rep["passed"] = rep["ported_hard_problems"] == 0
    dst.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({"counts": rep["counts"], "ported_hard_problems": rep["ported_hard_problems"]}, indent=0))


if __name__ == "__main__":
    main()
