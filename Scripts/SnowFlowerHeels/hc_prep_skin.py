"""Heels Unreal check: export the shipped heels + her lower legs as CPU-skinning data (Blender headless, READ ONLY).

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/hc_prep_skin.py

Nothing is saved. Positions are converted to Unreal component space (cm, y mirrored: ue = (x, -y, z) * 100), which is how
the FBX lands in Unreal (checked against the imported mesh bounds by the verify step). Writes
WorkFiles/SnowFlowerHeels/ue/skin_data.npz + skin_data.json (bone list, per-part vertex tags, weight stats).
"""
import json

import bpy
import numpy as np

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/skin_data"
BODY_MAX_Z_CM = 60.0
MAXINF = 8


def conv(co):
    a = np.array(co, dtype=np.float64).reshape(-1, 3) * 100.0
    a[:, 1] *= -1.0
    return a


def mesh_arrays(obj, bone_index, maxinf):
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    me.calc_loop_triangles()
    tris = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tris)
    tmat = np.empty(len(me.loop_triangles), dtype=np.int64)
    me.loop_triangles.foreach_get("material_index", tmat)
    gname = {g.index: g.name for g in obj.vertex_groups}
    idx = np.zeros((n, maxinf), dtype=np.int32)
    wts = np.zeros((n, maxinf), dtype=np.float64)
    ninf = np.zeros(n, dtype=np.int32)
    for v in me.vertices:
        ws = sorted(((g.weight, gname[g.group]) for g in v.groups if g.weight > 0 and gname.get(g.group) in bone_index),
                    reverse=True)
        ninf[v.index] = len(ws)
        ws = ws[:maxinf]
        tot = sum(w for w, _ in ws) or 1.0
        for k, (w, b) in enumerate(ws):
            idx[v.index, k] = bone_index[b]
            wts[v.index, k] = w / tot
    return conv(co), tris.reshape(-1, 3), tmat, idx, wts, ninf


arm = bpy.data.objects["root"]
bones = [b.name for b in arm.data.bones]
bone_index = {b: i for i, b in enumerate(bones)}
data, meta = {}, {"bones": bones, "parts": {}, "meshes": {}}
for lod, name in enumerate(["SK_SnowFlowerHeels", "SK_SnowFlowerHeels_LOD1", "SK_SnowFlowerHeels_LOD2"]):
    obj = bpy.data.objects[name]
    co, tris, tmat, idx, wts, ninf = mesh_arrays(obj, bone_index, 4)
    data["heel%d_co" % lod], data["heel%d_tris" % lod], data["heel%d_tmat" % lod] = co, tris, tmat
    data["heel%d_idx" % lod], data["heel%d_w" % lod] = idx, wts
    used = sorted({bones[i] for i, w in zip(idx.ravel(), wts.ravel()) if w > 0})
    raw = np.array([sum(g.weight for g in v.groups) for v in obj.data.vertices])
    meta["meshes"][name] = {"verts": len(co), "tris": len(tris), "max_influences": int(ninf.max()),
                            "influence_histogram": np.bincount(ninf).tolist(), "bones_used": used,
                            "raw_weight_sum_min": float(raw.min()), "raw_weight_sum_max": float(raw.max()),
                            "materials": [m.name for m in obj.data.materials],
                            "attributes": [a.name for a in obj.data.attributes],
                            "bbox_ue_cm": [co.min(0).tolist(), co.max(0).tolist()]}
body = bpy.data.objects["FIT_MH_PlayerFemale_Body"]
co, tris, tmat, idx, wts, ninf = mesh_arrays(body, bone_index, MAXINF)
keep_v = co[:, 2] < BODY_MAX_Z_CM
keep_t = keep_v[tris].all(1)
remap = -np.ones(len(co), dtype=np.int64)
remap[np.where(keep_v)[0]] = np.arange(keep_v.sum())
data["body_co"], data["body_tris"] = co[keep_v], remap[tris[keep_t]]
data["body_idx"], data["body_w"] = idx[keep_v], wts[keep_v]
meta["body"] = {"verts_total": len(co), "verts_kept": int(keep_v.sum()), "tris_kept": int(keep_t.sum()),
                "max_influences": int(ninf.max()), "cut_z_cm": BODY_MAX_Z_CM,
                "bones_used": sorted({bones[i] for i, w in zip(idx[keep_v].ravel(), wts[keep_v].ravel()) if w > 0})}
np.savez_compressed(OUT + ".npz", **data)
with open(OUT + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, indent=1)
print("HC_PREP done", {k: v.shape for k, v in data.items()})
