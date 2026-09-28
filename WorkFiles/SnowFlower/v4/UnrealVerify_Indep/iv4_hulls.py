"""(1) Unreal's own FBX export merges every convex element into ONE UCX node, so compare the UNION of hull points
(shipped FBX UCX_* nodes vs Unreal round trip) by nearest-neighbour distance both ways.
(2) Locate the sword-LOD0 / sheath-LOD0 surface samples that failed the cavity test in iv3 (depth past the mouth plane).
"""
import bpy, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep")
EXP = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\SnowFlower\v4")
res = {}


def ucx_points(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    pts, names = [], []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith("UCX_"):
            mw = np.array(ob.matrix_world)
            co = np.array([tuple(v.co) for v in ob.data.vertices])
            pts.append(co @ mw[:3, :3].T + mw[:3, 3]); names.append(ob.name)
    return np.concatenate(pts), names


for tag, shipped, rt in (("sword", EXP / "SM_SnowFlower.fbx", HERE / "ue_roundtrip_sword.fbx"),
                         ("sheath", EXP / "SM_SnowFlower_Sheath.fbx", HERE / "ue_roundtrip_sheath.fbx")):
    A, na = ucx_points(shipped)
    Bp, nb = ucx_points(rt)
    d = np.sqrt(((A[:, None] - Bp[None]) ** 2).sum(-1))
    res[tag] = {"shipped_nodes": na, "roundtrip_nodes": nb, "shipped_points": len(A), "roundtrip_points": len(Bp),
                "max_nn_shipped_to_rt_mm": float(d.min(1).max() * 1000), "max_nn_rt_to_shipped_mm": float(d.min(0).max() * 1000),
                "bbox_shipped_m": [A.min(0).round(5).tolist(), A.max(0).round(5).tolist()],
                "bbox_roundtrip_m": [Bp.min(0).round(5).tolist(), Bp.max(0).round(5).tolist()]}

# (2) failed samples
geo = json.loads((HERE / "ivB_geometry.json").read_text())
B = json.loads((HERE / "ivB_verify.json").read_text())
att = B["attach"]; bas = att["sword_to_sheath_basis"]
o = np.array(bas["o"]); M = np.stack([np.array(bas[k]) - o for k in "xyz"], axis=1)
mp = np.array(att["mouth_socket"]["t"]); mn = np.array(att["mouth_socket"]["z_axis"]); mn /= np.linalg.norm(mn)
def arr(l):
    return np.array(l["positions"]), np.array(l["triangles"])[:, -3:]
Pw, Tw = arr(geo["sword"][0]); Ps = Pw @ M.T + o
Ph, Th = arr(geo["sheath"][0])
tree = BVHTree.FromPolygons([tuple(p) for p in Ph], [tuple(t) for t in Th], all_triangles=True)
rng = np.random.default_rng(12345)
A_ = Ps[Tw[:, 0]]; B_ = Ps[Tw[:, 1]]; C_ = Ps[Tw[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(B_ - A_, C_ - A_), axis=1)
n = 200000
idx = rng.choice(len(Tw), size=n, p=area / area.sum()); u = rng.random(n); v = rng.random(n); f = u + v > 1; u[f] = 1 - u[f]; v[f] = 1 - v[f]
S = A_[idx] + (B_[idx] - A_[idx]) * u[:, None] + (C_[idx] - A_[idx]) * v[:, None]
dep = (S - mp) @ mn
S = S[dep > 0]; dep = dep[dep > 0]
def hits(p, d):
    c, org = 0, Vector(p)
    for _ in range(40):
        loc, _, _, dist = tree.ray_cast(org, Vector(d), 500)
        if loc is None: break
        c += 1; org = loc + Vector(d) * 1e-4
    return c
bad = []
for p, dp in zip(S, dep):
    hs = [hits(p, d) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))]
    if not all(h >= 1 and h % 2 == 0 for h in hs):
        bad.append({"p": p.round(4).tolist(), "depth_past_mouth_mm": float(dp * 10), "hits": hs, "above_sheath_top": bool(p[2] < -18.7551)})
res["lod0_samples_past_mouth"] = int(len(S))
res["lod0_failed_samples"] = len(bad)
res["lod0_failed_max_depth_past_mouth_mm"] = max((b["depth_past_mouth_mm"] for b in bad), default=None)
res["lod0_failed_all_above_sheath_rim"] = all(b["above_sheath_top"] for b in bad)
res["lod0_failed_examples"] = bad[:8]
(HERE / "iv4_hulls.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("IV4", json.dumps({k: v for k, v in res.items() if k != "lod0_failed_examples"}))
