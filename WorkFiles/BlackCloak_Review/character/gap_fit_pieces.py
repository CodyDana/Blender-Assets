"""Character-fit review (read-only): air gap of the FULL-RES fitted pieces (BlackCloak_MH_fit.blend copy, base meshes,
i.e. what the build decimates) to the locked fitting body, per piece. Also the ORIGINAL sculpt (Manny-shaped) vs the
same MetaHuman body, to show what a rebuild from the original without refit would hit.

blender -b copies/FitBody_copy.blend --factory-startup --python gap_fit_pieces.py -- <fit copy> <orig copy> <out.json>
"""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import garment_qa as gq  # noqa: E402

FIT, ORIG, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
lock = gq.load_base_lock()
fit = gq._fitbody_objects("MH_PlayerDefault", lock)
skin = [fit["body"], fit["head"]]
collider = gq.Collider(skin, [gq.dominant_regions(o) for o in skin])
out = {}
for label, path in (("mh_fit", FIT), ("original_manny_shaped", ORIG)):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(("Cloak_", "Clasp_"))]
    res = {}
    tot = {"verts": 0, "inside_non_arm": 0, "under_1cm_non_arm": 0, "inside_arm": 0}
    for o in dst.objects:
        me = o.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        m = np.array(o.matrix_world)
        co = co @ m[:3, :3].T + m[:3, 3]
        d, found, reg = collider.signed(co, max_distance=0.5)
        arm = reg == "arm"
        na = found & ~arm
        e = {"verts": len(co), "inside_non_arm": int(np.count_nonzero(na & (d < 0))),
             "deepest_non_arm_cm": round(float(-d[na].min() * 100), 2) if np.any(na & (d < 0)) else 0.0,
             "under_1cm_non_arm": int(np.count_nonzero(na & (d < 0.01))),
             "under_1_5cm_non_arm": int(np.count_nonzero(na & (d < 0.015))),
             "min_gap_non_arm_cm": round(float(d[na].min() * 100), 2) if np.any(na) else None,
             "inside_arm": int(np.count_nonzero(found & arm & (d < 0))),
             "deepest_arm_cm": round(float(-d[found & arm].min() * 100), 2) if np.any(found & arm & (d < 0)) else 0.0}
        res[o.name.split(".")[0]] = e
        for k in tot:
            tot[k] += e[k]
        bpy.data.objects.remove(o, do_unlink=True) if o.users else None
    out[label] = {"total": tot, "pieces": res}
Path(OUT).write_text(json.dumps(out, indent=1), encoding="utf-8")
print("GAP_DONE", json.dumps({k: v["total"] for k, v in out.items()}))
