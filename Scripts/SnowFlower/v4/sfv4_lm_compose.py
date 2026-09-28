"""Look-match round 1 (sword): reference crop | our render, same scale, for each comparison view.
Run with Blender's bundled python (numpy only):  python sfv4_lm_compose.py <render_dir> <out_png_prefix> [views]"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_lm_img as I

ROOT = HERE.parents[2]
REF = ROOT / "References" / "SnowFlower" / "SnowFlower_user_reference.png"
AX = {"front": 287.5, "side": 489.0, "back": 681.0}
DET = {"det_guard": (0, 530, 808, 1222), "det_blade": (572, 858, 800, 1222), "det_pommel": (878, 1195, 808, 1222)}


def ref_crop(ref, view):
    if view.startswith("hilt_"):
        v = view[5:]
        x0 = int(round(AX[v] - 75))
        return I.resize(ref[0:346, x0:x0 + 150], h=346 * 4)
    if view.startswith("full_"):
        v = view[5:]
        x0 = int(round(AX[v] - 150))
        return ref[:, x0:x0 + 300]
    y0, y1, x0, x1 = DET[view]
    return ref[y0:y1, x0:x1]


def main():
    rd = Path(sys.argv[1])
    outp = sys.argv[2]
    views = sys.argv[3].split(",") if len(sys.argv) > 3 else ["hilt_front", "hilt_side", "hilt_back"]
    tags = sys.argv[4].split(",") if len(sys.argv) > 4 else [""]
    ref = I.read_png(REF)[..., :3]
    for v in views:
        rc = ref_crop(ref, v)
        ims = [rc]
        for t in tags:
            p = rd / f"{t}{v}.png"
            if p.exists():
                ims.append(I.read_png(p))
        h = rc.shape[0] if not v.startswith("det_") else 900
        I.write_png(f"{outp}{v}.png", I.hcat(ims, h))
    print("COMPOSE_DONE")


if __name__ == "__main__":
    main()
