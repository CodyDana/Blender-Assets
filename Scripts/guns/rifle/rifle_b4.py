"""AR-01 gate B4 'sight picture' (form realism round, plain Python: numpy + PIL), on scratch/form_tris.npz (frame M):

    py -3 -B Scripts/guns/rifle/rifle_b4.py [--npz scratch/form_tris.npz] [--out scratch/b4_result.json]

The ADS camera of the realism set: the eye 0.25 m behind the Sight socket ON its line (spec sockets: Sight at the notch
top centre, pitch toward the post tip; R48), 55 deg horizontal FOV, 2560 x 1440. Every triangle of the build is
rasterised with a depth buffer (nearest surface wins, perspective-correct 1/z) at 8x supersampling in a window round
the image centre, so the measurement is OCCLUSION-AWARE: what the eye actually sees through the notch.

Measured (output pixels, then mm AT THE NOTCH: 1 px = 2 tan(27.5 deg) 250 / 2560 = 0.1016 mm):
  notch     the rear sight (leaf + slider + block) visible top edge per column; the notch = the run of columns round
            the centre whose top edge lies deeper than the lobes; notch centre column = midway between its walls;
            notch top row = median top edge of the lobes 1.5-5 mm either side (the shoulders the tip is held level
            with);
  post      the front sight post's VISIBLE pixels inside the notch: tip row = first visible row, centre column = mean
            of the visible columns over the top 0.3 mm of the tip; visible height down to the notch floor;
  occluders any other part visible inside the notch opening above the notch floor (the 'broken sight line' tell).
Gate: |lateral| and |vertical| offsets <= 0.2 mm at the notch, the post visible (>= 1 mm of it in the notch) and no
occluder. Writes the composite sight picture (window, 4x) to review/realism_form3/b4_sight_picture.png.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SPEC, SCRATCH, REVIEW, ROOT  # noqa: E402
from gunlib import raster as RZ  # noqa: E402

FOV, W, H, RELIEF, SS = 55.0, 2560, 1440, 250.0, 8
HALF = 110                                   # window half size (output px): the lobes (+-7.2 mm = +-71 px) and the ears


def sight_camera():
    soc = {s["socket"]: s for s in SPEC.sockets["rifle"]}["Sight"]
    p = math.radians(soc["unreal_rotation_deg"]["pitch"])
    fwd = np.array([math.cos(p), 0.0, math.sin(p)])
    sight = np.array(soc["M_mm"], float)
    eye = sight - RELIEF * fwd
    return RZ.Camera(eye, forward=fwd, up=(0.0, 0.0, 1.0), hfov_deg=FOV, W=W, H=H), sight, eye, soc


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(SCRATCH / "form_tris.npz"))
    ap.add_argument("--out", default=str(SCRATCH / "b4_result.json"))
    ap.add_argument("--img", default=str(REVIEW / "realism_form3" / "b4_sight_picture.png"))
    a = ap.parse_args()
    z = np.load(a.npz)
    V, T, lab, names = z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]
    cam, sight, eye, soc = sight_camera()
    win = (W // 2 - HALF, H // 2 - HALF, W // 2 + HALF, H // 2 + HALF)
    ID = zbuffer(cam, V, T, lab, win, SS)
    idx = {n: i for i, n in enumerate(names)}
    rear_ids = [idx[n] for n in ("rear_sight_leaf", "rear_sight_slider", "rear_sight_block") if n in idx]
    post_id = idx["front_sight_post"]
    mm_px = 2.0 * math.tan(math.radians(FOV / 2)) * RELIEF / W           # mm per output px at the notch
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
    res = {"camera": {"eye_M": eye.round(4).tolist(), "socket_M": sight.tolist(),
                      "pitch_deg": soc["unreal_rotation_deg"]["pitch"], "fov_deg": FOV, "res": [W, H],
                      "eye_relief_mm": RELIEF, "supersample": SS, "window_px": list(win)},
           "mm_per_px_at_notch": round(mm_px, 5)}
    if not len(rows):
        res.update({"pass": False, "error": "the post is not visible inside the notch"})
    else:
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
            if i >= 0 and i != post_id and i not in rear_ids and names[i] not in ("front_sight_block",):
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
        res["pass"] = bool(abs(lat_px * mm_px) <= 0.2 and abs(ver_px * mm_px) <= 0.2 and vis_mm_notch >= 1.0
                       and not occ)
    # composite picture: background light, rear sight mid grey, post black, other parts darker grey
    img = np.full(ID.shape + (3,), 205, np.uint8)
    img[ID >= 0] = (150, 150, 150)
    img[R] = (95, 95, 95)
    img[P] = (15, 15, 15)
    im = Image.fromarray(img).resize((ID.shape[1] // 2, ID.shape[0] // 2), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    f = 0.5
    if "notch" in res:
        dr.line([(notch_cx * f, 0), (notch_cx * f, im.height)], fill=(0, 150, 0))
        dr.line([(0, notch_top * f), (im.width, notch_top * f)], fill=(0, 150, 0))
        dr.text((6, 6), "B4: lateral %.3f mm, vertical %.3f mm, post visible %.2f mm in the notch, %s" % (
            res["lateral_offset_mm"], res["vertical_offset_mm"], res["post"]["visible_height_in_notch_mm_at_notch"],
            "PASS" if res["pass"] else "FAIL"), fill=(200, 0, 0))
    Path(a.img).parent.mkdir(parents=True, exist_ok=True)
    im.save(a.img)
    res["image"] = str(Path(a.img).resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "camera"}, indent=1))


if __name__ == "__main__":
    main()
