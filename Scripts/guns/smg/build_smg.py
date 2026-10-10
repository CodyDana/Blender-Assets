"""SMG01 (Compact SMG SM-01) build, staged (SMG_BUILD_PLAN section 15, W1b). Headless Blender only:

    blender -b --factory-startup --python Scripts/guns/smg/build_smg.py -- --stage blockout|form
            [--only name,name] [--groups receiver,rails,...] [--tag x] [--no-save]

blockout  primary volumes from the traces (+ the flip-sight generators for B4)
          -> WorkFiles/guns/smg/scratch/SMG01_blockout.blend + scratch/blockout_tris.npz
form      every part as real geometry -> Assets/Guns/SMG01.blend + scratch/form_tris.npz + scratch/form_build_report.json

The asset lock SMG01 is asserted at the top (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, CODE, GRIP, SCRATCH, BLEND, BLOCKOUT_BLEND, PARTS_COLL  # noqa: E402

import bpy  # noqa: E402

from gunlib import bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def assert_lock():
    from pipeline import lock as L
    info = L.assert_owner(CODE, "claude")
    print(f"[{CODE}] lock ok:", info.get("agent"), info.get("since"))


def stage_blockout():
    import smg_blockout as SB
    import smg_parts as SP
    from parts import sights
    bl.reset_scene()
    col = bl.collection(f"{CODE}_Blockout")
    objs = []
    for pid, m in SB.parts().items():
        objs.append(m.to_object(pid, col, GRIP))
    for it in sights.rear_sight() + sights.front_sight():
        objs.append(SP.build_one(it, col, GRIP))
    if "--no-save" not in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_BLEND))
    bl.export_npz(objs, SCRATCH / "blockout_tris.npz", GRIP, [o.name for o in objs])
    print(f"[{CODE}] blockout parts", len(objs), "tris", sum(len(o.data.polygons) for o in objs))


def stage_form():
    import smg_parts as SP
    bl.reset_scene()
    t0 = time.time()
    only = [v for v in arg("--only", "").split(",") if v]
    groups = [v for v in arg("--groups", "").split(",") if v]
    tag = arg("--tag", None)
    res = SP.build_all(only or None, tag=tag, groups=groups or None)
    if "--no-save" not in argv:
        partial = bool(only or groups)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND if not partial else SCRATCH / f"{CODE}_form_partial.blend"))
    print(f"[{CODE}] form built in %.1fs" % (time.time() - t0))
    return res


if __name__ == "__main__":
    assert_lock()
    st = arg("--stage", "blockout")
    {"blockout": stage_blockout, "form": stage_form}[st]()
    print(f"[{CODE}] STAGE_DONE", st)
