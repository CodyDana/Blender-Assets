"""Stage H: per-part compares (reference | build) and the silhouette IoU in the reference camera (numpy only).

    python hb_h_compare.py <tag>          (Blender's bundled python)

Reads Renders/SnowFlowerHeels/<tag>_refcam_viewA.png + r1/<tag>_refcam_viewA_rgba.png; writes
r1/cmp_<tag>_<part>.png and r1/compare_<tag>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hb_common as C  # noqa: E402
import metro_png as P  # noqa: E402

PARTS = {   # reference pixel boxes (x0, y0, x1, y1), view A
    "counter": (0, 0, 330, 660),
    "strap_buckle": (130, 120, 500, 300),
    "heel_stiletto": (40, 560, 220, 930),
    "insole": (130, 380, 420, 860),
    "vamp_vine": (190, 760, 720, 1110),
    "toe": (560, 780, 894, 1190),
}


def f01(a):
    a = a.astype(float)
    return a / 255.0 if a.max() > 1.5 else a


def main():
    tag = sys.argv[1]
    ref = f01(P.read(str(C.REF_PNG)))[..., :3]
    ren = f01(P.read(str(C.RENDER_DIR / f"{tag}_refcam_viewA.png")))[..., :3]
    rgba = f01(P.read(str(C.R1 / f"{tag}_refcam_viewA_rgba.png")))
    alpha = rgba[..., 3]
    # silhouette: object pixels are opaque AND not the pure shadow (shadow catcher writes alpha with black rgb)
    lum = rgba[..., :3].mean(2)
    ours = (alpha > 0.5)
    mask_ref = f01(P.read(str(C.WORK / "ref" / "viewA_mask.png")))
    mask_ref = mask_ref[..., 0] if mask_ref.ndim == 3 else mask_ref
    x0, y0, x1, y1 = 0, 0, 894, 1202
    mine = ours[y0:y1, x0:x1]
    theirs = mask_ref[:y1 - y0, :x1 - x0] > 0.5
    inter = (mine & theirs).sum()
    union = (mine | theirs).sum()
    res = {"silhouette_iou_viewA": round(float(inter / max(union, 1)), 4),
           "ours_only_px": int((mine & ~theirs).sum()), "ref_only_px": int((theirs & ~mine).sum())}
    # silhouette overlay: red = reference only, blue = ours only, grey = both
    ov = np.ones(mine.shape + (3,))
    ov[mine & theirs] = 0.6
    ov[theirs & ~mine] = (0.9, 0.2, 0.2)
    ov[mine & ~theirs] = (0.2, 0.3, 0.9)
    P.write(str(C.R1 / f"cmp_{tag}_silhouette.png"), (ov * 255).astype(np.uint8))
    for name, (a, b, c, d) in PARTS.items():
        sheet = np.concatenate([ref[b:d, a:c], np.ones((d - b, 6, 3)), ren[b:d, a:c]], 1)
        scale = 2 if (c - a) < 450 else 1
        sheet = np.repeat(np.repeat(sheet, scale, 0), scale, 1)
        P.write(str(C.R1 / f"cmp_{tag}_{name}.png"), (np.clip(sheet, 0, 1) * 255).astype(np.uint8))
        # tone stats inside the reference silhouette of the box
        m = (mask_ref[b:d, a:c] > 0.5) & (ours[b:d, a:c])
        if m.sum() > 50:
            res[f"{name}_mean_lum_ref"] = round(float(ref[b:d, a:c][m].mean()), 3)
            res[f"{name}_mean_lum_ours"] = round(float(ren[b:d, a:c][m].mean()), 3)
            res[f"{name}_p95_lum_ref"] = round(float(np.percentile(ref[b:d, a:c][m].mean(1), 95)), 3)
            res[f"{name}_p95_lum_ours"] = round(float(np.percentile(ren[b:d, a:c][m].mean(1), 95)), 3)
    (C.R1 / f"compare_{tag}.json").write_text(json.dumps(res, indent=1))
    print("COMPARE", json.dumps(res))


main()
