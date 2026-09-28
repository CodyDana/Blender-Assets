p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:120])
    s = s.replace(old, new)
rep('''    def tangent(self, phi_deg) -> np.ndarray:
        h = 0.01
        return normalize(self.point(np.asarray(phi_deg) + h) - self.point(np.asarray(phi_deg) - h))''',
'''    def tangent(self, phi_deg) -> np.ndarray:
        """unit direction of laying; one-sided at the ends of the arc (the spline is flat
        outside [phi_a, phi_b], which is not the tape's direction)."""
        ph = np.atleast_1d(np.asarray(phi_deg, np.float64))
        h = 0.02
        a = np.clip(ph - h, self.phi_a, self.phi_b)
        b = np.clip(ph + h, self.phi_a, self.phi_b)
        b = np.where(b - a < 1e-9, a + h, b)
        return normalize(self.point(b) - self.point(a))''')
# connector: hard front constraint
rep('''        z = P[:, 2]
        inner = (s > 8 * DEG) & (s < L - 8 * DEG)
        front = np.clip(z[inner] + 0.02, 0.0, None)
        # it must also leave the ends in their own directions (no hairpin at the joins)
        return float(np.mean(kg ** 2) * L + 400.0 * np.sum(front ** 2) + 0.02 * L)''',
'''        z = P[:, 2]
        inner = (s > 4 * DEG) & (s < L - 4 * DEG)
        front = np.clip(z[inner] + 0.03, 0.0, None)
        # the connector must stay on the far side: a hard wall
        return float(np.mean(kg ** 2) * L + 1e5 * np.sum(front ** 2) + 0.02 * L)''')
# core: a slowly precessing spiral of axes
rep('''def core_passes(n: int, first_axis, last_axis, width_frac_d: float = 0.15,
                turn_deg: float = 137.508) -> List[PassSpec]:
    """An evenly precessing yarn-ball core: n great circles whose axes sweep a spiral over
    the sphere (golden-angle turns, so the loops cover it evenly) and then home onto
    ``last_axis`` so the first fitted pass follows without a hard turn."""
    fa = normalize(first_axis)
    la = normalize(last_axis)
    out = []
    ref = normalize(np.cross(fa, [0.31, 0.47, 0.83]))
    for k in range(n):
        # Fibonacci-sphere axis k (hemisphere of fa), then blended toward last_axis at the end
        z = 1.0 - (k + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        ang = k * turn_deg * DEG
        loc = np.array([r * math.cos(ang), r * math.sin(ang), z])
        # local frame about fa
        e_a = ref
        e_b = np.cross(fa, e_a)
        ax = normalize(loc[0] * e_a + loc[1] * e_b + loc[2] * fa)
        wgt = smootherstep((k - (n - 4)) / 3.0) if n > 4 else 0.0
        ax = normalize((1 - wgt) * ax + wgt * la)''',
'''def core_passes(n: int, first_axis, last_axis, width_frac_d: float = 0.15,
                turns: float = 2.25) -> List[PassSpec]:
    """A yarn-ball core wound the way a winder does it: the loop's axis precesses slowly
    along a spiral from ``first_axis`` out over the hemisphere (``turns`` revolutions), so
    consecutive loops are close (gentle connectors) and together they cover the sphere
    evenly; the last few loops home onto ``last_axis`` so the first fitted pass follows
    without a hard turn."""
    fa = normalize(first_axis)
    la = normalize(last_axis)
    out = []
    ref = normalize(np.cross(fa, [0.31, 0.47, 0.83]))
    e_b = np.cross(fa, ref)
    for k in range(n):
        t = (k + 0.5) / n
        polar = (8.0 + 80.0 * t) * DEG          # from near the axis out to the equator
        ang = 2 * math.pi * turns * t
        ax = normalize(math.cos(polar) * fa + math.sin(polar) * (math.cos(ang) * ref + math.sin(ang) * e_b))
        wgt = smootherstep((k - (n - 5)) / 4.0) if n > 5 else 0.0
        if np.dot(ax, la) < 0:
            la = -la
        ax = normalize((1 - wgt) * ax + wgt * la)''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_fitlib.py"
s = open(p, encoding="utf-8").read()
rep('''def _fit_pass_nocache(pf: PassFit, verbose: bool = False) -> W.PassSpec:
    import dataclasses
    ps = _fit_pass(pf, verbose)
    ps = refine_pass(pf, ps)''', '''def _fit_pass_nocache(pf: PassFit, verbose: bool = False) -> W.PassSpec:
    """fit; if either end of the arc is not safely behind a limb (z <= -0.08), extend the
    arc there (the extension is hidden, so the regulariser runs it straight) and refit."""
    import dataclasses
    rng = pf.phi_range or (-90.0 - pf.phi_pad, 90.0 + pf.phi_pad)
    for it in range(8):
        cur = dataclasses.replace(pf, phi_range=rng)
        ps = _fit_pass(cur, verbose)
        za = float(ps.point(ps.phi_a)[0, 2])
        zb = float(ps.point(ps.phi_b)[0, 2])
        a, b = rng
        if za > -0.08:
            a = max(a - 12.0, -178.0)
        if zb > -0.08:
            b = min(b + 12.0, 178.0)
        if (a, b) == rng:
            break
        rng = (a, b)
    pf = cur
    ps = refine_pass(pf, ps)''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
