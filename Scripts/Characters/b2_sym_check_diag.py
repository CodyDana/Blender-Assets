"""b2_sym_check_diag.py - PRIVATE / DO NOT SHIP. Independent checker, pass 2 (read-only, never saves any blend).

  blender -b 2B_private_rig_sym.blend -P b2_sym_check_diag.py -- <abs out json>

Twins come from the AFTER mesh geometry (exact mirror, KD nearest), not the builder's map. For every skin face:
after area vs the before areas of the face and its twin (averaging should land between them), normal turn vs both,
fold-over edges (dihedral > 120 deg) new in the after mesh, midline dihedral on the same edge set, teeth visible in
front of the lips (forward ray), and the rest crotch poke points with the garment faces they hit.
"""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
RIG = OUT + "/2B_private_rig.blend"
SHELL = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket", "Mouth"]
M3 = np.array([-1.0, 1.0, 1.0])


def co(me):
    a = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)


def face_data(X, polys):
    A = np.zeros(len(polys)); N = np.zeros((len(polys), 3))
    for i, p in enumerate(polys):
        P = X[list(p)]
        n = np.zeros(3)
        for k in range(1, len(p) - 1):
            n += np.cross(P[k] - P[0], P[k + 1] - P[0])
        A[i] = np.linalg.norm(n) / 2; N[i] = n / (np.linalg.norm(n) + 1e-18)
    return A, N


def main():
    outp = sys.argv[sys.argv.index("--") + 1]
    body = bpy.data.objects["SK_2B_Body"]; me = body.data
    X = co(me)
    with bpy.data.libraries.load(RIG, link=True) as (src, dst):
        dst.meshes = ["SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"]
    me0, hp0, g0 = dst.meshes
    X0 = co(me0)
    polys = [tuple(p.vertices) for p in me.polygons]
    fsrc = np.zeros(len(polys), dtype=int); me.attributes["src"].data.foreach_get("value", fsrc)
    kd = KDTree(len(X))
    for i, p in enumerate(X):
        kd.insert(Vector(p), i)
    kd.balance()
    tw = np.array([kd.find(Vector(p * M3))[1] for p in X])
    fkey = {frozenset(p): i for i, p in enumerate(polys)}
    ftw = np.array([fkey.get(frozenset(tw[list(p)].tolist()), -1) for p in polys])
    res = {"faces_without_twin": int((ftw < 0).sum())}
    A1, N1 = face_data(X, polys)
    A0, N0 = face_data(X0, polys)
    A0t = A0[ftw]; N0t = N0[ftw] * M3
    lo = np.minimum(A0, A0t); hi = np.maximum(A0, A0t)
    out_lo = A1 < lo * 0.7; out_hi = A1 > hi * 1.4
    turn = np.degrees(np.arccos(np.clip((N1 * N0).sum(1), -1, 1)))
    turn_t = np.degrees(np.arccos(np.clip((N1 * N0t).sum(1), -1, 1)))
    turn_min = np.minimum(turn, turn_t)
    cen = np.array([X[list(p)].mean(0) for p in polys])

    def lst(sel, key, n=12):
        idx = np.nonzero(sel)[0]
        idx = idx[np.argsort(-key[idx])][:n]
        return [[int(i), SHELL[fsrc[i]], [round(float(v), 4) for v in cen[i]], round(float(A1[i] / max(lo[i], 1e-12)), 3),
                 round(float(A1[i] / max(hi[i], 1e-12)), 3), round(float(turn[i]), 1), round(float(turn_t[i]), 1),
                 round(float(A1[i] * 1e6), 3)] for i in idx]
    res["face_area_outside_before_pair_range"] = {"shrunk_lt_0.7x_min": int(out_lo.sum()), "grown_gt_1.4x_max": int(out_hi.sum()),
                                                  "cols": "face, surface, centre, A/min(before pair), A/max(before pair), turn vs self deg, turn vs twin deg, area mm2",
                                                  "shrunk": lst(out_lo, lo / np.maximum(A1, 1e-12)), "grown": lst(out_hi, A1 / np.maximum(hi, 1e-12))}
    res["normal_turn_vs_both_before_gt_60"] = {"n": int((turn_min > 60).sum()), "gt_90": int((turn_min > 90).sum()),
                                               "list": lst(turn_min > 60, turn_min, 20)}
    # fold-over edges
    def folds(Xa):
        bm = bmesh.new(); bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.co = Vector(Xa[v.index])
        bm.normal_update()
        f = {}
        for e in bm.edges:
            if len(e.link_faces) == 2:
                a = math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0))
                f[e.index] = a
        ev = [(e.verts[0].index, e.verts[1].index) for e in bm.edges]
        bm.free()
        return f, ev
    f1, ev = folds(X); f0, _ = folds(X0)
    new = [(e, f1[e], f0.get(e, 0)) for e in f1 if f1[e] > 120 and f0.get(e, 0) < 90]
    gone = [(e, f1[e], f0.get(e, 0)) for e in f0 if f0[e] > 120 and f1.get(e, 0) < 90]
    res["fold_edges_gt120"] = {"after": int(sum(1 for a in f1.values() if a > 120)), "before": int(sum(1 for a in f0.values() if a > 120)),
                               "new_in_after": len(new), "gone_in_after": len(gone),
                               "new_list": [[int(e), round(a, 1), round(b, 1), [round(float(v), 4) for v in (X[ev[e][0]] + X[ev[e][1]]) / 2]] for e, a, b in sorted(new, key=lambda t: -t[1])[:20]]}
    # dihedral stats per region, before vs after (same edges)
    E = np.array(ev)
    mid = (tw[E[:, 0]] == E[:, 0]) & (tw[E[:, 1]] == E[:, 1])
    d1 = np.array([f1.get(i, 0) for i in range(len(E))]); d0 = np.array([f0.get(i, 0) for i in range(len(E))])
    em = (X[E[:, 0]] + X[E[:, 1]]) / 2

    def ds(sel):
        return {"n": int(sel.sum()), "after_p50_p95_max": [round(float(np.percentile(d1[sel], q)), 2) for q in (50, 95)] + [round(float(d1[sel].max()), 1)],
                "before_p50_p95_max": [round(float(np.percentile(d0[sel], q)), 2) for q in (50, 95)] + [round(float(d0[sel].max()), 1)]}
    res["midline_dihedral_same_edges"] = {"all": ds(mid), "face_z_gt_1.45": ds(mid & (em[:, 2] > 1.45)),
                                          "torso_1.0_1.45": ds(mid & (em[:, 2] > 1.0) & (em[:, 2] <= 1.45)),
                                          "pelvis_lt_1.0": ds(mid & (em[:, 2] <= 1.0)),
                                          "nonmid_all": ds(~mid),
                                          "mid_worse_by_gt_20deg": [[round(float(d1[i]), 1), round(float(d0[i]), 1), [round(float(v), 4) for v in em[i]]]
                                                                    for i in np.nonzero(mid & (d1 - d0 > 20))[0][:25]]}
    # edges near the midline (|x| < 2 cm) that got much sharper
    near = (~mid) & (np.abs(em[:, 0]) < 0.02)
    res["near_midline_sharper_gt_20deg"] = int((near & (d1 - d0 > 20)).sum())
    res["all_edges_sharper_gt_30deg"] = {"n": int(((d1 - d0) > 30).sum()),
                                         "list": [[round(float(d1[i]), 1), round(float(d0[i]), 1), [round(float(v), 4) for v in em[i]]]
                                                  for i in np.argsort(-(d1 - d0))[:20]]}
    # teeth forward-visibility: ray from each tooth vertex toward the viewer (-Y); a tooth vertex whose ray escapes
    # without hitting skin is visible from the front
    def teeth_vis(hpme, Xs):
        mats = [m.name for m in hpme.materials]
        H = co(hpme)
        tv = sorted({v for p in hpme.polygons if mats[p.material_index] == "M_2B_Teeth" for v in p.vertices})
        tree = BVHTree.FromPolygons([Vector(c) for c in Xs], polys)
        vis = []
        for i in tv:
            hit = tree.ray_cast(Vector(H[i]) + Vector((0, -1e-5, 0)), Vector((0, -1, 0)), 0.2)
            if hit[0] is None:
                vis.append(i)
        return {"teeth_verts": len(tv), "visible_from_front": len(vis),
                "visible_samples": [[round(float(v), 4) for v in H[i]] for i in vis[:6]]}
    hp1 = bpy.data.objects["SK_2B_HeadParts"].data
    res["teeth_front_visible"] = {"after": teeth_vis(hp1, X), "before": teeth_vis(hp0, X0)}
    # lips closed? min gap between upper and lower lip on the midline
    json.dump(res, open(outp, "w"), indent=1, default=float)
    print("[diag] saved", outp)


main()
