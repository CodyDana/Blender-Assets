"""Which LOD vertices lie outside the single hull (shipped FBX and Unreal's re-export), by material and height.
    blender.exe -b --factory-startup --python bhv_hull_body.py"""
import json
from pathlib import Path
import bpy
import numpy as np
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v2")
SRC = {"shipped": Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\BlackHat\SM_BlackHat.fbx"),
       "unreal": HERE / "bhv_unreal_roundtrip.fbx"}
out = {}
for label, path in SRC.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    hull = next(o for n, o in objs.items() if n.upper().startswith("UCX"))
    def world(o):
        me = o.data
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3); mw = np.array(o.matrix_world)
        return (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3] * 100.0
    hv = world(hull); hm = hull.data; hm.calc_loop_triangles()
    tv = np.array([t.vertices[:] for t in hm.loop_triangles])
    P = hv[tv]; n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None]
    d = (n * P[:, 0]).sum(1); c = hv.mean(0); f = (n @ c - d) > 0; n[f] *= -1; d[f] *= -1
    rep = {"hull_vertices": int(len(hv)), "hull_z_range_cm": [float(hv[:, 2].min()), float(hv[:, 2].max())]}
    for name, o in sorted(objs.items()):
        if o is hull: continue
        v = world(o); s = (v @ n.T - d).max(1)
        me = o.data
        vmat = np.full(len(v), -1)
        for p in me.polygons:
            for vi in p.vertices: vmat[vi] = p.material_index if vmat[vi] < 0 else vmat[vi]
        mats = [sl.material.name if sl.material else str(i) for i, sl in enumerate(o.material_slots)]
        outm = s > 1e-3
        rec = {"points": int(len(v)), "outside": int(outm.sum()), "worst_cm": float(s.max())}
        for mi in sorted(set(vmat.tolist())):
            sel = vmat == mi
            key = mats[mi] if 0 <= mi < len(mats) else str(mi)
            o_ = outm & sel
            rec[key] = {"points": int(sel.sum()), "outside": int(o_.sum()),
                        "worst_cm": float(s[sel].max()),
                        "outside_z_range_cm": [float(v[o_, 2].min()), float(v[o_, 2].max())] if o_.any() else None}
        # anything outside that is ABOVE the hull floor (i.e. not the hanging tails)
        hi = outm & (v[:, 2] > rep["hull_z_range_cm"][0] + 0.5)
        rec["outside_above_hull_floor"] = int(hi.sum())
        rec["outside_above_hull_floor_worst_cm"] = float(s[hi].max()) if hi.any() else 0.0
        if hi.any():
            idx = np.argsort(-s[hi])[:8]
            rec["outside_above_floor_samples"] = [[*v[hi][i].round(3).tolist(), round(float(s[hi][i]), 4), int(vmat[hi][i])] for i in idx]
        # straw outside at all?
        rec["straw_outside"] = int((outm & (vmat == 0)).sum())
        rec["straw_worst_cm"] = float(s[vmat == 0].max())
        rep[name] = rec
    out[label] = rep
(HERE / "hull_body.json").write_text(json.dumps(out, indent=2))
print("BHV_HULL_BODY_DONE")
