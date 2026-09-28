"""b2_sym_check_diag2.py - PRIVATE / DO NOT SHIP. Independent checker, pass 3 (read-only, never saves any blend).

  blender -b 2B_private_rig_sym.blend -P b2_sym_check_diag2.py -- <abs out json>

Volume loss from the mirror averaging: per limb segment, the mean radial distance of its skin (dominant bone) from
the bone axis, before L / before R / after; and where the shrunk faces (after area < 0.7 x min(before pair)) sit.
"""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
RIG = OUT + "/2B_private_rig.blend"
SHELL = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket", "Mouth"]
M3 = np.array([-1.0, 1.0, 1.0])
CHILD = {"upperarm": "lowerarm", "lowerarm": "hand", "hand": "middle_01", "thigh": "calf", "calf": "foot", "foot": "ball", "clavicle": "upperarm"}


def co(me):
    a = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)


def main():
    outp = sys.argv[sys.argv.index("--") + 1]
    body = bpy.data.objects["SK_2B_Body"]; me = body.data; arm = bpy.data.objects["root"]
    X = co(me)
    with bpy.data.libraries.load(RIG, link=True) as (src, dst):
        dst.meshes = ["SK_2B_Body"]; dst.objects = ["root"]
    me0 = dst.meshes[0]; arm0 = dst.objects[0].data
    X0 = co(me0)
    names = [b.name for b in arm.data.bones]
    gi = {g.index: names.index(g.name) for g in body.vertex_groups if g.name in names}
    W = np.zeros((len(X), len(names)))
    for v in me.vertices:
        for g in v.groups:
            if g.group in gi:
                W[v.index, gi[g.group]] = g.weight
    dom = W.argmax(1)
    res = {"girth": {}}
    for seg in ("upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "clavicle"):
        row = {}
        for s in ("l", "r"):
            for tag, Xs, A in (("before", X0, arm0), ("after", X, arm.data)):
                b = A.bones[f"{seg}_{s}"]
                h = np.array(b.head_local); t = np.array(A.bones[CHILD[seg] + "_" + s].head_local)
                ax = (t - h) / np.linalg.norm(t - h)
                sel = dom == names.index(f"{seg}_{s}")
                P = Xs[sel] - h
                along = P @ ax
                rad = np.linalg.norm(P - along[:, None] * ax, axis=1)
                row[f"{tag}_{s}_mean_radius_mm"] = round(float(rad.mean()) * 1000, 2)
                # sections: 5 bins along the bone
                L = np.linalg.norm(t - h)
                bins = []
                for k in range(5):
                    m = (along >= k * L / 5) & (along < (k + 1) * L / 5)
                    bins.append(round(float(rad[m].mean()) * 1000, 2) if m.any() else None)
                row[f"{tag}_{s}_sections_mm"] = bins
        res["girth"][seg] = row
    # skin volume (closed? use divergence estimate on the whole shell, sign-agnostic) before vs after
    polys = [tuple(p.vertices) for p in me.polygons]

    def vol(Xa):
        v = 0.0
        for p in polys:
            for k in range(1, len(p) - 1):
                v += np.dot(Xa[p[0]], np.cross(Xa[p[k]], Xa[p[k + 1]])) / 6
        return v
    res["signed_volume_l"] = {"before": round(vol(X0) * 1000, 4), "after": round(vol(X) * 1000, 4)}
    # where did the shrunk faces go
    kd = KDTree(len(X))
    for i, p in enumerate(X):
        kd.insert(Vector(p), i)
    kd.balance()
    tw = np.array([kd.find(Vector(p * M3))[1] for p in X])
    fkey = {frozenset(p): i for i, p in enumerate(polys)}
    ftw = np.array([fkey[frozenset(tw[list(p)].tolist())] for p in polys])

    def areas(Xa):
        A = np.zeros(len(polys))
        for i, p in enumerate(polys):
            P = Xa[list(p)]; n = np.zeros(3)
            for k in range(1, len(p) - 1):
                n += np.cross(P[k] - P[0], P[k + 1] - P[0])
            A[i] = np.linalg.norm(n) / 2
        return A
    A1 = areas(X); A0 = areas(X0)
    lo = np.minimum(A0, A0[ftw])
    shr = A1 < 0.7 * lo
    fdom = np.array([np.bincount(dom[list(p)]).argmax() for p in polys])
    cnt = {}
    for i in np.nonzero(shr)[0]:
        k = names[fdom[i]]
        cnt[k] = cnt.get(k, 0) + 1
    res["shrunk_faces_by_bone"] = dict(sorted(cnt.items(), key=lambda kv: -kv[1]))
    res["total_area_m2"] = {"before": round(float(A0.sum()), 5), "after": round(float(A1.sum()), 5)}
    json.dump(res, open(outp, "w"), indent=1)
    print("[diag2] saved", outp)


main()
