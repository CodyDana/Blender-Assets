"""Diagnostic: LOD0 SURFACE (dense samples, not only vertices) vs the union of the hulls Unreal stored
(Unreal round-trip FBX shells), on the Unreal read-back LOD0 of both meshes."""
import bpy, bmesh, json, sys
import numpy as np
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Indep")
import kv_common as C
geo = json.loads((C.HERE / "kvB_geometry.json").read_text())


def import_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith("UCX_"):
            bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world)
            out[ob.name] = bm
    return out


def planes(pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    c = pts.mean(0); N = []; D = []
    for f in bm.faces:
        n = np.array(f.normal); d = n @ np.array(f.verts[0].co)
        if n @ c - d > 0: n, d = -n, -d
        N.append(n); D.append(d)
    return np.array(N), np.array(D)


res = {}
rng = np.random.default_rng(7)
for name, rt in (("SM_Katana", "ue_roundtrip_katana.fbx"), ("SM_Katana_Saya", "ue_roundtrip_saya.fbx")):
    bms = import_fbx(C.HERE / rt)
    HP = []
    for bm in bms.values():
        bm.verts.ensure_lookup_table()
        for comp in bmesh.ops.split_edges(bm, edges=[])["edges"] if False else [None]:
            pass
        # shells by linked faces
        seen = set()
        for f in bm.faces:
            if f.index in seen: continue
            stack = [f]; vs = set()
            while stack:
                g = stack.pop()
                if g.index in seen: continue
                seen.add(g.index)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen: stack.append(h)
                for v in g.verts: vs.add(v.index)
            HP.append(planes(np.array([tuple(bm.verts[i].co) for i in vs]) * 100.0))
    P = np.array(geo[name][0]["positions"]) * np.array([1, -1, 1])
    T = np.array(geo[name][0]["triangles"])[:, -3:]
    A, B_, Cc = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B_ - A, Cc - A), axis=1)
    n = 300000
    idx = rng.choice(len(T), size=n, p=area / area.sum()); u = rng.random(n); v = rng.random(n); f = u + v > 1; u[f] = 1 - u[f]; v[f] = 1 - v[f]
    S = A[idx] + (B_[idx] - A[idx]) * u[:, None] + (Cc[idx] - A[idx]) * v[:, None]
    out = np.full(n, np.inf)
    for N, D in HP:
        out = np.minimum(out, np.maximum((S @ N.T - D).max(1), 0))
    w = np.argsort(-out)[:5]
    res[name] = {"hull_shells": len(HP), "samples": n, "outside_gt_0.01mm": int((out > 1e-3).sum()),
                 "outside_frac": float((out > 1e-3).mean()), "max_outside_mm": float(out.max() * 10),
                 "outside_area_cm2_est": float((out > 1e-3).mean() * area.sum()), "area_cm2": float(area.sum()),
                 "worst_unreal_frame_cm": [[*(S[i] * np.array([1, -1, 1])).round(3).tolist(), round(float(out[i] * 10), 3)] for i in w]}
(C.HERE / "kv_diag_hullsurf.json").write_text(json.dumps(res, indent=1))
print("HULLSURF", json.dumps(res))
