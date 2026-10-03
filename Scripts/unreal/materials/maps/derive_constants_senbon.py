"""Derive the version-2 recolour constants of the senbon heavy needle's thread wrap (ADDED 2026-10-03, the senbon
finalise pass, materials lock owner senbon-wf; a copy of derive_constants_flashbang.py with the senbon's group, map and
output paths).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup         --python Scripts/unreal/materials/maps/derive_constants_senbon.py

Exactly ``derive_constants.fabric_part`` (imported, not copied or edited: the other items' recolour_constants.json record
derive_constants.py's sha256, so that file must not change), run on the Recolour map written by the senbon build
(Scripts/props/build_senbon.py, stage textures: Exports/Senbon/Textures/Recolour/T_Senbon_Heavy_Wrap_Detail16.png and
recolour_maps.json).  Writes Exports/Senbon/Textures/Recolour/recolour_constants.json (the schema of the other items'
files; the generator block names THIS script and records derive_constants.py's sha256) and a copy in
WorkFiles/senbon/fin/.  Same gates as every fabric part: the v2 twin at the default equals the v1 contract at mip 0 and
at every mip, every guard is inactive at the default, the fitted mip correction keeps the map mean within 2 %.
Exit 1 if any fails.  Re-run it after every senbon build that rewrites the Recolour maps.

The wrap slot uses M_Fabric_Master as the kunai grip does (Cloth Sheen OFF, Metal From ORM OFF, no lettering).
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import derive_constants as dc  # noqa: E402  (its main() is not run: only fabric_part is used)
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402

VERSION = "2.0.0-senbon"
GROUP = "Senbon"
REC = "Exports/Senbon/Textures/Recolour"
PARTS = {"Heavy/Wrap": f"{REC}/T_Senbon_Heavy_Wrap_Detail16.png"}


def main() -> int:
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    maps_json = rc.PROJECT / f"{REC}/recolour_maps.json"
    gen = json.loads(maps_json.read_text(encoding="utf-8"))
    doc = {"schema": "ninjapack.recolour_constants/1", "item": GROUP, "generated": datetime.date.today().isoformat(),
           "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                         "base_script": rc.rel(dc.__file__), "base_script_sha256": rc.sha256(dc.__file__),
                         "twin": rc.rel(tw.__file__), "twin_sha256": rc.sha256(tw.__file__),
                         "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender},
           "source": {"recolour_maps": rc.rel(maps_json), "sha256": rc.sha256(maps_json)},
           "merge_rule": "np_spec.py: params here override recolour_maps.json params of the same instance",
           "parts": {}}
    for part, png in PARTS.items():
        doc["parts"][part] = dc.fabric_part(GROUP, part, png, gen["parts"][part])
    doc["pass"] = all(v["pass"] for v in doc["parts"].values())
    out = rc.PROJECT / f"{REC}/recolour_constants.json"
    rc.write_json(out, doc)
    rc.write_json(rc.PROJECT / "WorkFiles" / "senbon" / "fin" / "recolour_constants_Senbon.json", doc)
    dc.log(f"wrote {rc.rel(out)} pass={doc['pass']}")
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    code = main()
    try:
        import bpy  # noqa: F401
        sys.stdout.flush()
        import os
        os._exit(code)
    except ImportError:
        sys.exit(code)
