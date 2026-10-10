"""Gate B6a: the parts joined as the static twin would be, qa_check topology + degenerate checks; plus the tokenised
gun deny list on every object name (inside Blender). Promoted from the AR-01's rifle_b6a.py (gunlib 0.2.0).

    blender -b <gun>.blend --factory-startup --python <shim> -- [--out json] [--collection name]

Config ``cfg.b6a``: ``out`` (default scratch/b6a_result.json), ``check_name`` (default SM_<code>_B6aCheck).
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import gateutil as GU
from .. import qa_gun


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    coll = GU.opt(argv, "--collection")
    src = bpy.data.collections[coll].objects if coll else bpy.data.objects
    objs = [o for o in src if o.type == "MESH" and not o.name.startswith("_")]
    res = qa_gun.b6a_topology(objs, name=cfg.b6a.get("check_name", f"SM_{cfg.code}_B6aCheck"))
    res["deny_list"] = {o.name: qa_gun.deny_hits(o.name) for o in objs if qa_gun.deny_hits(o.name)}
    res["deny_list_clean"] = not res["deny_list"]
    out = Path(GU.opt(argv, "--out") or cfg.b6a.get("out") or cfg.scratch / "b6a_result.json")
    out.write_text(json.dumps(res, indent=1))
    for c in res["checks"]:
        print("[B6a]", c["name"], c["passed"], c["detail"])
    print("[B6a] PASSED", res["passed"], "deny clean", res["deny_list_clean"])
    return res
