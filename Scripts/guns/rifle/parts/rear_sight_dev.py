"""Rear-sight detail builder's private harness (detail pass rounds 1-2). Lets this part iterate while the other part
builders run in parallel: it never writes Assets/Guns/AR01.blend or scratch/form_tris.npz.

    py -3 -B Scripts/guns/rifle/parts/rear_sight_dev.py build            rebuild only this module's objects into a
                                                                          copy of the baseline blend
    py -3 -B Scripts/guns/rifle/parts/rear_sight_dev.py crop  --tag r1   ROUGH LOOK crops at the solved c2 / q34
                                                                          cameras (fixed from the setup) + numbers
    py -3 -B Scripts/guns/rifle/parts/rear_sight_dev.py l2   [--tag r1]  per-part L2 (side view) on the private npz
    py -3 -B Scripts/guns/rifle/parts/rear_sight_dev.py sweep            B3 sight_rear sweep + this part's contacts
    py -3 -B Scripts/guns/rifle/parts/rear_sight_dev.py camera           round 2: re-solve the c2 part camera on the
                                                                          rear sight's own landmarks (CAM_LANDMARKS)
                                                                          and fix the round-2 crop window

Private scratch: WorkFiles/guns/rifle/scratch/detail/rear_sight/ (base.blend + base_tris.npz = the baseline form
build copied at the start of the round; rs.blend + rs_tris.npz = baseline with this module rebuilt; cameras/ =
copies of the setup's solved cameras, kept fixed so the comparison is not re-fitted to our own changes).
Review output: WorkFiles/guns/rifle/review/detail/rear_sight/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))

IN_BLENDER = "bpy" in sys.modules or any(a.endswith("blender.exe") for a in sys.argv[:1])
try:
    import bpy  # noqa: F401
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

from rifle_common import SCRATCH, REVIEW, GRIP, SHEET  # noqa: E402

PRIV = SCRATCH / "detail" / "rear_sight"
OUT = REVIEW / "detail" / "rear_sight"
MODULE = "rear_sight"
MY_OBJS = ["rear_sight_block", "rear_sight_leaf", "rear_sight_slider", "handguard_retainer"]
MY_KEYS = ["rear_sight_block", "rear_sight_leaf", "handguard_retainer"]


# ======================================================================================== Blender side
def _blender_build():
    import bpy
    from gunlib import bl
    from gunlib.parts import BuildCtx
    from rifle_common import SPEC
    import rifle_parts as RP
    import parts as PM
    for n in MY_OBJS:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    coll = bpy.data.collections.get("AR01_Parts") or bl.collection("AR01_Parts")
    ctx = BuildCtx(coll, GRIP, SPEC, MY_KEYS)
    mod = PM.load(MODULE)
    built = mod.build(SPEC, ctx)
    # npz in ORDER (+ the extra objects a key makes)
    extra = {"rear_sight_leaf": ["rear_sight_slider"]}
    objs = []
    for k in RP.ORDER:
        for n in [k] + extra.get(k, []):
            ob = bpy.data.objects.get(n)
            if ob is not None and ob.type == "MESH":
                objs.append(ob)
    rep = {}
    for k, lst in built.items():
        for ob in lst:
            rep[ob.name] = bl.manifold_report(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(PRIV / "rs.blend"))
    bl.export_npz(objs, PRIV / "rs_tris.npz", GRIP, [o.name for o in objs])
    tot = sum(len(o.data.polygons) for o in objs)
    out = {"parts": rep, "part_triangles": sum(r["triangles"] for r in rep.values()),
           "rifle_triangles_npz": int(sum(bl.manifold_report(o)["triangles"] for o in objs)), "polys": tot}
    (PRIV / "build_report.json").write_text(json.dumps(out, indent=1))
    print("[RS] built", json.dumps(out))


def _blender_sweep():
    import math
    import bpy
    import numpy as np
    from gunlib import fit as F
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
    G = F.geom(objs)
    pivot = np.asarray([504.0, 0, 41.0]) - GRIP
    mov = {n: G[n] for n in ("rear_sight_leaf", "rear_sight_slider")}
    fixed = {n: v for n, v in G.items() if n not in mov}
    lo, hi = 0.10, 0.30
    V = np.vstack([m[0] for m in mov.values()])
    rmax = float(np.linalg.norm(V - pivot, axis=1).max())
    step = min(1.0, math.degrees(lo / rmax))
    vals = np.arange(0.0, 6.0 + 1e-9, step)
    if vals[-1] < 6.0 - 1e-9:
        vals = np.r_[vals, 6.0]
    recs, summ = F.sweep(mov, fixed, lambda v: F.rot_matrix(pivot, [0, 1, 0], v), vals, clearance_every=1)
    summ["row_mm"] = [lo, hi]
    summ["r_max_mm"] = round(rmax, 2)
    summ["pass"] = (summ["intersecting_steps"] == 0 and summ["min_clearance_mm"] >= lo - 1e-4
                    and summ["min_clearance_mm"] <= hi + 1e-4)
    near = [n for n in G if n not in MY_OBJS]
    pairs = F.pair_intersections(G)
    mine = [p for p in pairs if any(x in MY_OBJS for x in (p if isinstance(p, (list, tuple)) else [p]))]
    cp = [("rear_sight_block", "receiver"), ("rear_sight_block", "dust_cover"), ("gas_tube_rear_cap", "rear_sight_block"),
          ("rear_sight_leaf", "rear_sight_block"), ("rear_sight_slider", "rear_sight_leaf"),
          ("handguard_retainer", "rear_sight_block"), ("rear_sight_block", "upper_handguard"),
          ("rear_sight_block", "gas_tube"), ("rear_sight_block", "bolt_carrier"), ("rear_sight_block", "lower_handguard")]
    cp = [tuple(sorted(p)) for p in cp if p[0] in G and p[1] in G]
    gaps = F.min_gaps(G, cp)
    out = {"sight_rear": summ, "worst": sorted([r for r in recs if r["intersections"]], key=lambda r: -r["intersections"])[:8],
           "static_intersections_all": pairs, "static_intersections_mine": mine, "contact_gaps": gaps}
    (PRIV / "sweep.json").write_text(json.dumps(out, indent=1, default=str))
    print("[RS] sweep", json.dumps(summ), "mine", mine, "gaps", json.dumps(gaps, default=str))


# ======================================================================================== plain Python side
def _run_blender(blend, mode):
    import gunlib
    log = PRIV / f"{mode}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(blend), "--factory-startup", "--python", str(Path(__file__).resolve()),
                        "--", mode], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "[RS]" not in txt:
        i = txt.find("Traceback")
        print(txt[i:i + 3000] if i >= 0 else txt[-3000:])
        raise SystemExit(f"blender {mode} failed, see {log}")
    for line in txt.splitlines():
        if line.startswith("[RS]"):
            print(line[:2000])


def kit():
    import gunlib
    from gunlib.detail import DetailKit
    import rifle_detail as RD
    cfg = {"sheet": str(SHEET), "panels": RD.PANELS, "parts": {MODULE: RD.parts_cfg()[MODULE]},
           "npz": str(PRIV / "rs_tris.npz"), "blend": str(PRIV / "rs.blend"), "offset_M": [float(v) for v in GRIP],
           "wood_slots": ["M_AR01_Furniture"], "review_dir": str(REVIEW / "detail"), "scratch_dir": str(PRIV),
           "blender": gunlib.BLENDER, "ss": 3, "samples": 96, "env": 0.55, "light": 1.35}
    return DetailKit(cfg)


def window_fixed():
    """The crop windows: the setup's (round 0/1 framing), with c2 replaced by the round-2 window once the c2 part
    camera has been re-solved (camera command), so every round-2 iteration compares the same reference crop."""
    d = json.loads((OUT / "before_crops.json").read_text())
    w = {k: tuple(v["window_px"]) for k, v in d.items()}
    p2 = OUT / "r2_window.json"
    if p2.exists():
        w.update({k: tuple(v) for k, v in json.loads(p2.read_text()).items()})
    return w


# Round 2: the setup's c2 part camera (silhouette refine on the whole window) put the rear-sight landmarks 11-78 px
# off. The image directions of the world axes in c2's rear sight (the leaf's rails = X, the front housing's top edge
# = Y, the block's front edge = Z) were measured off 7-12x zooms: X (0.91, -0.41), Y (-0.93, -0.37), Z (0, -1),
# lengths about 0.75 : 0.78 : 0.91, which solve to a camera looking along (0.66, 0.62, -0.42) (behind-right, 25 deg
# above). That is the prior, held within ~3 deg (a looser 10 deg bound let the silhouette term tip the camera to 31
# deg above, which shows the block's top more than c2 does, at a worse ROI IoU 0.922 vs 0.934); the landmarks below
# (rear sight only: the receiver points belong to a differently stylised part of the panel) place it. Close-ups are not to scale: the camera is never used for size.
CAM_PRIOR_FROM = (-0.66, -0.62, 0.42)
CAM_LANDMARKS = [
    ("retainer pin head centre", (262.2, 66.7), (516.5, -25.0, 41.0)),
    ("retainer lower end screw", (243.9, 101.7), (500.0, -23.6, 24.0)),
    ("near rail teeth rear end", (200.0, 81.0), (468.6, -8.5, 45.0)),
    ("near rail teeth front end", (234.0, 65.5), (497.0, -8.5, 45.0)),
    ("front housing far top corner", (213.0, 48.0), (513.0, 20.0, 43.6)),
]


def camera():
    import shutil
    import time
    import numpy as np
    from gunlib import closeup as CU
    K = kit()
    pc = dict(K.cfg["panels"]["c2"])
    pc.update({"landmarks": CAM_LANDMARKS, "lam_lm": 4.0, "bound_deg": 3.0, "prior_w": 30.0, "from_dir": CAM_PRIOR_FROM})
    P = K.panel("c2")
    H, W = P.shape[:2]
    V, T = K.subset(pc.get("objects"))
    ref = K.mask("c2")
    roi = np.zeros((H, W), bool)
    roi[10:190, 120:277] = True
    t0 = time.time()
    cam, rep = CU.solve_camera(pc, W, H, V, T, ref, roi=roi, iters=200)
    rep["seconds"] = round(time.time() - t0, 1)
    rep["method"] = "round 2: prior CAM_PRIOR_FROM (bound 3 deg, prior weight 30), landmarks CAM_LANDMARKS (lam 4) + silhouette in panel px 120-277 x 10-190"
    cp = PRIV / "cameras" / "rear_sight__c2.json"
    bk = PRIV / "cameras" / "rear_sight__c2_r1.json"
    if not bk.exists():
        shutil.copy(cp, bk)
    cp.write_text(json.dumps({"panel": "c2", "part": MODULE, "camera": cam.to_json(), "report": rep}, indent=1))
    win = CU.part_window(cam, K.part_vertices(MODULE), margin=0.15)
    (OUT / "r2_window.json").write_text(json.dumps({"c2": list(win)}))
    CU.solve_overlay(P, cam, V, T, ref, OUT / "solve_c2_r2.png", CAM_LANDMARKS, roi_box=win)
    print(json.dumps(rep), "window", win)


def crop(tag):
    K = kit()
    fixed = window_fixed()
    K.window = lambda part, key: fixed[key]          # same framing every round
    res = K.render_part_crop([MODULE], tag)[MODULE]
    tr = K.trace_closeup(MODULE)
    out = {"tag": tag, "crops": res, "traces": tr}
    out.update(part_iou(K, tag))
    (OUT / f"{tag}_metrics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: (v["silhouette_iou_window"], v["edges"]["f"]) for k, v in res.items()}),
          json.dumps(out.get("part_iou")))
    return out


def part_iou(K, tag):
    """Outline IoU in the part's own frame: the reference mask vs our render's alpha restricted to the part's zone
    (the window rows above the dust cover / handguard top line, where only the rear sight forms the outline), plus
    the whole-window number. Zone = pixels whose nearest rendered object is ours (label render via projection)."""
    import numpy as np
    from PIL import Image
    from gunlib import closeup as CU, compare as C
    out = {}
    V, T, lab, names = K.geometry()
    ids = [i for i, n in enumerate(names) if n in MY_OBJS]
    for key in K.cfg["parts"][MODULE]["panels"]:
        cam = K.part_camera(MODULE, key)
        P = K.panel(key)
        H, W = P.shape[:2]
        x0, y0, x1, y1 = K.window(MODULE, key)
        ref = K.mask(key)
        Tv = CU.visible_tris(cam, V, T)
        allc = C.raster_tris(cam.project(V), Tv, (H, W), ss=2) > 0.5
        sel = np.isin(lab, ids)
        Tm = CU.visible_tris(cam, V, T[sel])
        mine = C.raster_tris(cam.project(V), Tm, (H, W), ss=2) > 0.5
        others = C.raster_tris(cam.project(V), CU.visible_tris(cam, V, T[~sel]), (H, W), ss=2) > 0.5
        # part zone: our part's projected area dilated, minus pixels covered by other parts but not by ours
        from scipy import ndimage as ndi
        zone = ndi.binary_dilation(mine, iterations=6) & ~(others & ~mine)
        roi = np.zeros((H, W), bool)
        roi[y0:y1, x0:x1] = True
        z = zone & roi
        out[key] = {"iou_part_zone": round(C.iou(allc, ref, z), 4), "zone_px": int(z.sum()),
                    "iou_window_proj": round(C.iou(allc, ref, roi), 4)}
        # overlay
        rgb = P[y0:y1, x0:x1].copy().astype(float)
        a, r, zz = allc[y0:y1, x0:x1], ref[y0:y1, x0:x1], z[y0:y1, x0:x1]
        img = rgb * 0.6
        img[a & ~r & zz] = [255, 80, 0]
        img[r & ~a & zz] = [0, 120, 255]
        img[~zz] *= 0.5
        k = max(2, int(round(480 / (y1 - y0))))
        Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST).save(
            OUT / f"{tag}_partzone_{key}.png")
    return {"part_iou": out}


def l2(tag):
    import rifle_silhouette as RS
    res = RS.run(str(PRIV / "rs_tris.npz"), "detail/rear_sight/l2", tag)
    side = res["views"]["side"]
    out = {"rear_sight": side["parts"].get("rear_sight"), "dust_cover": side["parts"].get("dust_cover"),
           "gas_tube_rear_cap": side["parts"].get("gas_tube_rear_cap"), "side_iou_fit": side["iou_fit"],
           "top_iou_fit_valid": res["views"]["top"]["iou_fit_valid"], "triangles_total": res["triangles"],
           "all_parts_pass": all(v["pass"] for v in side["parts"].values()),
           "failing": [k for k, v in side["parts"].items() if not v["pass"]]}
    (PRIV / f"l2{('_' + tag) if tag else ''}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    return out


def main():
    a = sys.argv[1:]
    if IN_BLENDER:
        mode = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build"])[0]
        {"build": _blender_build, "sweep": _blender_sweep}[mode]()
        return
    cmd = a[0] if a else "build"
    tag = a[a.index("--tag") + 1] if "--tag" in a else "cur"
    if cmd == "build":
        _run_blender(PRIV / "base.blend", "build")
    elif cmd == "crop":
        crop(tag)
    elif cmd == "l2":
        l2(tag)
    elif cmd == "sweep":
        _run_blender(PRIV / "rs.blend", "sweep")
    elif cmd == "camera":
        camera()


if __name__ == "__main__":
    main()
