"""Run Scripts/pipeline/garment_qa.qa_garment (read-only import) on the ORIGINAL skeletal LOD0 cloak placed
into a COPY of the locked MH fitting body. Also measures the cloak's clearance to the MH skin at rest.
Run on: WorkFiles/BlackCloak_Review/engineering/eng_FitBody_copy.blend (never saved).
Args: -- <cloak fbx> <out.json>
"""
import bpy, sys, json
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
fbx, out = argv[0], argv[1]
ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
sys.path.insert(0, ROOT + "/Scripts")
from pipeline import garment_qa as G

res = {"fitbody_file": bpy.data.filepath, "cloak_fbx": fbx}
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=fbx, use_anim=False)
new = [o for o in bpy.data.objects if o not in before]
meshes = [o for o in new if o.type == "MESH"]
res["imported"] = {o.name: o.type for o in new}

# 1) the real gate, pose tests disabled (the cloak is not on metahuman_base_skel, so the MH test poses cannot be
#    applied to its armature). Everything else runs as written.
G.POSES = {}
try:
    r = G.qa_garment([o.name for o in meshes], "cloak")
    failed = [c for c in r["checks"] if not c["passed"]]
    agg = {}
    for c in failed:
        agg.setdefault(c["name"], []).append(f'{c["object"]}: {c["detail"]}')
    res["garment_qa"] = {"passed": r["passed"], "failed": r["failed"], "metrics": r["metrics"],
                         "n_checks": len(r["checks"]), "n_failed": len(failed),
                         "failed_detail": {k: {"count": len(v), "examples": v[:3]} for k, v in agg.items()}}
except Exception as exc:
    import traceback
    res["garment_qa"] = {"error": repr(exc), "tb": traceback.format_exc()[-2000:]}

# 2) clearance of the original cloak to the MH skin at rest (body + head skin), all vertices
lock = G.load_base_lock()
fit = {role: bpy.data.objects.get(name) for role, name in lock["objects"].items()}
arm = bpy.data.objects.get("root")
if arm is not None:
    G.clear_pose(arm)
col = G.Collider([fit["body"], fit["head"]], [G.dominant_regions(fit["body"]), G.dominant_regions(fit["head"])])
per = {}
alld = []
allr = []
for o in meshes:
    coords, _ = G.evaluated_world(o)
    d, found, reg = col.signed(coords, max_distance=0.6)
    d = np.where(found, d, np.inf)
    alld.append(d); allr.append(reg)
    inside = d < -0.001
    per[o.name] = {"verts": len(d), "inside_gt_1mm": int(inside.sum()),
                   "deepest_cm": round(float(-d.min() * 100), 2) if len(d) else 0,
                   "closer_than_1cm_outside": int(((d >= 0) & (d < 0.01)).sum())}
d = np.concatenate(alld); reg = np.concatenate(allr)
res["clearance_rest"] = {
    "verts": int(len(d)),
    "inside_gt_1mm": int((d < -0.001).sum()),
    "inside_gt_1mm_excl_arms": int(((d < -0.001) & (reg != "arm")).sum()),
    "inside_gt_1cm": int((d < -0.01).sum()),
    "deepest_cm": round(float(-d[np.isfinite(d)].min() * 100), 2),
    "outside_0_to_1cm": int(((d >= 0) & (d < 0.01)).sum()),
    "outside_1_to_1_5cm": int(((d >= 0.01) & (d < 0.015)).sum()),
    "no_surface_within_60cm": int((~np.isfinite(d)).sum()),
    "inside_by_region": {str(k): int(((d < -0.001) & (reg == k)).sum()) for k in np.unique(reg)},
    "per_mesh": per,
}
# body proportions for context
bb = np.array([fit["body"].matrix_world @ v.co for v in fit["body"].data.vertices])
res["mh_body_bounds_cm"] = [(bb.min(0) * 100).round(1).tolist(), (bb.max(0) * 100).round(1).tolist()]
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print("GARMENT_GATE_DONE", res.get("garment_qa", {}).get("failed"), res["clearance_rest"]["inside_gt_1mm"])
