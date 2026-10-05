"""Private iteration loop for the MUZZLE BRAKE detail part (detail pass round 1). Works on copies only, so the
other part builders running in parallel are never disturbed:

    WorkFiles/guns/rifle/scratch/detail/muzzle_brake/  base.blend + base_tris.npz (copies of the form build),
                                                       cameras/ (copies of the solved panel + part cameras)

  py -3 -B Scripts/guns/rifle/parts/muzzle_brake_dev.py iter --tag r1_i1      build -> render -> metrics -> L2 side
  py -3 -B Scripts/guns/rifle/parts/muzzle_brake_dev.py metrics --tag r1_i1   metrics only (renders exist)
  py -3 -B Scripts/guns/rifle/parts/muzzle_brake_dev.py solve --tag x       round 2: re-solve the c3 part camera on the
                                                                         brake only (window minus the FSB side of X 846)

Steps of `iter`:
  1. headless Blender opens base.blend, deletes the old muzzle_brake, builds parts/muzzle_brake.py into the same
     collection, saves work.blend and work_tris.npz (the base npz with the brake replaced, same object order);
  2. gunlib.detail.DetailKit renders the part's close-up shots (c3, q34) in the ROUGH LOOK at the solved cameras
     (fixed crop windows = the 'before' windows, so every iteration and the reference share one framing) and writes
     review/detail/muzzle_brake/<tag>_ours/pair/edges_<panel>.png + <tag>_crops.json;
  3. part metrics in the part's own frame: silhouette IoU in the part ROI (the window right of the brake's rear
     face, so the front sight block does not count), opening IoU (the dark cut-face opening + side slot), edge F;
  4. L2 side gate for the part (rifle_silhouette.run on work_tris.npz; the thin-part rule: outer contour P95 <= 1 px,
     max <= 2 px) -> review/detail/muzzle_brake/l2/.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
from rifle_common import SPEC, GRIP, SCRATCH, REVIEW, ROOT  # noqa: E402

PART = "muzzle_brake"
WORK = SCRATCH / "detail" / PART
OUT = REVIEW / "detail" / PART
FIXED_WINDOWS = {"c3": (155, 139, 267, 234), "q34": (661, 93, 725, 142)}   # the 'before' crop windows (panel px)
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"


# ============================================================================================ Blender side
def blender_build():
    import bpy
    import numpy as np
    from gunlib import bl
    from gunlib.parts import BuildCtx
    import parts.muzzle_brake as MB
    names = [str(n) for n in np.load(WORK / "base_tris.npz")["names"]]
    old = bpy.data.objects.get(PART)
    coll = old.users_collection[0]
    bpy.data.objects.remove(old, do_unlink=True)
    ctx = BuildCtx(coll, GRIP, SPEC)
    built = MB.build(SPEC, ctx)
    ob = built[PART][0]
    assert ob.name == PART, ob.name
    rep = bl.manifold_report(ob)
    objs = [bpy.data.objects[n] for n in names]
    bl.export_npz(objs, WORK / "work_tris.npz", GRIP, names)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "work.blend"))
    # G5 at rest against the neighbours (base.blend copies of the other parts): intersections and butt gaps
    from gunlib import fit as F
    near = [n for n in (PART, "barrel", "front_sight_block", "front_sight_post", "cleaning_rod") if n in bpy.data.objects]
    geo = F.geom([bpy.data.objects[n] for n in near])
    rep["intersections"] = F.pair_intersections(geo)
    rep["gaps"] = F.min_gaps(geo, [(PART, "barrel"), (PART, "front_sight_block")])
    (WORK / "work_build.json").write_text(json.dumps(rep, indent=1))
    print("[MB] BUILD_DONE", json.dumps(rep))


# ============================================================================================ plain Python side
def kit():
    import rifle_detail as RD
    from gunlib.detail import DetailKit
    cfg = dict(RD.kit().cfg)
    cfg["npz"] = str(WORK / "work_tris.npz")
    cfg["blend"] = str(WORK / "work.blend")
    cfg["scratch_dir"] = str(WORK)
    cfg["parts"] = {PART: cfg["parts"][PART]}

    class K(DetailKit):
        def window(self, part, key):
            return FIXED_WINDOWS[key]
    return K(cfg)


def run_build():
    log = WORK / "build.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([BLENDER, "-b", str(WORK / "base.blend"), "--factory-startup", "--python", str(Path(__file__)),
                        "--", "blender"], stdout=f, stderr=subprocess.STDOUT, check=False, cwd=str(ROOT))
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "BUILD_DONE" not in txt:
        print(txt[-4000:])
        raise SystemExit("build failed, see %s" % log)
    return json.loads((WORK / "work_build.json").read_text())


def junction_roi(cam, shape, x_face=848.82, r=10.6):
    """Pixels on the muzzle side of the brake's rear face: right of the line through the projected top / bottom of
    the rear face (the front sight block lies on the other side)."""
    import numpy as np
    P = cam.project(np.array([[x_face, 0.0, r], [x_face, 0.0, -r], [x_face + 10, 0.0, 0.0]]))
    (x0, y0), (x1, y1), (xf, yf) = P
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    side = (x1 - x0) * (yy - y0) - (y1 - y0) * (xx - x0)
    ref_side = (x1 - x0) * (yf - y0) - (y1 - y0) * (xf - x0)
    return np.sign(side) == np.sign(ref_side)


def dark_mask(rgb, sil, k=0.62):
    """Openings: pixels inside the silhouette clearly darker than the part's median steel (smoothed)."""
    import numpy as np
    from scipy import ndimage as ndi
    L = ndi.gaussian_filter(rgb.astype(float).mean(2), 1.0)
    if sil.sum() < 10:
        return np.zeros_like(sil)
    med = np.median(L[sil])
    m = sil & (L < med * k)
    m = ndi.binary_opening(m, iterations=1)
    return m


def metrics(K, tag):
    import numpy as np
    from PIL import Image
    from gunlib import closeup as CU
    from gunlib import compare as C
    res = {}
    for key in K.cfg["parts"][PART]["panels"]:
        P = K.panel(key)
        H, W = P.shape[:2]
        cam = K.part_camera(PART, key)
        x0, y0, x1, y1 = FIXED_WINDOWS[key]
        roi = np.zeros((H, W), bool)
        roi[y0:y1, x0:x1] = True
        roi &= junction_roi(cam, (H, W))
        rgba = np.asarray(Image.open(K.scratch / "renders" / f"{PART}__{key}_{tag}.png").convert("RGBA"))
        ss = K.ss
        alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), ss)[:, :, 0] / 255.0
        _, _, _, bg = CU.fit_background(P)
        ours = CU.downscale(CU.composite_on(bg, rgba, ss), ss)
        sil_o = alpha > 0.5
        ref_m = K.mask(key)
        iou = C.iou(sil_o, ref_m, roi)
        cd = C.contour_distance(sil_o & roi, ref_m & roi)
        do = dark_mask(ours, sil_o & roi)
        dr = dark_mask(P, ref_m & roi)
        oiou = C.iou(do, dr, roi)
        # shape-only: the close-ups are not to scale, so also fit a small similarity (scale <= 12 %, shift <= 8 px,
        # rot <= 3 deg) of our projected brake + neighbours to the reference silhouette inside the part ROI
        V, T = K.subset(K.cfg["panels"][key].get("objects"))
        Tv = CU.visible_tris(cam, V, T)
        try:
            prm, iou_fit, _ = C.similarity_fit(lambda: (cam.project(V), Tv), ref_m, roi, max_rot_deg=3.0,
                                               max_scale=0.12, max_shift=8.0)
        except Exception as e:  # noqa: BLE001
            prm, iou_fit = str(e), None
        crops = json.loads((OUT / f"{tag}_crops.json").read_text())[key]
        res[key] = {"part_roi_silhouette_iou": round(iou, 4),
                    "part_roi_iou_after_similarity_fit": None if iou_fit is None else round(iou_fit, 4),
                    "similarity_fit_s_rotdeg_tx_ty": prm, "opening_iou": round(oiou, 4),
                    "opening_px_ours": int(do.sum()), "opening_px_ref": int(dr.sum()),
                    "contour_p95_px": None if cd["p95"] is None else round(cd["p95"], 2),
                    "edge_f_2px": crops["edges"]["f"], "window_silhouette_iou": crops["silhouette_iou_window"]}
        # opening overlay (ref blue, ours red) at 6x for eyeballing
        vis = (P[y0:y1, x0:x1].astype(float) * 0.6).astype(np.uint8)
        vis[..., 2] = np.where(dr[y0:y1, x0:x1], 255, vis[..., 2])
        vis[..., 0] = np.where(do[y0:y1, x0:x1], 255, vis[..., 0])
        vis[~roi[y0:y1, x0:x1]] //= 3
        Image.fromarray(vis).resize(((x1 - x0) * 5, (y1 - y0) * 5), Image.NEAREST).save(OUT / f"{tag}_openings_{key}.png")
    return res


X_ROI = 846.0      # brake-only camera ROI: the window on the muzzle side of X 846 (keeps the junction + knob in)


def solve_brake_camera(K, key="c3", lam=0.05, bound=6.0, iters=400):
    """Round 2: re-solve the part camera on the BRAKE ONLY (window minus the front sight side of the rear face), with
    free ortho scale: the close-ups are not to scale and c3 draws the brake larger relative to the FSB than the side
    views (a camera fitted on brake + FSB made our brake read 13-21 % too thin, the round-1 'stretched tube' tell).
    The previous camera is kept as <name>.r1.json."""
    import shutil
    import numpy as np
    from gunlib import closeup as CU
    pc = dict(K.cfg["panels"][key])
    path = K._cam_path(key, PART)
    bak = path.with_name(path.stem + ".r1.json")
    if not bak.exists():
        shutil.copy(path, bak)
    cam0 = CU.cam_from_json(json.loads(bak.read_text())["camera"])
    P = K.panel(key)
    H, W = P.shape[:2]
    V, T = K.subset(pc.get("objects"))
    ref = K.mask(key)
    x0, y0, x1, y1 = FIXED_WINDOWS[key]
    roi = np.zeros((H, W), bool)
    roi[y0:y1, x0:x1] = True
    roi &= junction_roi(cam0, (H, W), x_face=X_ROI)
    pc["bound_deg"], pc["lam_lm"] = bound, lam
    cam, rep = CU.solve_camera(pc, W, H, V, T, ref, roi=roi, init=cam0, iters=iters)
    rep["roi"] = "brake only: window %s minus the FSB side of X %.1f" % (FIXED_WINDOWS[key], X_ROI)
    path.write_text(json.dumps({"panel": key, "part": PART, "camera": cam.to_json(), "report": rep}, indent=1))
    CU.solve_overlay(P, cam, V, T, ref, OUT / f"solve_{key}_r2.png", pc.get("landmarks", []), roi_box=FIXED_WINDOWS[key])
    print("[MB] camera", key, json.dumps(rep))
    return rep


def l2_side(tag):
    import rifle_silhouette as RS
    r = RS.run(str(WORK / "work_tris.npz"), f"detail/{PART}/l2", tag="_" + tag)
    parts = r["views"]["side"]["parts"]
    summary = {"side_iou_fit": r["views"]["side"]["iou_fit"], "top_iou_fit_valid": r["views"]["top"]["iou_fit_valid"],
               "top_iou_identity_valid": r["views"]["top"]["iou_identity_valid"],
               "left_vs_RIGHT_iou_fit": r["views"]["left_vs_RIGHT_panel"]["iou_fit"],
               "parts_pass": "%d / %d" % (sum(1 for v in parts.values() if v["pass"]), len(parts)),
               "parts_failing": [k for k, v in parts.items() if not v["pass"]]}
    return parts[PART], summary, r["triangles"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["iter", "metrics", "solve"])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--no-l2", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="build + L2 only")
    a = ap.parse_args()
    out = {"tag": a.tag}
    if a.cmd == "solve":
        print(json.dumps(solve_brake_camera(kit()), indent=1))
        return
    if a.cmd == "iter":
        out["build"] = run_build()
    K = kit()
    if a.cmd == "iter":
        if not a.no_render:
            K.render_part_crop(PART, a.tag)
    if not a.no_render:
        out["metrics"] = metrics(K, a.tag)
    if not a.no_l2:
        out["l2_side_part"], out["l2_summary"], out["rifle_tris_total"] = l2_side(a.tag)
    (OUT / f"{a.tag}_result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if "--" in sys.argv and "blender" in sys.argv[sys.argv.index("--") + 1:]:
        blender_build()
    else:
        main()
