"""Senbon Unreal verifier - offline analysis (headless Blender 5.2, NumPy) of what Unreal produced.
  A. Unreal's re-export (roundtrip/*.fbx): LOD triangle counts; the imported UCX is convex (no point off its own hull)
     and equals the shipped UCX; every vertex of every LOD lies inside it.
  B. mip probes: the last mip of each full chain is uniform and equals the source mean; mip 3 correlates with an 8x box
     downsample of the source.
  C. distance visibility / flicker from passC2's mask frames; LOD picked by the engine at each distance.
  D. contact sheets (renders/sheet_*.png).
Run: blender -b --factory-startup --python sv_analyse.py
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify_fin")
EXP = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\Senbon")
R = HERE / "renders"
MD = HERE / "renders_mask"
out = {"roundtrip": {}, "mips": {}, "visibility": {}, "lod_pick": {}}
truth = json.loads((HERE / "truth_fbx.json").read_text())


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for im in list(bpy.data.images):
        bpy.data.images.remove(im)


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
    interior = len([g for g in r.get("geom_interior", []) if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.delete(bm, geom=[v for v in r.get("geom_interior", []) if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
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


# ---------------- A. roundtrip ----------------
for name in ["SM_Senbon_Needle", "SM_Senbon_Heavy"]:
    clear()
    bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / f"{name}_ue_roundtrip.fbx"))
    bpy.context.view_layer.update()
    objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    rec = {"objects": {k: {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons), "verts": len(o.data.vertices)}
                       for k, o in objs.items()}}
    ucx = sorted(k for k in objs if k.upper().startswith("UCX_"))
    rend = sorted((k for k in objs if not k.upper().startswith("UCX_")), key=lambda k: -rec["objects"][k]["tris"])
    rec["ucx_names"], rec["render_names"] = ucx, rend
    rec["roundtrip_lod_tris"] = [rec["objects"][k]["tris"] for k in rend]
    rec["truth_lod_tris"] = truth[name]["lod_tris"]
    V = {k: world_verts(objs[k]) for k in rend}
    tv = np.load(HERE / "truth" / f"{name}__{name}_LOD0.npy")
    v0 = V[rend[0]]
    rec["lod0_bounds_ue"] = [v0.min(0).round(4).tolist(), v0.max(0).round(4).tolist()]
    rec["lod0_bounds_truth"] = [tv.min(0).round(4).tolist(), tv.max(0).round(4).tolist()]
    S = np.load(HERE / "truth" / f"{name}__UCX_{name}_LOD0_00.npy")
    hulls = []
    planes_all = []
    for k in ucx:
        P = world_verts(objs[k])
        planes, interior, hv = hull_planes(P)
        N = np.array([p[0] for p in planes])
        D = np.array([p[1] for p in planes])
        off = np.abs(P @ N.T - D).min(1)
        best = None
        for flip in ((1, 1, 1), (1, -1, 1)):
            Q = P * np.array(flip)
            d1 = np.sqrt(((Q[:, None, :] - S[None, :, :]) ** 2).sum(-1)).min(1).max()
            d2 = np.sqrt(((S[:, None, :] - Q[None, :, :]) ** 2).sum(-1)).min(1).max()
            if best is None or max(d1, d2) < best[1]:
                best = (flip, float(max(d1, d2)))
        hulls.append({"name": k, "verts": len(P), "unique_verts": int(len(np.unique(P.round(5), axis=0))),
                      "hull_verts": hv, "interior_points": interior, "planes": len(planes),
                      "max_point_off_own_hull_cm": float(off.max()), "shipped_ucx_verts": len(S),
                      "hausdorff_vs_shipped_cm": best[1], "frame_flip_used": best[0]})
        planes_all.append((N, D))
    rec["hulls"] = hulls
    cont = {}
    for k in rend:
        worst = np.full(len(V[k]), np.inf)
        for N, D in planes_all:
            worst = np.minimum(worst, (V[k] @ N.T - D).max(1))
        cont[k] = {"verts": int(len(V[k])), "worst_outside_cm": float(worst.max()),
                   "outside_gt_0.001cm": int((worst > 0.001).sum())}
    rec["containment"] = cont
    # LOD0 vs shipped LOD0: nearest-neighbour both ways (frame flip allowed)
    best = None
    for flip in ((1, 1, 1), (1, -1, 1)):
        Q = v0 * np.array(flip)
        d1 = np.sqrt(((Q[:, None, :] - tv[None, :, :]) ** 2).sum(-1)).min(1).max()
        d2 = np.sqrt(((tv[:, None, :] - Q[None, :, :]) ** 2).sum(-1)).min(1).max()
        if best is None or max(d1, d2) < best[1]:
            best = (flip, float(max(d1, d2)))
    rec["lod0_vs_shipped_hausdorff_cm"] = best[1]
    # open boundary edges of Unreal's LOD0 (the needle's tip caps)
    me = objs[rend[0]].data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bnd = [e for e in bm.edges if e.is_boundary]
    rec["lod0_boundary_edges_after_weld"] = len(bnd)
    rec["lod0_boundary_edge_x_cm"] = sorted({round(float((objs[rend[0]].matrix_world @ e.verts[0].co).x) * 100, 4)
                                            for e in bnd})[:8]
    bm.free()
    out["roundtrip"][name] = rec


# ---------------- B. mips ----------------
def load_img(p, linear_from_srgb=False):
    img = bpy.data.images.load(str(p))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * img.channels, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, img.channels)[::-1].astype(np.float64)
    bpy.data.images.remove(img)
    if linear_from_srgb:
        a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a


srcs = {}
for st in ("Needle", "Heavy", "Heavy_Wrap"):
    srcs[f"{st}_BC"] = (EXP / "Textures" / f"T_Senbon_{st}_BC.png", True, 3)
    srcs[f"{st}_ORM"] = (EXP / "Textures" / f"T_Senbon_{st}_ORM.png", False, 3)
    srcs[f"{st}_N"] = (EXP / "Textures" / f"T_Senbon_{st}_N.png", False, 3)
srcs["Heavy_Wrap_Detail16"] = (EXP / "Textures" / "Recolour" / "T_Senbon_Heavy_Wrap_Detail16.png", False, 1)
for key, (png, lin, nch) in srcs.items():
    S = load_img(png, lin)[..., :nch]
    if key.endswith("_N"):
        S = S * 2 - 1
    h, w = S.shape[:2]
    last = 10 if "Wrap" in key else 11
    ds8 = S.reshape(h // 8, 8, w // 8, 8, nch).mean((1, 3))
    m3 = load_img(R / f"mip_{key}_3.exr")[..., :nch]
    ml = load_img(R / f"mip_{key}_{last}.exr")[..., :nch]
    if m3.shape[1] != ds8.shape[1]:
        ds8 = np.repeat(ds8, m3.shape[1] // ds8.shape[1], axis=1)
    if m3.shape[0] != ds8.shape[0]:
        ds8 = np.repeat(ds8, max(1, m3.shape[0] // ds8.shape[0]), axis=0)[:m3.shape[0]]
    corr = []
    for ch in range(nch if not key.endswith("_N") else 2):
        a, b = m3[..., ch].ravel(), ds8[..., ch].ravel()
        corr.append(round(float(np.corrcoef(a, b)[0, 1]), 4) if a.std() > 1e-6 and b.std() > 1e-6 else None)
    out["mips"][key] = {"last_mip": last, "last_mip_std": ml.reshape(-1, nch).std(0).round(6).tolist(),
                        "last_mip_value": ml.reshape(-1, nch).mean(0).round(4).tolist(),
                        "src_mean": S.reshape(-1, nch).mean(0).round(4).tolist(),
                        "mip3_corr": corr}

# ---------------- C. visibility ----------------
c2 = json.loads((HERE / "passC2.json").read_text())
W = 1920
XB = {"needle": (-6.5, 6.5), "heavy": (-9.3697, 7.6303)}


def lum(fname):
    a = load_img(MD / fname)
    return a[..., :3].max(-1)


# spike extent from its near frame (lit columns at 0.5 m, horizontal, raw j0)
for rec in c2["frames"]:
    if rec["mesh"] == "spike" and rec["orient"] == "h" and rec["distance_m"] == 0.5:
        m = lum(rec["raw"][0]) > 0.5
        cols = np.nonzero(m.any(0))[0]
        px = rec["px_cm"]
        XB["spike"] = (-(cols.max() + 0.5 - W / 2) * px, -(cols.min() - 0.5 - W / 2) * px)
out["spike_x_extent_cm_measured"] = [round(v, 3) for v in XB["spike"]]
vis = {}
lod_pick = {}
for rec in c2["frames"]:
    key, orient, dm, px = rec["mesh"], rec["orient"], rec["distance_m"], rec["px_cm"]
    x0, x1 = XB[key]
    ct = math.cos(math.radians(20.0)) if orient == "diag" else 1.0
    # screen column of model x: col = W/2 - x*ct/px (+X appears to the left)
    c_lo, c_hi = W / 2 - x1 * ct / px, W / 2 - x0 * ct / px
    span = c_hi - c_lo
    a, b = int(math.ceil(c_lo + 0.05 * span)), int(math.floor(c_hi - 0.05 * span))   # central 90 %
    raws = np.array([lum(f) for f in rec["raw"]])
    ldrs = np.array([lum(f) for f in rec["ldr"]])
    thr = 0.5 * max(float(raws.max()), 1e-6)
    lit = raws > thr
    counts = lit.sum((1, 2))
    cont = [float(fr[:, a:b + 1].any(0).mean()) for fr in lit]
    acc = (raws / max(float(raws.max()), 1e-6)).mean(0)          # temporal stand-in (0..1 coverage)
    acc_cont = float((acc[:, a:b + 1].max(0) >= 0.25).mean())
    acc_cov_col = acc[:, a:b + 1].sum(0)                            # integrated coverage per column, in px
    lthr = 0.5 * max(float(ldrs.max()), 1e-6)
    llit = ldrs > lthr
    lcont = [float(fr[:, a:b + 1].any(0).mean()) for fr in llit]
    v = {"px_mm": round(px * 10, 4), "expected_cols": [round(c_lo, 1), round(c_hi, 1)],
         "raw_lit_px_per_frame": counts.tolist(),
         "raw_flicker_min_over_max": round(float(counts.min() / max(counts.max(), 1)), 3),
         "raw_continuity_min": round(min(cont), 3), "raw_continuity_mean": round(float(np.mean(cont)), 3),
         "accum_continuity": round(acc_cont, 3),
         "accum_coverage_px_per_col_mean": round(float(acc_cov_col.mean()), 3),
         "accum_coverage_px_per_col_min": round(float(acc_cov_col.min()), 3),
         "ldr_continuity_min": round(min(lcont), 3), "ldr_lit_px_per_frame": llit.sum((1, 2)).tolist(),
         "raw_max_value": round(float(raws.max()), 4), "ldr_max_value": round(float(ldrs.max()), 4)}
    if rec["lod"]:
        auto = lum(rec["lod"]["auto"]) > thr
        diffs = {}
        for t in ("LOD0", "LOD1", "LOD2"):
            f = lum(rec["lod"][t]) > thr
            diffs[t] = int((auto ^ f).sum())
        pick = min(diffs, key=diffs.get)
        lod_pick.setdefault(key, {})[f"{dm:.2f}"] = {"picked": pick, "xor_px": diffs}
        # pop between neighbouring LODs at this distance (pixels that change)
        f = {t: lum(rec["lod"][t]) > thr for t in ("LOD0", "LOD1", "LOD2")}
        v["pop_px_LOD0_LOD1"] = int((f["LOD0"] ^ f["LOD1"]).sum())
        v["pop_px_LOD1_LOD2"] = int((f["LOD1"] ^ f["LOD2"]).sum())
        v["lit_px_LOD0_LOD1_LOD2"] = [int(f[t].sum()) for t in ("LOD0", "LOD1", "LOD2")]
    vis[f"{key}_{orient}_{dm:.2f}"] = v
out["visibility"] = vis
out["lod_pick"] = lod_pick


# ---------------- D. contact sheets ----------------
def save_png(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def crop(a, cy, cx, hh, hw, scale):
    c = a[max(cy - hh, 0):cy + hh, max(cx - hw, 0):cx + hw]
    return np.repeat(np.repeat(c, scale, 0), scale, 1)


rows = []
for key in ("needle", "heavy", "spike"):
    tiles = []
    for dm in ("0.500", "0.889", "2.540", "5.000"):
        a = load_img(R / f"dist_lit_{key}_{dm}m.png")[..., :3]
        d = float(dm) * 100
        px = 2 * d / W
        hw = int(min(110, 10.5 / px))
        t = crop(a, 540, 960, 12, hw, 1)
        t = np.repeat(np.repeat(t, max(1, 220 // max(t.shape[1], 1)), 0), max(1, 220 // max(t.shape[1], 1)), 1)
        canvas = np.zeros((120, 480, 3))
        h_, w_ = min(t.shape[0], 120), min(t.shape[1], 480)
        canvas[(120 - h_) // 2:(120 - h_) // 2 + h_, (480 - w_) // 2:(480 - w_) // 2 + w_] = t[:h_, :w_]
        canvas[:, -2:] = 0.3
        tiles.append(canvas)
    rows.append(np.concatenate(tiles, 1))
    rows.append(np.full((4, 1920, 3), 0.3))
save_png(np.concatenate(rows, 0), R / "sheet_dist_lit.png")
# mask frames at the switch distances: 8 raw jitters stacked + their mean, for needle / heavy / spike
for key in ("needle", "heavy", "spike"):
    blocks = []
    for dm in (0.86, 0.92, 2.45, 2.63):
        rec = next(r for r in c2["frames"] if r["mesh"] == key and r["orient"] == "h" and r["distance_m"] == dm)
        px = rec["px_cm"]
        hw = int(min(470, 10.0 / px))
        fr = [lum(f) for f in rec["raw"]]
        mx = max(max(float(f.max()) for f in fr), 1e-6)
        fr = [f / mx for f in fr]
        tiles = [crop(f, 540, 960, 4, hw, 2) for f in fr] + [crop(np.mean(fr, 0), 540, 960, 4, hw, 2)]
        b = np.concatenate([np.pad(t, ((1, 1), (0, 0)), constant_values=0.25) for t in tiles], 0)
        b = np.pad(b, ((6, 6), (0, max(0, 1880 - b.shape[1]))), constant_values=0.0)[:, :1880]
        blocks.append(np.dstack([b, b, b]))
    save_png(np.concatenate(blocks, 0), R / f"sheet_mask_{key}.png")
(HERE / "analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("SV_ANALYSE_DONE")
