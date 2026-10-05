"""Grip detail loop (plain Python): private review build -> ROUGH LOOK crops at the solved close-up cameras -> numbers.

    py -3 -B Scripts/guns/rifle/parts/grip_loop.py --tag r1_i1 [--no-build] [--no-render]

1. copies Assets/Guns/AR01.blend to scratch/detail_grip/input.blend (a stable snapshot; other part builders rewrite
   the asset blend) and runs grip_review.py on it -> scratch/detail_grip/AR01_grip.blend + grip_tris.npz + report
2. renders the grip's panels (c6, c1, q34) through gunlib.detail.DetailKit with the rifle's config, pointed at the
   private blend / npz / scratch (cameras copied from scratch/detail/cameras), into review/detail/grip/<tag>_*
3. measures, per panel: the kit's window silhouette IoU and edge agreement; the grip-only silhouette IoU (the part's
   own region: below the flange, behind the guard leg); the checker panel outline IoU against the traced reference
   quad (corner picks in panel px, grip_measure.py); the cell lattice of our crop vs the reference by FFT at the same
   panel windows (period px, groove direction deg)
-> review/detail/grip/<tag>_loop.json
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
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import rifle_detail as RDt  # noqa: E402
from rifle_common import SCRATCH, BLEND  # noqa: E402
import gunlib  # noqa: E402
from gunlib import closeup as CU  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib.detail import DetailKit  # noqa: E402
from parts import grip_measure as GM  # noqa: E402

PART = "grip"
PS = SCRATCH / "detail_grip"
REV = RDt.DETAIL_REVIEW / PART


def build():
    PS.mkdir(parents=True, exist_ok=True)
    inp = PS / "input.blend"
    for k in range(10):
        try:
            shutil.copy2(BLEND, inp)
            break
        except OSError:
            time.sleep(3)
    log = PS / "review_build.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(inp), "--factory-startup", "--python", str(HERE / "grip_review.py"),
                        "--", "--out", str(PS / "AR01_grip.blend"), "--npz", str(PS / "grip_tris.npz"),
                        "--report", str(PS / "review_report.json")], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "[grip_review] DONE" not in txt:
        raise RuntimeError("review build failed, see %s" % log)
    rep = json.loads((PS / "review_report.json").read_text())
    rep["xz_silhouette_iou_vs_input"] = xz_iou()
    return rep


def xz_iou(res=0.1):
    """Side (XZ) silhouette IoU of the rebuilt grip vs the grip in the input blend, rasterised at res mm."""
    D = np.load(PS / "grip_old_new.npz")
    lo = np.minimum(D["V"].min(0), D["oldV"].min(0))[[0, 2]] - 1
    hi = np.maximum(D["V"].max(0), D["oldV"].max(0))[[0, 2]] + 1
    shape = (int((hi[1] - lo[1]) / res) + 1, int((hi[0] - lo[0]) / res) + 1)

    def m(V, T):
        P = np.c_[(V[:, 0] - lo[0]) / res, (hi[1] - V[:, 2]) / res]
        return C.raster_tris(P, T, shape, ss=1) > 0.5
    a, b = m(D["V"], D["T"]), m(D["oldV"], D["oldT"])
    return round(float((a & b).sum() / max((a | b).sum(), 1)), 5)


def kit():
    K = RDt.kit()
    cfg = dict(K.cfg)
    cfg["blend"] = str(PS / "AR01_grip.blend")
    cfg["npz"] = str(PS / "grip_tris.npz")
    cfg["scratch_dir"] = str(PS / "kit")
    K2 = DetailKit(cfg)
    src = RDt.DETAIL_SCRATCH / "cameras"
    for p in list(src.glob("grip__*.json")) + list(src.glob("panel_*.json")):
        shutil.copy2(p, K2.scratch / "cameras" / p.name)
    return K2


def grip_roi(K, key):
    """Panel px region that only the grip occupies: below the flange (Z < -40) and behind the guard leg (X < 297),
    inside the part window."""
    cam = K.part_camera(PART, key)
    H, W = K.panel(key).shape[:2]
    V, T = K.subset(["pistol_grip"])
    Tv = T[(V[T][:, :, 2].max(1) < -40.0) & (V[T][:, :, 0].max(1) < 297.0)]
    cov = C.raster_tris(cam.project(V), CU.visible_tris(cam, V, Tv, cull_back=False), (H, W), ss=2) > 0.5
    from scipy import ndimage as ndi
    roi = ndi.binary_dilation(cov, iterations=4)
    x0, y0, x1, y1 = K.window(PART, key)
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    return roi & box


def run(tag, do_build=True, do_render=True):
    out = {"tag": tag, "date": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if do_build:
        out["build"] = build()
    else:
        out["build"] = json.loads((PS / "review_report.json").read_text())
    K = kit()
    crops = K.render_part_crop(PART, tag, render=do_render)
    out["crops"] = {k: {"silhouette_iou_window": v["silhouette_iou_window"], "edges_f": v["edges"]["f"],
                        "edges": v["edges"]} for k, v in crops[PART].items()}
    ref = GM.reference()
    for key in K.cfg["parts"][PART]["panels"]:
        rgba = np.asarray(Image.open(K.scratch / "renders" / f"{PART}__{key}_{tag}.png").convert("RGBA"))
        alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), K.ss)[:, :, 0] / 255.0
        roi = grip_roi(K, key)
        d = out["crops"][key]
        d["grip_only_silhouette_iou"] = round(C.iou(alpha > 0.5, K.mask(key), roi), 4)
        if key in ref["panels"]:
            cam = K.part_camera(PART, key)
            d["panel"] = GM.panel_iou(cam, K.panel(key).shape[:2], ref["panels"][key])
            bg = CU.fit_background(K.panel(key))[3]
            ours = CU.downscale(CU.composite_on(bg, rgba, K.ss), K.ss)
            d["lattice"] = GM.lattice_compare(K.panel(key), ours, ref["panels"][key]["fft_windows"])
    (REV / f"{tag}_loop.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float)[:4000])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    run(a.tag, not a.no_build, not a.no_render)
