"""Gate B4 'sight picture' (plain Python: numpy + PIL) on a gun's triangle dump (npz with V, T, lab, names; frame M).
Promoted from the AR-01's rifle_b4.py (gunlib 0.2.0); the notch method is the AR-01's to the bit, the aperture method
is new for diopter sights (SMG01, CB01).

    py -3 -B <shim> [--npz scratch/form_tris.npz] [--out scratch/b4_result.json] [--img png] [--lod-label LOD0]

The ADS camera: the eye RELIEF mm behind the Sight socket ON its line (the socket's +X = (cos p, 0, sin p) from its
Unreal pitch p), FOV horizontal, W x H. Every triangle is rasterised with a depth buffer (nearest surface wins,
perspective-correct 1/z) at SS x supersampling in a window round the image centre, so the measurement is
OCCLUSION-AWARE: what the eye actually sees through the notch / aperture.

kind "notch" (open sights, AR-01 R48): the rear sight's visible top edge per column; the notch = the run of columns
round the centre whose top edge lies deeper than the lobes; post tip vs the notch TOP line (the shoulders) and the
notch centre. Gate |lateral|, |vertical| <= tol_mm at the notch, post visible >= min_post_mm, no occluder.
kind "aperture" (diopter / ghost ring): the see-through hole of the rear sight round the image centre (4-neighbour
flood fill of the non-rear pixels from the centre; a hole touching the window edge = no closed aperture); its centroid
and equivalent diameter; the post's visible pixels inside it: tip row and tip centre column. Gate: the post tip at the
aperture centre within tol_mm both ways (the diopter picture: the eye centres the ring by itself, the tip sits in its
middle), post visible >= min_post_mm, no occluder except the parts listed as allowed (front sight ears / hood seen
round the post).

Config ``cfg.b4``: kind, socket ("Sight"), rear (part names), post (part name), ignore (parts that may show inside
the opening besides rear/post), fov, W, H, relief, ss, half, tol_mm, min_post_mm (notch), min_post_mm_aperture
(default 0.4 x the measured hole diameter), npz, out, img.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .. import raster as RZ

DEFAULTS = {"kind": "notch", "socket": "Sight", "fov": 55.0, "W": 2560, "H": 1440, "relief": 250.0, "ss": 8,
            "half": 110, "tol_mm": 0.2, "min_post_mm": 1.0, "ignore": []}


def conf(cfg):
    c = dict(DEFAULTS)
    c.update(cfg.b4)
    return c


def sight_camera(cfg, c):
    soc = cfg.socket(c["socket"])
    p = math.radians(soc["unreal_rotation_deg"]["pitch"])
    fwd = np.array([math.cos(p), 0.0, math.sin(p)])
    sight = np.array(soc["M_mm"], float)
    eye = sight - c["relief"] * fwd
    return RZ.Camera(eye, forward=fwd, up=(0.0, 0.0, 1.0), hfov_deg=c["fov"], W=c["W"], H=c["H"]), sight, eye, soc


def zbuffer(cam, V, T, lab, win, ss):
    """Nearest-surface label per supersample in the window (-1 = background)."""
    S, z = cam.project(V)
    x0, y0, x1, y1 = win
    w, h = (x1 - x0) * ss, (y1 - y0) * ss
    ID = np.full((h, w), -1, np.int32)
    IZ = np.zeros((h, w), np.float64)                        # 1/z of the nearest surface (0 = none)
    P = (S - np.array([x0, y0])) * ss
    tri, zt = P[T], z[T]
    ok = np.all(zt > 1.0, axis=1)
    lo = np.floor(tri.min(1) - 0.5).astype(int)
    hi = np.ceil(tri.max(1) + 0.5).astype(int)
    keep = ok & (hi[:, 0] > 0) & (hi[:, 1] > 0) & (lo[:, 0] < w) & (lo[:, 1] < h)
    for t, a, b, zz, lb in zip(tri[keep], lo[keep], hi[keep], zt[keep], lab[keep]):
        xa, ya = max(a[0], 0), max(a[1], 0)
        xb, yb = min(b[0], w), min(b[1], h)
        if xb <= xa or yb <= ya:
            continue
        X, Y = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = t
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any():
            continue
        iz = l1 / zz[0] + l2 / zz[1] + l3 / zz[2]
        sub = IZ[ya:yb, xa:xb]
        upd = m & (iz > sub)
        sub[upd] = iz[upd]
        ID[ya:yb, xa:xb][upd] = lb
    return ID


def _notch(c, ID, names, rear_ids, post_id, mm_px, win, res):
    SS = c["ss"]
    R = np.isin(ID, rear_ids)
    Hs, Ws = R.shape
    top = np.where(R.any(0), R.argmax(0), Hs).astype(float)          # rear sight's visible top edge (supersamples)
    cc = Ws // 2
    lobe_cols = np.r_[np.arange(cc - int(5.0 / mm_px * SS), cc - int(1.5 / mm_px * SS)),
                      np.arange(cc + int(1.5 / mm_px * SS), cc + int(5.0 / mm_px * SS))]
    notch_top = float(np.median(top[lobe_cols]))
    deep = top > notch_top + 0.5 / mm_px * SS                         # columns whose top edge is > 0.5 mm deeper
    l = cc
    while l > 0 and deep[l - 1]:
        l -= 1
    r = cc
    while r < Ws - 1 and deep[r + 1]:
        r += 1
    notch_cx = 0.5 * (l + r + 1)                                      # supersample units (pixel edges l .. r+1)
    floor = float(np.median(top[l + 2:r - 1])) if r - l > 4 else float(top[cc])
    P = ID == post_id
    in_notch = np.zeros_like(P)
    in_notch[:int(floor), l:r + 1] = True
    Pn = P & in_notch
    rows = np.nonzero(Pn.any(1))[0]
    if not len(rows):
        res.update({"pass": False, "error": "the post is not visible inside the notch"})
        return R, P, None
    tip = rows[0]
    band = Pn[tip:tip + max(1, int(0.3 / mm_px * SS))]
    cols = np.nonzero(band.any(0))[0]
    post_cx = cols.mean() + 0.5
    lat_px = (post_cx - notch_cx) / SS
    ver_px = (tip - notch_top) / SS                                # + = tip below the notch top line
    vis_mm_notch = (floor - tip) / SS * mm_px                      # visible post height (at the notch scale)
    occ = {}
    region = np.zeros_like(P)
    region[int(notch_top):int(floor), l:r + 1] = True
    for i in np.unique(ID[region]):
        if i >= 0 and i != post_id and i not in rear_ids and names[i] not in c["ignore"]:
            occ[names[i]] = int((ID[region] == i).sum())
    res.update({
        "notch": {"centre_x_px": round(win[0] + notch_cx / SS, 3), "top_y_px": round(win[1] + notch_top / SS, 3),
                  "floor_y_px": round(win[1] + floor / SS, 3), "width_px": round((r + 1 - l) / SS, 2),
                  "width_mm": round((r + 1 - l) / SS * mm_px, 3)},
        "post": {"centre_x_px": round(win[0] + post_cx / SS, 3), "tip_y_px": round(win[1] + tip / SS, 3),
                 "visible_height_in_notch_mm_at_notch": round(vis_mm_notch, 3),
                 "visible_px_in_notch": int(Pn.sum() / SS / SS)},
        "lateral_offset_px": round(lat_px, 3), "vertical_offset_px": round(ver_px, 3),
        "lateral_offset_mm": round(lat_px * mm_px, 4), "vertical_offset_mm": round(ver_px * mm_px, 4),
        "occluders_in_notch_px": occ,
        "rule": "|lateral|, |vertical| <= 0.2 mm at the notch; the post visible in the notch (>= 1.0 mm); no "
                "occluder in the notch opening"})
    res["pass"] = bool(abs(lat_px * mm_px) <= c["tol_mm"] and abs(ver_px * mm_px) <= c["tol_mm"]
                       and vis_mm_notch >= c["min_post_mm"] and not occ)
    return R, P, (notch_cx, notch_top)


def _aperture(c, ID, names, rear_ids, post_id, mm_px, win, res):
    SS = c["ss"]
    R = np.isin(ID, rear_ids)
    P = ID == post_id
    Hs, Ws = R.shape
    cy, cx = Hs // 2, Ws // 2
    hole = np.zeros_like(R)
    if R[cy, cx]:
        res.update({"pass": False, "error": "the image centre (the sight line) is on the rear sight, not in its "
                                            "aperture"})
        return R, P, None
    q = deque([(cy, cx)])
    hole[cy, cx] = True
    edge = False
    while q:
        y, x = q.popleft()
        for a, b in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= a < Hs and 0 <= b < Ws:
                if not R[a, b] and not hole[a, b]:
                    hole[a, b] = True
                    q.append((a, b))
            else:
                edge = True
    if edge:
        res.update({"pass": False, "error": "no closed aperture round the sight line inside the window"})
        return R, P, None
    ys, xs = np.nonzero(hole)
    hcx, hcy = xs.mean() + 0.5, ys.mean() + 0.5
    diam_px = 2.0 * math.sqrt(len(ys) / math.pi) / SS
    Pn = P & hole
    rows = np.nonzero(Pn.any(1))[0]
    occ = {}
    for i in np.unique(ID[hole]):
        if i >= 0 and i != post_id and i not in rear_ids and names[i] not in c["ignore"]:
            occ[names[i]] = int((ID[hole] == i).sum())
    res.update({"aperture": {"centre_x_px": round(win[0] + hcx / SS, 3), "centre_y_px": round(win[1] + hcy / SS, 3),
                             "diameter_px": round(diam_px, 3), "diameter_mm_at_aperture": round(diam_px * mm_px, 3)},
                "occluders_in_aperture_px": occ})
    if not len(rows):
        res.update({"pass": False, "error": "the post is not visible inside the aperture"})
        return R, P, (hcx, hcy)
    tip = rows[0]
    band = Pn[tip:tip + max(1, int(0.3 / mm_px * SS))]
    cols = np.nonzero(band.any(0))[0]
    post_cx = cols.mean() + 0.5
    lat_px = (post_cx - hcx) / SS
    ver_px = (tip - hcy) / SS                                      # + = tip below the aperture centre
    vis_mm = (ys.max() + 1 - tip) / SS * mm_px                     # visible post height inside the aperture
    min_vis = float(c.get("min_post_mm_aperture", 0.4 * diam_px * mm_px))
    res.update({"post": {"centre_x_px": round(win[0] + post_cx / SS, 3), "tip_y_px": round(win[1] + tip / SS, 3),
                         "visible_height_in_aperture_mm_at_aperture": round(vis_mm, 3),
                         "visible_px_in_aperture": int(Pn.sum() / SS / SS)},
                "lateral_offset_px": round(lat_px, 3), "vertical_offset_px": round(ver_px, 3),
                "lateral_offset_mm": round(lat_px * mm_px, 4), "vertical_offset_mm": round(ver_px * mm_px, 4),
                "rule": "post tip at the aperture centre: |lateral|, |vertical| <= %.2f mm at the aperture; post visible "
                        ">= %.2f mm inside the hole (0.4 x its diameter: the post fills the hole's lower half up to "
                        "the centre); no occluder but the allowed parts" % (c["tol_mm"], min_vis)})
    res["pass"] = bool(abs(lat_px * mm_px) <= c["tol_mm"] and abs(ver_px * mm_px) <= c["tol_mm"]
                       and vis_mm >= min_vis and not occ)
    return R, P, (hcx, hcy)


def measure(cfg, npz, out, img):
    c = conf(cfg)
    z = np.load(npz)
    V, T, lab, names = z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]
    cam, sight, eye, soc = sight_camera(cfg, c)
    W, H, HALF, SS = c["W"], c["H"], c["half"], c["ss"]
    win = (W // 2 - HALF, H // 2 - HALF, W // 2 + HALF, H // 2 + HALF)
    ID = zbuffer(cam, V, T, lab, win, SS)
    idx = {n: i for i, n in enumerate(names)}
    rear_ids = [idx[n] for n in c["rear"] if n in idx]
    post_id = idx[c["post"]]
    mm_px = 2.0 * math.tan(math.radians(c["fov"] / 2)) * c["relief"] / W     # mm per output px at the rear sight
    res = {"camera": {"eye_M": eye.round(4).tolist(), "socket_M": sight.tolist(),
                      "pitch_deg": soc["unreal_rotation_deg"]["pitch"], "fov_deg": c["fov"], "res": [W, H],
                      "eye_relief_mm": c["relief"], "supersample": SS, "window_px": list(win)},
           "mm_per_px_at_notch" if c["kind"] == "notch" else "mm_per_px_at_aperture": round(mm_px, 5)}
    if c["kind"] == "notch":
        R, P, mark = _notch(c, ID, names, rear_ids, post_id, mm_px, win, res)
    else:
        res["kind"] = c["kind"]
        R, P, mark = _aperture(c, ID, names, rear_ids, post_id, mm_px, win, res)
    # composite picture: background light, rear sight mid grey, post black, other parts darker grey
    pic = np.full(ID.shape + (3,), 205, np.uint8)
    pic[ID >= 0] = (150, 150, 150)
    pic[R] = (95, 95, 95)
    pic[P] = (15, 15, 15)
    im = Image.fromarray(pic).resize((ID.shape[1] // 2, ID.shape[0] // 2), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    f = 0.5
    if mark is not None and "lateral_offset_mm" in res:
        dr.line([(mark[0] * f, 0), (mark[0] * f, im.height)], fill=(0, 150, 0))
        dr.line([(0, mark[1] * f), (im.width, mark[1] * f)], fill=(0, 150, 0))
        if c["kind"] == "notch":
            dr.text((6, 6), "B4: lateral %.3f mm, vertical %.3f mm, post visible %.2f mm in the notch, %s" % (
                res["lateral_offset_mm"], res["vertical_offset_mm"], res["post"]["visible_height_in_notch_mm_at_notch"],
                "PASS" if res["pass"] else "FAIL"), fill=(200, 0, 0))
        else:
            dr.text((6, 6), "B4: lateral %.3f mm, vertical %.3f mm, post visible %.2f mm, aperture %.2f mm, %s" % (
                res["lateral_offset_mm"], res["vertical_offset_mm"],
                res["post"]["visible_height_in_aperture_mm_at_aperture"], res["aperture"]["diameter_mm_at_aperture"],
                "PASS" if res["pass"] else "FAIL"), fill=(200, 0, 0))
    Path(img).parent.mkdir(parents=True, exist_ok=True)
    im.save(img)
    try:
        res["image"] = cfg.rel(img)
    except ValueError:
        res["image"] = str(img)
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "camera"}, indent=1))
    return res


def main(cfg, argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    c = conf(cfg)
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(c.get("npz") or cfg.scratch / "form_tris.npz"))
    ap.add_argument("--out", default=str(c.get("out") or cfg.scratch / "b4_result.json"))
    ap.add_argument("--img", default=str(c.get("img") or cfg.review / "b4" / "b4_sight_picture.png"))
    a = ap.parse_args(argv)
    return measure(cfg, a.npz, a.out, a.img)
