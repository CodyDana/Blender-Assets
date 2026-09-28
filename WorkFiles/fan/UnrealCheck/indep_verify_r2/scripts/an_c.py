import bpy, json, sys, os
import numpy as np
D = sys.argv[sys.argv.index("--") + 1]
out = {}
# ---------------- per-LOD triangles of the meshes exported back out of Unreal
for n in ("SK_Fan", "SK_Fan_Tassel"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=D + f"/ueout/export/{n}_from_ue.fbx")
    r = {}
    for o in bpy.data.objects:
        if o.type == "MESH":
            me = o.data
            me.calc_loop_triangles()
            per = {}
            for t in me.loop_triangles:
                m = me.materials[t.material_index].name if me.materials and me.materials[t.material_index] else None
                per[m] = per.get(m, 0) + 1
            r[o.name] = {"tris": len(me.loop_triangles), "verts": len(me.vertices), "per_material": per,
                         "vgroups": len(o.vertex_groups), "parent": o.parent.name if o.parent else None}
        elif o.type == "EMPTY":
            r[o.name] = {"empty": True}
        elif o.type == "ARMATURE":
            r[o.name] = {"armature_bones": len(o.data.bones)}
    out[n] = r
# ---------------- base colour: tint law vs baked BC, segmented by the debug colours


def load(p):
    im = bpy.data.images.load(p)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return a


bpy.ops.wm.read_factory_settings(use_empty=True)
R = D + "/ueout/renders_c/"
dbg = load(R + "dbg_SCS_BASE_COLOR.exr")
tint = load(R + "tint_SCS_BASE_COLOR.exr")
bc = load(R + "bc_SCS_BASE_COLOR.exr")
col = {"leaf": (0.55, 0.62, 0.75), "sticks": (0.75, 0.35, 0.08), "rivet": (0.9, 0.9, 0.9), "tassel": (0.1, 0.6, 0.2)}
res = {"dbg_px_sample": dbg[384, 384].tolist()}
for part, c in col.items():
    d = np.abs(dbg[..., :3] - np.array(c)).max(-1)
    m = d < 0.03
    # erode by one pixel to avoid edges
    e = m.copy()
    e[1:, :] &= m[:-1, :]; e[:-1, :] &= m[1:, :]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
    if e.sum() < 10:
        res[part] = {"px": int(e.sum())}
        continue
    t = tint[e][:, :3]; b = bc[e][:, :3]
    res[part] = {"px": int(e.sum()), "tint_mean": t.mean(0).round(5).tolist(), "bc_mean": b.mean(0).round(5).tolist(),
                 "mean_ratio": (t.mean(0) / np.maximum(b.mean(0), 1e-9)).round(4).tolist(),
                 "tint_p10_p90": [np.percentile(t.mean(1), 10).round(5), np.percentile(t.mean(1), 90).round(5)],
                 "bc_p10_p90": [np.percentile(b.mean(1), 10).round(5), np.percentile(b.mean(1), 90).round(5)],
                 "abs_diff_p95": float(np.percentile(np.abs(t - b).max(1), 95))}
out["base_colour_tint_vs_bc"] = res
json.dump(out, open(D + "/an_c.json", "w"), indent=1, default=float)
print("AN_C_DONE")
print(json.dumps(out, indent=1, default=float))
