"""Place the round-1 sword (snapshot game blend, LOD0-2) in the sheath frame exactly as the r1 fit did (fit.json R,t)
and save its vertices + triangles (mm) for the mouth-clearance check."""
import bpy, numpy as np, json, os
SN = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/lookmatch/r1_snapshot_interrupted"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
fit = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sheath_build/fit/fit.json"))
R = np.array(fit["R"]); t = np.array(fit["t_mm"])
with bpy.data.libraries.load(SN + "/SnowFlower_Game_v4.blend") as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("SM_SnowFlower_LOD")]
zm = -187.551
res = {"R": R.tolist(), "t_mm": t.tolist(), "source": SN + "/SnowFlower_Game_v4.blend"}
for o in dst.objects:
    me = o.data
    V = np.array([v.co[:] for v in me.vertices])
    Vw = np.array(o.matrix_world); V = (np.c_[V, np.ones(len(V))] @ Vw.T)[:, :3] * 1000.0
    S = V @ R.T + t
    me.calc_loop_triangles()
    T = np.array([lt.vertices[:] for lt in me.loop_triangles], int)
    np.savez(OUT + f"/sword_{o.name}_S.npz", V=S, T=T)
    below = S[S[:, 2] > zm]
    sl = []
    for z0 in np.arange(zm, zm + 30, 2.0):
        s = below[(below[:, 2] >= z0) & (below[:, 2] < z0 + 2)]
        if len(s):
            sl.append([round(float(z0), 1), round(float(s[:, 0].min()), 2), round(float(s[:, 0].max()), 2), round(float(np.abs(s[:, 1]).max()), 2)])
    ab = S[(S[:, 2] <= zm) & (S[:, 2] > zm - 6)]
    print(o.name, "verts", len(S), "lowest-above-mouth guard z", float(S[S[:,2] <= zm][:,2].max()) if (S[:,2]<=zm).any() else None)
    for r in sl[:8]: print("  slice z0,xmin,xmax,|y|max", r)
    res[o.name] = {"slices": sl, "guard_within_6mm_above": [ab[:, 0].min(), ab[:, 0].max(), ab[:, 1].min(), ab[:, 1].max()] if len(ab) else None}
json.dump(res, open(OUT + "/plug_slices.json", "w"), indent=1, default=float)
