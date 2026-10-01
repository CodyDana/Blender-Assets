"""r20 final: integration checks on the combined test copy (plank map + tint, side-case placement / rotation, image paths)."""
import json
import math
from pathlib import Path

import bpy

out = {}
m = bpy.data.materials.get("M_AK_Plank")
info = {"images": [], "tints": []}
for n in m.node_tree.nodes:
    if n.type == "TEX_IMAGE" and n.image:
        info["images"].append(n.image.filepath)
    if n.type == "VECT_MATH" and n.operation == "MULTIPLY":
        info["tints"].append([round(v, 3) for v in n.inputs[1].default_value])
out["M_AK_Plank"] = info
missing = [i.filepath for i in bpy.data.images if i.source == "FILE" and not Path(bpy.path.abspath(i.filepath)).exists()]
out["images_total"] = sum(1 for i in bpy.data.images if i.source == "FILE")
out["images_missing"] = missing
out["images_preview_tex"] = sorted({Path(i.filepath).name for i in bpy.data.images if "room_preview" in i.filepath})
cases = []
for o in bpy.context.scene.objects:
    if o.data and o.type == "MESH" and "_Case_" in o.data.name and o.data.name.endswith("_Plinth"):
        cases.append((o.data.name.replace("SM_AK_Case_", "").replace("_Plinth", ""), round(o.location.x, 3),
                      round(o.location.y, 3), round(math.degrees(o.rotation_euler.z)) % 360,
                      [round(v, 3) for v in o.dimensions]))
out["case_plinths"] = sorted(cases, key=lambda c: (c[1], c[2]))
print("INSPECT", json.dumps(out))
