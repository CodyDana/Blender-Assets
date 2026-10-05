"""Magazine detail loop, isolated from the parallel part builders (they share Assets/Guns/AR01.blend, form_tris.npz
and scratch/detail/). Works on a SNAPSHOT of the form build in scratch/mag_detail/base/ and writes only to
scratch/mag_detail/ and review/detail/magazine/.

    # 1. rebuild the magazine into the snapshot (headless Blender; asserts the AR01 lock)
    blender -b scratch/mag_detail/base/AR01_base.blend --factory-startup --python Scripts/guns/rifle/parts/magazine_dev.py -- --build --tag r1_i1
    # 2. ROUGH LOOK crops at the solved close-up cameras + numbers (plain Python)
    py -3 -B Scripts/guns/rifle/parts/magazine_dev.py --render --tag r1_i1

Build writes scratch/mag_detail/AR01_mag_<tag>.blend, mag_<tag>_tris.npz (every object, base order) and
mag_<tag>_build.json (manifold, triangles, static intersections, contact gaps, L3 rib tips, L4 thickness / bottom,
mag_release sweep, a rock-path probe). Render writes review/detail/magazine/<tag>_{ours,pair,edges}_<panel>.png and
<tag>_crops.json, plus mag_<tag>_metrics.json (raw window IoU, own-frame IoU after a similarity fit, edge F, L2 part).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent                  # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
from rifle_common import ROOT, SCRATCH, REVIEW, GRIP, SPEC, TRACE  # noqa: E402

MD = SCRATCH / "mag_detail"
MAG_OBJS = ("magazine", "magazine_floor_plate")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


# --base <dir under scratch/mag_detail>: the snapshot whose object list / neighbours the build uses (round 1-2: base;
# detail round 2b: base2 = the integrated build of 2026-10-05 02:54)
BASE_NPZ = MD / arg("--base", "base") / "form_tris_base.npz"


# ======================================================================================== Blender: build + checks
def blender_build(tag):
    import bpy
    import numpy as np
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    from gunlib import bl, fit as F
    from gunlib.parts import BuildCtx
    import importlib
    from parts import magazine as M
    importlib.reload(M)
    probe = "--probe" in argv                    # checks only, on the opened blend as it is (e.g. the base)
    if not probe:
        for n in MAG_OBJS:
            ob = bpy.data.objects.get(n)
            if ob is not None:
                me = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if me.users == 0:
                    bpy.data.meshes.remove(me)
        coll = bpy.data.collections.get("AR01_Parts")
        ctx = BuildCtx(coll, GRIP, SPEC)
        M.build(SPEC, ctx)
    D = np.load(BASE_NPZ)
    names = [str(n) for n in D["names"]]
    objs = [bpy.data.objects[n] for n in names]
    out_blend = MD / f"AR01_mag_{tag}.blend"
    if not probe:
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
        bl.export_npz(objs, MD / f"mag_{tag}_tris.npz", GRIP, names)
    rep = {"tag": tag, "blend": str(out_blend), "floor": {"f0": M.FLOOR[0].tolist(), "f1": M.FLOOR[1].tolist(),
                                                          "shift_mm": M.FLOOR_SHIFT}}
    rep["manifold"] = {n: bl.manifold_report(bpy.data.objects[n]) for n in MAG_OBJS}
    rep["triangles_mag"] = sum(v["triangles"] for v in rep["manifold"].values())
    # geometry in frame B (mm) for the fit checks
    G = F.geom([o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")])
    mags = {n: G[n] for n in MAG_OBJS}
    rest = {n: v for n, v in G.items() if n not in MAG_OBJS}
    # static intersections: magazine objects against everything (and each other)
    pairs = []
    for a in MAG_OBJS:
        ta = F.tree(*G[a])
        for b, gb in G.items():
            if b == a or (b in MAG_OBJS and b < a):
                continue
            (la, ha), (lb, hb) = (G[a][0].min(0), G[a][0].max(0)), (gb[0].min(0), gb[0].max(0))
            if np.any(ha < lb - 0.01) or np.any(hb < la - 0.01):
                continue
            hits = ta.overlap(F.tree(*gb))
            if hits:
                pairs.append({"a": a, "b": b, "intersecting_triangle_pairs": len(hits)})
    rep["static_intersections"] = pairs
    rep["contact_gaps"] = F.min_gaps(G, [("magazine", "magazine_floor_plate"), ("magazine", "receiver"),
                                         ("magazine", "mag_catch"), ("magazine", "trigger_guard"),
                                         ("magazine_floor_plate", "receiver")], cap_mm=1.0)
    # L3 / L4 numbers as rifle_measure.py reads them (frame M)
    Vm = G["magazine"][0] + GRIP
    rib = Vm[Vm[:, 1] < -(float(SPEC.key["magazine"]["thickness"]) / 2 + 0.5)]
    rep["L3_rib_top_tips_Z"] = {"measured": round(float(rib[:, 2].max()), 3) if len(rib) else None, "spec": -38.5,
                                "tol": 1.5}
    Vf = G["magazine_floor_plate"][0] + GRIP
    allm = np.vstack([Vm, Vf])
    rep["L4_thickness"] = {"measured": round(float(Vm[:, 1].max() - Vm[:, 1].min() - 2.0), 3),
                           "spec": float(SPEC.key["magazine"]["thickness"]), "tol": 0.05}
    rep["L4_bottom_Z"] = {"measured": round(float(allm[:, 2].min()), 3), "spec": float(SPEC.key["magazine"]["bottom_Z"]),
                          "tol": 0.05}
    allv = np.vstack([v[0] for v in G.values()]) + GRIP
    rest_v = np.vstack([v[0] for v in rest.values()]) + GRIP
    rep["L4_overall_height_with_mag"] = {"measured": round(float(allv[:, 2].max() - allv[:, 2].min()), 3),
                                         "spec": SPEC.key["overall_height_with_mag"], "tol": 0.05}
    rep["L4_overall_height_without_mag"] = {"measured": round(float(rest_v[:, 2].max() - rest_v[:, 2].min()), 3),
                                            "spec": SPEC.key["overall_height_without_mag"], "tol": 0.05}
    # mag_release sweep (B3 row hinge [0.1, 0.3]) with the new magazine as a fixed part
    Bp = np.array([362.0, 0, -50.0]) - GRIP
    mov = {"mag_catch": G["mag_catch"]}
    fixed = {n: v for n, v in G.items() if n != "mag_catch"}
    rmax = float(np.linalg.norm(G["mag_catch"][0] - Bp, axis=1).max())
    step = min(1.0, math.degrees(0.1 / rmax))
    vals = np.arange(0.0, 10.0 + 1e-9, step)
    if vals[-1] < 10.0 - 1e-9:
        vals = np.r_[vals, 10.0]
    recs, summ = F.sweep(mov, fixed, lambda v: F.rot_matrix(Bp, [0, -1, 0], v), vals, clearance_every=1)
    summ["row_mm"] = [0.1, 0.3]
    summ["pass"] = summ["intersecting_steps"] == 0 and summ["min_clearance_mm"] >= 0.1 - 1e-4
    rep["B3_mag_release"] = summ
    # rock path probe (informational; the fit stage owns M4): MagInsertStart -> MagRockStart -> Mag about the hook
    hook = np.array([429.0, 0.0, -16.0]) - GRIP
    MV = np.vstack([mags[n][0] for n in MAG_OBJS])
    MT, off = [], 0
    for n in MAG_OBJS:
        MT.append(mags[n][1] + off)
        off += len(mags[n][0])
    MT = np.vstack(MT)
    FV, FT, Fid, fn = [], [], [], []
    o2 = 0
    for k, (n, (V, T)) in enumerate(rest.items()):
        FV.append(V)
        FT.append(T + o2)
        Fid.append(np.full(len(T), k))
        fn.append(n)
        o2 += len(V)
    FV, FT, Fid = np.vstack(FV), np.vstack(FT), np.concatenate(Fid)
    ftree = F.tree(FV, FT)
    floor_c = Vf.mean(0) - GRIP
    sgn = 1.0 if F.apply(F.rot_matrix(hook, [0, 1, 0], 18.0), floor_c[None])[0, 0] > floor_c[0] else -1.0
    theta = 18.0
    R18 = F.rot_matrix(hook, [0, 1, 0], sgn * theta)
    down = R18[:3, :3] @ np.array([0, 0, -1.0])
    rock = []
    for d in np.arange(8.0, -1e-9, -0.5):
        M4 = R18.copy()
        M4[:3, 3] += down * d
        hits = ftree.overlap(F.tree(F.apply(M4, MV), MT))
        rock.append({"phase": "insert", "d_mm": round(float(d), 2), "intersections": len(hits),
                     "parts": sorted({fn[Fid[a]] for a, _ in hits})})
    for th in np.arange(theta, -1e-9, -0.25):
        M4 = F.rot_matrix(hook, [0, 1, 0], sgn * th)
        hits = ftree.overlap(F.tree(F.apply(M4, MV), MT))
        rock.append({"phase": "rock", "deg": round(float(th), 2), "intersections": len(hits),
                     "parts": sorted({fn[Fid[a]] for a, _ in hits})})
    bad = [r for r in rock if r["intersections"]]
    rep["rock_probe"] = {"theta_deg": theta, "steps": len(rock), "intersecting_steps": len(bad),
                         "parts_hit": sorted({p for r in bad for p in r["parts"]}),
                         "first_hits": bad[:6], "last_hits": bad[-6:],
                         "note": "informational: the spec's provisional 18 deg rock about the provisional hook "
                                 "(429, 0, -16) against the current well (no front-lug recess, no catch motion)"}
    (MD / f"mag_{tag}_build.json").write_text(json.dumps(rep, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print("[magdev] BUILD_DONE", tag, rep["triangles_mag"], json.dumps({k: rep[k] for k in
          ("L3_rib_top_tips_Z", "L4_thickness", "L4_bottom_Z")}), "static", pairs)


# ======================================================================================== plain Python: render + metrics
def own_frame_iou(ours, ref, roi, aspect=False):
    """IoU after the best similarity transform (scale, rotation, shift) of our silhouette onto the reference inside
    the window: compares shape in the part's own frame (close-ups are not to scale)."""
    import numpy as np
    from scipy import ndimage as ndi
    from scipy.optimize import minimize
    y0, y1, x0, x1 = roi
    o = ours[y0:y1, x0:x1].astype(float)
    r = ref[y0:y1, x0:x1].astype(bool)
    H, W = o.shape
    cy, cx = (np.array(np.nonzero(o > 0.5)).mean(1) if (o > 0.5).any() else (H / 2, W / 2))

    def warp(q):
        q = np.clip(q, [-0.5, -20.0, -40.0, -40.0, -0.4][:len(q)], [0.5, 20.0, 40.0, 40.0, 0.4][:len(q)])
        s, th, ty, tx = math.exp(q[0]), math.radians(q[1]), q[2], q[3]
        k = math.exp(q[4]) if aspect else 1.0                     # stretch along the image's vertical axis
        c, sn = math.cos(th), math.sin(th)
        A = np.linalg.inv(np.array([[c, -sn], [sn, c]]) @ np.diag([k, 1.0])) / s      # output -> input
        ctr = np.array([cy, cx])
        offs = ctr - A @ (ctr + np.array([ty, tx]))
        return ndi.affine_transform(o, A, offset=offs, order=1, mode="constant", cval=0.0)

    def cost(q):
        w = warp(q)
        inter = np.minimum(w, r).sum()
        uni = np.maximum(w, r).sum()
        return -inter / max(uni, 1e-9)

    best = None
    for s0 in (-0.08, 0.0, 0.08):
        res = minimize(cost, [s0, 0.0, 0.0, 0.0] + ([0.0] if aspect else []), method="Powell",
                       options={"xtol": 1e-3, "ftol": 1e-5, "maxiter": 4000})
        if best is None or res.fun < best.fun:
            best = res
    best.x = np.clip(best.x, [-0.5, -20.0, -40.0, -40.0, -0.4][:len(best.x)], [0.5, 20.0, 40.0, 40.0, 0.4][:len(best.x)])
    w = warp(best.x) > 0.5
    inter = (w & r).sum()
    uni = (w | r).sum()
    fit = {"scale": round(math.exp(best.x[0]), 4), "rot_deg": round(best.x[1], 2),
           "shift_px": [round(best.x[3], 2), round(best.x[2], 2)]}
    if aspect:
        fit["vertical_stretch"] = round(math.exp(best.x[4]), 4)
    return round(float(inter / max(uni, 1)), 4), fit


def l2_magazine(npz):
    import numpy as np
    from gunlib import compare as C
    import rifle_silhouette as RS
    D = np.load(npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    frL, jL = C.load_trace(TRACE, "LEFT")
    keys = list(RS.PART_MAP)
    remap = np.full(len(names), -1)
    for ki, k in enumerate(keys):
        for nm in RS.PART_MAP[k]:
            if nm in names:
                remap[names.index(nm)] = ki
    tl = remap[lab]
    tc = V[T].mean(axis=1)
    if "trigger_guard" in names:
        g = lab == names.index("trigger_guard")
        tl[g & (tc[:, 2] > -34.85) & (tc[:, 0] < 368.0)] = keys.index("receiver")
        tl[g & (tc[:, 0] > 355.3) & (tc[:, 2] > -54.5) & (tc[:, 2] <= -34.85)] = keys.index("mag_catch")    # rifle_silhouette since integration
    if "bolt_carrier" in names:
        tl[(lab == names.index("bolt_carrier")) & (tc[:, 2] > 10.6)] = keys.index("dust_cover")
    ok = tl >= 0
    covs = C.raster_labels(C.side_px(frL, V), T[ok], V[:, 1], tl[ok], frL.shape, nlab=len(keys))
    out = {}
    for k in ("magazine", "mag_catch"):
        ki = keys.index(k)
        refp = C.rings_mask([r["px"] for r in jL["parts"][k]], frL.shape)
        op = covs[ki] > 0.5
        cd = C.contour_distance(op, refp)
        out[k] = {"iou": round(C.iou(op, refp), 4), "contour_p95_px": round(cd["p95"], 3), "contour_max_px": round(cd["max"], 3)}
        if k == "magazine":
            ys, xs = np.nonzero(op | refp)
            y0, y1, x0, x1 = ys.min() - 6, ys.max() + 7, xs.min() - 6, xs.max() + 7
            C.diff_image(op[y0:y1, x0:x1], refp[y0:y1, x0:x1], MD / f"l2_{Path(npz).stem}.png", scale=6)
    # whole-side silhouette (L2 side IoU identity) as a guard
    ref = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    ours = C.raster_tris(C.side_px(frL, V), T, frL.shape) > 0.5
    out["side_iou_identity"] = round(C.iou(ours, ref), 4)
    return out


def mag_panels():
    """c4 / c5 panel configs for the magazine's own camera solve: the rifle_detail panels plus landmarks read off
    6x / 5x gridded zooms of the close-ups for the detail-pass features (plate corners, posts, lug, floor-plate
    front end; +-2 px). c5's prior is raised to 40 deg above the front: the sheet draws the floor plate nearly edge-on
    (its outer face shows 19 px of 363 = 12 mm), which the 19.6 deg panel solve could not (the face showed 30 mm)."""
    import copy
    import numpy as np
    import rifle_detail as RD
    from parts import magazine as M
    P = copy.deepcopy(RD.PANELS)
    L = float(np.linalg.norm(M._F1 - M._F0))
    sd = M._plate_sd(L)
    xz = M._sd_to_xz(sd, M._F0)
    low = xz[np.argmin(xz[:, 1])]
    s_f = L + M.PLATE_FRONT
    fe = M._sd_to_xz([(s_f, -M.PLATE_TH)], M._F0)[0]
    lip = M.MAG_HT + M.PLATE_LIP

    def at(u, z):
        R = M.FR.R(u)
        return M.FR.pt(R, M.FR.a_at_z(R, z))
    pft, prt = at(M.U_STEP - 0.01, M.PLATE_TOP_Z), at(0.08, M.PLATE_TOP_Z)
    prb, pfb = at(0.08, -34.0), at(M.U_STEP - 0.01, -36.0)
    yp = M.MAG_HT + M.PLATE_PROUD
    P["c4"]["landmarks"] = P["c4"]["landmarks"][:2] + [
        ("plate front-top corner", (61.0, 39.0), (pft[0], yp, pft[1])),
        ("plate rear-top corner", (106.0, 8.0), (prt[0], yp, prt[1])),
        ("plate rear-bottom corner", (120.0, 43.0), (prb[0], yp, prb[1])),
        ("plate front-bottom corner", (76.0, 70.0), (pfb[0], yp, pfb[1]))]
    P["c4"]["part_bound_deg"] = 12.0
    P["c4"]["part_lam_lm"] = 0.5
    ez = M.FR.pt(M.R_F, M.FR.a_at_z(M.R_F, M.FRONT_TOP_Z))
    stp = M.FR.pt(M.FR.R(M.U_STEP), M.FR.a_at_z(M.FR.R(M.U_STEP), M.LIP_Z))
    P["c5"]["from_dir"] = (math.cos(math.radians(40.0)), 0.0, math.sin(math.radians(40.0)))
    P["c5"]["bound_deg"] = 15.0
    P["c5"]["part_bound_deg"] = 8.0
    P["c5"]["landmarks"] = [
        ("floor plate rear corner (right side, image left)", (38.0, 342.0), (low[0], -lip, low[1])),
        ("floor plate rear corner (left side, image right)", (80.0, 342.0), (low[0], lip, low[1])),
        ("floor plate front end, top edge centre", (59.0, 323.0), (fe[0], 0.0, fe[1])),
        ("front zone top front corner (right)", (39.0, 33.0), (ez[0], -M.MAG_HT, ez[1])),
        ("front zone top front corner (left)", (79.0, 33.0), (ez[0], M.MAG_HT, ez[1])),
        ("lip post top (right)", (45.0, 7.0), (stp[0], -7.4, stp[1])),
        ("lip post top (left)", (69.0, 7.0), (stp[0], 7.4, stp[1])),
        ("lug bottom centre", (60.0, 56.0), (431.0, 0.0, -27.3))]
    return P


def kit_for(tag, panels=None):
    import rifle_detail as RD
    from gunlib.detail import DetailKit
    cfg = dict(RD.kit().cfg)
    cfg["npz"] = str(MD / f"mag_{tag}_tris.npz")
    cfg["blend"] = str(MD / f"AR01_mag_{tag}.blend")
    cfg["scratch_dir"] = str(MD / "kit")
    if panels is not None:
        cfg["panels"] = panels
    return DetailKit(cfg)


def solve(tag):
    """Re-solve the magazine's c4 / c5 cameras (panel + part refinement) against the current magazine build."""
    K = kit_for(tag, mag_panels())
    out = {}
    for k in ("c4", "c5"):
        cam, rep = K.solve_panel(k, force=True)
        out["panel_" + k] = rep
    out["part"] = K.solve_closeup_camera("magazine", force=True)
    (MD / f"mag_{tag}_solve.json").write_text(json.dumps(out, indent=1, default=str))
    print("[magdev] SOLVE_DONE", json.dumps({k: (v if not isinstance(v, dict) else {kk: v.get(kk) for kk in ("iou_in_frame", "landmark_rms_px", "rotation_from_prior_deg")}) for k, v in out.items() if k != "part"}),
          {k: v["part_camera"].get("iou_in_roi", v["part_camera"].get("iou_in_frame")) for k, v in out["part"].items()})


def render(tag):
    import numpy as np
    from PIL import Image
    from gunlib import closeup as CU
    K = kit_for(tag, mag_panels())
    res = K.render_part_crop("magazine", tag)["magazine"]
    met = {"tag": tag, "panels": {}}
    for k, d in res.items():
        P = K.panel(k)
        H, W = P.shape[:2]
        rgba = np.asarray(Image.open(K.scratch / "renders" / f"magazine__{k}_{tag}.png").convert("RGBA"))
        alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), K.ss)[:, :, 0] / 255.0
        x0, y0, x1, y1 = d["window_px"]
        ref = K.mask(k)
        oi, fit = own_frame_iou(alpha, ref, (y0, y1, x0, x1))
        oa, fita = own_frame_iou(alpha, ref, (y0, y1, x0, x1), aspect=True)
        met["panels"][k] = {"window_iou_raw": d["silhouette_iou_window"], "own_frame_iou": oi, "own_frame_fit": fit,
                            "own_frame_iou_with_stretch": oa, "own_frame_fit_with_stretch": fita,
                            "edge_f_2px": d["edges"]["f"], "edge_precision": d["edges"]["precision"],
                            "edge_recall": d["edges"]["recall"], "pair": f"review/detail/magazine/{tag}_pair_{k}.png"}
    met["L2_side"] = l2_magazine(MD / f"mag_{tag}_tris.npz")
    (MD / f"mag_{tag}_metrics.json").write_text(json.dumps(met, indent=1))
    print("[magdev] RENDER_DONE", json.dumps(met))


if __name__ == "__main__":
    tag = arg("--tag", "dev")
    if "--build" in argv or "--probe" in argv:
        blender_build(tag)
    elif "--solve" in argv:
        solve(tag)
    elif "--render" in argv:
        render(tag)
    elif "--l2" in argv:
        print(json.dumps(l2_magazine(MD / f"mag_{tag}_tris.npz")))
