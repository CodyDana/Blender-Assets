"""Look-match round 1 (sword): per-part before / after compares on the sheet's own grid.

    python sfv4_lm_parts.py <before_dir> <after_dir> <out_dir> [before_tag] [after_tag]

Each part_<name>.png stacks, per view: [sheet crop | BEFORE (pre-look-match shipped asset) | AFTER (current shipped asset)]
at the same scale (ortho views on the sheet's pixel grid; detail views framed like the sheet's crops).
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_lm_img as I
import sfv4_lm_compose as C

#: part -> list of (view, sheet-row range or None for the whole view)
PARTS = {
    "pommel": [("hilt_front", (0, 60)), ("hilt_side", (0, 60)), ("hilt_back", (0, 60)), ("det_pommel", None)],
    "collar": [("hilt_front", (225, 300)), ("hilt_side", (225, 300)), ("hilt_back", (225, 300))],
    "guard": [("hilt_front", (255, 346)), ("hilt_side", (255, 346)), ("hilt_back", (255, 346)), ("det_guard", None)],
    "grip": [("hilt_front", (35, 280)), ("hilt_side", (35, 280)), ("hilt_back", (35, 280))],
    "blade": [("full_front", (330, 1225)), ("full_side", (330, 1225)), ("full_back", (330, 1225)), ("det_blade", None)],
}


def crop(img, view, rows):
    if rows is None:
        return img
    k = 4 if view.startswith("hilt_") else 1
    return img[rows[0] * k:rows[1] * k]


def main():
    bd, ad, od = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    bt = sys.argv[4] if len(sys.argv) > 4 else "before_"
    at = sys.argv[5] if len(sys.argv) > 5 else "after_"
    ref = I.read_png(C.REF)[..., :3]
    od.mkdir(parents=True, exist_ok=True)
    for part, views in PARTS.items():
        rows_img = []
        for view, rows in views:
            ims = [crop(C.ref_crop(ref, view), view, rows)]
            for d, t in ((bd, bt), (ad, at)):
                p = d / f"{t}{view}.png"
                ims.append(crop(I.read_png(p), view, rows) if p.exists() else np.ones_like(ims[0]))
            h = 520 if view.startswith("det_") else min(900, ims[0].shape[0] * (1 if view.startswith("hilt_") else 1))
            if view.startswith("hilt_"):
                h = min(900, max(360, ims[0].shape[0]))
            rows_img.append(I.hcat(ims, h))
        if part in ("blade",):
            # side by side (tall strips)
            H = max(r.shape[0] for r in rows_img[:3])
            strip = I.hcat(rows_img[:3], H, gap=16, gapv=0.6)
            det = rows_img[3]
            W = max(strip.shape[1], det.shape[1])
            pad = lambda a: np.concatenate([a, np.ones((a.shape[0], W - a.shape[1], 3))], 1)
            out = np.concatenate([pad(strip), np.full((16, W, 3), 0.6), pad(det)], 0)
        else:
            W = max(r.shape[1] for r in rows_img)
            pad = lambda a: np.concatenate([a, np.ones((a.shape[0], W - a.shape[1], 3))], 1)
            parts = []
            for i, r in enumerate(rows_img):
                if i:
                    parts.append(np.full((16, W, 3), 0.6))
                parts.append(pad(r))
            out = np.concatenate(parts, 0)
        I.write_png(od / f"part_{part}_sheet_before_after.png", out)
        print("part", part, out.shape)


if __name__ == "__main__":
    main()
