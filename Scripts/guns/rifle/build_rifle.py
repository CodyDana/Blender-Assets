"""AR-01 rifle build, staged (RIFLE_BUILD_PLAN section 12). Headless Blender only:

    blender -b --factory-startup --python Scripts/guns/rifle/build_rifle.py -- --stage blockout|form [--mag-thickness 28]

blockout  primary volumes from the traces  -> WorkFiles/guns/rifle/scratch/AR01_blockout.blend + blockout_tris.npz
form      every part as real geometry      -> Assets/Guns/AR01.blend + scratch/form_tris.npz (+ per-pose data for B3)

The asset lock AR01 is asserted at the top (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, BLEND, BLOCKOUT_BLEND  # noqa: E402

import bpy  # noqa: E402

from gunlib import bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def assert_lock():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    info = L.assert_owner("AR01", "claude")
    print("[AR01] lock ok:", info.get("agent"), info.get("since"))


def stage_blockout():
    import rifle_blockout as RB
    bl.reset_scene()
    col = bl.collection("AR01_Blockout")
    t = float(arg("--mag-thickness", "28"))
    objs = []
    for pid, m in RB.parts(t).items():
        ob = m.to_object("BO_" + pid, col, GRIP)
        objs.append(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_BLEND))
    bl.export_npz(objs, SCRATCH / "blockout_tris.npz", GRIP, [o.name[3:] for o in objs])
    print("[AR01] blockout parts", len(objs), "tris", sum(len(o.data.polygons) for o in objs))


def stage_form():
    import rifle_parts as RP
    bl.reset_scene()
    t0 = time.time()
    only = [v for v in arg('--only', '').split(',') if v]
    res = RP.build_all(only or None)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND if not only else SCRATCH / 'AR01_form_partial.blend'))
    print("[AR01] form built in %.1fs" % (time.time() - t0))
    return res


if __name__ == "__main__":
    assert_lock()
    st = arg("--stage", "blockout")
    {"blockout": stage_blockout, "form": stage_form}[st]()
    print("[AR01] STAGE_DONE", st)
