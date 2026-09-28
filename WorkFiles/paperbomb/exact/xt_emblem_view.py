# -*- coding: utf-8 -*-
"""4x visual comparison of a tracer variant on the emblem."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props"))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from props_lib import trace as T  # noqa: E402
import xt_io  # noqa: E402
import xt_emblem_bench as EB  # noqa: E402

kind = sys.argv[1] if len(sys.argv) > 1 else "bspline"
knot = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
S = 8
src = T.read_source()
fit = T.fit_card(src)
ak, behind, unm = T.ink_layers(src, fit)
x0, y0, x1, y1 = EB.WIN
keep = EB.component_mask(ak, EB.WIN)
loops, curves, stats = EB.trace_variant(ak, keep, kind, 8, knot)
for s in stats:
    print(s)
H, W = ak.shape
hi = EB.render(curves, H, W, scale=S)[y0 * S:y1 * S, x0 * S:x1 * S]
v2 = src.rgb[y0:y1, x0:x1]
v2n = np.repeat(np.repeat(v2, S, 0), S, 1)
paper = np.array(T.PAPER_STORED)
ink = np.array(T.BLACK_STORED)
ours = paper[None, None] * (1 - hi[..., None]) + ink[None, None] * hi[..., None]
# overlay: V2 (nearest) with our contour drawn in green
over = v2n.copy()
edge = (hi > 0.5) ^ T.erode(hi > 0.5, 1)
over[edge] = [0.0, 0.8, 0.1]
# corners
for c in curves:
    if not c.periodic:
        for p in c.pieces:
            cx, cy = int((p[0][0] - x0) * S), int((p[0][1] - y0) * S)
            over[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3] = [1, 0, 1]
row = np.concatenate([v2n, np.ones((v2n.shape[0], 8, 3)), ours, np.ones((v2n.shape[0], 8, 3)), over], 1)
xt_io.write(os.path.join(HERE, "emblem_view_%s_%.2f.png" % (kind, knot)), row)
print("written")
