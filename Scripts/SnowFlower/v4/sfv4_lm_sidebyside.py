"""Look-match round 1 (sword): the published side-by-side - the sheet vs the SHIPPED asset, whole views on the sheet's
own pixel grid (front / side / back) and the three detail crops.

    python sfv4_lm_sidebyside.py <render_dir> <tag> <out.png>
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_lm_img as I
import sfv4_lm_compose as C


def main():
    rd, tag, outp = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    ref = I.read_png(C.REF)[..., :3]
    top = []
    for v in ("full_front", "full_side", "full_back"):
        pair = I.hcat([C.ref_crop(ref, v)[:1230], I.read_png(rd / f"{tag}{v}.png")[:1230]], 1230, gap=4, gapv=0.85)
        top.append(pair)
    row1 = I.hcat(top, 1230, gap=24, gapv=0.55)
    dets = []
    for v in ("det_guard", "det_pommel", "det_blade"):
        dets.append(I.hcat([C.ref_crop(ref, v), I.read_png(rd / f"{tag}{v}.png")], 520, gap=4, gapv=0.85))
    # the three detail pairs stacked in a column beside the whole views
    Wd = max(d.shape[1] for d in dets)
    col = []
    for k, d in enumerate(dets):
        if k:
            col.append(np.full((24, Wd, 3), 0.55))
        col.append(np.concatenate([d, np.ones((d.shape[0], Wd - d.shape[1], 3))], 1))
    col = np.concatenate(col, 0)
    col = I.resize(col, h=row1.shape[0])
    out = np.concatenate([row1, np.full((row1.shape[0], 24, 3), 0.55), col], 1)
    I.write_png(outp, out)
    print("SIDEBYSIDE", outp, out.shape)


if __name__ == "__main__":
    main()
