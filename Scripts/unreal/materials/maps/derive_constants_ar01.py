"""Derive the version-2 recolour constants of the Assault Rifle AR-01's furniture (the walnut stock, pistol grip and both
handguards). ADDED 2026-10-09 (the AR-01 pack-materials stage, materials lock owner ar01-gun-chat); a copy of
derive_constants_katana.py with the rifle's group, map and output paths.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup         --python Scripts/unreal/materials/maps/derive_constants_ar01.py

Exactly ``derive_constants.fabric_part`` (imported, not copied or edited: the other items' recolour_constants.json record
derive_constants.py's sha256, so that file must not change), run on the Recolour map written by
Scripts/guns/rifle/rifle_recolour.py (Exports/Guns/AR01/Textures/Recolour/T_AR01_Furniture_Detail16.png and
recolour_maps.json).  Writes Exports/Guns/AR01/Textures/Recolour/recolour_constants.json (the schema of the other
items' files; the generator block names THIS script and records derive_constants.py's sha256) and a copy in
WorkFiles/guns/rifle/materials/.  Same gates as every fabric part: the v2 twin at the default equals the v1 contract at
mip 0 and at every mip, every guard is inactive at the default, the fitted mip correction keeps the map mean within
2 %.  Exit 1 if any fails.  Re-run it after every furniture maps rebuild (rifle_recolour.py first).

The furniture uses M_Fabric_Master (Cloth Sheen OFF, no lettering, Metal From ORM OFF).  The four wood pieces carry
slightly different hues in the shipped BC (the reference's mismatched furniture); the scalar detail keeps their VALUE
ratios but not their hue offsets, so the shipped default instance has Use Original Baked Colours ON (exactly the BC)
and a buyer recolour (switch off, pick Colour) moves all four pieces together.  Paths are written as literal
project-relative strings (no resolve(): the build may run from a mirror root whose Exports folders are junctions).
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

VERSION = "2.0.0-ar01"
GROUP = "AR01"
REC = "Exports/Guns/AR01/Textures/Recolour"
PARTS = {"AR01/Furniture": f"{REC}/T_AR01_Furniture_Detail16.png"}
COPY = "WorkFiles/guns/rifle/materials/recolour_constants_AR01.json"


def main() -> int:
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    maps_rel = f"{REC}/recolour_maps.json"
    maps_json = rc.PROJECT / maps_rel
    gen = json.loads(maps_json.read_text(encoding="utf-8"))
    doc = {"schema": "ninjapack.recolour_constants/1", "item": GROUP, "generated": datetime.date.today().isoformat(),
           "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                         "base_script": rc.rel(dc.__file__), "base_script_sha256": rc.sha256(dc.__file__),
                         "twin": rc.rel(tw.__file__), "twin_sha256": rc.sha256(tw.__file__),
                         "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender},
           "source": {"recolour_maps": maps_rel, "sha256": rc.sha256(maps_json)},
           "merge_rule": "np_spec.py: params here override recolour_maps.json params of the same instance",
           "parts": {}}
    for part, png in PARTS.items():
        doc["parts"][part] = dc.fabric_part(GROUP, part, png, gen["parts"][part])
    doc["pass"] = all(v["pass"] for v in doc["parts"].values())
    out = rc.PROJECT / f"{REC}/recolour_constants.json"
    rc.write_json(out, doc)
    copy = rc.PROJECT / COPY
    copy.parent.mkdir(parents=True, exist_ok=True)
    rc.write_json(copy, doc)
    dc.log(f"wrote {REC}/recolour_constants.json pass={doc['pass']}")
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
