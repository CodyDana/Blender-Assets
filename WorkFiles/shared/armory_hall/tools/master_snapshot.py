"""The shell masters' graph snapshot (SYNC.md sections 11.4 and 15): shell_masters.json. Plain Python 3 (no Unreal).

ArmoryLab builds the two shell masters (shell_materials.json `masters`: M_DJ_Lib_Opaque, M_DJ_Lib_Emissive) from the
dojo's graph code at run time (tools/ue_armorylab_shell.py executes Scripts/dojo/unreal/dj_sc_materials.py). This
tool writes, into the shared folder, the exact code those two graphs run and the parameters they read, so a dojo-side
master change is a shared change: it must be snapshotted and bumped, and then puts ArmoryLab (and DojoLab) behind.

    py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py            # compare only: exit 0 = fresh, 4 = differs
    py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py --write    # (ArmoryHall lock) write shell_masters.json

What is captured (the call graph of the two builders, nothing else, so the dojo's other masters can change freely):
  * Scripts/dojo/unreal/dj_sc_materials.py: the MASTERS entries of the shell masters, their builder functions,
    get_or_create (which the ArmoryLab tool calls directly) and, transitively, every module function, module constant and `G` graph method they reference (g.X / self.X);
  * Scripts/dojo/unreal/dj_sc_common.py: every `S.X` member that code references (and its own module names);
  * WorkFiles/dojo/build/showcase/layout_showcase.json: the values that code reads (the sampler default textures'
    package paths, DEF_TEX through S.tex_path).
  The code is kept as source lines with comments, docstrings and blank lines removed (a comment edit is not a change).
  graph_sha256 = sha256 of {masters, code, params}; manifest.json `shell_master_graph` records it at every bump.
"""
import argparse
import ast
import hashlib
import io
import json
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ahcommon as A  # noqa: E402

MAT_SRC = A.ROOT / "Scripts/dojo/unreal/dj_sc_materials.py"
COMMON_SRC = A.ROOT / "Scripts/dojo/unreal/dj_sc_common.py"
LAYOUT_SRC = A.ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json"
OUT = A.SH / "shell_masters.json"
GRAPH_CLASS = "G"
GRAPH_SELF = ("g", "self")
COMMON_ALIAS = "S"


class Module:
    """A source file's top-level functions, classes (with methods) and assignments, with comment-free line text."""

    def __init__(self, path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.tree = ast.parse(self.text)
        self.comment_at = {}
        for tok in tokenize.generate_tokens(io.StringIO(self.text).readline):
            if tok.type == tokenize.COMMENT:
                self.comment_at[tok.start[0]] = tok.start[1]
        self.funcs, self.assigns, self.classes = {}, {}, {}
        for n in self.tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs[n.name] = n
            elif isinstance(n, ast.ClassDef):
                self.classes[n.name] = {m.name: m for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
                self.classes[n.name][""] = n
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, ast.Name):
                        self.assigns[t.id] = n

    def code(self, node, header_only=False):
        """The node's source lines: comments, docstrings and blank lines removed, trailing spaces stripped."""
        first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        last = node.end_lineno
        if header_only:   # a class: its own line(s) up to the first body statement
            last = node.body[0].lineno - 1
        skip = set()
        for body_owner in [node] + ([] if header_only else [m for m in ast.walk(node)
                                                          if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]):
            b = getattr(body_owner, "body", None)
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
                skip.update(range(b[0].lineno, b[0].end_lineno + 1))
        out = []
        for i in range(first, last + 1):
            if i in skip:
                continue
            s = self.lines[i - 1]
            if i in self.comment_at:
                s = s[:self.comment_at[i]]
            s = s.rstrip()
            if s:
                out.append(s)
        return "\n".join(out)


def _refs(node, mod, cls_methods):
    """(kind, name) references of a node: module functions / assigns / the graph class, graph methods, S members."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if n.id in mod.funcs:
                out.add(("func", n.id))
            elif n.id in mod.assigns:
                out.add(("assign", n.id))
            elif n.id in mod.classes:
                out.add(("class", n.id))
        elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            if n.value.id in GRAPH_SELF and n.attr in cls_methods:
                out.add(("method", n.attr))
            elif n.value.id == COMMON_ALIAS:
                out.add(("common", n.attr))
    return out


def build():
    SM = A.jload(A.SH / "shell_materials.json")
    names = sorted(SM["masters"])
    mat, com = Module(MAT_SRC), Module(COMMON_SRC)
    methods = mat.classes.get(GRAPH_CLASS, {})
    md = mat.assigns.get("MASTERS")
    if md is None or not isinstance(md.value, ast.Dict):
        raise SystemExit("STOP: dj_sc_materials.py has no MASTERS dict: update tools/master_snapshot.py")
    entries = {k.value: v for k, v in zip(md.value.keys, md.value.values) if isinstance(k, ast.Constant)}
    code, seen, masters = {}, set(), {}
    todo = [("func", "get_or_create")]   # tools/ue_armorylab_shell.py calls it directly to create the masters
    for m in names:
        v = entries.get(m)
        if v is None:
            raise SystemExit(f"STOP: {m} is not in dj_sc_materials.py MASTERS")
        masters[m] = {"ue_path": SM["masters"][m]["ue_path"], "builder": ast.get_source_segment(mat.text, v)}
        todo += sorted(_refs(v, mat, methods))
    while todo:
        kind, name = todo.pop(0)
        if (kind, name) in seen:
            continue
        seen.add((kind, name))
        if kind == "func":
            node, key = mat.funcs[name], f"dj_sc_materials.py:{name}"
        elif kind == "assign":
            if name == "MASTERS":     # only the shell masters' entries matter (recorded above)
                continue
            node, key = mat.assigns[name], f"dj_sc_materials.py:{name} ="
        elif kind == "class":
            node, key = mat.classes[name][""], f"dj_sc_materials.py:class {name}"
            code[key] = mat.code(node, header_only=True)
            if "__init__" in mat.classes[name]:
                todo.append(("method", "__init__"))
            continue
        elif kind == "method":
            node, key = methods[name], f"dj_sc_materials.py:{GRAPH_CLASS}.{name}"
        else:   # common
            node = com.funcs.get(name) or com.assigns.get(name)
            if node is None:
                raise SystemExit(f"STOP: dj_sc_common.py has no top-level {name}")
            code[f"dj_sc_common.py:{name}"] = com.code(node)
            for k2, n2 in sorted(_refs(node, com, {})):
                if k2 in ("func", "assign"):
                    todo.append(("common", n2))
            continue
        code[key] = mat.code(node)
        todo += sorted(_refs(node, mat, methods))
    # the layout values that code reads: the sampler defaults (G.tex: S.tex_path(L, DEF_TEX[kind]))
    params = {}
    if ("assign", "DEF_TEX") in seen:
        L = A.jload(LAYOUT_SRC)
        dt = ast.literal_eval(mat.assigns["DEF_TEX"].value)
        params["sampler_default_textures"] = {k: f"{L['textures'][t]['ue_dir']}/{t}" for k, t in sorted(dt.items())}
    code = dict(sorted(code.items()))
    core = {"masters": masters, "code": code, "params": params}
    snap = {
        "about": "the exact graph code + parameters of the shell masters ArmoryLab builds (SYNC.md 11.4 and 15); "
                 "written only by tools/master_snapshot.py --write; a change here is a shared change (bump)",
        "generator": "WorkFiles/shared/armory_hall/tools/master_snapshot.py",
        "sources": [A.rel(MAT_SRC), A.rel(COMMON_SRC), A.rel(LAYOUT_SRC)],
        "graph_sha256": hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        "counts": {"masters": len(masters), "code_members": len(code), "code_lines": sum(c.count("\n") + 1 for c in code.values())},
    }
    snap.update(core)
    return snap


def diff(old, new):
    if old is None:
        return ["shell_masters.json does not exist"]
    out = []
    for sec in ("masters", "params"):
        if old.get(sec) != new.get(sec):
            out.append(f"{sec} differ")
    oc, nc = old.get("code", {}), new.get("code", {})
    for k in sorted(set(oc) | set(nc)):
        if oc.get(k) != nc.get(k):
            out.append(f"code {k}: " + ("added" if k not in oc else "removed" if k not in nc else "changed"))
    return out


def main():
    ap = argparse.ArgumentParser(description="snapshot the shell masters' graph code (SYNC.md 15)")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--agent", default="claude")
    a = ap.parse_args()
    new = build()
    old = A.jload(OUT) if OUT.exists() else None
    d = diff(old, new)
    print(f"master_snapshot: graph_sha256 {new['graph_sha256'][:16]}, {new['counts']}; "
          f"{'FRESH' if not d else 'DIFFERS: ' + '; '.join(d[:20])}")
    if not a.write:
        return 0 if not d else 4
    if not A.lock_held(a.agent):
        print("STOP: claim the lock first: py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude")
        return 1
    A.jdump(OUT, new)
    print(f"shell_masters.json WRITTEN. Next: check_sync.py --side dojo, then bump_manifest.py --chat dojo --summary ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
