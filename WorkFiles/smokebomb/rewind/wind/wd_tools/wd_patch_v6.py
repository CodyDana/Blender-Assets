p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:120])
    s = s.replace(old, new)


a = s.index("def coverage(")
new = '''def core_axes(n: int, first_axis, last_axis) -> np.ndarray:
    """n loop axes spread evenly over the hemisphere (a Fibonacci set: a circle's axis and
    its antipode are one circle), walked as a short path (nearest neighbour + 2-opt) that
    starts at ``first_axis``; signs aligned so the sense of travel never flips between
    loops.  The walk is reversed if that brings its end nearer ``last_axis``."""
    fa = normalize(first_axis)
    la = normalize(last_axis)
    ga = math.pi * (3 - math.sqrt(5))
    pts = []
    for k in range(n):
        z = 1 - (k + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        pts.append([r * math.cos(k * ga), r * math.sin(k * ga), z])
    pts = normalize(np.array(pts))
    zc = np.array([0.0, 0.0, 1.0])
    v = np.cross(zc, fa)
    if np.linalg.norm(v) > 1e-9:
        pts = pts @ rot_about(v, math.acos(np.clip(fa[2], -1, 1))).T

    def dist(a, b):
        return math.acos(min(1.0, abs(float(np.dot(a, b)))))
    left = list(range(1, n))
    path = [0]
    while left:
        j = min(left, key=lambda q: dist(pts[path[-1]], pts[q]))
        path.append(j)
        left.remove(j)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a0, a1, b0, b1 = pts[path[i - 1]], pts[path[i]], pts[path[j]], pts[path[j + 1]]
                if dist(a0, b0) + dist(a1, b1) < dist(a0, a1) + dist(b0, b1) - 1e-9:
                    path[i:j + 1] = path[i:j + 1][::-1]
                    improved = True
    axes = [pts[i] for i in path]
    if dist(axes[0], la) < dist(axes[-1], la):
        axes = axes[::-1]
    out = [normalize(axes[0])]
    for ax in axes[1:]:
        ax = normalize(ax)
        out.append(ax if np.dot(ax, out[-1]) >= 0 else -ax)
    return np.array(out)


def core_path(axes: np.ndarray, width_frac_d: float = 0.18, ds_deg: float = 0.2):
    """The CORE as one continuous precessing winding: loop k runs round axis n_k, and the
    axis turns smoothly (a slerp, eased) from n_k to n_{k+1} WHILE the loop is laid, so the
    tape is everywhere a near-great-circle (its in-plane curvature is the axis's turning
    rate, about (step angle) / (2 pi)) and there is no join anywhere.  Returns (points (M,3),
    width rad (M,))."""
    m = len(axes)
    per = int(round(360.0 / ds_deg))
    t = np.arange(m * per) / per
    k = np.minimum(np.floor(t).astype(int), m - 1)
    f = smootherstep(t - k)
    k1 = np.minimum(k + 1, m - 1)
    A, B = axes[k], axes[k1]
    om = np.arccos(np.clip(np.einsum("ij,ij->i", A, B), -1, 1))
    so = np.where(om < 1e-9, 1.0, np.sin(np.maximum(om, 1e-9)))
    wa = np.where(om < 1e-9, 1 - f, np.sin((1 - f) * om) / so)
    wb = np.where(om < 1e-9, f, np.sin(f * om) / so)
    N = normalize(wa[:, None] * A + wb[:, None] * B)
    U = np.zeros_like(N)
    ref = np.array([0.31, 0.47, 0.83])
    u = normalize(ref - np.dot(ref, N[0]) * N[0])
    for i in range(len(N)):
        u = u - np.dot(u, N[i]) * N[i]
        u = u / np.linalg.norm(u)
        U[i] = u
    V = np.cross(N, U)
    th = 2 * math.pi * t
    P = np.cos(th)[:, None] * U + np.sin(th)[:, None] * V
    return normalize(P), np.full(len(P), width_frac_d * 2.0)


'''
s = s[:a] + new + s[a:]

rep('''def assemble(passes: Sequence[PassSpec], tucks: Sequence[Tuck] = (), tail_deg: float = 60.0,
             ds_deg: float = 0.2, dphi_deg: float = 0.2, connectors: Optional[Sequence[dict]] = None) -> Winding:
    """Chain the passes (front arcs + far-side connectors + the finishing tail) into one
    tape sampled uniformly in s.  ``connectors`` may give frozen (La, Lb) per join."""
    pts, wid, gat, pid, phis, tails = [], [], [], [], [], []
    conn_info = []''', '''def _core_pass_stub(w: float) -> PassSpec:
    """a PassSpec standing for the core in the pass list (its geometry lives in the path)."""
    return PassSpec(name="core", shows=(), n=(0.0, 0.0, 1.0), e1=(1.0, 0.0, 0.0), phi_a=0.0, phi_b=1.0,
                    beta=(0.0,) * 4, width=(w,) * 4, role="core", note="continuous precessing core winding")


def _join(A0, tA, wa, ga, B0, tB, wb, gb, wall=True, La_max=175.0, Lb_max=175.0):
    """a connector between two free ends (point + unit tangent), as ``_connector``."""
    ea = PassSpec(name="_a", shows=(), n=tuple(normalize(np.cross(A0, tA))), e1=tuple(A0), phi_a=-1.0, phi_b=0.0,
                  beta=(0.0,) * 4, width=(0.5 * wa,) * 4, gather=(ga,) * 4)
    eb = PassSpec(name="_b", shows=(), n=tuple(normalize(np.cross(B0, tB))), e1=tuple(B0), phi_a=0.0, phi_b=1.0,
                  beta=(0.0,) * 4, width=(0.5 * wb,) * 4, gather=(gb,) * 4)
    return _connector(ea, eb, La_max=La_max, Lb_max=Lb_max, wall=wall)


def assemble(passes: Sequence[PassSpec], tucks: Sequence[Tuck] = (), tail_deg: float = 60.0,
             ds_deg: float = 0.2, dphi_deg: float = 0.2, connectors: Optional[Sequence[dict]] = None,
             core: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> Winding:
    """Chain the passes (front arcs + far-side connectors + the finishing tail) into one
    tape sampled uniformly in s.  ``core`` = (points, width rad) of a continuous core path
    laid first (``core_path``); it becomes pass 0, named "core"."""
    pts, wid, gat, pid, phis, tails = [], [], [], [], [], []
    conn_info = []
    passes = list(passes)
    off = 0
    if core is not None:
        CP, CW = core
        pts.append(CP)
        wid.append(CW)
        gat.append(np.zeros(len(CP)))
        pid.append(np.zeros(len(CP), int))
        phis.append(np.full(len(CP), np.nan))
        tails.append(np.full(len(CP), np.nan))
        tA = normalize(CP[-1] - CP[-2])
        p0 = passes[0]
        B0 = p0.point(p0.phi_a)[0]
        tB = p0.tangent(p0.phi_a)[0]
        tB = normalize(tB - np.dot(tB, B0) * B0)
        P, Wd, G, T, info = _join(CP[-1], tA, float(CW[-1]), 0.0, B0, tB, float(p0.width_rad(p0.phi_a)[0]),
                                  float(p0.gather_at(p0.phi_a)[0]), wall=False)
        pts.append(P)
        wid.append(Wd)
        gat.append(G)
        pid.append(np.zeros(len(P), int))
        phis.append(np.full(len(P), np.nan))
        tails.append(np.full(len(P), np.nan))
        conn_info.append(dict(frm="core", to=p0.name, **info))
        passes = [_core_pass_stub(float(CW[0]) / 2)] + passes
        off = 1''')
rep('''    for k, ps in enumerate(passes):
        nph = max(8, int(math.ceil((ps.phi_b - ps.phi_a) / dphi_deg)))''', '''    for k, ps in enumerate(passes):
        if k < off:
            continue
        nph = max(8, int(math.ceil((ps.phi_b - ps.phi_a) / dphi_deg)))''')
rep('''"StackGrid", "splat_tape", "assemble", "apply_tucks", "core_passes", "coverage",''',
    '''"StackGrid", "splat_tape", "assemble", "apply_tucks", "core_passes", "core_axes", "core_path", "coverage",''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
