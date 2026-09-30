"""One-off repair (f1): fold duplicate '<name>.001' materials / images / node groups in Assets/Dojo/DojoStoneKit.blend
onto their originals, under the shared file lock (the wall merge did not fold them before f1). Reports the slot names
of every SM_DKT_ piece afterwards.
Run: blender -b --factory-startup --python Scripts/dojo/stonekit/fold_kit_blend.py
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sk_shared as sk  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402

assert_owner("DojoStoneKit", "claude")
with sk.file_lock(sk.BLEND):
    bpy.ops.wm.open_mainfile(filepath=str(sk.BLEND))
    n = 0
    for coll_ in (bpy.data.materials, bpy.data.images, bpy.data.node_groups):
        for d_ in list(coll_):
            base, _, suf = d_.name.rpartition(".")
            if base and suf.isdigit() and len(suf) == 3 and base in coll_:
                d_.user_remap(coll_[base])
                coll_.remove(d_)
                n += 1
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sk.BLEND))
    bad = sorted({m.name for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_")
                  for m in o.data.materials if m and m.name[-4:-3] == "." and m.name[-3:].isdigit()})
    print("FOLDED", n, "remaining suffixed slots:", bad, flush=True)
