"""Entryfix round 2: fit the C1 camera AND the entry layout together to reference 2 (1448 x 1086).

Level shift-lens camera at X 6 (look along +Y). Free: camera Y / Z, lens, shift (closed form); layout: the entry
lanterns' half spacing s (centres 6 -+ s), the bar's front face Y (by; the lanterns' backs 7 mm off it) and the genkan
floor Z (gz; the lanterns stand on it). Landmarks measured on the reference (profiles, entryfix round 2):
  lanterns: outer silhouette x 45 / 1398, inner x 195 / 1250, bottom y 1062, top (back rail) y 846
  bar: back top edge y 901, front arris y 928, face foot on the lower floor y 950
  case 1 plinth front foot (5.1 / 6.9, 3.05, 0): (543, 835) / (903, 835)
  painting (4.8, 15.9, 3.8) (650, 74); (7.2, 15.9, 1.5) (800, 221)
"""
import math
import sys

import numpy as np

W, H = 1448, 1086
GZ_LO, GAP_HI = -0.18, 0.40
LW, LHT = 0.46, 0.645


def proj(p, cam, f, shift, w=W, h=H):
    x, y, z = (p[i] - cam[i] for i in range(3))
    k = f / 36.0 * max(w, h)
    return (w / 2 + k * x / y, h / 2 - k * z / y + shift * max(w, h))


def lantern_box(cx, by, gz, gap=0.007):
    ly = by - gap - LW / 2
    return [(cx + sx * LW / 2, ly + sy * LW / 2, gz + t * LHT) for sx in (-1, 1) for sy in (-1, 1) for t in (0, 1)]


def feats(cam, f, s, lay, w=W, h=H):
    """Predicted landmark values: list of (value, target, weight, label)."""
    sx, by, gz = lay[:3]
    gap = lay[3] if len(lay) > 3 else 0.007
    out = []
    for side, cx in (("L", 6 - sx), ("R", 6 + sx)):
        pts = [proj(p, cam, f, s, w, h) for p in lantern_box(cx, by, gz, gap)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if side == "L":
            out += [(min(xs), 45, 1, "L out"), (max(xs), 195, 1, "L in")]
        else:
            out += [(max(xs), 1398, 1, "R out"), (min(xs), 1250, 1, "R in")]
        out += [(max(ys), 1062, 1, side + " bottom"), (min(ys), 846, 1, side + " top")]
    out += [(proj((6, by + 0.16, 0), cam, f, s, w, h)[1], 901, 2, "bar back"),
            (proj((6, by, 0), cam, f, s, w, h)[1], 928, 2, "bar arris"),
            (proj((6, by, gz), cam, f, s, w, h)[1], 950, 2, "bar foot")]
    for X, u in ((5.1, 543), (6.9, 903)):
        a, b = proj((X, 3.05, 0), cam, f, s, w, h)
        out += [(a, u, 1, f"case {X} x"), (b, 835, 1, f"case {X} y")]
    for p, (u, v) in (((4.8, 15.9, 3.8), (650, 74)), ((7.2, 15.9, 1.5), (800, 221))):
        a, b = proj(p, cam, f, s, w, h)
        out += [(a, u, 0.7, "paint x"), (b, v, 0.7, "paint y")]
    return out


def resid(cam, f, s, lay):
    return np.array([(v - t) * wt for v, t, wt, _ in feats(cam, f, s, lay)])


def best_shift(cam, f, lay):
    fs = feats(cam, f, 0.0, lay)
    num = den = 0.0
    for (v, t, wt, lab) in fs:
        if lab.endswith("x") or " out" in lab or " in" in lab:
            continue
        num += wt * wt * (t - v)
        den += wt * wt
    return num / den / W


def lintel_ok(cam, f, s, zl=3.63):
    top = (H / 2 / W * 36 + s * 36) / f          # frame-top slope (z per y) of the level camera
    return cam[2] + top * (0.24 - cam[1]) <= zl


def fit(f, lay_grid, yr=(-7.0, -1.0), zr=(2.4, 4.4)):
    best = None
    for lay in lay_grid:
        for yc in np.arange(yr[0], yr[1] + 1e-6, 0.1):
            for zc in np.arange(zr[0], zr[1] + 1e-6, 0.05):
                cam = (6.0, yc, zc)
                s = best_shift(cam, f, lay)
                if not lintel_ok(cam, f, s):
                    continue
                e = float(np.sqrt(np.mean(resid(cam, f, s, lay) ** 2)))
                if best is None or e < best[0]:
                    best = (e, cam, s, lay)
    return best


def refine(e, cam, f, s, lay):
    """Coordinate descent on (yc, zc, s_x, by, gz) at fixed f."""
    x = [cam[1], cam[2], lay[0], lay[1], lay[2], lay[3] if len(lay) > 3 else 0.007]
    steps = [0.05, 0.02, 0.02, 0.02, 0.01, 0.02]
    lo = [-9, 1.5, 1.8, 1.8, GZ_LO, 0.007]
    hi = [0.0, 4.6, 3.2, 3.0, -0.04, GAP_HI]

    def cost(x):
        cam, lay = (6.0, x[0], x[1]), (x[2], x[3], x[4], x[5])
        s = best_shift(cam, f, lay)
        if not lintel_ok(cam, f, s):
            return 1e9, s
        return float(np.sqrt(np.mean(resid(cam, f, s, lay) ** 2))), s

    c, s = cost(x)
    for _ in range(60):
        improved = False
        for i in range(6):
            for d in (-steps[i], steps[i]):
                y = list(x)
                y[i] = min(hi[i], max(lo[i], y[i] + d))
                cy, sy = cost(y)
                if cy < c - 1e-6:
                    x, c, s, improved = y, cy, sy, True
        if not improved:
            steps = [v / 2 for v in steps]
            if max(steps) < 1e-3:
                break
    return c, (6.0, x[0], x[1]), s, (x[2], x[3], x[4], x[5])


def report(tag, e, cam, f, s, lay):
    print(f"{tag}: f {f} rms {e:.1f} cam (6, {cam[1]:.2f}, {cam[2]:.2f}) shift {s:.3f} | lantern centres "
          f"{6 - lay[0]:.2f}/{6 + lay[0]:.2f} bar Y {lay[1]:.3f} gz {lay[2]:.3f} gap {(lay[3] if len(lay) > 3 else 0.007):.3f}")
    for v, t, wt, lab in feats(cam, f, s, lay):
        print(f"   {lab:12s} {v:7.1f}  ref {t}")
    # lantern shape: front face w:h and top-over-front in the frame
    sx, by, gz = lay[:3]
    ly = by - (lay[3] if len(lay) > 3 else 0.007) - LW / 2
    fb = proj((6 - sx - LW / 2, ly - LW / 2, gz), cam, f, s)
    ft = proj((6 - sx + LW / 2, ly - LW / 2, gz + LHT), cam, f, s)
    bt = proj((6 - sx, ly + LW / 2, gz + LHT), cam, f, s)
    print(f"   lantern front w:h {abs(ft[0]-fb[0]) / abs(fb[1]-ft[1]):.3f} (real {LW/LHT:.3f}), top/front "
          f"{(ft[1]-bt[1]) / abs(fb[1]-ft[1]):.3f}")


if __name__ == "__main__":
    cur_lay = (2.24, 2.56, -0.12)
    cur = ((6.0, -3.05, 3.42), 35.0, -0.316)
    e = float(np.sqrt(np.mean(resid(cur[0], cur[1], cur[2], cur_lay) ** 2)))
    report("current b2", e, cur[0], cur[1], cur[2], cur_lay)
    grid = [(sx, by, gz) for sx in (2.24, 2.5, 2.7) for by in (2.3, 2.56) for gz in (-0.12, -0.08)]
    for f in [float(a) for a in sys.argv[1:]] or [35.0, 40.0, 45.0, 50.0]:
        e, cam, s, lay = fit(f, grid)
        e, cam, s, lay = refine(e, cam, f, s, lay)
        report("fit", e, cam, f, s, lay)
