"""Skeptic geometry checks on a COPY of the Blender capture scene (never saved)."""
import bpy, bmesh, json, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/verify/vf_scene.json"
dg = bpy.context.evaluated_depsgraph_get()
R = {}
def eval_world(name):
    o = bpy.data.objects[name]
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    mw = o.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [(list(p.vertices), p.material_index) for p in me.polygons]
    oe.to_mesh_clear()
    return verts, polys
cv, cp = eval_world("SKM_BlackCloak_MH")
bv, bp = eval_world("FIT_MH_PlayerDefault_Body")
hv, hp = eval_world("FIT_MH_PlayerDefault_Head")
pv, pp = eval_world("FIT_MH_PlayerDefault_HeadParts")

def tris_of(polys):
    t = []
    for vs, _ in polys:
        for i in range(1, len(vs) - 1): t.append((vs[0], vs[i], vs[i + 1]))
    return t
body_tree = BVHTree.FromPolygons(bv, [p for p, _ in bp])
head_tree = BVHTree.FromPolygons(hv, [p for p, _ in hp])
# signed distance by closest point + face normal
inside = []; under1 = 0
for i, v in enumerate(cv):
    best = None
    for tree in (body_tree, head_tree):
        loc, nrm, idx, d = tree.find_nearest(v, 0.5)
        if loc is not None and (best is None or d < best[0]): best = (d, loc, nrm)
    if best is None: continue
    d, loc, nrm = best
    s = d if (v - loc).dot(nrm) >= 0 else -d
    if s < -0.001: inside.append((round(s * 100, 2), [round(x, 3) for x in v]))
    if s < 0.01: under1 += 1
inside.sort()
R["rest_inside_gt_1mm"] = len(inside)
R["rest_inside_gt_1cm"] = sum(1 for s, _ in inside if s < -1.0)
R["rest_deepest"] = inside[:5]
R["rest_under_1cm"] = under1
# z extents
zs = [v.z for v in cv]
R["cloak_z_cm"] = [round(min(zs) * 100, 1), round(max(zs) * 100, 1)]
front = [v for v in cv if abs(v.x) < 0.05 and v.y < -0.05]
R["cowl_front_centre_zmax_cm"] = round(max(v.z for v in front) * 100, 1) if front else None
# eyes: HeadParts faces with material index 2/3
eye_vs = set()
for vs, mi in pp:
    if mi in (2, 3): eye_vs.update(vs)
if eye_vs:
    ez = [pv[i].z for i in eye_vs]
    R["eye_z_cm_min_mean_max"] = [round(min(ez) * 100, 1), round(sum(ez) / len(ez) * 100, 1), round(max(ez) * 100, 1)]
nose = min((v for v in hv if abs(v.x) < 0.01), key=lambda v: v.y)
R["nose_tip_cm"] = [round(nose.z * 100, 1), round(nose.y * 100, 1)]
R["head_top_cm"] = round(max(v.z for v in hv) * 100, 1)
R["body_min_z_cm"] = round(min(v.z for v in bv) * 100, 1)
# per slot bbox + tri counts + sliver tris
slots = {}
for vs, mi in cp:
    slots.setdefault(mi, []).append(vs)
for mi, faces in slots.items():
    ids = set(i for f in faces for i in f)
    xs = [cv[i].x for i in ids]; ys = [cv[i].y for i in ids]; zz = [cv[i].z for i in ids]
    ntri = sum(len(f) - 2 for f in faces)
    sliver = 0
    for f in faces:
        for k in range(1, len(f) - 1):
            a, b, c = cv[f[0]], cv[f[k]], cv[f[k + 1]]
            angs = []
            for p, q, r in ((a, b, c), (b, c, a), (c, a, b)):
                u = q - p; w = r - p
                if u.length < 1e-9 or w.length < 1e-9: angs.append(0); continue
                angs.append(math.degrees(u.angle(w)))
            if min(angs) < 5: sliver += 1
    slots[mi] = dict(tris=ntri, verts=len(ids), sliver_lt5deg=sliver,
                     size_cm=[round((max(xs) - min(xs)) * 100, 1), round((max(ys) - min(ys)) * 100, 1), round((max(zz) - min(zz)) * 100, 1)],
                     centre_cm=[round((max(xs) + min(xs)) * 50, 1), round((max(ys) + min(ys)) * 50, 1), round((max(zz) + min(zz)) * 50, 1)],
                     zmin_cm=round(min(zz) * 100, 1))
R["slots"] = {str(k): v for k, v in slots.items()}
# self intersections in the sim slot (0), excluding pairs that share a vertex
sim_faces = [f for f in slots and [vs for vs, mi in cp if mi == 0]]
tree = BVHTree.FromPolygons(cv, sim_faces, all_triangles=False)
pairs = tree.overlap(tree)
real = 0
for a, b in pairs:
    if a >= b: continue
    if set(sim_faces[a]) & set(sim_faces[b]): continue
    real += 1
R["sim_self_intersecting_pairs_nonadjacent"] = real
# all wool (slots 0+1) together
wool = [vs for vs, mi in cp if mi in (0, 1)]
t2 = BVHTree.FromPolygons(cv, wool)
real2 = 0
for a, b in t2.overlap(t2):
    if a >= b: continue
    if set(wool[a]) & set(wool[b]): continue
    real2 += 1
R["wool_all_self_intersecting_pairs_nonadjacent"] = real2
# hem clearance above floor for the lowest strips: lowest z per 10 cm x-bin, front half
bins = {}
for v in cv:
    if v.y < 0.0:
        k = int(math.floor(v.x * 10))
        bins[k] = min(bins.get(k, 9), v.z)
R["front_lowest_z_cm_by_10cm_x"] = {str(k / 10): round(z * 100, 1) for k, z in sorted(bins.items())}
json.dump(R, open(OUT, "w"), indent=1)
print("VF_SCENE_DONE")
