"""Offline analysis (headless Blender 5.2, NumPy) of what Unreal produced:
  A. the Unreal re-export (roundtrip/*.fbx): each imported UCX hull must be convex (no vertex off its own convex hull)
     and equal the shipped UCX; every LOD0 vertex must lie inside the union of hulls (worst outside distance);
     LOD triangle counts again.
  B. mip probes (EXR): mip 11 uniform and equal to the texture mean; mip 3 correlates with an 8x box downsample.
  C. render pixel checks: parts-at-sockets vs assembled (same camera), LOD renders non-empty, coverage.
"""
import json
from pathlib import Path

import bmesh
import bpy
import numpy as np

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealVerify_claude")
EXP = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\Flashbang")
R = HERE / "renders"
out = {"roundtrip": {}, "mips": {}, "renders": {}}


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def world_verts(o):
    me = o.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    return (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3] * 100.0


def hull_planes(pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    r = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    interior = len(r.get("geom_interior", []))
    for g in r.get("geom_interior", []) + r.get("geom_unused", []):
        pass
    bmesh.ops.delete(bm, geom=[v for v in r.get("geom_interior", []) if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    planes = []
    for f in bm.faces:
        n = np.array(f.normal)
        if np.linalg.norm(n) < 0.5:
            continue
        planes.append((n, float(np.dot(n, np.array(f.verts[0].co)))))
    hv = len(bm.verts)
    bm.free()
    return planes, interior, hv


truth = json.loads((HERE / "truth_fbx.json").read_text())
for name in ["SM_Flashbang", "SM_Flashbang_Body", "SM_Flashbang_PullRing", "SM_Flashbang_Lever"]:
    clear()
    bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / f"{name}_ue_roundtrip.fbx"))
    bpy.context.view_layer.update()
    objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    rec = {"objects": {k: {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons), "verts": len(o.data.vertices)}
                       for k, o in objs.items()}}
    ucx = sorted(k for k in objs if k.upper().startswith("UCX_"))
    rend = [k for k in objs if not k.upper().startswith("UCX_")]
    rec["ucx_names"] = ucx
    rec["render_names"] = rend
    # LOD0 = the render mesh with the most triangles
    lod0 = max(rend, key=lambda k: rec["objects"][k]["tris"])
    V = world_verts(objs[lod0])
    tv = np.load(HERE / f"truth_{name}__{name}_LOD0.npy")
    rec["lod0_bounds_ue_export"] = [V.min(0).round(4).tolist(), V.max(0).round(4).tolist()]
    rec["lod0_bounds_truth"] = [tv.min(0).round(4).tolist(), tv.max(0).round(4).tolist()]
    hulls = []
    all_planes = []
    shipped = sorted(k for k in truth[name]["objects"] if k.startswith("UCX_"))
    comps = []
    for k in ucx:
        o = objs[k]
        Wv = world_verts(o)
        # Unreal writes every convex element into ONE UCX mesh: split it into connected components (one per hull)
        parent = list(range(len(Wv)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for e in o.data.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b:
                parent[a] = b
        roots = {}
        for i in range(len(Wv)):
            roots.setdefault(find(i), []).append(i)
        for j, idx in enumerate(sorted(roots.values(), key=lambda v: min(v))):
            comps.append((f"{k}#{j}", Wv[idx]))
    rec["hull_components"] = len(comps)
    for i, (k, P) in enumerate(comps):
        planes, interior, hv = hull_planes(P)
        # distance of each point to its own hull surface (0 for a convex point set)
        N = np.array([p[0] for p in planes])
        D = np.array([p[1] for p in planes])
        sd = P @ N.T - D  # <= 0 inside
        on_hull = np.abs(sd).min(1)
        h = {"name": k, "verts": len(P), "hull_verts": hv, "interior_points": interior,
             "max_point_off_hull_cm": float(on_hull.max()), "planes": len(planes)}
        # compare with shipped UCX (nearest-neighbour both ways), matched by order
        best = None
        for sk in shipped:
            S = np.load(HERE / f"truth_{name}__{sk}.npy")
            d1 = np.sqrt(((P[:, None, :] - S[None, :, :]) ** 2).sum(-1)).min(1).max()
            d2 = np.sqrt(((S[:, None, :] - P[None, :, :]) ** 2).sum(-1)).min(1).max()
            if best is None or max(d1, d2) < best[1]:
                best = (sk, float(max(d1, d2)))
        h["matches_shipped"] = best[0]
        h["hausdorff_vs_shipped_cm"] = best[1]
        hulls.append(h)
        all_planes.append((N, D))
    rec["hulls"] = hulls
    # containment of LOD0 in the union of hulls (Unreal's hulls)
    worst_each = np.full(len(V), np.inf)
    for N, D in all_planes:
        worst_each = np.minimum(worst_each, (V @ N.T - D).max(1))
    rec["lod0_verts"] = int(len(V))
    rec["lod0_outside_count_gt_0.01cm"] = int((worst_each > 0.01).sum())
    rec["lod0_worst_outside_cm"] = float(worst_each.max())
    rec["lod0_worst_vertex"] = V[int(worst_each.argmax())].round(4).tolist()
    out["roundtrip"][name] = rec


# ---------------- mips ----------------
def load_exr(p):
    img = bpy.data.images.load(str(p))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1]


def load_png(p, linear_from_srgb=False):
    img = bpy.data.images.load(str(p))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * img.channels, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, img.channels)[::-1].astype(np.float64)
    if linear_from_srgb:
        a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a


src = {"BC": (EXP / "Textures/T_Flashbang_BC.png", True, 3), "ORM": (EXP / "Textures/T_Flashbang_ORM.png", False, 3),
       "N": (EXP / "Textures/T_Flashbang_N.png", False, 3),
       "Paint_Detail": (EXP / "Textures/T_Flashbang_Paint_Detail.png", True, 1),
       "Paint_Detail16": (EXP / "Textures/Recolour/T_Flashbang_Paint_Detail16.png", False, 1)}
for key, (png, lin, nch) in src.items():
    S = load_png(png, lin)[..., :nch]
    if key == "N":  # engine returns the reconstructed normal in [-1,1]; DirectX green as stored (no flip)
        S = S * 2 - 1
    ds8 = S.reshape(256, 8, 256, 8, nch).mean((1, 3))
    m3 = load_exr(R / f"mip_{key}_3.exr")[..., :nch].astype(np.float64)
    m11 = load_exr(R / f"mip_{key}_11.exr")[..., :nch].astype(np.float64)
    c = []
    for ch in range(nch if key != "N" else 2):
        a, b = m3[..., ch].ravel(), ds8[..., ch].ravel()
        c.append(float(np.corrcoef(a, b)[0, 1]) if a.std() > 1e-6 and b.std() > 1e-6 else None)
    out["mips"][key] = {
        "mip3_corr_per_channel": c,
        "mip3_mean": m3.reshape(-1, nch).mean(0).round(4).tolist(), "src_mean": S.reshape(-1, nch).mean(0).round(4).tolist(),
        "mip11_std": m11.reshape(-1, nch).std(0).round(6).tolist(),
        "mip11_value": m11.reshape(-1, nch).mean(0).round(4).tolist(),
        "mip3_std": m3.reshape(-1, nch).std(0).round(4).tolist()}

# ---------------- renders ----------------
def rgb(name):
    return load_png(R / f"{name}.png")[..., :3]


bg_thr = 0.02
for view in ("three_q", "ring_front", "lever_side", "fuze_close"):
    a, b = rgb(f"asm_look_{view}"), rgb(f"parts_look_{view}")
    d = np.abs(a - b).max(-1)
    dimg = bpy.data.images.new(f"diff_{view}", d.shape[1], d.shape[0])
    amp = np.clip(d * 8, 0, 1)[::-1]
    dimg.pixels.foreach_set(np.dstack([amp, amp, amp, np.ones_like(amp)]).astype(np.float32).ravel())
    dimg.filepath_raw = str(HERE / f"diff_parts_vs_asm_{view}_x8.png")
    dimg.file_format = "PNG"
    dimg.save()
    ma, mb = a.max(-1) > bg_thr, b.max(-1) > bg_thr
    out["renders"][f"parts_vs_asm_{view}"] = {
        "max_abs_diff_8bit": float(d.max() * 255), "pixels_diff_gt_2of255": int((d > 2 / 255).sum()),
        "mask_iou": float((ma & mb).sum() / max((ma | mb).sum(), 1))}
for n in sorted(p.stem for p in R.glob("*.png")):
    a = rgb(n)
    m = a.max(-1) > bg_thr
    ys, xs = np.nonzero(m)
    out["renders"].setdefault("coverage", {})[n] = {
        "fg_frac": round(float(m.mean()), 4),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None,
        "touches_edge": bool(len(xs) and (xs.min() == 0 or ys.min() == 0 or xs.max() == a.shape[1] - 1
                                           or ys.max() == a.shape[0] - 1)),
        "fg_mean_8bit": (a[m].mean(0) * 255).round(1).tolist() if m.any() else None}
for view in ("three_q", "ring_front"):
    a0 = rgb(f"asm_look_{view}")
    for lod in (1, 2):
        b = rgb(f"asm_look_{view}_LOD{lod}")
        ma, mb = a0.max(-1) > bg_thr, b.max(-1) > bg_thr
        out["renders"][f"lod{lod}_vs_lod0_{view}"] = {"mask_iou": float((ma & mb).sum() / max((ma | mb).sum(), 1)),
                                                      "mean_abs_diff_8bit": float(np.abs(a0 - b).mean() * 255)}
(HERE / "analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("UV_ANALYSE_DONE")
