"""VERIFY r8: sky banding. For each still with sky, the sky mask = pixels above the highest non-sky edge per column
(approx: rows 0..k where the column is 'sky-like': saturation of a smooth gradient, no strong edges), simplified to
fixed boxes chosen by eye (listed). In each box, on the green channel (8-bit): (a) code gaps: fraction of integer
levels missing inside the 2..98 percentile range; (b) staircase: after a 15 px box blur along the column the residual's
sign-runs; (c) contour score: fraction of pixels whose 3x3 neighbourhood has exactly two distinct values differing by 1
AND whose 9x9 neighbourhood is otherwise flat (the Mach-band contour signature); plus a 4x contrast-stretched crop for
the eye. Out: verify_r8/sky_banding.json, crops/sky_<cam>.png"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view as swv


class nd:  # tiny max / min filters (edge padded), no scipy on this machine
    @staticmethod
    def maximum_filter(g, k):
        p = np.pad(g, k // 2, mode="edge"); return swv(p, (k, k)).max(axis=(2, 3))

    @staticmethod
    def minimum_filter(g, k):
        p = np.pad(g, k // 2, mode="edge"); return swv(p, (k, k)).min(axis=(2, 3))
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/f1"
VD = B / "WorkFiles/dojo/build/verify_r8"
BOXES = {  # x0, y0, x1, y1 (sky only, by eye)
    "CAM_EstablishingRef2": [(560, 0, 1440, 120), (0, 150, 420, 240), (1000, 180, 1448, 250)],
    "CU_Training": [], "CAM_GateFromStreet": [], "CU_R4_RidgeGate": [], "CAM_EastYard": [], "CU_HallUpperRoof": [],
    "CAM_Ref2Match": [],
    "CAM_Establishing": [],
    "CU_R5_FarBackground": [],
    "CU_R5_Skyline": [],
    "CAM_Overview": [],
    "CU_R5_ApproachRoad": [],
    "CAM_PlayerEyeSand": [],
    "CU_R6_RidgesNorth": [],
    "CU_R6_TownEdgeE": [],
    "CAM_WallTop": [],
}
auto = {}
res = {}
for n in BOXES:
    a = np.asarray(Image.open(CAP / f"{n}.png").convert("RGB")).astype(np.int32)
    h, w, _ = a.shape
    boxes = BOXES[n]
    if not boxes:   # automatic: rows from the top while the row is smooth (sky); take the top band up to the first row
        g = a[..., 1].astype(float)          # whose median gradient jumps
        gy = np.abs(np.diff(g, axis=1))
        rowedge = (gy > 12).mean(axis=1)
        k = 0
        while k < h // 2 and rowedge[k] < 0.01:
            k += 1
        if k >= 40:
            boxes = [(0, 0, w, k - 4)]
    out = []
    for (x0, y0, x1, y1) in boxes:
        r = a[y0:y1, x0:x1]
        g = r[..., 1]
        lo, hi = np.percentile(g, 2), np.percentile(g, 98)
        levels = np.unique(g[(g >= lo) & (g <= hi)])
        gaps = 1 - len(levels) / max(1, (hi - lo + 1))
        # contour signature
        mx = nd.maximum_filter(g, 3); mn = nd.minimum_filter(g, 3)
        edge1 = (mx - mn == 1)
        mx9 = nd.maximum_filter(g, 9); mn9 = nd.minimum_filter(g, 9)
        contour = edge1 & (mx9 - mn9 <= 1)
        flat5 = (nd.maximum_filter(g, 5) - nd.minimum_filter(g, 5) == 0)
        # the largest jump between neighbouring rows of the column-median profile (a visible band edge)
        prof = np.median(r, axis=1)
        jump = float(np.abs(np.diff(prof, axis=0)).max()) if len(prof) > 1 else 0.0
        out.append({"box": [x0, y0, x1, y1], "median": [int(v) for v in np.median(r.reshape(-1, 3), axis=0)],
                    "g_range": [int(lo), int(hi)], "missing_code_frac": round(float(gaps), 3),
                    "contour_frac": round(float(contour.mean()), 4), "flat5_frac": round(float(flat5.mean()), 4),
                    "max_row_median_jump": round(jump, 2)})
        c = r.astype(float); m = c.mean(axis=(0, 1)); c = np.clip((c - m) * 4 + 128, 0, 255).astype(np.uint8)
        Image.fromarray(c).save(VD / "crops" / f"sky_{n}_{x0}_{y0}.png")
    res[n] = out
(VD / "sky_banding.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for n, o in res.items():
    for b in o:
        print(n, b)
