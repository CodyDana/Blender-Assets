"""SR01 (Sniper Rifle SR-01) build, staged (SR01_BUILD_PLAN section 9, W1). Headless Blender only:

    blender -b --factory-startup --python Scripts/guns/sniper/build_sniper.py -- --stage blockout|form
            [--only name,name] [--no-save]

blockout  primary volumes from the traces -> WorkFiles/guns/sniper/scratch/w1/SR01_blockout.blend + blockout_tris.npz
form      every part as real geometry (sniper_parts) -> Assets/Guns/SR01.blend + scratch/w1/form_tris.npz
          + scratch/w1/form_build_report.json (per part: manifold report, UD summary, triangles, seconds, record)

The asset lock SR01 is asserted first (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import CODE, GRIP, SCRATCH, BLEND, BLOCKOUT_BLEND, PARTS_COLL  # noqa: E402

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
    import sr_blockout as SB
    bl.reset_scene()
    col = bl.collection(f"{CODE}_Blockout")
    objs = [m.to_object(pid, col, GRIP) for pid, m in SB.parts().items()]
    for name, cl in SB.cuts().items():
        ob = bpy.data.objects[name]
        for c in cl:
            bl.boolean(ob, c, "DIFFERENCE", offset=GRIP)
    if "--no-save" not in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_BLEND))
    bl.export_npz(objs, SCRATCH / "blockout_tris.npz", GRIP, [o.name for o in objs])
    print(f"[{CODE}] blockout parts", len(objs), "tris", sum(len(o.data.polygons) for o in objs))


def stage_form():
    import sniper_parts as SP
    bl.reset_scene()
    t0 = time.time()
    only = [v for v in arg("--only", "").split(",") if v]
    SP.NO_BEVEL = "--no-bevel" in argv
    if "--repair-only" in argv:
        SP.REPAIR_ONLY = set(v for v in arg("--repair-only", "").split(",") if v)
    res = SP.build_all(only or None)
    partial = bool(only)
    if "--no-save" not in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND if not partial else SCRATCH / f"{CODE}_form_partial.blend"))
    objs = [o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"]
    tag = "form" if not partial else "form_partial"
    bl.export_npz(objs, SCRATCH / f"{tag}_tris.npz", GRIP, [o.name for o in objs])
    (SCRATCH / f"{tag}_build_report.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    tot = sum(r.get("triangles", 0) for r in res.values())
    print(f"[{CODE}] form built in %.1fs, parts %d, total tris %d" % (time.time() - t0, len(res), tot))
    bad = {k: v for k, v in res.items() if v.get("boundary_edges") or v.get("multi_face_edges") or v.get("shells", 1) != 1}
    print(f"[{CODE}] non-closed or multi-shell parts:", json.dumps({k: {x: v.get(x) for x in ("boundary_edges", "multi_face_edges", "shells")} for k, v in bad.items()}))


def stage_scope():
    """W1b: SM_Att_Scope_LongRange form, built at its mounted pose in frame M -> Assets/Guns/Att_Scope_LongRange.blend
    (+ an Empty 'Mount' at the attachment origin) and scratch/w1/scope_tris.npz / scope_build_report.json."""
    import sr_scope as SC
    import sniper_parts as SP
    SP.RELAXED = True        # the scope's shells were built and gated with the relaxed pass (A1-A5 pass)
    bl.reset_scene()
    col = bl.collection("SM_Att_Scope_LongRange_Parts")
    res, objs = {}, []
    for p in SC.all_parts():
        ob, rep = p.build(col)
        res[p.name] = rep
        objs.append(ob)
        print(f"[{CODE}] scope part {p.name}: tris {rep.get('triangles')} shells {rep.get('shells')} boundary {rep.get('boundary_edges')}")
    e = bpy.data.objects.new("Mount", None)
    e.location = [float(v) for v in (SC.MOUNT - GRIP) / 1000.0]
    col.objects.link(e)
    if "--no-save" not in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(BLEND).parent / "Att_Scope_LongRange.blend"))
    bl.export_npz(objs, SCRATCH / "scope_tris.npz", GRIP, [o.name for o in objs])
    (SCRATCH / "scope_build_report.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"[{CODE}] scope total tris", sum(r.get("triangles", 0) for r in res.values()))


if __name__ == "__main__":
    assert_lock()
    st = arg("--stage", "form")
    {"blockout": stage_blockout, "form": stage_form, "scope": stage_scope}[st]()
