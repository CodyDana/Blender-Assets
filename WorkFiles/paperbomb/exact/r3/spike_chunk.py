

# ===========================================================================
# Tapered prong tips (the corner flourishes' claws)
# ===========================================================================
#
# The thin prongs of the bottom corner flourishes are one or two reference pixels wide
# and taper to a point.  A half-level contour of a line that thin is rounded where it
# ends (the tip reads under half strength) and its spline, refined against the blur,
# grows a neck and a bulb: the claws came out as blobby fingers.  Each prong's END is
# therefore re-drawn by analysis by synthesis as a TAPERED SPIKE: the traced contour's
# arc past a cut (``cut_mm`` of contour either side of the tip) is erased, and a new tip
# outline is laid in its place - two cubic edges leaving the cut points along the traced
# contour's own tangents and meeting in a sharp point.  The tip position, the direction
# the edges arrive in, their opening and their fullness are moved (pattern search) until
# the re-rendered red (source PSF, full-strength density) reproduces the observed red in
# a window round the prong.  ``tip_mm`` only says WHERE to look.

SPIKES = (
    {"name": "claw_BL_long", "group": "frame", "layer": "red", "tip_mm": (7.895, 157.131), "cut_mm": 1.50},
    {"name": "claw_BR_spike", "group": "frame", "layer": "red", "tip_mm": (61.888, 157.301), "cut_mm": 1.80},
    {"name": "claw_BR_hook", "group": "frame", "layer": "red", "tip_mm": (64.467, 154.494), "cut_mm": 0.70},
)
#: the erased arc is pushed this far (source px) outward so no half-covered edge pixel
#: of the old tip survives the erase
SPIKE_CUT_OFFSET_PX = 0.25
#: the new outline also re-lays this much (source px) of the traced contour before each
#: cut point, so the join is inside solid ink and never shows a seam
SPIKE_OVERLAP_PX = 1.0


def _arc(loop, i0, n):
    """``abs(n)`` + 1 consecutive points of a closed loop from index ``i0`` (n < 0: backwards)."""
    m = len(loop)
    idx = (i0 + (np.arange(n + 1) if n >= 0 else -np.arange(-n + 1))) % m
    return loop[idx]


def _loop_index_at(loop, i0, s):
    """Index of the loop point ``s`` (px, signed) of arc length from index ``i0``."""
    m = len(loop)
    seg = np.hypot(*np.diff(np.vstack([loop, loop[:1]]), axis=0).T)
    k, acc = i0, 0.0
    if s >= 0:
        while acc < s:
            acc += seg[k % m]; k += 1
    else:
        while acc < -s:
            k -= 1; acc += seg[k % m]
    return k % m, k - i0


def spike_frame(loops_px, tip_px, cut_px):
    """Locate the prong on the traced loops: its loop, tip index, cut points, tangents."""
    best = None
    for li, q in enumerate(loops_px):
        d = np.hypot(q[:, 0] - tip_px[0], q[:, 1] - tip_px[1])
        i = int(np.argmin(d))
        if best is None or d[i] < best[2]:
            best = (li, i, float(d[i]))
    li, it, _ = best
    q = loops_px[li]
    m = len(q)

    def walk(it, u, sgn):
        # from the tip along the loop until the contour is ``cut_px`` back along the axis
        k, acc = 0, 0.0
        while True:
            k += 1
            a, b = q[(it + sgn * (k - 1)) % m], q[(it + sgn * k) % m]
            acc += float(np.hypot(*(b - a)))
            if float(np.dot(b - q[it], -u)) >= cut_px:
                break
            if acc > 3.0 * cut_px + 3.0:
                raise ValueError("spike cut not found within %.1f px of contour" % acc)
        return (it + sgn * k) % m, sgn * k
    # the axis: first from the tip to the mean of the arc round it, then from the cut's
    # midpoint to the tip; the tip is the loop point farthest along the axis
    _, n0 = _loop_index_at(q, it, cut_px)
    arcpts = _arc(q, (it - n0) % m, 2 * n0)
    u = q[it] - arcpts.mean(0)
    u = u / max(1e-9, float(np.hypot(*u)))
    for _ in range(4):
        _, n = _loop_index_at(q, it, 1.5)
        cand = [(it + k) % m for k in range(-n, n + 1)]
        it = max(cand, key=lambda k: (float(np.dot(q[k], u)), -k))
        i1, n1 = walk(it, u, -1)
        i2, n2 = walk(it, u, 1)
        v = q[it] - 0.5 * (q[i1] + q[i2])
        u = v / max(1e-9, float(np.hypot(*v)))
    tg = T._tangents(q, True)
    return {"loop": li, "tip_i": it, "i1": i1, "i2": i2, "n1": n1, "n2": n2,
            "E1": q[i1].copy(), "E2": q[i2].copy(), "t1": tg[i1].copy(), "t2": tg[i2].copy(),
            "tip": q[it].copy()}


def _bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def spike_polys(p, fr, loop):
    """p = [Tx, Ty, theta, psi, a1, a2, s1, s2] -> (erase polygon, ink polygon), px."""
    E1, E2, t1, t2 = fr["E1"], fr["E2"], fr["t1"], fr["t2"]
    Tp = np.array([p[0], p[1]])
    u = np.array([math.cos(p[2]), math.sin(p[2])]); perp = np.array([-u[1], u[0]])
    mid = 0.5 * (E1 + E2)
    s1 = 1.0 if float(np.dot(E1 - mid, perp)) >= 0 else -1.0
    psi = max(0.0, p[3])
    a1, a2, l1, l2 = (max(0.05, v) for v in p[4:8])
    left = _bez(E1, E1 + l1 * t1, Tp - a1 * (u - psi * s1 * perp), Tp)
    right = _bez(Tp, Tp - a2 * (u + psi * s1 * perp), E2 - l2 * t2, E2)
    ov = max(1, int(round(SPIKE_OVERLAP_PX / 0.05)))
    before = _arc(loop, fr["i1"], -ov)[::-1]          # E1' .. E1
    after = _arc(loop, fr["i2"], ov)                   # E2 .. E2'
    ink = np.vstack([before[:-1], left, right[1:], after[1:]])
    # the erased arc E1 -> tip -> E2, pushed outward, closed by its chord
    arc = _arc(loop, fr["i1"], (fr["i2"] - fr["i1"]) % len(loop))
    c = 0.5 * (arc[0] + arc[-1])
    d = arc - c
    nrm = np.hypot(d[:, 0], d[:, 1])[:, None]
    arc_o = arc + SPIKE_CUT_OFFSET_PX * d / np.maximum(nrm, 1e-9)
    ink = ink if T.signed_area(ink) > 0 else ink[::-1]
    cut = arc_o if T.signed_area(arc_o) > 0 else arc_o[::-1]
    return cut, ink


def fit_spike(spec, loops_px, obs, dens, fit) -> dict:
    tx, ty = fit.mm_to_px(*spec["tip_mm"])
    cut_px = spec["cut_mm"] * fit.ppmm
    fr = spike_frame(loops_px, (tx, ty), cut_px)
    loop = loops_px[fr["loop"]]
    mid = 0.5 * (fr["E1"] + fr["E2"])
    th0 = math.atan2(fr["tip"][1] - mid[1], fr["tip"][0] - mid[0])
    Lp = float(np.hypot(*(fr["tip"] - mid)))
    p0 = np.array([fr["tip"][0], fr["tip"][1], th0, 0.1, 0.35 * Lp, 0.35 * Lp, 0.3 * Lp, 0.3 * Lp])
    cut0, ink0 = spike_polys(p0, fr, loop)
    allp = np.vstack([cut0, ink0])
    x0, y0 = int(math.floor(allp[:, 0].min())) - 2, int(math.floor(allp[:, 1].min())) - 2
    x1, y1 = int(math.ceil(allp[:, 0].max())) + 2, int(math.ceil(allp[:, 1].max())) + 2
    win = _Window(loops_px, obs, dens, x0, y0, x1, y1)
    base_cut = win.base * (1.0 - T.fill_polys([cut0 - win.off], win.h, win.w, ss=16))

    def render(p):
        _, ink = spike_polys(p, fr, loop)
        a = T.fill_polys([ink - win.off], win.h, win.w, ss=16)
        return np.maximum(base_cut, a)

    def loss_cov(cov):
        pred = T.gauss_blur(cov, T.SOURCE_PSF_SIGMA_PX) * win.dens
        d = pred - win.obs
        o = win.obs / win.dens; q = pred / win.dens
        hinge = np.where(o > 0.5, np.clip(0.5 - q, 0, None), np.clip(q - 0.5, 0, None))
        hinge = np.where(np.abs(o - 0.5) > 0.03, hinge, 0.0)
        return float((d[win.inner] ** 2).sum() + HALF_LEVEL_WEIGHT * hinge[win.inner].sum())

    def prior(p):
        pen = 10 * max(0.0, float(np.hypot(p[0] - fr["tip"][0], p[1] - fr["tip"][1])) - 2.0)
        pen += 10 * (max(0.0, -p[3]) + max(0.0, p[3] - 0.6))
        pen += 10 * sum(max(0.0, 0.1 - v) + max(0.0, v - 1.2 * Lp) for v in p[4:8])
        return pen
    f = lambda p: loss_cov(render(p)) + prior(p)
    loss_traced = loss_cov(win.base)          # the traced tip as it was
    step = np.array([0.3, 0.3, 0.08, 0.1, 0.3, 0.3, 0.3, 0.3])
    mstep = np.array([0.01, 0.01, 0.003, 0.005, 0.01, 0.01, 0.01, 0.01])
    linit = f(p0)
    best, lb = pattern_search(f, p0, step, mstep)
    best, lb = pattern_search(f, best, step / 3.0, mstep)
    cut, ink = spike_polys(best, fr, loop)
    return {"name": spec["name"], "group": spec["group"], "layer": spec["layer"], "kind": "spike",
            "window_px": [x0, y0, x1, y1], "params_px": [round(float(v), 5) for v in best],
            "loss_traced": round(loss_traced, 5), "loss_init": round(linit, 5),
            "loss_fit": round(lb, 5), "cut_px": cut, "ink_px": ink,
            "density": round(float(win.dens.flat[0]), 5)}
