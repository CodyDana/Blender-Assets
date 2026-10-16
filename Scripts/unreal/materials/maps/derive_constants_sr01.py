"""Derive the version-2 recolour constants of the Sniper Rifle SR-01's OD paint (recolour group SR01: ONE member, the
OD paint on the Chassis set).  ADDED 2026-10-16 (the SR-01 pack-colours stage, materials lock owner sr01-pack); a copy
of derive_constants_smg01.py with the sniper's group, one part, map and output paths.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup         --python Scripts/unreal/materials/maps/derive_constants_sr01.py

Exactly ``derive_constants.fabric_part`` (imported, not copied or edited: the other items' recolour_constants.json record
derive_constants.py's sha256, so that file must not change), run on the Recolour map written by
WorkFiles/guns/sniper/materials/sr01_recolour_maps.py (Exports/Guns/SR01/Textures/Recolour/T_SR01_Chassis_Detail16.png
and recolour_maps.json, schema ninjapack.recolour_maps/1).  Writes Exports/Guns/SR01/Textures/Recolour/
recolour_constants.json (the schema of the other items' files; the generator block names THIS script and records
derive_constants.py's sha256) and a copy in WorkFiles/guns/sniper/materials/.  Same gates as every fabric part: the v2
twin at the default equals the v1 contract at mip 0 and at every mip, every guard is inactive at the default, the fitted
mip correction keeps the map mean within 2 %.  Exit 1 if any fails.  Re-run it after every maps rebuild.

M_SR01_Chassis uses M_Fabric_Master with Metal From ORM ON (Cloth Sheen OFF, no lettering).  Option D1-a: the OD
carries chip and rub hue that one Colour flattens (the default recolour path sits 3-4 levels p99.9 from the BC on the
OD), and the set also carries anodize, polymer and rubber (28 % of its texels) that the master's recolour path would
tint (it has no mask input), so the shipped instance has Use Original Baked Colours ON (exactly the BC).  Paths are
literal project-relative strings (no resolve(): the build may run from a mirror root whose Exports folders are
junctions).
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

VERSION = "2.0.0-sr01"
GROUP = "SR01"
REC = "Exports/Guns/SR01/Textures/Recolour"
PARTS = {"SR01/Chassis": f"{REC}/T_SR01_Chassis_Detail16.png"}
COPY = "WorkFiles/guns/sniper/materials/recolour_constants_SR01.json"


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
