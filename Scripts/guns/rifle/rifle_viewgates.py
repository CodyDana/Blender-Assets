"""AR-01 stage 4 view gates (plain Python, numpy + PIL), on the twin's per-LOD triangles (scratch/game/lod<k>_tris.npz,
frame M, mm):

    py -3 -B Scripts/guns/rifle/rifle_viewgates.py

LOD-pop (RIFLE_BUILD_PLAN 2.4, GUN_BUILDING_STUDY 7.2 B8): LOD k and LOD k+1 silhouettes at the switch distance of
screen size s_{k+1} (d = 1.778 r / s at 2560 x 1440, 90 deg horizontal FOV: Unreal's 2 max(0.5 P00, 0.5 P11) r / d),
from 4 headings (right, left, front-right 3/4, rear-left 3/4, 10 deg up), 2x supersampled; gate: mean contour
difference <= 1 px and max <= 3 px. A failing switch moves farther (s x 0.9) until it passes; the sizes found go to
gates/game_lod_sizes.json (the export stage writes them into the sidecar). Strips of the switch frames are saved.

S2 sight picture (plan 6, B4): eye 0.25 m behind the Sight socket along its -X (spec position and pitch), 55 deg
horizontal FOV, 2560 x 1440; the rear sight (leaf + slider + block) and the front post rasterised separately at 4x in
a window round the centre: the notch's centre column and bottom row vs the post's centre column and tip row; gate:
both offsets <= 0.5 px. Also the composite sight picture (nearest-surface ids) as an image.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(HERE))
from gunlib import raster as RZ  # noqa: E402

WORK = ROOT / "WorkFiles" / "guns" / "rifle"
GAME = WORK / "scratch" / "game"
OUTR = WORK / "review" / "game"
GATES = WORK / "gates"
SPEC = json.loads((WORK / "rifle_spec.json").read_text())
GRIP = np.array(SPEC["frames"]["B"]["Grip_in_M"], float)


def load(lv):
    z = np.load(GAME / f"lod{lv}_tris.npz")
    return z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]


def headings(center, d):
    out = []
    for name, az, el in (("right", -90.0, 10.0), ("left", 90.0, 10.0), ("front_right_34", -35.0, 10.0),
                         ("rear_left_34", 145.0, 10.0)):
        a, e = math.radians(az), math.radians(el)
        dirv = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        out.append((name, center + dirv * d))
    return out


def lod_pop(sizes, r_m, ss=2):
    L = [load(k) for k in range(4)]
    V0 = L[0][0]
    center = 0.5 * (V0.min(0) + V0.max(0))
    res = {"bounds_radius_m": r_m, "start_sizes": list(sizes), "switches": []}
    final = list(sizes)
    OUTR.mkdir(parents=True, exist_ok=True)
    for k in range(3):
        s = final[k + 1]
        tries = []
        while True:
            d_mm = 1.778 * r_m / s * 1000.0
            worst = {"mean": 0.0, "max": 0.0}
            per = []
            strip = []
            for hname, eye in headings(center, d_mm):
                cam = RZ.Camera(eye, target=center, hfov_deg=90.0)
                A, _ = RZ.raster_mask(cam, L[k][0], L[k][1], ss)
                B, _ = RZ.raster_mask(cam, L[k + 1][0], L[k + 1][1], ss)
                mean, mx, p99, xor = RZ.contour_distance(A, B, ss)
                per.append({"heading": hname, "mean_px": round(mean, 3), "max_px": round(mx, 3), "p99_px": round(p99, 3),
                            "xor_px": xor})
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
                canvas.save(OUTR / f"lodpop_{k}{k + 1}.png")
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


def sight_picture(lv=0):
    V, T, lab, names = load(lv)
    soc = {r["socket"]: r for r in SPEC["sockets"]["rifle"]}["Sight"]
    sight_B = np.array(soc["blender_mm"], float)
    pitch = soc["unreal_rotation_deg"]["pitch"]
    # Unreal pitch +up; the socket's +X: (cos p, 0, sin p) in the gun frame (Unreal +Z = Blender +Z)
    fwd = np.array([math.cos(math.radians(pitch)), 0.0, math.sin(math.radians(pitch))])
    eye = sight_B + GRIP - 250.0 * fwd                     # frame M
    cam = RZ.Camera(eye, forward=fwd, up=(0.0, 0.0, 1.0), hfov_deg=55.0)
    rear = [i for i, n in enumerate(names) if n in ("rear_sight_leaf", "rear_sight_slider")]
    post = [i for i, n in enumerate(names) if n == "front_sight_post"]
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
    # notch: the rear sight's top edge per column (first covered row from the top); the notch is the run of columns
    # round the centre where that edge is deepest
    H, W = R.shape
    top = np.where(R.any(0), R.argmax(0), H)
    cc = W // 2
    floor = top[cc]
    # notch walls: walk out from the centre until the top edge rises above the floor by > 2 px (output)
    lim = floor - 2 * ss
    l = cc
    while l > 0 and top[l] > lim:
        l -= 1
    r = cc
    while r < W - 1 and top[r] > lim:
        r += 1
    notch_cx = 0.5 * (l + r + 1) / ss + x0                 # pixel units (centre between the walls at that level)
    notch_bottom = (top[cc - ss:cc + ss + 1].max()) / ss + y0
    # post tip: first covered row; centre of the covered columns over the top 1 output pixel
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
    # picture: composite (rear dark grey, post black over a light ground) of the window, 4x upscaled for viewing
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
    OUTR.mkdir(parents=True, exist_ok=True)
    im.save(OUTR / ("s2_sight_window.png" if lv == 0 else f"s2_sight_window_lod{lv}.png"))
    out["lod"] = lv
    return out


def sight_picture_b4(lv):
    """S2 on the twin's LOD triangles with the form stage's occlusion-aware B4 measurement (rifle_b4.py: the eye 0.25 m
    behind the Sight socket ON its line, 55 deg, 2560 x 1440, z-buffered). Since R48 the Sight socket sits at the
    notch TOP centre and the real-pattern picture holds the post tip LEVEL WITH THE NOTCH TOP (the older notch-bottom
    test above measures a 20 px drop by design). Plan 6 threshold: |lateral|, |vertical| <= 0.5 px; plus B4's own
    conditions (the post visible >= 1 mm in the notch, no occluder)."""
    import subprocess
    z = np.load(GAME / f"lod{lv}_tris.npz")
    names = [str(n) for n in z["names"]]
    if "front_sight_post" not in names or "rear_sight_leaf" not in names:
        return {"lod": lv, "pass": None, "note": "no rear sight leaf / front post at this LOD (the blockout silhouette "
                                                 "level): no sight picture to test"}
    js = GAME / f"s2_lod{lv}.json"
    subprocess.run([sys.executable, "-B", str(HERE / "rifle_b4.py"), "--npz", str(GAME / f"lod{lv}_tris.npz"),
                    "--out", str(js), "--img", str(OUTR / f"s2_sight_picture_lod{lv}.png")],
                   stdout=subprocess.DEVNULL, check=True)
    r = json.loads(js.read_text())
    out = {"lod": lv, "method": "rifle_b4 (occlusion-aware; post tip vs the notch TOP line, R48)",
           "lateral_offset_px": r.get("lateral_offset_px"), "vertical_offset_px": r.get("vertical_offset_px"),
           "lateral_offset_mm": r.get("lateral_offset_mm"), "vertical_offset_mm": r.get("vertical_offset_mm"),
           "post_visible_mm": (r.get("post") or {}).get("visible_height_in_notch_mm_at_notch"),
           "occluders": r.get("occluders_in_notch_px"), "notch": r.get("notch"), "image": r.get("image")}
    out["pass"] = bool(r.get("lateral_offset_px") is not None and abs(r["lateral_offset_px"]) <= 0.5
                       and abs(r["vertical_offset_px"]) <= 0.5 and (out["post_visible_mm"] or 0) >= 1.0
                       and not r.get("occluders_in_notch_px"))
    return out


def main():
    rep = json.loads((GAME / "game_report.json").read_text())
    r = rep["bounds_radius_m"]["twin_with_mag_box_half_diagonal"]
    sizes = [1.0, 0.30, 0.12, 0.04]
    out = {"lod_pop": lod_pop(sizes, r), "s2": sight_picture_b4(0),
           "s2_lods": {f"LOD{k}": sight_picture_b4(k) for k in (1, 2, 3)},
           "s2_notch_bottom_info": sight_picture(0)}
    for k, v in out["s2_lods"].items():
        print("[viewgates] S2", k, v.get("lateral_offset_px"), v.get("vertical_offset_px"), v.get("pass"))
    (GAME / "viewgates.json").write_text(json.dumps(out, indent=1))
    (GATES / "game_lod_sizes.json").write_text(json.dumps({"SM_AR01": out["lod_pop"]["final_sizes"],
                                                           "bounds_radius_m": r}, indent=1))
    print("[viewgates] S2 LOD0", out["s2"].get("lateral_offset_px"), out["s2"].get("vertical_offset_px"),
          out["s2"].get("pass"))
    print("[viewgates] DONE sizes", out["lod_pop"]["final_sizes"])


if __name__ == "__main__":
    main()
