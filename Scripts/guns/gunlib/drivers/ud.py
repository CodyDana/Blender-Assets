"""Gates UD1-UD2 on a gun's built parts (inside Blender; gunlib 0.2.0, SMG_BUILD_PLAN 14.2). Every mesh object of the
collection (default: the gun's parts collection; ``--collection`` repeats for LOD collections) through
gunlib.ud.check_object; the per-object reports, the failure locations and the two gate records go to a JSON.

    blender -b <gun>.blend --factory-startup --python drivers/run.py -- --gun <cfg.py> --driver ud
            [--collection <name>]... [--out json] [--label text]

Part generators call ``gunlib.ud.check_object`` on their own output at build time; this driver is the stage gate
over the whole set (and, at W2, over the joined export meshes with UD3 added).
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import gateutil as GU
from .. import ud as UD


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    colls = [argv[i + 1] for i, a in enumerate(argv) if a == "--collection"] or [cfg.parts_collection]
    label = GU.opt(argv, "--label", "")
    reps, where = [], {}
    for c in colls:
        for o in bpy.data.collections[c].objects:
            if o.type != "MESH" or o.name.startswith(("_", "UCX_")):
                continue
            r = UD.check_object(o)
            r["collection"] = c
            reps.append(r)
            if not (r["pass_ud1"] and r["pass_ud2"]):
                where[o.name] = UD.locate(o, 8)
    gates = UD.gate(reps, label)
    out = {"gate": "UD1-UD2 (Unreal degenerate rule at form time)", "collections": colls, "gates": gates,
           "failed": [g["name"] for g in gates if not g["pass"]], "objects": reps, "failure_locations_mm": where}
    out["status"] = "pass" if not out["failed"] else "fail"
    p = Path(GU.opt(argv, "--out") or cfg.scratch / "ud_result.json")
    p.write_text(json.dumps(out, indent=1, default=str))
    for g in gates:
        print("[UD]", "PASS" if g["pass"] else "FAIL", g["name"], json.dumps(g["value"], default=str)[:300])
    return out
