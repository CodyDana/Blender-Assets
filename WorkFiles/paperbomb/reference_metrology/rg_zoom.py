# -*- coding: utf-8 -*-
"""Debug zooms of the real-glyph reference. METROLOGY ONLY - debug/ never ships."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

a, _ = R.read_stored(R.RG)
H, W = a.shape[:2]

CROPS = dict(
    top_strip=(0, 300, 0, 70),
    bottom_strip=(0, 300, 590, 653),
    left_strip=(0, 60, 0, 653),
    right_strip=(245, 300, 0, 653),
    flame=(95, 205, 55, 140),
    ring_glyph=(20, 285, 130, 420),
    col_TL=(20, 90, 20, 190),
    col_TR=(195, 280, 20, 190),
    col_BR=(200, 280, 405, 520),
    col_BC=(105, 195, 420, 600),
    seal_big=(20, 120, 480, 610),
    seal_small=(215, 285, 530, 600),
    lower_centre=(110, 200, 420, 640),
    corner_TL_wide=(5, 75, 5, 75),
    corner_TR_wide=(230, 300, 5, 75),
    corner_BL_wide=(5, 75, 580, 650),
    corner_BR_wide=(230, 300, 580, 650),
)
for name, (x0, x1, y0, y1) in CROPS.items():
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(W, x1); y1 = min(H, y1)
    sc = max(2, min(10, int(600 / max(1, (x1 - x0)))))
    R.save_debug(a[y0:y1, x0:x1], "zoom_%s" % name, scale=sc)
    print(name, x0, x1, y0, y1, "scale", sc)
