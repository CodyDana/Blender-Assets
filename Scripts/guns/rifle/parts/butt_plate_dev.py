"""Butt-plate detail builder's loop driver (plain Python; detail pass round 1).

    py -3 -B Scripts/guns/rifle/parts/butt_plate_dev.py trace              c7 plate trace (the plate's own outline)
    py -3 -B Scripts/guns/rifle/parts/butt_plate_dev.py iter --tag r1_i1   isolated rebuild + ROUGH LOOK crops +
                                                                           plate IoU + side-view L2 for this part
    py -3 -B Scripts/guns/rifle/parts/butt_plate_dev.py profile --tag r1_i3 dense c7 vs rendered row widths of an
                                                                           iteration; the corrected section fit
                                                                           (round 2: butt_plate.C7_FIT came from it)

Isolation: the rebuild runs on a snapshot of the form blend (scratch/detail/butt_plate_wip/base_AR01.blend) and only
replaces buttstock / butt_plate / butt_screws (butt_plate_devbuild.py), so it never writes the shared form blend
while other part builders work. Crops go through gunlib DetailKit.render_part_crop with the rifle's kit config
(rifle_detail.kit) pointed at the private blend + npz and the already solved butt_plate cameras.

Plate IoU vs the c7 trace, "in the part's own frame": c7 is a stylised close-up and not to scale (it draws the plate
at ~0.6x the width the TOP view gives, with wood beside it), so the outline SHAPE is compared after mapping each mask's
bounding box onto the unit box (part frame u = across the plate, v = heel -> toe). The raw IoU at the solved camera
and the half-width profile w(v) are reported beside it.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
from rifle_common import ROOT, SCRATCH, REVIEW  # noqa: E402

import gunlib  # noqa: E402
from gunlib import closeup as CU  # noqa: E402
from gunlib import compare as C  # noqa: E402

WIP = SCRATCH / "detail" / "butt_plate_wip"
OUT = REVIEW / "detail" / "butt_plate"
import os  # noqa: E402
# round 2b: the snapshot can be switched (BP_BASE=<file in WIP>); r2b uses a copy of the integrated Assets/Guns/AR01.blend
BASE_BLEND = WIP / os.environ.get("BP_BASE", "base_AR01.blend")
PLATE_OBJS = ["butt_plate", "butt_screws"]


def kit(npz, blend):
    import rifle_detail as RD
    K = RD.kit()
    K.cfg["npz"] = str(npz)
    K.cfg["blend"] = str(blend)
    K.scratch = WIP
    K.cfg["scratch_dir"] = str(WIP)
    (WIP / "renders").mkdir(parents=True, exist_ok=True)
    return K


# ------------------------------------------------------------------------------------------ c7 plate trace
def plate_mask_c7(K):
    """The plate's own region in c7 (panel px): inside the butt silhouette, not wood (R - B > 12), opened, largest
    component, holes filled. The dark rolled rim is low-chroma, so it belongs to the plate."""
    P = K.panel("c7").astype(float)
    sil = K.mask("c7")
    wood = (P[..., 0] - P[..., 2]) > 12.0
    wood = ndi.binary_opening(wood, iterations=1)
    # backdrop level per row from the pixels outside the (dilated) silhouette: the panel's backdrop gradient is
    # not well fitted by the global polynomial at the top end
    L = P.mean(2)
    out = ~ndi.binary_dilation(sil, iterations=3)
    bgL, _, _, _ = CU.fit_background(K.panel("c7"))
    bg_row = np.array([np.median(L[y][out[y]]) if out[y].sum() > 5 else np.nan for y in range(L.shape[0])])
    bg = np.where(np.isnan(bg_row)[:, None], bgL, bg_row[:, None])
    near_bg = (np.abs(L - bg) < 6.0) & ((P.max(2) - P.min(2)) < 6.0)
    near_bg = ndi.binary_opening(near_bg, iterations=1)
    m = sil & ~wood & ~near_bg
    m = ndi.binary_opening(m, iterations=2)
    m = CU.largest_component(m)
    m = ndi.binary_fill_holes(ndi.binary_closing(m, iterations=2))
    return m


def save_mask_overlay(P, masks_colors, path, scale=3):
    im = Image.fromarray(P.astype(np.uint8)).resize((P.shape[1] * scale, P.shape[0] * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for m, col in masks_colors:
        b = C.boundary(m)
        ys, xs = np.nonzero(b)
        for y, x in zip(ys, xs):
            d.rectangle([x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1], fill=col)
    im.save(path)


def width_profile(m, n=21):
    ys, xs = np.nonzero(m)
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    W = x1 - x0 + 1
    out = []
    for t in np.linspace(0.02, 0.98, n):
        y = int(round(y0 + t * (y1 - y0)))
        row = np.nonzero(m[y])[0]
        out.append(round(float((row.max() - row.min() + 1) / W) if len(row) else 0.0, 3))
    return out


def section_profile(m, cam_x=-342.4, rear_x=(0.2, 8.8)):
    """Sub-pixel width of the c7 plate per row (Gaussian-softened mask, 0.5 crossings), smoothed along the rows,
    corrected for perspective depth (the rear face is 8.6 mm farther at the toe than at the heel), as a fraction of
    the widest row; v = 0 at the heel tip, 1 at the toe tip."""
    F = ndi.gaussian_filter(m.astype(float), 0.8)
    ys = np.nonzero(m.any(1))[0]
    rows = []
    for y in range(ys.min() - 2, ys.max() + 3):
        r = F[y]
        on = np.nonzero(r >= 0.5)[0]
        if len(on) == 0:
            continue
        a, b = on.min(), on.max()
        xl = a - (r[a] - 0.5) / max(r[a] - r[a - 1], 1e-6)
        xr = b + (r[b] - 0.5) / max(r[b] - r[b + 1], 1e-6)
        rows.append((y, xr - xl))
    rows = np.array(rows, float)
    # tips: the 0.5 level of the softened mask's column through the tip
    col = F[:, int(round(np.average(np.nonzero(m)[1])))]
    on = np.nonzero(col >= 0.5)[0]
    t0 = on.min() - (col[on.min()] - 0.5) / max(col[on.min()] - col[on.min() - 1], 1e-6)
    t1 = on.max() + (col[on.max()] - 0.5) / max(col[on.max()] - col[on.max() + 1], 1e-6)
    v = (rows[:, 0] - t0) / (t1 - t0)
    w = rows[:, 1] * (1.0 + (rear_x[0] + v * (rear_x[1] - rear_x[0])) / -cam_x)
    ok = (v > 0) & (v < 1)
    v, w = v[ok], w[ok]
    ws = ndi.gaussian_filter1d(w, 1.5, mode="nearest")
    ws[:3], ws[-3:] = w[:3], w[-3:]                 # keep the blunt tips (smoothing would round them twice)
    f = ws / ws.max()
    st = np.r_[0.004, 0.008, 0.013, 0.02, 0.03, 0.045, 0.065, 0.09, 0.12, 0.155, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
               0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.845, 0.88, 0.91, 0.935, 0.955, 0.97, 0.98, 0.987, 0.992, 0.996]
    return {"v": st.round(4).tolist(), "f": np.interp(st, v, f).round(4).tolist(),
            "tips_px": [round(float(t0), 2), round(float(t1), 2)], "w_max_px": round(float(ws.max()), 2)}


def unit_box(m, H=600, W=200, robust=False):
    """Map the mask's bounding box onto an H x W grid. robust=True takes the box's x-range from the 2nd / 98th
    percentile of the row extents, so a one-row bump on the trace's edge (wood fleck) does not set the width."""
    ys, xs = np.nonzero(m)
    x0, x1 = xs.min(), xs.max()
    if robust:
        rows = [np.nonzero(r)[0] for r in m[ys.min():ys.max() + 1]]
        x0 = int(round(np.percentile([r.min() for r in rows if len(r)], 2)))
        x1 = int(round(np.percentile([r.max() for r in rows if len(r)], 98)))
    sub = m[ys.min():ys.max() + 1, x0:x1 + 1].astype(np.uint8) * 255
    return np.asarray(Image.fromarray(sub).resize((W, H), Image.BILINEAR)) > 127


def cmd_trace(K):
    m = plate_mask_c7(K)
    P = K.panel("c7")
    save_mask_overlay(P, [(m, (255, 140, 0))], OUT / "trace_plate_c7.png")
    ys, xs = np.nonzero(m)
    rep = {"panel": "c7", "plate_bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
           "plate_w_over_h": round((xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1), 4),
           "half_width_profile_fraction_of_max_width (heel->toe, 21 stations)": width_profile(m),
           "method": "inside the c7 butt silhouette (DetailKit.mask), not wood (R-B > 12), opening 2, largest "
                     "component, holes filled; the dark rolled rim counts as plate"}
    rep["section_profile (butt_plate.C7_SECTION)"] = section_profile(m)
    np.save(WIP / "plate_mask_c7.npy", m)
    (OUT / "trace_plate_c7.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    return m, rep


# ------------------------------------------------------------------------------------------ build + crops
def devbuild(tag):
    blend = WIP / f"bp_{tag}.blend"
    npz = WIP / f"bp_{tag}_tris.npz"
    rep = WIP / f"bp_{tag}_build.json"
    log = WIP / f"bp_{tag}_build.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(BASE_BLEND), "--factory-startup", "--python",
                        str(HERE / "butt_plate_devbuild.py"), "--", "--out-blend", str(blend), "--out-npz", str(npz),
                        "--report", str(rep)], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "DEVBUILD_DONE" not in txt:
        print(txt[-3000:])
        raise SystemExit("devbuild failed: " + str(log))
    return blend, npz, json.loads(rep.read_text())


def plate_compare(K, npz, tag):
    ref = np.load(WIP / "plate_mask_c7.npy") if (WIP / "plate_mask_c7.npy").exists() else plate_mask_c7(K)
    cam = K.part_camera("butt_plate", "c7")
    D = np.load(npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    ids = [i for i, n in enumerate(names) if n in PLATE_OBJS]
    Tp = T[np.isin(lab, ids)]
    cov = C.raster_tris(cam.project(V), Tp, ref.shape, ss=4) > 0.5
    raw = C.iou(cov, ref)
    ub_o, ub_r = unit_box(cov), unit_box(ref)
    shape_iou = C.iou(ub_o, ub_r)
    shape_iou_robust = C.iou(unit_box(cov, robust=True), unit_box(ref, robust=True))
    # height-matched (uniform scale by height, centred): the aspect difference shows up here
    P = K.panel("c7")
    save_mask_overlay(P, [(ref, (255, 140, 0)), (cov, (0, 200, 255))], OUT / f"{tag}_plate_outline_c7.png")
    ov = np.zeros(ub_r.shape + (3,), np.uint8)
    ov[ub_r] = (255, 140, 0)
    ov[ub_o & ~ub_r] = (0, 170, 255)
    ov[ub_o & ub_r] = (90, 90, 90)
    Image.fromarray(ov).save(OUT / f"{tag}_plate_unitbox_c7.png")
    ys, xs = np.nonzero(cov)
    return {"plate_iou_unit_box (shape, part frame)": round(shape_iou, 4),
            "plate_iou_unit_box_robust (2/98 % row-extent box)": round(shape_iou_robust, 4),
            "plate_iou_raw_at_solved_camera": round(raw, 4),
            "ours_w_over_h_c7": round((xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1), 4),
            "ours_width_profile": width_profile(cov), "ref_width_profile": width_profile(ref),
            "width_profile_max_abs_diff": round(float(np.max(np.abs(np.subtract(width_profile(cov), width_profile(ref))))), 3)}


def side_l2(npz, tag):
    js = WIP / f"sil_{tag}.json"
    subprocess.run([sys.executable, "-B", str(RIFLE / "rifle_silhouette.py"), "--npz", str(npz), "--stage",
                    "detail/butt_plate/sil", "--tag", "_" + tag, "--json", str(js)], check=True,
                   stdout=subprocess.DEVNULL)
    d = json.loads(js.read_text())
    parts = d["views"]["side"]["parts"]
    return {"butt_plate": parts.get("butt_plate"), "stock": parts.get("stock"),
            "side_iou_fit": d["views"]["side"]["iou_fit"], "top_iou_fit_valid": d["views"]["top"]["iou_fit_valid"],
            "side_contour_p95": d["views"]["side"]["contour_px"]["p95"]}


def cmd_iter(tag):
    t0 = time.time()
    blend, npz, brep = devbuild(tag)
    K = kit(npz, blend)
    crops = K.render_part_crop("butt_plate", tag)["butt_plate"]
    pc = plate_compare(K, npz, tag)
    l2 = side_l2(npz, tag)
    res = {"tag": tag, "date": time.strftime("%Y-%m-%dT%H:%M:%S"), "build": brep, "plate_c7": pc, "crops": crops,
           "side_L2": l2, "seconds": round(time.time() - t0, 1)}
    (OUT / f"{tag}_result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("plate_c7", "side_L2")}, indent=1))
    print("tris", {k: v["triangles"] for k, v in brep.items() if isinstance(v, dict)}, "total", brep["_total_tris"])
    print("crops", {k: (v["silhouette_iou_window"], v["edges"]["f"]) for k, v in crops.items()})
    return res


# ------------------------------------------------------------------------------------------ profile correction
def dense_profiles(K, npz, ss=4):
    """Row widths (fraction of the widest row) of the c7 plate trace and of our projected plate, at ss x the panel
    resolution, on t = 0..1 (mask top .. bottom), Gaussian-smoothed along t."""
    ref = np.load(WIP / "plate_mask_c7.npy")
    cam = K.part_camera("butt_plate", "c7")
    D = np.load(npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    ids = [i for i, n in enumerate(names) if n in PLATE_OBJS]
    cov = C.raster_tris(cam.project(V) * ss, T[np.isin(lab, ids)], (ref.shape[0] * ss, ref.shape[1] * ss), ss=2) > 0.5
    refh = ndi.binary_fill_holes(ndi.zoom(ndi.gaussian_filter(ref.astype(float), 0.7), ss, order=1) > 0.5)

    def prof(m):
        ys = np.nonzero(m.any(1))[0]
        rows = np.arange(ys.min(), ys.max() + 1)
        w = np.array([(lambda r: r.max() - r.min() + 1 if len(r) else 0)(np.nonzero(m[y])[0]) for y in rows], float)
        return (rows - rows[0]) / (rows[-1] - rows[0]), w / w.max()
    tg = np.linspace(0, 1, 401)
    tr, wr = prof(refh)
    to, wo = prof(cov)
    fr = ndi.gaussian_filter1d(np.interp(tg, tr, wr), 3, mode="nearest")
    fo = ndi.gaussian_filter1d(np.interp(tg, to, wo), 3, mode="nearest")
    return tg, fr, fo, C.iou(unit_box(cov), unit_box(refh))


def _fit_model(p, v):
    vc, at, bt, ab, bb, kt, kb = p
    top = v < vc
    s = np.clip(np.where(top, (vc - v) / vc, (v - vc) / (1 - vc)), 0, 1)
    a, b, k = np.where(top, at, ab), np.where(top, bt, bb), np.where(top, kt, kb)
    return np.clip(1 - s ** a, 0, 1) ** b * (1 - k * s * s)


def cmd_profile(tag, gain=1.0):
    """f_new(v) = f_now(v) x (c7 row width / our row width at t = v), smoothed; fitted by butt_plate's profile model."""
    from scipy.optimize import least_squares
    from parts import butt_plate as BP
    npz = WIP / f"bp_{tag}_tris.npz"
    K = kit(npz, WIP / f"bp_{tag}.blend")
    tg, fr, fo, iou_hi = dense_profiles(K, npz)
    ratio = np.clip(ndi.gaussian_filter1d(fr / np.maximum(fo, 1e-3), 3, mode="nearest"), 0.5, 1.2)
    v = np.linspace(0.004, 0.996, 300)
    fnow = BP.c7_profile(v)
    tgt = fnow * (1 + gain * (np.interp(v, tg, ratio) - 1))
    tgt /= tgt.max()
    w = 1 + 2 * ((v < 0.06) | (v > 0.94))
    c = BP.C7_FIT
    p0 = [c["vc"], c["a_top"], c["b_top"], c["a_bot"], c["b_bot"], c.get("k_top", 0.05), c.get("k_bot", 0.05)]
    r = least_squares(lambda p: (_fit_model(p, v) - tgt) * w, p0,
                      bounds=([0.3, 1.2, 0.15, 1.2, 0.15, 0, 0], [0.6, 12, 1, 12, 1, 0.5, 0.5]))
    m = _fit_model(r.x, v)
    st = [0.004, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.996]
    rep = {"tag": tag, "unit_box_iou_hires": round(float(iou_hi), 4),
           "rows (t, c7, ours)": [(t, round(float(fr[int(round(t * 400))]), 3), round(float(fo[int(round(t * 400))]), 3))
                                  for t in st],
           "max_abs_row_diff": round(float(np.max(np.abs(fr - fo)[8:-8])), 3),
           "fit": dict(zip(["vc", "a_top", "b_top", "a_bot", "b_bot", "k_top", "k_bot"], np.round(r.x, 4).tolist())),
           "fit_rms": round(float(np.sqrt(np.mean((m - tgt) ** 2))), 4)}
    (OUT / f"{tag}_profile.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["trace", "iter", "base", "profile"])
    ap.add_argument("--tag", default="r1_i0")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "trace":
        cmd_trace(kit(WIP / "base_form_tris.npz", BASE_BLEND))
    elif a.cmd == "base":            # numbers of the untouched snapshot (no rebuild)
        K = kit(WIP / "base_form_tris.npz", BASE_BLEND)
        print(json.dumps(plate_compare(K, WIP / "base_form_tris.npz", a.tag), indent=1))
    elif a.cmd == "profile":
        cmd_profile(a.tag)
    else:
        cmd_iter(a.tag)


if __name__ == "__main__":
    main()
