"""Corner rounding by the curvature-integral estimator, with a synthetic self-test.

For a circular fillet of radius r the tangent angle turns at a constant rate 1/r along the arc, so
    r = (total turn) / integral( (dphi/ds)^2 ds )
over the corner region. This needs no line fits or vertex, and it degrades gracefully: a perfectly
sharp corner returns the blur/pixelation floor, which the synthetic test calibrates.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C


def contour_curvature(cont, sm=5, dw=5):
    P = cont.astype(float)
    n = len(P)
    k = 2 * sm + 1
    ext = np.concatenate([P[-sm:], P, P[:sm]], 0)
    cs = np.cumsum(np.concatenate([np.zeros((1, 2)), ext], 0), 0)
    S = (cs[k:] - cs[:-k]) / k                      # smoothed contour
    seg = np.hypot(np.diff(S[:, 0], append=S[0, 0]), np.diff(S[:, 1], append=S[0, 1]))
    arc = np.concatenate([[0], np.cumsum(seg)[:-1]])
    L = float(seg.sum())
    t = np.roll(S, -dw, 0) - np.roll(S, dw, 0)
    phi = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    ds = (np.roll(arc, -dw) - np.roll(arc, dw)) % L
    dphi = (np.roll(phi, -dw) - np.roll(phi, dw))
    kappa = dphi / np.maximum(ds, 1e-6)
    return S, arc, L, phi, kappa, seg


def corner_radius(cont, i, half=60.0):
    S, arc, L, phi, kappa, seg = contour_curvature(cont)
    ds = np.minimum((arc - arc[i]) % L, (arc[i] - arc) % L)
    sel = ds < half
    turn = float(np.sum(kappa[sel] * seg[sel]))
    integ = float(np.sum(kappa[sel] ** 2 * seg[sel]))
    r = abs(turn) / integ if integ > 0 else float('nan')
    return r, math.degrees(turn), integ


def synth_corner(r_true, angle_deg=95.0, size=400):
    """rasterise a wedge of the given interior angle with a fillet radius r_true; return contour and the corner index"""
    a = math.radians(angle_deg)
    yy, xx = np.mgrid[0:size, 0:size]
    X = xx - size / 2.0; Y = (size / 2.0) - yy
    # wedge: interior between direction 0 and direction a (measured CCW), apex at origin
    n1 = np.array([0.0, 1.0])                      # inward normal of edge along +x
    d2 = np.array([math.cos(a), math.sin(a)])
    n2 = np.array([d2[1], -d2[0]])
    s1 = X * n1[0] + Y * n1[1]
    s2 = X * n2[0] + Y * n2[1]
    m = (s1 > 0) & (s2 > 0)
    if r_true > 0:
        # centre of the inscribed circle on the bisector at distance r/sin(a/2)
        dist = r_true / math.sin(a / 2)
        bx, by = math.cos(a / 2) * dist, math.sin(a / 2) * dist
        cut = (np.hypot(X - bx, Y - by) > r_true) & (s1 < r_true) & (s2 < r_true)
        m = m & ~cut
    m[0, :] = m[-1, :] = m[:, 0] = m[:, -1] = False
    cont = C.trace_contour(m)
    d = np.hypot(cont[:, 0] - size / 2.0, cont[:, 1] - size / 2.0)
    return cont, int(np.argmin(d)), m


if __name__ == "__main__":
    print("SELF TEST (interior angle 95 deg)")
    for rt in (0, 3, 6, 10, 15, 20, 25, 30, 40):
        cont, i, m = synth_corner(rt)
        r, turn, integ = corner_radius(cont, i)
        print("  r_true %5.1f -> r_est %6.2f  (turn %.1f deg)" % (rt, r, turn))
    OUTD = C.OUT
    rgbh = None
    mask = None
    import common
    R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
    cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
    res = []
    for cinfo in R1["corners"]:
        r, turn, integ = corner_radius(cont, cinfo["contour_i"])
        res.append(dict(kind=cinfo["kind"], radius_px=r, turn_deg=turn,
                        radius_ratio_span=r / R1["SPAN_px"]))
        print("%-20s r %6.2f px  (%.4f span)  turn %6.1f deg" % (cinfo["kind"], r, r / R1["SPAN_px"], turn))
    # tips too
    for q in range(4):
        i = R1["quarters_contour_idx"][q]["tip"]
        r, turn, integ = corner_radius(cont, i, half=40)
        res.append(dict(kind="tip", radius_px=r, turn_deg=turn, radius_ratio_span=r / R1["SPAN_px"]))
        print("%-20s r %6.2f px  (%.4f span)  turn %6.1f deg" % ("tip", r, r / R1["SPAN_px"], turn))
    json.dump(res, open(os.path.join(C.OUT, "corner_radius.json"), "w"), indent=1)
