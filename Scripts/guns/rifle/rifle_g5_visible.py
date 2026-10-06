"""AR-01 G5 at LOD2-3, the visible measure (plain Python, numpy + PIL), after rifle_g5_lods.py:

    py -3 -B Scripts/guns/rifle/rifle_g5_visible.py

GUN_BUILDING_STUDY 7.2 G5 / finding R5: 0 intersections at LOD0-LOD1, '< 1 px at LOD2-3'. rifle_g5_lods.py lists the
intersecting pairs of LOD2 and LOD3 with a conservative depth (the deepest sample of one part inside the other): it
counts parts buried in hidden interiors (the blockout barrel running through the receiver and the handguards, a coarse
pivot inside its block) at their full burial depth although nothing of it can be seen. This step measures what the
intersection does to the picture: at the LOD's switch-in distance (2560 x 1440, 90 deg, the LOD-pop gate's four
headings, 4x supersampled, z-buffered with rifle_b4.zbuffer) each intersecting part's VISIBLE region at LOD k is
compared with the same part's visible region at LOD k-1 (the LOD it replaces): symmetric contour distance, mean and max
(output px), recorded beside the study's depth gate (pass flag: mean < 1 px per part). Updates scratch/game/g5_lods.json
(key 'visible') and writes review/game/g5_visible_lod<k>.png (the worst heading, LOD k-1 red only / LOD k blue only).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(HERE))
from gunlib import raster as RZ  # noqa: E402
import rifle_b4 as B4  # noqa: E402

W_ = ROOT / "WorkFiles" / "guns" / "rifle"
GAME = W_ / "scratch" / "game"
OUTR = W_ / "review" / "game"
SS = 4


def load(lv):
    z = np.load(GAME / f"lod{lv}_tris.npz")
    return z["V"], z["T"], z["lab"], [str(n) for n in z["names"]]


def headings(center, d):
    out = []
    for name, az, el in (("right", -90.0, 10.0), ("left", 90.0, 10.0), ("front_right_34", -35.0, 10.0),
                         ("rear_left_34", 145.0, 10.0)):
        a, e = math.radians(az), math.radians(el)
        out.append((name, center + np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)]) * d))
    return out


def base(n):
    for k in (1, 2, 3):
        if n.endswith(f"_LOD{k}"):
            return n[:-5]
    return n


def main():
    g5 = json.loads((GAME / "g5_lods.json").read_text())
    sz = json.loads((W_ / "gates" / "game_lod_sizes.json").read_text())
    r_m, sizes = sz["bounds_radius_m"], sz["SM_AR01"]
    L = {k: load(k) for k in range(4)}
    V0 = L[0][0]
    center = 0.5 * (V0.min(0) + V0.max(0))
    ok_all = True
    vis = {}
    for lv in (2, 3):
        pairs = g5["lods"][f"LOD{lv}"]["pairs"]
        parts = sorted({base(p["a"]) for p in pairs} | {base(p["b"]) for p in pairs})
        d_mm = 1.778 * r_m / sizes[lv] * 1000.0
        Vp, Tp, lp, np_ = L[lv - 1]
        Vc, Tc, lc, nc = L[lv]
        ip = {n: i for i, n in enumerate(np_)}
        ic = {n: i for i, n in enumerate(nc)}
        res = {}
        worst_img = None
        for hname, eye in headings(center, d_mm):
            cam = RZ.Camera(eye, target=center, hfov_deg=90.0)
            S, _ = cam.project(np.vstack([Vp, Vc]))
            x0, y0 = np.floor(S.min(0)).astype(int) - 4
            x1, y1 = np.ceil(S.max(0)).astype(int) + 4
            win = (int(x0), int(y0), int(x1), int(y1))
            IDp = B4.zbuffer(cam, Vp, Tp, lp, win, SS)
            IDc = B4.zbuffer(cam, Vc, Tc, lc, win, SS)
            for n in parts:
                if n not in ip or n not in ic:
                    continue
                A, Bm = IDp == ip[n], IDc == ic[n]
                if not A.any() and not Bm.any():
                    continue
                if not A.any() or not Bm.any():
                    mean = mx = float(np.sqrt(max(A.sum(), Bm.sum())) / SS)     # appears / vanishes: its size
                else:
                    mean, mx, _, _ = RZ.contour_distance(A, Bm, SS)
                rr = res.setdefault(n, {"worst_mean_px": 0.0, "worst_max_px": 0.0, "headings": {}})
                rr["headings"][hname] = {"mean_px": round(mean, 3), "max_px": round(mx, 3)}
                if mean > rr["worst_mean_px"]:
                    rr["worst_mean_px"] = round(mean, 3)
                if mx > rr["worst_max_px"]:
                    rr["worst_max_px"] = round(mx, 3)
                if worst_img is None or mean > worst_img[0]:
                    img = np.full(A.shape + (3,), 255, np.uint8)
                    img[(IDp >= 0) | (IDc >= 0)] = (200, 200, 200)
                    img[A & Bm] = (90, 90, 90)
                    img[A & ~Bm] = (220, 40, 40)
                    img[Bm & ~A] = (40, 90, 220)
                    worst_img = (mean, img, n, hname)
        for n, rr in res.items():
            rr["pass"] = rr["worst_mean_px"] < 1.0
        ok = all(rr["pass"] for rr in res.values())
        ok_all &= ok
        vis[f"LOD{lv}"] = {"distance_m": round(d_mm / 1000.0, 3), "supersample": SS, "parts": res, "pass": ok,
                           "worst_mean_px": max([rr["worst_mean_px"] for rr in res.values()] or [0.0]),
                           "worst_max_px": max([rr["worst_max_px"] for rr in res.values()] or [0.0])}
        if worst_img is not None:
            OUTR.mkdir(parents=True, exist_ok=True)
            Image.fromarray(worst_img[1]).save(OUTR / f"g5_visible_lod{lv}.png")
            vis[f"LOD{lv}"]["image"] = f"review/game/g5_visible_lod{lv}.png ({worst_img[2]}, {worst_img[3]})"
        print("[G5-visible] LOD%d parts %d worst mean %.3f max %.3f px %s" % (
            lv, len(res), vis[f"LOD{lv}"]["worst_mean_px"], vis[f"LOD{lv}"]["worst_max_px"], "PASS" if ok else "FAIL"),
            flush=True)
    g5["visible"] = {"rule": "each intersecting part's visible region at LOD k vs LOD k-1 at the switch-in distance, "
                             "4 headings: mean < 1 px (max reported)", "lods": vis, "pass": ok_all}
    # the gate stays the study's penetration-depth rule (rifle_g5_lods.py); this measure is recorded beside it
    (GAME / "g5_lods.json").write_text(json.dumps(g5, indent=1))


if __name__ == "__main__":
    main()
