#!/usr/bin/env python
"""props_lib.flashbang_gallery - every SM_Flashbang render, from the BAKED maps only (bpy).

    reference row   one camera, four copies of LOD0 at the per-view yaws, exactly the reference's top-row scene
    close-ups       p1 fuze head, p2 perforated body, p3 base end, p4 one hole (cameras set to the panels' framing)
    sheet           the eight views composed into the reference's 1254 x 1254 layout, and the side-by-side
    part compares   reference crop | ours at the same pixels, per view and part (WorkFiles/flashbang/r1/)
    hero, wire, lods, back
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import flashbang_look as LK

PROJECT = Path(__file__).resolve().parents[3]
REF_NPY = PROJECT / "WorkFiles/flashbang/metrology/fb_ref_srgb.npy"
REF_PNG = PROJECT / "References/Flashbang/flashbang_reference.png"
#: per-view yaw = the object's LOCAL azimuth facing the camera (degrees).  Fitted in round 1 by rendering flat label
#: masks over a 5 deg sweep (WorkFiles/flashbang/r1/tools/fb_yaw_search.py) and by the views' own descriptions:
#: v1 the holes' best fit (-130), v2 lever hidden behind / ring edge-on right (170), v3 lever at the right limb (-110),
#: v4 the lever-side view whose holes AND lever both fit (-25).
YAWS = {"v1": -130.0, "v2": 170.0, "v3": -110.0, "v4": -25.0}
PANELS = {"p1": (6, 756, 318, 1220), "p2": (323, 756, 629, 1220), "p3": (634, 756, 939, 1220),
          "p4": (946, 756, 1249, 1220)}
VIEW_BOX = {"v1": (40, 30, 345, 725), "v2": (345, 30, 615, 725), "v3": (615, 30, 950, 725), "v4": (950, 30, 1240, 725)}
VIEW_CX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
VIEW_BOTTOM = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}
D_PX = 175.31
#: part boxes in D units (h0, h1, x0, x1): the Study's own part crops (fb_m22_parts.py)
PARTS = dict(head=(3.00, 3.97, -1.00, 1.15), sleeve_and_rowA=(2.15, 3.10, -0.62, 0.62),
             holes_rows=(0.85, 2.55, -0.62, 0.62), base_cap=(-0.04, 0.60, -0.62, 0.62),
             lever_lower=(0.70, 3.40, 0.35, 1.00))


def _hide_all_but(keep):
    saved = [(o, o.hide_render) for o in bpy.data.objects]
    for o in bpy.data.objects:
        o.hide_render = o not in keep
    return saved


def _restore(saved):
    for o, h in saved:
        try:
            o.hide_render = h
        except ReferenceError:
            pass


def _copies(src, n):
    out = [src]
    for _ in range(n - 1):
        c = src.copy()
        bpy.context.scene.collection.objects.link(c)
        out.append(c)
    return out


def ref_image():
    return np.load(REF_NPY)[..., :3].astype(np.float32)


# =============================================================================== reference row
def render_row(lod0, out_png, work, samples=256, yaws=YAWS):
    cps = _copies(lod0, 4)
    m0 = lod0.matrix_world.copy()
    saved = _hide_all_but(cps)
    rig = LK.Rig()
    try:
        LK.setup_cycles(samples)
        LK.studio(rig)
        cam, info = LK.row_camera(rig)
        LK.place_row({v: [c] for v, c in zip(("v1", "v2", "v3", "v4"), cps)}, yaws)
        LK.render(out_png)
    finally:
        rig.teardown()
        for c in cps[1:]:
            bpy.data.objects.remove(c, do_unlink=True)
        lod0.matrix_world = m0
        _restore(saved)
    return {"png": str(out_png), "camera": info, "yaws": yaws}


# =============================================================================== close-ups
def _look_camera(rig, loc_mm, target_mm, lens_mm, res, roll_deg=0.0, sensor=36.0):
    cam = bpy.data.cameras.new("FB_CloseCam")
    cam.sensor_fit = "HORIZONTAL" if res[0] >= res[1] else "VERTICAL"
    cam.sensor_width = sensor
    cam.sensor_height = sensor
    cam.lens = lens_mm
    cam.clip_start = 0.005
    ob = bpy.data.objects.new("FB_CloseCam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc_mm) * 0.001
    d = Vector(target_mm) * 0.001 - ob.location
    q = d.to_track_quat("-Z", "Y")
    ob.rotation_euler = (q @ Matrix.Rotation(math.radians(roll_deg), 4, "Z").to_quaternion()).to_euler()
    bpy.context.scene.camera = ob
    rig.objects.append(ob)
    return ob


def _polar(az_deg, el_deg, dist, target):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return (target[0] + dist * math.cos(e) * math.cos(a), target[1] + dist * math.cos(e) * math.sin(a),
            target[2] + dist * math.sin(e))


#: close-up framings (object local azimuth of the camera, elevation, distance mm, target mm, lens mm, roll deg),
#: set by eye against the reference panels
CLOSEUPS = {
    # ROUND 2b: p1 pulled back and raised to the reference panel's scale (housing ~7 px/mm, the sleeve's green
    # shoulder and the ring hanging in front of it in frame, the top plate seen from above)
    "p1": dict(az=-105.0, el=26.0, dist=165.0, target=(4.0, -8.0, 136.0), lens=75.0, roll=0.0, floor=True),
    # ROUND 2b: p2 re-framed to the reference panel - rows B and C, the ring line between them and the cap's top
    # chamfer at the bottom, the body a little larger, seen from slightly above with the line rising to the right
    "p2": dict(az=-70.0, el=20.0, dist=155.0, target=(0.0, 0.0, 44.0), lens=75.0, roll=14.0, floor=True,
               view_local=160.0),
    # p3: the grenade lies tilted with its base toward the camera (the object is turned, not the light):
    #     the base-end normal is aimed tilt deg off the view ray, the axis runs to the image's upper left
    "p3": dict(az=-90.0, el=28.0, dist=163.0,           # ROUND 2b: a little closer (the end face fills more of the panel)
 target=(0.0, 0.0, 0.0), lens=75.0, roll=0.0, floor=False,
               obj_tilt=25.0, obj_spin=-150.0, obj_yaw=-40.0),
    "p4": dict(az=-60.0, el=5.0, dist=58.0, target=(22.0 * math.cos(math.radians(52.0)),
                                                     22.0 * math.sin(math.radians(52.0)), 66.9), lens=75.0, roll=0.0,
               floor=True, view_local=70.0),
}


def render_closeup(lod0, key, out_png, samples=256, res=None):
    box = PANELS[key]
    res = res or (box[2] - box[0], box[3] - box[1])
    c = CLOSEUPS[key]
    saved = _hide_all_but([lod0])
    rig = LK.Rig()
    m0 = lod0.matrix_world.copy()
    try:
        LK.setup_cycles(samples, res=res)
        lod0.matrix_world = Matrix.Identity(4)
        if "obj_tilt" in c:
            # base normal (-Z) -> toward the camera, tilted; the object's own yaw picks which holes face us
            cam_dir = Vector(_polar(c["az"], c["el"], 1.0, (0, 0, 0))).normalized()
            q = Vector((0, 0, -1)).rotation_difference(cam_dir)
            tilt = Matrix.Rotation(math.radians(c["obj_tilt"]), 4, cam_dir.cross(Vector((0, 0, 1))).normalized())
            spin = Matrix.Rotation(math.radians(c["obj_spin"]), 4, cam_dir)
            R = spin @ tilt @ q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(c["obj_yaw"]), 4, "Z")
            lod0.matrix_world = Matrix.Translation(Vector(c["target"]) * 0.001) @ R @ Matrix.Translation((0, 0, -0.04))
        tgt = c["target"]
        if "view_local" in c:
            # turn the OBJECT so its local azimuth view_local faces a camera on the key's side (the lights stay put)
            M = Matrix.Rotation(math.radians(c["az"] - c["view_local"]), 4, "Z")
            lod0.matrix_world = M
            tgt = tuple(M @ Vector(tgt))
        LK.studio(rig, floor=c.get("floor", True), bg_lin=None if c.get("floor", True) else 0.024)
        loc = _polar(c["az"], c["el"], c["dist"], tgt)
        _look_camera(rig, loc, tgt, c["lens"], res, c["roll"])
        LK.render(out_png)
    finally:
        rig.teardown()
        lod0.matrix_world = m0
        _restore(saved)
    return {"png": str(out_png), **c, "res": list(res)}


# =============================================================================== sheet + compares
def compose_sheet(row_png, close_pngs, out_png):
    ref = ref_image()
    H, W = ref.shape[:2]
    row = LK.load_png(row_png)
    sheet = np.empty_like(ref)
    sheet[:] = LK.lin_to_srgb(LK.srgb_to_lin(np.array(LK.BG_SRGB) / 255.0))
    sheet[:748] = row[:748]
    # the reference's light panel frames: copy the frame pixels (layout only), then our panels inside
    frame = ref.copy()
    sheet[748:] = frame[748:]
    for k, (x0, y0, x1, y1) in PANELS.items():
        im = LK.load_png(close_pngs[k])
        sheet[y0:y1, x0:x1] = im[: y1 - y0, : x1 - x0]
    LK.save_png(out_png, sheet)
    return str(out_png)


def side_by_side(sheet_png, out_png, label_gap=12):
    ref = ref_image()
    ours = LK.load_png(sheet_png)
    gap = np.full((ref.shape[0], label_gap, 3), 0.9, np.float32)
    LK.save_png(out_png, np.concatenate([ref, gap, ours], 1))
    return str(out_png)


def _crop(img, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    h, w = img.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    return img[y0:y1, x0:x1]


def _up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


#: ROUND 2: the shipped round-1 (finalised) renders, kept for the three-way compares
R1_STATE = PROJECT / "WorkFiles/flashbang/r2/r1_state/Renders_Flashbang"


def part_compares(row_png, close_pngs, out_dir: Path):
    """reference crop | round 1 | round 2 (this build), at the same reference pixels, 2x; one image per part (the four
    views stacked) and one per close-up panel.  Round 1 = the shipped finalised renders in R1_STATE (skipped if absent)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ref = ref_image()
    row = LK.load_png(row_png)
    r1_row = R1_STATE / "flashbang_reference_row.png"
    row1 = LK.load_png(r1_row) if r1_row.is_file() else None
    sep = lambda h: np.full((h, 4, 3), 0.9, np.float32)
    made = []
    for part, (h0, h1, x0, x1) in PARTS.items():
        tiles = []
        for v in ("v1", "v2", "v3", "v4"):
            cx, by = VIEW_CX[v], VIEW_BOTTOM[v]
            box = (cx + x0 * D_PX, by - h1 * D_PX, cx + x1 * D_PX, by - h0 * D_PX)
            ims = [_crop(ref, box)] + ([_crop(row1, box)] if row1 is not None else []) + [_crop(row, box)]
            hh = min(a.shape[0] for a in ims)
            ww = min(a.shape[1] for a in ims)
            seq = []
            for a in ims:
                seq += [a[:hh, :ww], sep(hh)]
            tiles.append(_up(np.concatenate(seq[:-1], 1), 2))
        wmax = max(t.shape[1] for t in tiles)
        tiles = [np.pad(t, ((0, 8), (0, wmax - t.shape[1]), (0, 0)), constant_values=0.9) for t in tiles]
        p = out_dir / f"fb_r2_compare_{part}.png"
        LK.save_png(p, np.concatenate(tiles, 0))
        made.append(str(p))
    for k, box in PANELS.items():
        a = _crop(ref, box)
        ims = [a]
        c1 = R1_STATE / f"flashbang_closeup_{k}.png"
        if c1.is_file():
            ims.append(LK.load_png(c1)[: a.shape[0], : a.shape[1]])
        ims.append(LK.load_png(close_pngs[k])[: a.shape[0], : a.shape[1]])
        seq = []
        for im in ims:
            seq += [im, np.full((a.shape[0], 6, 3), 0.9, np.float32)]
        p = out_dir / f"fb_r2_compare_{k}.png"
        LK.save_png(p, np.concatenate(seq[:-1], 1))
        made.append(str(p))
    return made


# =============================================================================== metrics
def row_metrics(row_png) -> Dict[str, object]:
    """Per view: silhouette IoU against the Study's traced outline, olive-paint IoU, and the paint / steel / brass
    appearance percentiles (sRGB8) of ours against the reference, measured the same way."""
    ref = ref_image() * 255.0
    ours = LK.load_png(row_png) * 255.0
    spec = json.loads((PROJECT / "WorkFiles/flashbang/flashbang_spec.json").read_text())
    H, W = ref.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]

    def poly_mask(poly):
        poly = np.asarray(poly, float)
        m = np.zeros((H, W), bool)
        x0, y0 = poly.min(0).astype(int)
        x1, y1 = poly.max(0).astype(int) + 1
        sy, sx = yy[y0:y1, x0:x1] + 0.5, xx[y0:y1, x0:x1] + 0.5
        ins = np.zeros(sx.shape, bool)
        for i in range(len(poly)):
            xa, ya = poly[i]
            xb, yb = poly[(i + 1) % len(poly)]
            ins ^= ((ya > sy) != (yb > sy)) & (sx < (xb - xa) * (sy - ya) / (yb - ya + 1e-12) + xa)
        m[y0:y1, x0:x1] = ins
        return m

    def paint_mask(im):
        R, G, B = im[..., 0], im[..., 1], im[..., 2]
        return (np.abs(R - G) <= 6) & ((G - B) >= 8) & (G >= 22)

    def pct(im, m):
        if m.sum() < 20:
            return None
        lum = im[m] @ np.array([0.2126, 0.7152, 0.0722])
        o = np.argsort(lum)
        k = [o[int(len(o) * q)] for q in (0.1, 0.5, 0.9)]
        return [[int(round(x)) for x in im[m][i]] for i in k]

    rp, op = paint_mask(ref), paint_mask(ours)
    out = {}
    for v, (x0, y0, x1, y1) in VIEW_BOX.items():
        sl = (slice(y0, y1), slice(x0, x1))
        sil = poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"])[sl]
        # our silhouette: differs from the backdrop by > 6 levels
        bg = np.median(ours[5:25, 5:60].reshape(-1, 3), axis=0)
        osil = (np.abs(ours[sl] - bg).max(axis=2) > 7)
        iou = float((sil & osil).sum() / max((sil | osil).sum(), 1))
        a, b = rp[sl], op[sl]
        piou = float((a & b).sum() / max((a | b).sum(), 1))
        out[v] = {"silhouette_iou": round(iou, 4), "paint_iou": round(piou, 4),
                  "paint_fraction_ref": round(float(a[sil].mean()), 4) if sil.any() else None,
                  "paint_fraction_ours": round(float(b[osil].mean()), 4) if osil.any() else None,
                  "paint_p10_p50_p90_ref": pct(ref[sl], a), "paint_p10_p50_p90_ours": pct(ours[sl], b)}
    # background
    out["background_p50_ref"] = [int(x) for x in np.median(ref[5:25, 5:300].reshape(-1, 3), axis=0)]
    out["background_p50_ours"] = [int(x) for x in np.median(ours[5:25, 5:300].reshape(-1, 3), axis=0)]
    return out


# =============================================================================== FINALISE checks
def render_row_alpha(lod0, out_png, yaws=YAWS, samples=16):
    """The reference row's four copies with a transparent film and NO backdrop: its alpha says where the background
    shows.  Returns the alpha (H, W) in [0, 1] (row 0 = top)."""
    cps = _copies(lod0, 4)
    m0 = lod0.matrix_world.copy()
    saved = _hide_all_but(cps)
    rig = LK.Rig()
    sc = bpy.context.scene
    try:
        LK.setup_cycles(samples, denoise=False)
        LK.studio(rig, floor=False)
        cam, info = LK.row_camera(rig)
        LK.place_row({v: [c] for v, c in zip(("v1", "v2", "v3", "v4"), cps)}, yaws)
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        LK.render(out_png)
        im = bpy.data.images.load(str(Path(out_png).resolve()), check_existing=False)
        w, h = im.size
        a = np.empty(w * h * 4, np.float32)
        im.pixels.foreach_get(a)
        bpy.data.images.remove(im)
        alpha = a.reshape(h, w, 4)[::-1, :, 3].copy()
    finally:
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
        rig.teardown()
        for c in cps[1:]:
            bpy.data.objects.remove(c, do_unlink=True)
        lod0.matrix_world = m0
        _restore(saved)
    return alpha


def see_through(alpha, spec) -> Dict[str, int]:
    """Background pixels INSIDE each view's perforated body (the band between the cap top and the sleeve step,
    within 0.9 of the body radius of the view's axis): there must be none (the reference's limb holes read dark)."""
    out = {}
    D = spec.body_r * 2.0
    for v in ("v1", "v2", "v3", "v4"):
        cx, by = VIEW_CX[v], VIEW_BOTTOM[v]
        y0 = int(round(by - spec.sleeve_z0 / D * D_PX)) + 2
        y1 = int(round(by - spec.body_z0 / D * D_PX)) - 2
        x0 = int(round(cx - 0.45 * D_PX))
        x1 = int(round(cx + 0.45 * D_PX))
        box = alpha[y0:y1, x0:x1]
        out[v] = int((box < 0.5).sum())
    return out


def _fov_camera(rig, loc_mm, target_mm, res, hfov_deg=90.0):
    cam = bpy.data.cameras.new("FB_FpCam")
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    cam.lens = 18.0 / math.tan(math.radians(hfov_deg / 2.0))
    cam.clip_start = 0.005
    ob = bpy.data.objects.new("FB_FpCam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc_mm) * 0.001
    ob.rotation_euler = (Vector(target_mm) * 0.001 - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    rig.objects.append(ob)
    return ob


def _render_rgba(png):
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    try:
        LK.render(png)
    finally:
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
    im = bpy.data.images.load(str(Path(png).resolve()), check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1].copy()


def lod_pop(lods, switch_m, out_dir: Path, samples=48, res=(1920, 1080), turns=(30.0, 120.0, 240.0)):
    """FINALISE gate (craft review): at each shipped switch distance (90 deg hfov, 1080p) render LODn and LODn+1 with
    the object turned three ways (the camera stays in front, key light as in every render); the fraction of object
    pixels (alpha of either) whose colour changes by more than 20/255 (any channel, over a mid-grey) must be < 2 %."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = {"switch_m": list(switch_m), "views": []}
    worst = 0.0
    tgt0 = Vector((2.0, -3.0, 84.0))
    for k, d in enumerate(switch_m):
        pair = (lods[k], lods[k + 1])
        for turn in turns:
            imgs = []
            for o in pair:
                saved = _hide_all_but([o])
                rig = LK.Rig()
                m0 = o.matrix_world.copy()
                sc = bpy.context.scene
                try:
                    R = Matrix.Rotation(math.radians(turn), 4, "Z")
                    o.matrix_world = R
                    tgt = tuple(R @ tgt0)
                    LK.setup_cycles(samples, res=res)
                    sc.cycles.seed = 7
                    LK.studio(rig, floor=False)
                    _fov_camera(rig, _polar(-90.0, 12.0, d * 1000.0, tgt), tgt, res)
                    png = out_dir / f"lodpop_d{k}_turn{int(turn)}_{o.name}.png"
                    imgs.append(_render_rgba(png))
                finally:
                    rig.teardown()
                    o.matrix_world = m0
                    _restore(saved)
            a, b = imgs
            grey = 0.18
            ca = a[..., :3] + (1 - a[..., 3:4]) * grey
            cb = b[..., :3] + (1 - b[..., 3:4]) * grey
            obj = (a[..., 3] > 0.5) | (b[..., 3] > 0.5)
            diff = np.abs(ca - cb).max(2) > 20 / 255
            frac = float((diff & obj).sum() / max(obj.sum(), 1))
            worst = max(worst, frac)
            rep["views"].append({"switch": k + 1, "distance_m": round(d, 4), "turn": turn,
                                 "object_px": int(obj.sum()), "frac_gt20": round(frac, 5)})
            if turn == turns[0]:
                # the noise floor: the SAME LOD (the nearer one) rendered with another sampling seed
                o = pair[0]
                saved = _hide_all_but([o])
                rig = LK.Rig()
                m0 = o.matrix_world.copy()
                sc = bpy.context.scene
                try:
                    R = Matrix.Rotation(math.radians(turn), 4, "Z")
                    o.matrix_world = R
                    tgt = tuple(R @ tgt0)
                    LK.setup_cycles(samples, res=res)
                    sc.cycles.seed = 8
                    LK.studio(rig, floor=False)
                    _fov_camera(rig, _polar(-90.0, 12.0, d * 1000.0, tgt), tgt, res)
                    c = _render_rgba(out_dir / f"lodpop_d{k}_turn{int(turn)}_{o.name}_seed8.png")
                finally:
                    rig.teardown()
                    o.matrix_world = m0
                    _restore(saved)
                cc = c[..., :3] + (1 - c[..., 3:4]) * grey
                nf = float(((np.abs(ca - cc).max(2) > 20 / 255) & obj).sum() / max(obj.sum(), 1))
                rep.setdefault("noise_floor", []).append({"switch": k + 1, "turn": turn, "frac_gt20_same_lod_other_seed":
                                                          round(nf, 5)})
                LK.save_png(out_dir / f"lodpop_diff_d{k}_turn{int(turn)}.png",
                            np.repeat((np.abs(ca - cb).max(2) * 4)[..., None], 3, 2))
    rep["worst_frac_gt20"] = round(worst, 5)
    nfl = {e["switch"]: e["frac_gt20_same_lod_other_seed"] for e in rep.get("noise_floor", [])}
    exc = max(v["frac_gt20"] - nfl.get(v["switch"], 0.0) for v in rep["views"])
    rep["worst_excess_over_noise_floor"] = round(exc, 5)
    rep["rule"] = ("pass when the worst view's changed fraction, less that switch's render-noise floor (the same LOD "
                   "rendered with another seed), is under 2 % of the object pixels; the raw fraction is reported too")
    rep["pass"] = exc < 0.02
    return rep


# =============================================================================== gallery shots
def render_hero(lod0, out_png, samples=256, res=(1600, 900), az=-60.0, el=22.0, dist=640.0, turn=0.0):
    """``turn`` rotates the OBJECT (the back view): the camera stays in front of the backdrop.  FINALISE: round 1's
    back view put the camera behind the backdrop sweep (an empty frame)."""
    saved = _hide_all_but([lod0])
    rig = LK.Rig()
    m0 = lod0.matrix_world.copy()
    try:
        LK.setup_cycles(samples, res=res)
        LK.studio(rig)
        R = Matrix.Rotation(math.radians(turn), 4, "Z")
        lod0.matrix_world = R
        tgt = tuple(R @ Vector((4.0, -4.0, 84.0)))
        _look_camera(rig, _polar(az, el, dist, tgt), tgt, 75.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        lod0.matrix_world = m0
        _restore(saved)
    return str(out_png)


def frame_coverage(png) -> float:
    """Fraction of the frame that differs from its corner backdrop by > 8/255 (a gallery render must show the object:
    > 5 %)."""
    im = LK.load_png(png)
    bg = np.median(im[:30, :30].reshape(-1, 3), axis=0)
    return float((np.abs(im - bg).max(2) > 8 / 255).mean())


def render_wire(lod0, out_png, samples=64, res=(1600, 900)):
    """LOD0 in flat clay with its wireframe (Wireframe node, 1 px)."""
    saved = _hide_all_but([lod0])
    mats = list(lod0.data.materials)
    m = bpy.data.materials.new("FB_Wire")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    wire = nt.nodes.new("ShaderNodeWireframe")
    wire.use_pixel_size = True
    wire.inputs["Size"].default_value = 1.0
    b1 = nt.nodes.new("ShaderNodeBsdfDiffuse")
    b1.inputs["Color"].default_value = (0.35, 0.36, 0.38, 1)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (0.02, 0.5, 0.9, 1)
    e.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(wire.outputs[0], mix.inputs[0])
    nt.links.new(b1.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    rig = LK.Rig()
    try:
        lod0.data.materials.clear()
        for _ in mats:
            lod0.data.materials.append(m)
        LK.setup_cycles(samples, res=res)
        LK.studio(rig)
        tgt = (4.0, -4.0, 84.0)
        _look_camera(rig, _polar(-60.0, 22.0, 860.0, tgt), tgt, 75.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        lod0.data.materials.clear()
        for mm in mats:
            lod0.data.materials.append(mm)
        bpy.data.materials.remove(m)
        _restore(saved)
    return str(out_png)


def render_lods(lods, out_png, tris, samples=128, res=(1600, 900)):
    saved = _hide_all_but(list(lods))
    rig = LK.Rig()
    ms = [o.matrix_world.copy() for o in lods]
    txt = []
    try:
        LK.setup_cycles(samples, res=res)
        for i, o in enumerate(lods):
            o.matrix_world = Matrix.Translation(((i - 1) * 0.085, 0.0, 0.0)) @ Matrix.Rotation(math.radians(-60 + 90), 4, "Z")
        for i, t in enumerate(tris):
            cu = bpy.data.curves.new(f"FB_Label{i}", "FONT")
            cu.body = f"LOD{i}  {t} tris"
            cu.size = 0.009
            cu.align_x = "CENTER"
            ob = bpy.data.objects.new(f"FB_Label{i}", cu)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = ((i - 1) * 0.085, -0.03, 0.0005)
            ob.data.materials.append(LK._mat_diffuse("FB_LabelMat", (0.8, 0.8, 0.8), 0.6))
            txt.append(ob)
            rig.objects.append(ob)
        LK.studio(rig)
        tgt = (0.0, 0.0, 80.0)
        _look_camera(rig, _polar(-90.0, 14.0, 640.0, tgt), tgt, 50.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        for o, m in zip(lods, ms):
            o.matrix_world = m
        _restore(saved)
    return str(out_png)


def render_all(spec, objs, report, renders: Path, r1: Path, work: Path, quick=False, log=print):
    renders.mkdir(parents=True, exist_ok=True)
    spp = 64 if quick else 384
    lod0 = objs["assembled"][0]
    out = {}
    log("render: reference row")
    out["row"] = render_row(lod0, renders / "flashbang_reference_row.png", work, samples=spp)
    closes = {}
    for k in PANELS:
        log(f"render: close-up {k}")
        closes[k] = render_closeup(lod0, k, renders / f"flashbang_closeup_{k}.png", samples=spp)["png"]
    out["closeups"] = closes
    sheet = compose_sheet(out["row"]["png"], closes, renders / "flashbang_eight_views.png")
    out["sheet"] = sheet
    out["side_by_side"] = side_by_side(sheet, renders / "flashbang_side_by_side.png")
    out["part_compares"] = part_compares(out["row"]["png"], closes, r1)
    out["row_metrics"] = row_metrics(out["row"]["png"])
    log("render: hero / wire / lods")
    out["hero"] = render_hero(lod0, renders / "flashbang_hero.png", samples=spp)
    out["back"] = render_hero(lod0, renders / "flashbang_back.png", samples=spp, turn=180.0)
    out["wire"] = render_wire(lod0, renders / "flashbang_wire.png", samples=32 if quick else 64)
    out["lods"] = render_lods(objs["assembled"], renders / "flashbang_lods.png", report.get("lod_triangles") or [],
                              samples=spp // 2)
    out["coverage"] = {k: round(frame_coverage(out[k]), 4) for k in ("hero", "back", "wire", "lods")}
    out["coverage_pass"] = all(v > 0.05 for v in out["coverage"].values())
    log("render: see-through alpha row (every LOD)")
    st_all = {}
    for i, o in enumerate(objs["assembled"]):
        alpha = render_row_alpha(o, work / (f"flashbang_row_alpha.png" if i == 0 else f"flashbang_row_alpha_lod{i}.png"))
        st_all[f"LOD{i}"] = see_through(alpha, spec)
    for v in ("v1", "v2", "v3", "v4"):
        out["row_metrics"].setdefault(v, {})["see_through_px"] = sum(st_all[k][v] for k in st_all)
    out["see_through_px_per_lod"] = st_all
    log(f"  see-through px per LOD and view: {st_all}")
    log("render: LOD pop at the switch distances")
    sw = report["measure"]["assembled"]["switch_distances_m"]
    out["lod_pop"] = lod_pop(objs["assembled"], sw, work / "lodpop", samples=24 if quick else 48)
    log(f"  LOD pop worst frac(>20/255) {out['lod_pop']['worst_frac_gt20']}")
    return out


__all__ = ["render_all", "render_row", "render_closeup", "compose_sheet", "side_by_side", "part_compares",
           "row_metrics", "YAWS", "CLOSEUPS"]
