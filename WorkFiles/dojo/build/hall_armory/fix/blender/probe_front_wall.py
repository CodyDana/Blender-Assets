"""FIX round probe (read-only): which hall geometry pokes through the INNER face of the front wall (world y > 24.045,
the transom / plaster inner face) between the head beam and the wall plate, X 15-29. Imports the exported FBX."""
import bpy, json, sys
from mathutils import Matrix
ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
PIECES = {"SM_DKH_RoofLower_Front": (22.0, 29.0, 0.0, 0), "SM_DKH_Frame_Open": (22.0, 29.0, 0.0, 0),
          "SM_DKH_VerandaFrame": (22.0, 29.0, 0.0, 0), "SM_DKH_Bay_Transom": (17.0, 24.0, 0.5, 0),
          "SM_DKH_Bay_Plaster": (17.0, 24.0, 0.5, 0), "SM_DKH_Bay_ClereFrieze": (17.0, 24.0, 0.5, 0),
          "SM_DKH_RoofUpper_Front": (22.0, 29.0, 0.0, 0)}
bpy.ops.wm.read_factory_settings(use_empty=True)
out = {}
for name, (x, y, z, r) in PIECES.items():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f"{ROOT}/Exports/DojoKit/Hall/{name}.fbx")
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH" and not o.name.startswith("UCX_")]
    rows = []
    for o in new:
        M = Matrix.Translation((x, y, z)) @ o.matrix_world
        for v in o.data.vertices:
            w = M @ v.co
            if 15.0 <= w.x <= 29.0 and 2.6 <= w.z <= 5.0 and w.y > 24.03 and w.y < 24.5:
                rows.append((round(w.x, 3), round(w.y, 4), round(w.z, 3)))
    ys = sorted({r_[1] for r_ in rows})
    zs = sorted({r_[2] for r_ in rows})
    out[name] = {"objs": [o.name for o in new], "n": len(rows), "y_max": max(ys) if ys else None,
                 "y_vals": ys[:12], "z_range": [zs[0], zs[-1]] if zs else None,
                 "x_sample": sorted({r_[0] for r_ in rows})[:30]}
    for o in new:
        o.hide_set(True)
print("PROBE_FRONT", json.dumps(out, indent=1))
json.dump(out, open(f"{ROOT}/WorkFiles/dojo/build/hall_armory/fix/json/probe_front_wall.json", "w"), indent=1)
