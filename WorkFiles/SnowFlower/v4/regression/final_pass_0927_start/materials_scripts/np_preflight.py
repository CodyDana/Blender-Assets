"""Preflight for the pack-material build: prove the build CAN succeed before anything in Unreal is deleted.

Pure Python (no ``unreal``), run by ``run_build.sh`` before ``clean`` / ``build``::

    py -3 -B np_preflight.py                 # exit 0 = safe to clean and build; prints the code fingerprint
    py -3 -B np_preflight.py --fingerprint   # print only the fingerprint (used to detect edits during a run)

Why it exists (2026-09-27): one chat added a static switch ('Metal From ORM') to np_masters.py while its spec entry
was still unwritten; another chat then ran clean + build.  ``clean`` deleted M_Fabric_Master, ``build`` raised
KeyError on the missing parameter, and 13 instances were left without a parent.  Every parameter a master graph asks
for must exist in that master's spec table, and that is checkable offline - so it is checked here, first.

Checks:
  1. every P("...") / P.switch("...") name in each builder of np_masters.py (string literals and module-level string
     constants) exists in that master's parameter table in material_spec.json; names used in shared helpers must
     exist in at least one master's table;
  2. every master in the spec has a builder and vice versa;
  3. np_spec.py resolves (the same check ``maps_check`` runs).
The fingerprint is a SHA-256 over every *.py in this folder plus material_spec.json, so run_build.sh can refuse to
continue if someone edits the materials code or spec part-way through a run.
"""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "material_spec.json"
MASTERS_PY = HERE / "np_masters.py"


def fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted(HERE.glob("*.py")) + [SPEC]:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _param_calls(node: ast.AST, consts: dict) -> set:
    """Names passed as the first argument of P(...) or P.switch(...) anywhere under ``node``."""
    names = set()
    for n in ast.walk(node):
        if not isinstance(n, ast.Call) or not n.args:
            continue
        f = n.func
        is_p = isinstance(f, ast.Name) and f.id == "P"
        is_switch = isinstance(f, ast.Attribute) and f.attr == "switch" and isinstance(f.value, ast.Name) and f.value.id == "P"
        if not (is_p or is_switch):
            continue
        a = n.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            names.add(a.value)
        elif isinstance(a, ast.Name) and a.id in consts:
            names.add(consts[a.id])
        else:
            names.add(f"<unresolved:{ast.unparse(a)}>")
    return names


def check() -> list:
    problems = []
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    masters = spec["masters"]
    tables = {m: {p["name"] for p in v["parameters"]} for m, v in masters.items()}

    tree = ast.parse(MASTERS_PY.read_text(encoding="utf-8"))
    consts = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    builders = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BUILDERS" for t in n.targets):
            for k, v in zip(n.value.keys, n.value.values):
                builders[k.value] = v.id
    if not builders:
        problems.append("np_masters.py: BUILDERS table not found")

    for m in masters:
        if m not in builders:
            problems.append(f"spec master {m} has no builder in np_masters.BUILDERS")
    for m, fn in builders.items():
        if m not in masters:
            problems.append(f"builder for {m} but no such master in material_spec.json")
            continue
        for name in sorted(_param_calls(funcs[fn], consts)):
            if name.startswith("<unresolved"):
                problems.append(f"{m} ({fn}): parameter name {name} cannot be checked - use a literal or a module constant")
            elif name not in tables[m]:
                problems.append(f"{m} ({fn}) uses parameter '{name}' which is NOT in its spec table "
                                f"(add it to material_spec.json masters.{m}.parameters)")

    union = set().union(*tables.values()) if tables else set()
    builder_fns = set(builders.values())
    for fn, node in funcs.items():
        if fn in builder_fns:
            continue
        for name in sorted(_param_calls(node, consts)):
            if not name.startswith("<unresolved") and name not in union:
                problems.append(f"helper {fn}() uses parameter '{name}' which no master declares")

    r = subprocess.run([sys.executable, "-B", str(HERE / "np_spec.py")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        problems.append("np_spec.py failed to resolve the spec:\n" + (r.stdout + r.stderr)[-2000:])
    return problems


def main() -> int:
    if "--fingerprint" in sys.argv:
        print(fingerprint())
        return 0
    problems = check()
    fp = fingerprint()
    if problems:
        print("PREFLIGHT FAILED - nothing was deleted; fix these first:")
        for p in problems:
            print("  - " + p)
        print(f"fingerprint {fp}")
        return 1
    print(f"PREFLIGHT OK  fingerprint {fp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
