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
    "p1": dict(az=-105.0, el=18.0, dist=122.0, target=(4.0, -8.0, 141.0), lens=75.0, roll=0.0, floor=True),
    "p2": dict(az=-70.0, el=12.0, dist=155.0, target=(0.0, 0.0, 74.0), lens=75.0, roll=0.0, floor=True,
               view_local=150.0),
    # p3: the grenade lies tilted with its base toward the camera (the object is turned, not the light):
    #     the base-end normal is aimed tilt deg off the view ray, the axis runs to the image's upper left
    "p3": dict(az=-90.0, el=28.0, dist=175.0, target=(0.0, 0.0, 0.0), lens=75.0, roll=0.0, floor=False,
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


def part_compares(row_png, close_pngs, out_dir: Path):
    """reference crop | ours, at the same reference pixels, 2x; one image per part (the four views stacked) and one per
    close-up panel."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ref = ref_image()
    row = LK.load_png(row_png)
    made = []
    for part, (h0, h1, x0, x1) in PARTS.items():
        tiles = []
        for v in ("v1", "v2", "v3", "v4"):
            cx, by = VIEW_CX[v], VIEW_BOTTOM[v]
            box = (cx + x0 * D_PX, by - h1 * D_PX, cx + x1 * D_PX, by - h0 * D_PX)
            a, b = _crop(ref, box), _crop(row, box)
            hh = min(a.shape[0], b.shape[0])
            ww = min(a.shape[1], b.shape[1])
            pair = np.concatenate([a[:hh, :ww], np.full((hh, 4, 3), 0.9, np.float32), b[:hh, :ww]], 1)
            tiles.append(_up(pair, 2))
        wmax = max(t.shape[1] for t in tiles)
        tiles = [np.pad(t, ((0, 8), (0, wmax - t.shape[1]), (0, 0)), constant_values=0.9) for t in tiles]
        p = out_dir / f"fb_r1_compare_{part}.png"
        LK.save_png(p, np.concatenate(tiles, 0))
        made.append(str(p))
    for k, box in PANELS.items():
        a = _crop(ref, box)
        b = LK.load_png(close_pngs[k])[: a.shape[0], : a.shape[1]]
        pair = np.concatenate([a, np.full((a.shape[0], 6, 3), 0.9, np.float32), b], 1)
        p = out_dir / f"fb_r1_compare_{k}.png"
        LK.save_png(p, pair)
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


# =============================================================================== gallery shots
def render_hero(lod0, out_png, samples=256, res=(1600, 900), az=-60.0, el=22.0, dist=860.0):
    saved = _hide_all_but([lod0])
    rig = LK.Rig()
    try:
        LK.setup_cycles(samples, res=res)
        LK.studio(rig)
        tgt = (4.0, -4.0, 84.0)
        _look_camera(rig, _polar(az, el, dist, tgt), tgt, 75.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        _restore(saved)
    return str(out_png)


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
    out["back"] = render_hero(lod0, renders / "flashbang_back.png", samples=spp, az=120.0)
    out["wire"] = render_wire(lod0, renders / "flashbang_wire.png", samples=32 if quick else 64)
    out["lods"] = render_lods(objs["assembled"], renders / "flashbang_lods.png", report.get("lod_triangles") or [],
                              samples=spp // 2)
    return out


__all__ = ["render_all", "render_row", "render_closeup", "compose_sheet", "side_by_side", "part_compares",
           "row_metrics", "YAWS", "CLOSEUPS"]
