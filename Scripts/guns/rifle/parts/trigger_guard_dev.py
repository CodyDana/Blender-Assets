"""Trigger guard detail loop harness (detail pass round 1; private scratch so the parallel part builders never share
files): WorkFiles/guns/rifle/scratch/detail/trigger_guard/.

    py -3 -B Scripts/guns/rifle/parts/trigger_guard_dev.py segment             reference part masks in c1 / c6
    blender -b <scratch>/base.blend --factory-startup --python Scripts/guns/rifle/parts/trigger_guard_dev.py -- blend
                                                                                 rebuild trigger + trigger_guard into a
                                                                                 copy of the form blend, sweeps, gaps
    py -3 -B Scripts/guns/rifle/parts/trigger_guard_dev.py render --tag r1_i1  ROUGH LOOK crops (gunlib DetailKit)
    py -3 -B Scripts/guns/rifle/parts/trigger_guard_dev.py metrics --tag r1_i1 part IoU in the close-ups + side L2

base.blend / base_tris.npz are a snapshot of the form build (Assets/Guns/AR01.blend + scratch/form_tris.npz) taken
at the start of the round; the part cameras are the ones rifle_detail.py solved on it (copied, not re-solved).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
from rifle_common import SCRATCH, REVIEW, GRIP  # noqa: E402

PART = "trigger_guard"
PRIV = SCRATCH / "detail" / PART
OBJS = ("trigger", "trigger_guard")
PANELS = ("c6", "c1")
REVIEW_PART = REVIEW / "detail" / PART


# ============================================================================================ inside Blender
def blender_main(argv):
    import bpy
    import numpy as np
    sys.path.insert(0, str(RIFLE.parent))
    from gunlib import bl
    from gunlib import fit as F
    from gunlib.parts import BuildCtx
    import importlib
    import rifle_common
    mod = importlib.import_module("parts." + PART)
    for n in OBJS:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    coll = bpy.data.collections.get("AR01_Parts")
    ctx = BuildCtx(coll, GRIP, rifle_common.SPEC, set(OBJS))
    built = mod.build(rifle_common.SPEC, ctx)
    rep = {}
    for k, obs in built.items():
        for ob in obs:
            rep[ob.name] = bl.manifold_report(ob)
            print("[TG] part", ob.name, json.dumps(rep[ob.name]))
    bpy.ops.wm.save_as_mainfile(filepath=str(PRIV / "cur.blend"))
    # npz in the snapshot's object order
    D = np.load(PRIV / "base_tris.npz")
    names = [str(n) for n in D["names"]]
    objs = [bpy.data.objects[n] for n in names]
    bl.export_npz(objs, PRIV / "cur_tris.npz", GRIP, names)
    total = sum(len(bl.tris_np(o, GRIP)[1]) for o in objs)
    out = {"parts": rep, "total_tris_all_objects": int(total),
           "total_tris_rifle_no_mag": int(total - sum(len(bl.tris_np(bpy.data.objects[n], GRIP)[1])
                                                      for n in ("magazine", "magazine_floor_plate")))}
    if "--no-sweep" not in argv:
        meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
        G = F.geom(meshes)
        B = lambda p: np.asarray(p, float) - GRIP  # noqa: E731
        groups = {"trigger": (["trigger"], B([318.0, 0, -20.0]), [0, 1, 0], 12.0),
                  "mag_release": (["mag_catch"], B([362.0, 0, -50.0]), [0, -1, 0], 10.0)}
        out["sweeps"] = {}
        import math
        for g, (pn, pv, ax, hi) in groups.items():
            mov = {n: G[n] for n in pn}
            fixed = {n: v for n, v in G.items() if n not in pn}
            V = np.vstack([G[n][0] for n in pn])
            rmax = float(np.linalg.norm(V - pv, axis=1).max())
            step = min(1.0, math.degrees(0.10 / rmax))
            vals = np.arange(0.0, hi + 1e-9, step)
            if vals[-1] < hi - 1e-9:
                vals = np.r_[vals, hi]
            motion = (lambda p_, a_: (lambda v: F.rot_matrix(p_, a_, v)))(pv, ax)
            recs, summ = F.sweep(mov, fixed, motion, vals, clearance_every=1)
            summ["row_mm"] = [0.10, 0.30]
            summ["pass"] = (summ["intersecting_steps"] == 0 and summ["min_clearance_mm"] >= 0.10 - 1e-4
                            and summ["min_clearance_mm"] <= 0.30 + 1e-4)
            out["sweeps"][g] = summ
            print("[TG] sweep", g, json.dumps(summ))
        pairs = F.pair_intersections(G)
        out["static_intersections_with_ours"] = [p for p in pairs if any(n in json.dumps(p) for n in OBJS)]
        cp = [("pistol_grip", "trigger_guard"), ("trigger_guard", "receiver"), ("trigger", "receiver"),
              ("trigger", "trigger_guard"), ("mag_catch", "trigger_guard"), ("magazine", "trigger_guard"),
              ("rivets", "trigger_guard")]
        cp = [tuple(sorted(p)) for p in cp]
        out["contact_gaps"] = F.min_gaps(G, cp)
        print("[TG] gaps", json.dumps(out["contact_gaps"]))
    (PRIV / "blend_result.json").write_text(json.dumps(out, indent=1))
    print("[TG] BLEND_DONE")


# ============================================================================================ plain Python
def kit():
    import rifle_detail as RD
    from gunlib.detail import DetailKit
    cfg = dict(RD.kit().cfg)
    cfg["npz"] = str(PRIV / "cur_tris.npz")
    cfg["blend"] = str(PRIV / "cur.blend")
    cfg["scratch_dir"] = str(PRIV / "kit")
    cfg["parts"] = {PART: cfg["parts"][PART]}
    cam_dir = PRIV / "kit" / "cameras"
    cam_dir.mkdir(parents=True, exist_ok=True)
    src = SCRATCH / "detail" / "cameras"
    for p in list(src.glob(f"{PART}__*.json")) + [src / f"panel_{k}.json" for k in ("c1", "c6")]:
        if not (cam_dir / p.name).exists():
            shutil.copy(p, cam_dir / p.name)
    return DetailKit(cfg)


def part_zone(K, key):
    """Panel px zone of the part: below the flange's lower edge (Z -34.9 on the near face), between X 297 (behind it
    is the grip) and X 356 (in front is the catch housing, mag_catch label in the trace convention)."""
    import numpy as np
    cam = K.part_camera(PART, key)
    H, W = K.mask(key).shape
    yface = 5.0 if key == "c6" else -5.0
    yy, xx = np.mgrid[0:H, 0:W]

    def side_of(p0, p1, q):
        a, b, c = cam.project(np.array([p0, p1, q], float))
        cr = (b[0] - a[0]) * (yy - a[1]) - (b[1] - a[1]) * (xx - a[0])
        cq = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return np.sign(cr) == np.sign(cq)
    z = side_of([200.0, yface, -34.9], [380.0, yface, -34.9], [320.0, yface, -60.0])
    z &= side_of([297.0, yface, -20.0], [297.0, yface, -90.0], [320.0, yface, -60.0])
    z &= side_of([356.0, yface, -20.0], [356.0, yface, -90.0], [320.0, yface, -60.0])
    return z


def ref_part_mask(K, key):
    """Steel of the guard + trigger in a close-up panel: foreground, not wood (chroma), below the receiver's bottom
    line (the flange's lower edge Z -34.8 projected on the near face) and behind the catch housing (X < 356)."""
    import numpy as np
    from scipy import ndimage as ndi
    from gunlib import closeup as CU
    P = K.panel(key)
    cam = K.part_camera(PART, key)
    m = K.mask(key)
    H, W = m.shape
    R, G, Bc = P[:, :, 0], P[:, :, 1], P[:, :, 2]
    wood = ((R - Bc) > 22) & ((R - G) > 8)
    wood = ndi.binary_opening(wood, iterations=1)
    wood = ndi.binary_closing(wood, iterations=3)
    wood = ndi.binary_fill_holes(wood)
    wood = ndi.binary_dilation(wood, iterations=1)
    sel = m & ~wood & part_zone(K, key)
    sel = CU.drop_small(sel, 30)
    return sel


def our_part_mask(K, key):
    """Visible pixels of our trigger + trigger_guard at the part camera (painter's order, all objects occluding)."""
    import numpy as np
    from gunlib import compare as C
    V, T, lab, names = K.geometry()
    cam = K.part_camera(PART, key)
    show = K.cfg["panels"][key].get("objects")
    keep = np.ones(len(T), bool) if not show else np.isin(lab, [names.index(n) for n in show])
    ids = [names.index(n) for n in OBJS]
    L = np.where(np.isin(lab, ids), 1, 0)
    from gunlib import closeup as CU
    Tk = T[keep]
    Lk = L[keep]
    vis = CU.visible_tris(cam, V, Tk)
    vis_set = {tuple(t) for t in vis.tolist()}
    fm = np.array([tuple(t) in vis_set for t in Tk.tolist()])
    cov = C.raster_labels(cam.project(V), Tk[fm], cam.depth(V), Lk[fm], (cam.H, cam.W), ss=3, nlab=2)
    # ours stops at the same zone as the reference selection
    return (cov[1] > 0.5) & part_zone(K, key)


def aligned_iou(ours, ref, roi, max_shift=8, scales=(0.94, 0.97, 1.0, 1.03, 1.06)):
    """IoU after the best similarity (scale about the ref part centroid + integer shift): the close-ups are not to
    scale, so the part is compared in its own frame."""
    import numpy as np
    from scipy import ndimage as ndi
    best = (0.0, 1.0, 0, 0)
    r = ref & roi
    cy, cx = [float(v) for v in ndi.center_of_mass(r)]
    H, W = ref.shape
    for s in scales:
        if abs(s - 1.0) > 1e-6:
            M = np.array([[1 / s, 0], [0, 1 / s]])
            off = np.array([cy, cx]) - M @ np.array([cy, cx])
            o = ndi.affine_transform(ours.astype(float), M, offset=off, order=1) > 0.5
        else:
            o = ours
        for dy in range(-max_shift, max_shift + 1):
            for dx in range(-max_shift, max_shift + 1):
                oo = np.roll(np.roll(o, dy, 0), dx, 1) & roi
                inter = (oo & r).sum()
                uni = (oo | r).sum()
                v = inter / max(uni, 1)
                if v > best[0]:
                    best = (float(v), s, dy, dx)
    return best


def metrics(tag):
    import numpy as np
    from PIL import Image
    K = kit()
    out = {"tag": tag, "panels": {}}
    for key in PANELS:
        x0, y0, x1, y1 = K.window(PART, key)
        roi = np.zeros(K.mask(key).shape, bool)
        roi[y0:y1, x0:x1] = True
        ref = ref_part_mask(K, key) & roi
        ours = our_part_mask(K, key) & roi
        raw = float((ref & ours).sum() / max((ref | ours).sum(), 1))
        al = aligned_iou(ours, ref, roi)
        out["panels"][key] = {"window_px": [x0, y0, x1, y1], "ref_px": int(ref.sum()), "our_px": int(ours.sum()),
                              "iou_raw": round(raw, 4), "iou_aligned": round(al[0], 4),
                              "align_scale_shift": [al[1], al[2], al[3]]}
        # overlay: ref only red, ours only blue, both white
        P = K.panel(key)[y0:y1, x0:x1].astype(np.uint8)
        o = np.roll(np.roll(ours, al[2], 0), al[3], 1)[y0:y1, x0:x1]
        r = ref[y0:y1, x0:x1]
        im = (P * 0.45).astype(np.uint8)
        im[r & ~o] = (230, 60, 50)
        im[o & ~r] = (60, 120, 255)
        im[r & o] = (235, 235, 235)
        k = 4
        Image.fromarray(im).resize((im.shape[1] * k, im.shape[0] * k), Image.NEAREST).save(
            REVIEW_PART / f"{tag}_partmask_{key}.png")
        print("[TG] part IoU", key, out["panels"][key])
    # side-view L2 (per-part gate, the form-stage rule) on the private npz
    import rifle_silhouette as RS
    res = RS.run(str(PRIV / "cur_tris.npz"), f"detail/{PART}/sil_{tag}")
    sp = res["views"]["side"]["parts"]
    out["side_L2"] = {k: sp[k] for k in ("trigger", "trigger_guard", "receiver", "mag_catch", "pistol_grip") if k in sp}
    out["side_iou_fit"] = res["views"]["side"]["iou_fit"]
    out["top_iou_fit_valid"] = res["views"]["top"]["iou_fit_valid"]
    print("[TG] side L2", json.dumps(out["side_L2"]))
    (REVIEW_PART / f"{tag}_metrics.json").write_text(json.dumps(out, indent=1))
    return out


def segment():
    import numpy as np
    from PIL import Image
    K = kit()
    for key in PANELS:
        x0, y0, x1, y1 = K.window(PART, key)
        ref = ref_part_mask(K, key)
        P = K.panel(key).astype(np.uint8)[y0:y1, x0:x1].copy()
        r = ref[y0:y1, x0:x1]
        P[r] = (0.5 * P[r] + 0.5 * np.array([255, 40, 40])).astype(np.uint8)
        Image.fromarray(P).resize((P.shape[1] * 4, P.shape[0] * 4), Image.NEAREST).save(PRIV / f"refmask_{key}.png")
        print(key, int(r.sum()))


def render(tag):
    K = kit()
    res = K.render_part_crop(PART, tag)
    print(json.dumps(res, indent=1)[:2000])


if __name__ == "__main__":
    if "bpy" in sys.modules or any(a.endswith("blender.exe") for a in sys.argv[:1]):
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        if argv and argv[0] == "blend":
            sys.path.insert(0, str(RIFLE.parent / ".." ))
            blender_main(argv)
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd", choices=["segment", "render", "metrics"])
        ap.add_argument("--tag", default="r1")
        a = ap.parse_args()
        {"segment": lambda: segment(), "render": lambda: render(a.tag), "metrics": lambda: metrics(a.tag)}[a.cmd]()
