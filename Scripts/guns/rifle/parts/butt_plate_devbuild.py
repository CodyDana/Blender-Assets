"""Butt-plate detail builder's isolated rebuild (headless Blender; detail pass round 1). Opens a SNAPSHOT of the form
blend, rebuilds only buttstock + butt_plate + butt_screws (the stock's end cut follows the plate outline) and saves a
private blend + triangles .npz, so the parallel part builders never share a file being written:

    blender -b <snapshot.blend> --factory-startup --python parts/butt_plate_devbuild.py -- \
        --out-blend <blend> --out-npz <npz> --report <json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rifle_common import ROOT, SPEC, GRIP  # noqa: E402

import bpy  # noqa: E402

from gunlib import bl  # noqa: E402
from gunlib.parts import BuildCtx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


KEYS = ["buttstock", "butt_plate", "butt_screws"]


def main():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    import rifle_parts as RP
    import parts as PM
    coll = bpy.data.collections["AR01_Parts"]
    order = [o.name for o in coll.objects if o.type == "MESH" and not o.name.startswith("_")]
    for n in KEYS:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    ctx = BuildCtx(coll, GRIP, SPEC, KEYS)
    ctx.make("buttstock", RP.part_defs()["buttstock"])
    PM.load("butt_plate").build(SPEC, ctx)
    objs = [bpy.data.objects[n] for n in order if n in bpy.data.objects]
    rep = {}
    for n in KEYS:
        ob = bpy.data.objects[n]
        rep[n] = bl.manifold_report(ob)
        print("[bp] part %-12s %s" % (n, rep[n]))
    rep["_total_tris"] = int(sum(bl.manifold_report(o)["triangles"] for o in objs))
    bl.export_npz(objs, arg("--out-npz"), GRIP, [o.name for o in objs])
    Path(arg("--report")).write_text(json.dumps(rep, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(arg("--out-blend")))
    print("[bp] DEVBUILD_DONE total tris", rep["_total_tris"])


main()
