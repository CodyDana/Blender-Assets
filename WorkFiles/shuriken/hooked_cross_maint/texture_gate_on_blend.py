"""Run the 3.9.1 texture-handedness gate (shuriken_lib.outline_plate.texture_handedness) on the hooked cross of an
already-built .blend, READ ONLY (nothing is saved):

    blender -b <copy of a Shuriken.blend> --factory-startup --python texture_gate_on_blend.py -- <out.json>

Used on a scratch COPY of the 3.9.0 shipped Assets/Shuriken.blend (sha 09e80c6a...) to show the gate FAILS on the
layout the visual review flagged (the -Z island mapped as seen from below), and on the 3.9.1 build to show it passes.
"""
import json
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
sys.path.insert(0, str(PROJ / "Scripts"))
import build_hooked_cross as B  # noqa: E402
from shuriken_lib.outline_plate import texture_handedness  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
lods = [bpy.data.objects[f"SM_Shuriken_HookedCross_LOD{i}"] for i in range(3)]
res = texture_handedness(lods, B.SPEC.outline())
res["blend"] = bpy.data.filepath
out.write_text(json.dumps(res, indent=2), encoding="utf-8")
print("TEXTURE_GATE", res["passed"], "caught", res["negative_control"]["caught"],
      json.dumps({r["faces"]: [r["determinant_uv_per_m2"], r["tip_offsets_in_texture_deg"], r["reads"]]
                  for r in res["lod0_islands"]["islands"]}))
