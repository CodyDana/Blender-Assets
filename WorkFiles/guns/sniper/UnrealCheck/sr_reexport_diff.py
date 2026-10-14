"""SR01 W5: what the physics-envelope re-export changed (Blender headless). Compares every FBX of the W4b export (copied
to WorkFiles/guns/sniper/scratch/w5_pre/) with the re-exported Exports/Guns/SR01: per mesh object the vertex positions,
the triangles, every UV layer and the vertex groups (sorted, so the comparison does not depend on object order); per
action every F-curve sample. And the two sidecars as JSON with only the physics block allowed to differ.

    blender -b --factory-startup --python sr_reexport_diff.py
"""
import bpy, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_common as C  # noqa: E402
PRE = C.ROOT / "WorkFiles" / "guns" / "sniper" / "scratch" / "w5_pre"


def load(p):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(p))
    out = {}
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            me = ob.data
            me.calc_loop_triangles()
            V = np.array([tuple(ob.matrix_world @ v.co) for v in me.vertices])
            T = np.array([tuple(t.vertices) for t in me.loop_triangles])
            uv = {}
            for l in me.uv_layers:
                a = np.empty(len(me.loops) * 2)
                l.data.foreach_get("uv", a)
                uv[l.name] = a
            vg = sorted(g.name for g in ob.vertex_groups)
            out[ob.name] = {"V": V, "T": T, "uv": uv, "vg": vg}
    acts = {}
    for a in bpy.data.actions:
        cur = []
        for fc in getattr(a, "fcurves", []):
            cur.append((fc.data_path, fc.array_index, [tuple(k.co) for k in fc.keyframe_points]))
        acts[a.name] = sorted(cur)
    return out, acts


res = {}
for p in sorted(PRE.glob("*.fbx")):
    new = C.EXP / p.name
    a, aa = load(p)
    b, bb = load(new)
    r = {"objects_equal": sorted(a) == sorted(b)}
    dmax = 0.0
    same_topo = True
    for k in a:
        if k not in b:
            continue
        if a[k]["V"].shape != b[k]["V"].shape or a[k]["T"].shape != b[k]["T"].shape or not np.array_equal(a[k]["T"], b[k]["T"]):
            same_topo = False
            continue
        dmax = max(dmax, float(np.abs(a[k]["V"] - b[k]["V"]).max()) if len(a[k]["V"]) else 0.0)
        for ln in a[k]["uv"]:
            if ln in b[k]["uv"]:
                dmax = max(dmax, float(np.abs(a[k]["uv"][ln] - b[k]["uv"][ln]).max()))
        same_topo &= a[k]["vg"] == b[k]["vg"]
    r["topology_equal"] = same_topo
    r["max_abs_diff_positions_uv"] = dmax
    r["actions_equal"] = aa == bb
    res[p.name] = r
side = {}
for nm in ("SK_SR01.skeletal.json", "SM_SR01.sockets.json", "SM_SR01_Mag.sockets.json"):
    x = json.loads((PRE / nm).read_text())
    y = json.loads((C.EXP / nm).read_text())
    side[nm] = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
res["sidecar_keys_changed"] = side
(HERE / "sr_reexport_diff.json").write_text(json.dumps(res, indent=1))
print("REEXPORT_DIFF", json.dumps(res))
