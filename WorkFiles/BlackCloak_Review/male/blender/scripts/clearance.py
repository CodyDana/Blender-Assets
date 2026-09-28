"""Cloak-vs-body interpenetration at the game's start shape (rest) and with the arms posed down (arms only; cloak is spine-only).
Counts cloak vertices >1 mm inside the body/head skin, split by the body region of the nearest skin face."""
import sys, os, json, bpy, bmesh
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from mathutils.bvhtree import BVHTree

arm = bpy.data.objects["root"]; body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]; head = bpy.data.objects["FIT_MH_PlayerDefault_Head"]
cl = cloak()
names = {g.index: g.name for g in body.vertex_groups}
def region_of_vertex(v):
    g = max(v.groups, key=lambda gg: gg.weight, default=None)
    n = names.get(g.group, "") if g else ""
    if any(t in n for t in ("thigh", "calf", "foot", "ball", "toe")): return "legs"
    if any(t in n for t in ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")): return "arms"
    if any(t in n for t in ("neck", "head")): return "neck_head"
    return "torso"
vreg = [region_of_vertex(v) for v in body.data.vertices]

def world_mesh(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh()
    verts = [o.matrix_world @ v.co for v in m.vertices]; polys = [tuple(p.vertices) for p in m.polygons]
    e.to_mesh_clear(); return verts, polys

def measure(tag):
    bpy.context.view_layer.update()
    bv, bp = world_mesh(body); hv, hp = world_mesh(head)
    off = len(bv)
    allv = bv + hv; allp = bp + [tuple(i + off for i in p) for p in hp]
    preg = [vreg[p[0]] for p in bp] + ["neck_head"] * len(hp)
    bm = bmesh.new()
    for v in allv: bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    for p in allp:
        try: bm.faces.new([bm.verts[i] for i in p])
        except ValueError: pass
    bm.faces.ensure_lookup_table(); bm.normal_update()
    # face index order in bm == allp order only if no failures; map through a lookup of first vertex instead
    tree = BVHTree.FromBMesh(bm)
    cv, _ = world_mesh(cl)
    res = {"inside_gt_1mm": {}, "inside_gt_1cm": {}, "deepest_cm": {}, "under_1cm_clearance": {}}
    for p in cv:
        loc, nrm, idx, d = tree.find_nearest(p, 0.3)
        if loc is None: continue
        f = bm.faces[idx]; r = vreg[f.verts[0].index] if f.verts[0].index < off else "neck_head"
        sd = d if (p - loc).dot(f.normal) >= 0 else -d
        if sd < 0.01: res["under_1cm_clearance"][r] = res["under_1cm_clearance"].get(r, 0) + 1
        if sd < -0.001:
            res["inside_gt_1mm"][r] = res["inside_gt_1mm"].get(r, 0) + 1
            res["deepest_cm"][r] = min(res["deepest_cm"].get(r, 0), sd * 100)
        if sd < -0.01: res["inside_gt_1cm"][r] = res["inside_gt_1cm"].get(r, 0) + 1
    bm.free()
    # body-vs-cloak: body vertices of each region that are OUTSIDE every cloak layer when seen from the front is a render
    # question (see renders/*_mask.png); here count arm vertices whose segment to the torso axis crosses the cloak surface
    return res

out = {"cloak_verts": len(cl.data.vertices), "rest": measure("rest")}
out["arm_rotation_deg"] = pose_arms_down(arm)
out["down"] = measure("down")
json.dump(out, open(D + "logs/clearance_by_region.json", "w"), indent=1)
print("CLEAR", json.dumps(out))
