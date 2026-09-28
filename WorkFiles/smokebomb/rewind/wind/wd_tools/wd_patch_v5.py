p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()
a = s.index("def core_passes(")
b = s.index("# --------------------------------------------------------------------------- views + raster")
new = '''def core_passes(n: int, first_axis, last_axis, width_frac_d: float = 0.16, arc_deg: float = 170.0) -> List[PassSpec]:
    """The CORE: n near-closed loops wound the way a winder does it - each loop's axis a
    small step from the last (the ball turned a little in the hand), the axes together
    spread evenly over the sphere (a Fibonacci set, walked as a short path from
    ``first_axis`` to ``last_axis``), so the loops cover every point of the ball at least
    once and the first fitted pass follows the last loop without a hard turn.  Each loop
    runs phi -arc..+arc about the point nearest the camera, so it starts and ends on the far
    side, close to where the next loop starts."""
    fa = normalize(first_axis)
    la = normalize(last_axis)
    m = n
    ga = math.pi * (3 - math.sqrt(5))
    pts = []
    for k in range(m):
        z = 1 - (k + 0.5) / m              # hemisphere: a circle's axis and its antipode are one circle
        r = math.sqrt(max(0.0, 1 - z * z))
        pts.append([r * math.cos(k * ga), r * math.sin(k * ga), z])
    pts = normalize(np.array(pts))
    # rotate the set so its first axis is fa
    zc = np.array([0.0, 0.0, 1.0])
    v = np.cross(zc, fa)
    if np.linalg.norm(v) > 1e-9:
        pts = pts @ rot_about(v, math.acos(np.clip(fa[2], -1, 1))).T
    # a short path through the axes (nearest neighbour on |cos|, then 2-opt), fa -> near la
    def dist(a, b):
        return math.acos(min(1.0, abs(float(np.dot(a, b)))))
    left = list(range(1, m))
    path = [0]
    while left:
        j = min(left, key=lambda q: dist(pts[path[-1]], pts[q]))
        path.append(j)
        left.remove(j)
    improved = True
    while improved:
        improved = False
        for i in range(1, m - 2):
            for j in range(i + 1, m - 1):
                a0, a1, b0, b1 = pts[path[i - 1]], pts[path[i]], pts[path[j]], pts[path[j + 1]]
                if dist(a0, b0) + dist(a1, b1) < dist(a0, a1) + dist(b0, b1) - 1e-9:
                    path[i:j + 1] = path[i:j + 1][::-1]
                    improved = True
    axes = [pts[i] for i in path]
    # end on the fitted pass's axis
    if dist(axes[-1], la) > dist(axes[0], la) and m > 2:
        axes = axes[::-1]
    out = []
    prev = None
    for k, ax in enumerate(axes):
        ax = normalize(ax)
        if prev is not None and np.dot(ax, prev) < 0:
            ax = -ax                       # keep the sense of travel (no reversal between loops)
        prev = ax
        e1 = normalize(np.array([0.0, 0.0, 1.0]) - ax[2] * ax) if abs(ax[2]) < 0.999 else np.array([1.0, 0, 0])
        out.append(PassSpec(name=f"core{k:02d}", shows=(), n=tuple(float(x) for x in ax), e1=tuple(float(x) for x in e1),
                            phi_a=-arc_deg, phi_b=arc_deg, beta=(0.0,) * 4, width=(width_frac_d,) * 4,
                            role="core", note="core loop (buried under the outer passes)"))
    return out


def coverage(wd: "Winding", n_face: int = 128) -> Dict[str, object]:
    """how many stretches cover each cube-map cell; voids = cells nothing covers."""
    sg = StackGrid.build(wd, n_face=n_face)
    cnt = sg.count
    cen = _cube_centres(n_face)
    void = cnt == 0
    return dict(min=int(cnt.min()), mean=float(cnt.mean()), p05=float(np.percentile(cnt, 5)),
                max=int(cnt.max()), void_cells=int(void.sum()), void_frac=float(void.mean()),
                void_dirs=cen[void][:50].tolist(), grid=sg)


'''
s = s[:a] + new + s[b:]
# connector: allow no wall (core-to-core)
s = s.replace('''def _connector(pa: PassSpec, pb: PassSpec, La_max: float = 175.0, Lb_max: float = 175.0,
               step_deg: float = 0.25):''', '''def _connector(pa: PassSpec, pb: PassSpec, La_max: float = 175.0, Lb_max: float = 175.0,
               step_deg: float = 0.25, wall: bool = True):''')
s = s.replace('''        front = np.clip(z[inner] + 0.03, 0.0, None)
        # the connector must stay on the far side: a hard wall
        return float(np.mean(kg ** 2) * L + 1e5 * np.sum(front ** 2) + 0.02 * L)''', '''        front = np.clip(z[inner] + 0.03, 0.0, None) if wall else np.zeros(1)
        # the connector must stay on the far side: a hard wall
        return float(np.mean(kg ** 2) * L + 1e5 * np.sum(front ** 2) + 0.02 * L)''')
s = s.replace('''    for La in np.arange(30.0, La_max + 0.1, 7.5):
        for Lb in np.arange(30.0, Lb_max + 0.1, 7.5):''', '''    lo = 5.0 if not wall else 30.0
    for La in np.arange(lo, La_max + 0.1, 7.5):
        for Lb in np.arange(lo, Lb_max + 0.1, 7.5):''')
s = s.replace('''            else:
                P, W, G, T, info = _connector(ps, passes[k + 1])''', '''            else:
                both_core = ps.role == "core" and passes[k + 1].role == "core"
                P, W, G, T, info = _connector(ps, passes[k + 1], wall=not both_core,
                                              La_max=60.0 if both_core else 175.0,
                                              Lb_max=60.0 if both_core else 175.0)''')
s = s.replace('''"StackGrid", "splat_tape", "assemble", "apply_tucks", "core_passes",''', '''"StackGrid", "splat_tape", "assemble", "apply_tucks", "core_passes", "coverage",''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
