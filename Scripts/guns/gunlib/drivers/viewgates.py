"""Stage-4 view gates (plain Python, numpy + PIL) on the static twin's per-LOD triangle dumps (lod<k>_tris.npz, frame M):
LOD-pop and the S2 sight picture at every LOD. Promoted from the AR-01's rifle_viewgates.py (gunlib 0.2.0).

    py -3 -B <shim> [--outdir dir] [--sizes-out json]

LOD-pop (GUN_BUILDING_STUDY 7.2 B8): LOD k and LOD k+1 silhouettes at the switch distance of screen size s_{k+1}
(d = 1.778 r / s at 2560 x 1440, 90 deg horizontal FOV: Unreal's 2 max(0.5 P00, 0.5 P11) r / d) from 4 headings
(right, left, front-right 3/4, rear-left 3/4, 10 deg up), 2x supersampled; gate: mean contour difference <= 1 px and
max <= 3 px. A failing switch moves farther (s x 0.9) until it passes; the sizes go to gates/game_lod_sizes.json
(``{<twin>: sizes, bounds_radius_m}``; the export stage writes them into the sidecar). Strips of the switch frames
are saved. Guns with two body states (the SMG's stock) pass several ``--states``: one npz set per state, every
switch must pass on every state.

S2 (plan 6): gunlib.drivers.b4 on each LOD's triangles (occlusion-aware, the gun's own sight kind); |lateral|,
|vertical| <= 0.5 px plus B4's conditions (post visible, no occluder). ``s2_notch_bottom_info`` (AR-01 only) keeps the
older notch-bottom raster as information.

Config ``cfg.viewgates``: lod_npz ("scratch/game/lod{k}_tris.npz" relative to the work folder, or a callable(k,
state)), game_report, radius (callable(report) -> r_m), start_sizes, outr (review images), out (viewgates.json),
sizes_out (game_lod_sizes.json), s2_requires, s2_method, s2_notch_bottom_info, states (default [None]).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .. import raster as RZ
from . import b4 as B4


def _npz_path(cfg, k, state=None):
    p = cfg.viewgates.get("lod_npz", "scratch/game/lod{k}_tris.npz")
    if callable(p):
        return Path(p(k, state))
    return cfg.work / p.format(k=k, state=state or "")


def load(cfg, lv, state=None):
    z = np.load(_npz_path(cfg, lv, state))
    return z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]


def headings(center, d):
    out = []
    for name, az, el in (("right", -90.0, 10.0), ("left", 90.0, 10.0), ("front_right_34", -35.0, 10.0),
                         ("rear_left_34", 145.0, 10.0)):
        a, e = math.radians(az), math.radians(el)
        dirv = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        out.append((name, center + dirv * d))
    return out


def lod_pop(cfg, sizes, r_m, outr, ss=2, states=(None,)):
    Ls = {st: [load(cfg, k, st) for k in range(4)] for st in states}
    res = {"bounds_radius_m": r_m, "start_sizes": list(sizes), "switches": []}
    if states != (None,):
        res["states"] = list(states)
    final = list(sizes)
    outr.mkdir(parents=True, exist_ok=True)
    for k in range(3):
        s = final[k + 1]
        tries = []
        while True:
            d_mm = 1.778 * r_m / s * 1000.0
            worst = {"mean": 0.0, "max": 0.0}
            per = []
            strip = []
            for st in states:
                L = Ls[st]
                V0 = L[0][0]
                center = 0.5 * (V0.min(0) + V0.max(0))
                for hname, eye in headings(center, d_mm):
                    cam = RZ.Camera(eye, target=center, hfov_deg=90.0)
                    A, _ = RZ.raster_mask(cam, L[k][0], L[k][1], ss)
                    B, _ = RZ.raster_mask(cam, L[k + 1][0], L[k + 1][1], ss)
                    mean, mx, p99, xor = RZ.contour_distance(A, B, ss)
                    row = {"heading": hname, "mean_px": round(mean, 3), "max_px": round(mx, 3), "p99_px": round(p99, 3),
                           "xor_px": xor}
                    if st is not None:
                        row["state"] = st
                    per.append(row)
                    worst["mean"] = max(worst["mean"], mean)
                    worst["max"] = max(worst["max"], mx)
                    ys, xs = np.nonzero(A | B)
                    if len(ys):
                        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
                        pad = 6 * ss
                        sl = (slice(max(y0 - pad, 0), y1 + pad), slice(max(x0 - pad, 0), x1 + pad))
                        img = np.zeros(A[sl].shape + (3,), np.uint8) + 255
                        img[A[sl] & B[sl]] = (90, 90, 90)
                        img[A[sl] & ~B[sl]] = (220, 40, 40)
                        img[B[sl] & ~A[sl]] = (40, 90, 220)
                        strip.append(Image.fromarray(img))
            ok = worst["mean"] <= 1.0 and worst["max"] <= 3.0
            tries.append({"screen_size": round(s, 5), "distance_m": round(d_mm / 1000, 3), "worst_mean_px":
                          round(worst["mean"], 3), "worst_max_px": round(worst["max"], 3), "pass": ok,
                          "headings": per})
            if strip:
                Wd = sum(im.width for im in strip) + 10 * len(strip)
                Hd = max(im.height for im in strip)
                canvas = Image.new("RGB", (Wd, Hd + 22), (255, 255, 255))
                x = 0
                for im in strip:
                    canvas.paste(im, (x, 22))
                    x += im.width + 10
                ImageDraw.Draw(canvas).text((4, 4), "LOD%d (red only) vs LOD%d (blue only) at screen size %.4f, %.2f m, "
                                            "%dx ss; worst mean %.2f px, max %.2f px" % (k, k + 1, s, d_mm / 1000, ss,
                                                                                        worst["mean"], worst["max"]),
                                            fill=(0, 0, 0))
                canvas.save(outr / f"lodpop_{k}{k + 1}.png")
            if ok or s < final[k + 1] * 0.2:
                break
            s *= 0.9
        final[k + 1] = round(s, 5)
        res["switches"].append({"from": k, "to": k + 1, "tries": tries, "chosen_screen_size": final[k + 1],
                                "pass": tries[-1]["pass"]})
        print("[lodpop] LOD%d->%d size %.4f d %.2f m mean %.2f max %.2f %s" % (
            k, k + 1, s, tries[-1]["distance_m"], tries[-1]["worst_mean_px"], tries[-1]["worst_max_px"],
            "PASS" if tries[-1]["pass"] else "FAIL"), flush=True)
    res["final_sizes"] = final
    return res


def sight_picture_notch_bottom(cfg, outr, lv=0):
    """AR-01 information only: the pre-R48 notch-bottom raster (post tip vs the notch floor)."""
    V, T, lab, names = load(cfg, lv)
    soc = cfg.socket(cfg.b4.get("socket", "Sight"))
    grip = cfg.grip
    sight_B = np.array(soc["blender_mm"], float)
    pitch = soc["unreal_rotation_deg"]["pitch"]
    fwd = np.array([math.cos(math.radians(pitch)), 0.0, math.sin(math.radians(pitch))])
    eye = sight_B + grip - 250.0 * fwd                     # frame M
    cam = RZ.Camera(eye, forward=fwd, up=(0.0, 0.0, 1.0), hfov_deg=55.0)
    rear_names = cfg.viewgates.get("notch_bottom_rear", cfg.b4.get("rear", []))
    rear = [i for i, n in enumerate(names) if n in rear_names]
    post = [i for i, n in enumerate(names) if n == cfg.b4["post"]]
    if not rear or not post:
        return {"lod": lv, "pass": None, "note": "no rear sight leaf / front post at this LOD (the blockout "
                                                 "silhouette level): no sight picture to test"}
    ss = 8
    win = (1280 - 60, 720 - 60, 1280 + 60, 720 + 60)

    def mask(ids):
        sel = np.isin(lab, ids)
        M, _ = RZ.raster_mask(cam, V, T[sel], ss, win)
        return M
    R = mask(rear)
    P = mask(post)
    x0, y0 = win[0], win[1]
    H, W = R.shape
    top = np.where(R.any(0), R.argmax(0), H)
    cc = W // 2
    floor = top[cc]
    lim = floor - 2 * ss
    l = cc
    while l > 0 and top[l] > lim:
        l -= 1
    r = cc
    while r < W - 1 and top[r] > lim:
        r += 1
    notch_cx = 0.5 * (l + r + 1) / ss + x0
    notch_bottom = (top[cc - ss:cc + ss + 1].max()) / ss + y0
    rows = np.nonzero(P.any(1))[0]
    out = {"eye_M": eye.round(3).tolist(), "fov_deg": 55.0, "eye_relief_mm": 250.0, "supersample": ss,
           "window_px": win}
    if not len(rows):
        out["error"] = "post not in the window"
        return out
    tip = rows[0]
    band = P[tip:tip + ss]
    cols = np.nonzero(band.any(0))[0]
    post_cx = (cols.mean() + 0.5) / ss + x0
    post_tip = tip / ss + y0
    out.update({"notch_centre_x_px": round(float(notch_cx), 3), "notch_bottom_y_px": round(float(notch_bottom), 3),
                "notch_width_px": round((r - l - 1) / ss, 2), "post_centre_x_px": round(float(post_cx), 3),
                "post_tip_y_px": round(float(post_tip), 3),
                "lateral_offset_px": round(float(post_cx - notch_cx), 3),
                "vertical_offset_px": round(float(post_tip - notch_bottom), 3)})
    out["pass"] = abs(out["lateral_offset_px"]) <= 0.5 and abs(out["vertical_offset_px"]) <= 0.5
    img = np.zeros(R.shape + (3,), np.uint8) + 225
    img[P] = (20, 20, 20)
    img[R] = (110, 110, 110)
    im = Image.fromarray(img).resize((R.shape[1] // 2, R.shape[0] // 2), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    f = 0.5 * ss
    dr.line([((notch_cx - x0) * f, 0), ((notch_cx - x0) * f, im.height)], fill=(0, 160, 0))
    dr.line([(0, (notch_bottom - y0) * f), (im.width, (notch_bottom - y0) * f)], fill=(0, 160, 0))
    dr.text((4, 4), "S2: lateral %.2f px, vertical %.2f px (post drawn over the rear sight)" % (
        out["lateral_offset_px"], out["vertical_offset_px"]), fill=(200, 0, 0))
    outr.mkdir(parents=True, exist_ok=True)
    im.save(outr / ("s2_sight_window.png" if lv == 0 else f"s2_sight_window_lod{lv}.png"))
    out["lod"] = lv
    return out


def sight_picture_b4(cfg, lv, outdir, outr, state=None):
    """S2 on the twin's LOD triangles with the form stage's occlusion-aware B4 measurement. Threshold |lateral|,
    |vertical| <= 0.5 px; plus B4's own conditions (the post visible >= min_post_mm, no occluder)."""
    npz = _npz_path(cfg, lv, state)
    z = np.load(npz)
    names = [str(n) for n in z["names"]]
    req = cfg.viewgates.get("s2_requires", [cfg.b4["post"]] + list(cfg.b4.get("rear", []))[:1])
    if any(n not in names for n in req):
        return {"lod": lv, "pass": None, "note": "no rear sight leaf / front post at this LOD (the blockout silhouette "
                                                 "level): no sight picture to test"}
    js = outdir / f"s2_lod{lv}.json"
    r = B4.measure(cfg, str(npz), str(js), str(outr / f"s2_sight_picture_lod{lv}.png"))
    vis_key = "visible_height_in_notch_mm_at_notch" if cfg.b4.get("kind", "notch") == "notch" else \
        "visible_height_in_aperture_mm_at_aperture"
    occ_key = "occluders_in_notch_px" if cfg.b4.get("kind", "notch") == "notch" else "occluders_in_aperture_px"
    out = {"lod": lv, "method": cfg.viewgates.get("s2_method", "gunlib.drivers.b4 (occlusion-aware)"),
           "lateral_offset_px": r.get("lateral_offset_px"), "vertical_offset_px": r.get("vertical_offset_px"),
           "lateral_offset_mm": r.get("lateral_offset_mm"), "vertical_offset_mm": r.get("vertical_offset_mm"),
           "post_visible_mm": (r.get("post") or {}).get(vis_key),
           "occluders": r.get(occ_key), "notch" if cfg.b4.get("kind", "notch") == "notch" else "aperture":
           r.get("notch") if cfg.b4.get("kind", "notch") == "notch" else r.get("aperture"), "image": r.get("image")}
    out["pass"] = bool(r.get("lateral_offset_px") is not None and abs(r["lateral_offset_px"]) <= 0.5
                       and abs(r["vertical_offset_px"]) <= 0.5
                       and (out["post_visible_mm"] or 0) >= cfg.b4.get("min_post_mm", 1.0)
                       and not r.get(occ_key))
    return out


def main(cfg, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    C = cfg.viewgates
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(C.get("outdir") or cfg.scratch / "game"))
    ap.add_argument("--outr", default=str(C.get("outr") or cfg.review / "game"))
    ap.add_argument("--sizes-out", default=str(C.get("sizes_out") or cfg.gates / "game_lod_sizes.json"))
    a = ap.parse_args(argv)
    outdir, outr = Path(a.outdir), Path(a.outr)
    outdir.mkdir(parents=True, exist_ok=True)
    rep = json.loads(Path(C.get("game_report") or cfg.scratch / "game" / "game_report.json").read_text())
    r = C["radius"](rep)
    sizes = list(C.get("start_sizes", [1.0, 0.30, 0.12, 0.04]))
    states = tuple(C.get("states", [None]))
    out = {"lod_pop": lod_pop(cfg, sizes, r, outr, states=states), "s2": sight_picture_b4(cfg, 0, outdir, outr),
           "s2_lods": {f"LOD{k}": sight_picture_b4(cfg, k, outdir, outr) for k in (1, 2, 3)}}
    if C.get("s2_notch_bottom_info"):
        out["s2_notch_bottom_info"] = sight_picture_notch_bottom(cfg, outr, 0)
    for k, v in out["s2_lods"].items():
        print("[viewgates] S2", k, v.get("lateral_offset_px"), v.get("vertical_offset_px"), v.get("pass"))
    (outdir / "viewgates.json").write_text(json.dumps(out, indent=1))
    Path(a.sizes_out).write_text(json.dumps({cfg.twin: out["lod_pop"]["final_sizes"], "bounds_radius_m": r}, indent=1))
    print("[viewgates] S2 LOD0", out["s2"].get("lateral_offset_px"), out["s2"].get("vertical_offset_px"),
          out["s2"].get("pass"))
    print("[viewgates] DONE sizes", out["lod_pop"]["final_sizes"])
    return out
