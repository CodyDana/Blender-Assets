"""VERIFY r8: compare every Blender check JSON of this verifier (verify_r9/) with the round-8 verifier (verify_r8/):
pass flags and every differing leaf value. Out: verify_r9/compare_blender.json"""
import json
from pathlib import Path
W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
FILES = ["walk_check.json", "climb_check.json", "roof_walk_check.json", "hall_roof_walk.json", "ob_roof_walk.json",
         "corridor_roof_walk_showcase.json", "corridor_clearance_showcase.json", "sp_roof_walk_shed.json",
         "sp_roof_walk_pavilion.json", "clearance_r4.json", "ground_holes_r4.json"]


def leaves(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from leaves(v, f"{p}/{k}")
    elif isinstance(d, list):
        for i, v in enumerate(d):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, d


def flags(d):
    return {p: v for p, v in leaves(d) if p.split("/")[-1].startswith("passed") or p.split("/")[-1] in ("ok", "PASS", "pass")}


out = {}
for f in FILES:
    a = json.loads((W / "verify_r8" / f).read_text(encoding="utf-8"))
    b = json.loads((W / "verify_r9" / f).read_text(encoding="utf-8"))
    la, lb = dict(leaves(a)), dict(leaves(b))
    diff = {k: [la.get(k), lb.get(k)] for k in sorted(set(la) | set(lb)) if la.get(k) != lb.get(k)}
    top = {k: b[k] for k in b if isinstance(b, dict) and k.startswith("passed")} if isinstance(b, dict) else {}
    out[f] = {"top_pass_r6": top, "top_pass_r5": {k: a[k] for k in a if k.startswith("passed")} if isinstance(a, dict) else {},
              "n_leaves_r5": len(la), "n_leaves_r6": len(lb), "n_diff": len(diff), "diff": dict(list(diff.items())[:400])}
(W / "verify_r9" / "compare_blender.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
for f, v in out.items():
    print(f"{f:36s} r6 {v['top_pass_r6']} r5 {v['top_pass_r5']} leaves {v['n_leaves_r5']}->{v['n_leaves_r6']} diffs {v['n_diff']}")
