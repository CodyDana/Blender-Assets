# -*- coding: utf-8 -*-
"""Debug zooms round 2. METROLOGY ONLY - debug/ never ships."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rg_lib as R
a, _ = R.read_stored(R.RG); H, W = a.shape[:2]
CROPS = dict(
    flame2=(95, 200, 80, 185),
    seal_big2=(15, 105, 480, 605),
    seal_small2=(210, 285, 525, 610),
    col_TL2=(15, 95, 25, 230),
    col_TR2=(190, 275, 25, 230),
    col_BR2=(195, 275, 410, 530),
    ring_full=(15, 290, 165, 445),
    bottom_chain=(120, 185, 580, 653),
    rule_top_mid=(100, 220, 25, 50),
    rule_left_mid=(5, 35, 200, 460),
)
for name, (x0, x1, y0, y1) in CROPS.items():
    x0=max(0,x0); y0=max(0,y0); x1=min(W,x1); y1=min(H,y1)
    sc = max(2, min(12, int(620/max(1,(x1-x0)))))
    R.save_debug(a[y0:y1, x0:x1], "zoom2_%s" % name, scale=sc)
    print(name, sc)
