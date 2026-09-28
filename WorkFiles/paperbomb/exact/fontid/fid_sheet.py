# -*- coding: utf-8 -*-
import os, sys, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C
sys.path.insert(0, C.MET)
import pngread
names = sys.argv[sys.argv.index("--") + 1:]
out = names[0]; files = names[1:]
ims = []
for f in files:
    a, _ = pngread.read_png(os.path.join(C.HERE, f))
    a = a.astype(float) / 255.0
    ims.append(a[..., :3])
h = max(i.shape[0] for i in ims)
row = []
for i in ims:
    pad = np.ones((h, i.shape[1] + 8, 3)); pad[:i.shape[0], :i.shape[1]] = i
    row.append(pad)
C.save_png(np.concatenate(row, 1), os.path.join(C.HERE, out))
