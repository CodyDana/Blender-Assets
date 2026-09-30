"""ROUND 6 capture measures (plain Python, read-only): py -3 measure_r6.py <capture dir> [out.json]
  near-black (max channel < 12 sRGB) per 4 x 4 cell (the verify_r5 rule: no cell over 10 %) + blown (min >= 250);
  the drum-top hotspot (blown px in the drum cameras); sunlit tiles R/B (verify_r5 boxes, brightest 30 %);
  courtyard gravel (ref 1 / ref 2 targets: R/B 1.31-1.48, s 0.23-0.32); downpipes (were (8, 6, 6))."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

CAP = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else CAP / "measure_r6.json"
LUM = np.array([0.2126, 0.7152, 0.0722])


def load(cam):
    p = CAP / f"{cam}.png"
    return np.asarray(Image.open(p).convert("RGB")).astype(float) if p.exists() else None


def st(c):
    m = np.median(c, axis=0)
    return {"rgb": [int(v) for v in m], "R/B": round(float(m[0] / max(m[2], 1)), 3),
            "sat": round(float((m.max() - m.min()) / max(m.max(), 1)), 3)}


def meas(a, box):
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1].reshape(-1, 3)
    lum = r @ LUM
    return {"box": box, "all": st(r), "lit30": st(r[lum >= np.percentile(lum, 70)]),
            "p10_max": int(np.percentile(r.max(axis=1), 10))}


TILES = {   # verify_r5 v5_look_measure.py boxes (the cameras are unchanged)
    "CU_R4_PavilionTaiko": {"pav_roof_E_face_sunlit": (1000, 140, 1680, 290), "wallcap_E_sunlit": (1420, 600, 1900, 720),
                            "wallcap_W": (0, 590, 640, 660),
                            "pav_E_tight": (1080, 185, 1420, 232), "wallcapE_tight": (1560, 612, 1860, 660)},
    "CU_R4_RidgeGate": {"onigawara_lit_face": (840, 480, 970, 700), "noshi_stack": (980, 640, 1900, 760),
                        "cap_rolls": (980, 540, 1900, 640), "gate_roof_tiles": (1250, 780, 1900, 1060),
                        "storehouse_roof_far": (150, 120, 1250, 320)},
    "CU_R4_RidgeHall": {"hall_roof_tiles_lower_right": (1050, 560, 1920, 1080), "onigawara": (520, 450, 860, 750),
                        "cap_rolls": (800, 350, 1920, 560)},
    "CAM_Ref2Match": {"hall_upper_roof": (470, 80, 980, 175), "hall_lower_roof": (230, 250, 1230, 295)},
    "CAM_EstablishingRef2": {"hall_upper_roof": (450, 190, 1000, 285), "hall_lower_roof": (140, 365, 1320, 420)},
    "CU_HallUpperRoof": {"whole": (0, 0, 1920, 1080)},
}
TIMBER = {
    "CU_R4_PavilionTaiko": {"post_E_sunlit": (1290, 440, 1385, 760), "post_W": (668, 440, 752, 770),
                            "eave_beam_front": (930, 245, 1430, 305), "crate_top": (1100, 880, 1600, 990),
                            "ceiling_under_roof": (760, 395, 1200, 450)},
    "CU_R4_RidgeGate": {"fence_boards": (0, 700, 820, 910)},
}
GRAVEL = {   # courtyard gravel (picked on the r6 it1 stills: open gravel, no props / shadows)
    "CAM_Overview": {"yard_W_sunlit": (440, 380, 520, 440), "yard_E": (1330, 420, 1440, 470),
                     "yard_front_hall_W": (560, 425, 660, 455)},
    "CAM_EastYard": {}, "CAM_WallTop": {},
}
PIPES = {"CU_R4_CorridorOpen": {"downpipe_left": (62, 330, 92, 780), "downpipe_mid": (482, 330, 500, 900)}}
HOT = ("CU_Taiko", "CAM_Drum", "CU_R4_PavilionTaiko")

res = {"cells": {}, "tiles": {}, "timber": {}, "gravel": {}, "pipes": {}, "hotspot": {}}
for p in sorted(CAP.glob("C*_*.png")):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    mx, mn = a.max(axis=2), a.min(axis=2)
    h, w = mx.shape
    cells = []
    worst = 0.0
    for r in range(4):
        for c in range(4):
            sl = (slice(r * h // 4, (r + 1) * h // 4), slice(c * w // 4, (c + 1) * w // 4))
            f = float((mx[sl] < 12).mean())
            worst = max(worst, f)
            if f > 0.10:
                cells.append([r, c, round(f, 3), [int(v) for v in np.median(a[sl].reshape(-1, 3), axis=0)]])
    res["cells"][p.stem] = {"frame_nb": round(float((mx < 12).mean()), 4), "max_cell_nb": round(worst, 3),
                            "cells_over_10pct": cells, "blown_px": int((mn >= 250).sum())}
for grp, D in (("tiles", TILES), ("timber", TIMBER), ("gravel", GRAVEL), ("pipes", PIPES)):
    for cam, boxes in D.items():
        a = load(cam)
        if a is None:
            continue
        for k, b in boxes.items():
            res[grp][f"{cam}:{k}"] = meas(a, b)
for cam in HOT:
    a = load(cam)
    if a is not None:
        res["hotspot"][cam] = int((a.min(axis=2) >= 250).sum())
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
bad = {k: v for k, v in res["cells"].items() if v["cells_over_10pct"]}
print("stills", len(res["cells"]), "with a cell > 10 % near-black:", len(bad))
for k, v in sorted(bad.items(), key=lambda kv: -kv[1]["max_cell_nb"]):
    print(f"  {k:26s} frame {v['frame_nb']:.3f} worst {v['max_cell_nb']:.3f} cells {[(c[0], c[1], c[2], c[3]) for c in v['cells_over_10pct']]}")
for grp in ("tiles", "timber", "gravel", "pipes"):
    for k, v in res[grp].items():
        print(f"{grp:6s} {k:44s} all {v['all']['rgb']} R/B {v['all']['R/B']:.2f} s {v['all']['sat']:.2f} | lit30 {v['lit30']['rgb']} R/B {v['lit30']['R/B']:.2f} s {v['lit30']['sat']:.2f}")
print("hotspot blown px", res["hotspot"])
