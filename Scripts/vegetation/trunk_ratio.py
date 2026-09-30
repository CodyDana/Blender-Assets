"""Trunk width / crown width, measured the same way on a reference panel and on our render (PIL + numpy only).

f1 gate for the r0 judge's girth blocker. Along the trunk centreline (pixels), on every row between 15 % and 50 % of
the tree height above the base, take the horizontal run of trunk pixels through the centreline; the ratio is the
median run width over the crown width (foliage extent). Horizontal runs overestimate a leaning trunk the same way
on both images, so the comparison is like for like; the absolute number is not a true diameter.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

import numpy as np


def ratio(wood: np.ndarray, foliage: np.ndarray, centreline_px: Sequence[Tuple[float, float]], base_y: float,
          apex_y: float, lo: float = 0.15, hi: float = 0.5) -> Dict:
    C = np.asarray(centreline_px, float)
    order = np.argsort(-C[:, 1])                 # base (large y) first
    C = C[order]
    H = base_y - apex_y
    ws = []
    for y in np.arange(int(base_y - hi * H), int(base_y - lo * H)):
        if y < 0 or y >= wood.shape[0]:
            continue
        x = float(np.interp(-y, -C[:, 1], C[:, 0]))
        xi = int(round(x))
        row = wood[y]
        if not (0 <= xi < len(row)):
            continue
        if not row[xi]:
            # snap to the nearest trunk pixel within 4 px (the centreline trace is hand-drawn)
            near = [xi + d for d in (-1, 1, -2, 2, -3, 3, -4, 4) if 0 <= xi + d < len(row) and row[xi + d]]
            if not near:
                continue
            xi = near[0]
        l = xi
        while l > 0 and row[l - 1]:
            l -= 1
        r = xi
        while r < len(row) - 1 and row[r + 1]:
            r += 1
        ws.append(r - l + 1)
    xs = np.nonzero(foliage.any(0))[0]
    cw = float(xs.max() - xs.min() + 1) if len(xs) else 1.0
    if not ws:
        return {"ratio": None, "rows": 0, "crown_px": cw}
    w = np.array(ws, float)
    return {"ratio": round(float(np.median(w)) / cw, 4), "rows": len(ws), "crown_px": cw,
            "width_px_median": float(np.median(w))}
