"""AR-01 gate B6a: the parts joined as the static twin would be, qa_check topology + degenerate checks; plus the
tokenised gun deny list on every object name.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_b6a.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH  # noqa: E402

import bpy  # noqa: E402

from gunlib import qa_gun  # noqa: E402

objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
res = qa_gun.b6a_topology(objs)
res["deny_list"] = {o.name: qa_gun.deny_hits(o.name) for o in objs if qa_gun.deny_hits(o.name)}
res["deny_list_clean"] = not res["deny_list"]
(SCRATCH / "b6a_result.json").write_text(json.dumps(res, indent=1))
for c in res["checks"]:
    print("[B6a]", c["name"], c["passed"], c["detail"])
print("[B6a] PASSED", res["passed"], "deny clean", res["deny_list_clean"])
