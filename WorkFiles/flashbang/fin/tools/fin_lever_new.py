def lever_path(spec: FlashbangSpec, q: LodQuality):
    """Centreline of the lever's web in the XZ plane (y handled by the width functions), from the curl's free end
    over the knuckle and down to the bent tip.  Returns ([(x, z, tx, tz)], marks) with the unit tangent and the
    indices of the curl's end (top) and of the joggle's first / last point.

    FINALISE: the joggle is ONE straight diagonal step with a fillet at each bend (it was a cosine S-crank)."""
    kx, _ky, kz = spec.knuckle_c
    t = spec.lever_t
    rc = spec.knuckle_r + 0.05 + t / 2.0
    xu = kx + rc                                         # upper segment centreline x (= knuckle + clearance)
    xl = spec.lever_lower_x + t / 2.0
    pts = []
    for i in range(q.lever_curl + 1):                    # 165 deg -> 0 deg round the knuckle (clockwise, over the top)
        a = math.radians(165.0 - 165.0 * i / q.lever_curl)
        pts.append((kx + rc * math.cos(a), kz + rc * math.sin(a)))
    top_i = len(pts) - 1
    zj0, zj1 = spec.lever_joggle_z
    nf = 2 if q.lever_curl >= 8 else (1 if q.lever_curl >= 4 else 0)
    zt = spec.lever_tip_z
    zb = zt + spec.lever_tip_bend
    A, B, C, Dd = np.array([xu, kz]), np.array([xu, zj0]), np.array([xl, zj1]), np.array([xl, zb])

    def fillet(P0, P1, P2, r, n):
        d0, d1 = _unit(P1 - P0), _unit(P2 - P1)
        a, b = P1 - d0 * r, P1 + d1 * r
        out = []
        for f in np.linspace(0.0, 1.0, n + 2):
            out.append(tuple((1 - f) ** 2 * a + 2 * (1 - f) * f * P1 + f * f * b))
        return out
    f1 = fillet(A, B, C, 2.4, nf)
    j0 = len(pts)
    pts += f1
    f2 = fillet(B, C, Dd, 2.4, nf)
    pts += f2
    j1 = len(pts) - 1
    pts.append((xl, zb))
    nb = 2 if q.lever_curl >= 4 else 1
    for i in range(1, nb + 1):
        f = i / nb
        pts.append((xl - spec.lever_tip_in * f * f, zb - (zb - zt) * f))
    out = []
    P = np.array(pts)
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        tng = _unit(b - a)
        out.append((P[i][0], P[i][1], tng[0], tng[1]))
    return out, {"top": top_i, "j0": j0, "j1": j1}


def _lever_section(q: LodQuality, t: float, F: float, yp: float, ym: float):
    """The lever's cross-section in (n, y), n = along the outward normal from the web's centreline.
    FINALISE: a CHANNEL (U) - the web plus two flanges F deep toward the body - at LOD0/1 (8 points, CCW); a solid
    box of the same outline at LOD2 (the silhouette is identical)."""
    h = t / 2.0
    if q.box_chamfer:
        return [(h, ym), (h, yp), (h - F, yp), (h - F, yp - t), (-h, yp - t), (-h, ym + t), (h - F, ym + t),
                (h - F, ym)]
    return [(h, ym), (h, yp), (h - F, yp), (h - F, ym)]


def build_lever(mb: MeshBuilder, spec: FlashbangSpec, q: LodQuality):
    """The spoon: a CHANNEL swept along lever_path (FINALISE), its width tapering on the upper segment (the -Y edge
    slants, the +Y edge is straight - v4), the lower segment 0.26 D wide, the tip squared with rounded corners.  The
    flanges run the full length, so round the knuckle they become the hinge's cheeks either side of the knuckle."""
    path, marks = lever_path(spec, q)
    t = spec.lever_t
    F = spec.lever_flange
    P = np.array([(p[0], p[1]) for p in path])
    # the UV's v is the arc length of a DENSE reference path (the same at every LOD), read at each sample
    dense, _dm = lever_path(spec, LodQuality(1, 1, 1, 3, 1, 1, 1, 3, 3, 1, False, 3, 3, 3, 3, 3, 3, 96, True, (0, 0)))
    DP = np.array([(p[0], p[1]) for p in dense])
    fine = [DP[0]]
    for i in range(1, len(DP)):
        for f in np.linspace(0, 1, 41)[1:]:
            fine.append(DP[i - 1] + (DP[i] - DP[i - 1]) * f)
    fine = np.array(fine)
    fs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    s = np.array([fs[int(np.argmin(np.linalg.norm(fine - p, axis=1)))] for p in P])
    top_i, j0, j1 = marks["top"], marks["j0"], marks["j1"]
    yp_top, ym_top = 6.4, 6.4 - spec.lever_w_top
    yp_j, ym_j = 6.4, 6.4 - spec.lever_w_joggle
    yp_l, ym_l = spec.lever_w / 2.0, -spec.lever_w / 2.0

    def widths(si):
        if si <= s[top_i]:
            return yp_top, ym_top
        if si <= s[j0]:
            f = (si - s[top_i]) / max(s[j0] - s[top_i], 1e-9)
            return yp_top + (yp_j - yp_top) * f, ym_top + (ym_j - ym_top) * f
        if si <= s[j1]:
            f = (si - s[j0]) / max(s[j1] - s[j0], 1e-9)
            return yp_j + (yp_l - yp_j) * f, ym_j + (ym_l - ym_j) * f
        return yp_l, ym_l

    secs = []
    for i, (x, z, tx, tz) in enumerate(path[:-1]):
        yp, ym = widths(s[i])
        secs.append((x, z, tx, tz, yp, ym, s[i]))
    xe, ze, txe, tze = path[-1]
    xa, za = path[-2][0], path[-2][1]
    seg = math.hypot(xe - xa, ze - za)
    rcn = min(spec.lever_tip_corner_r, seg * 0.9)
    nt = 3 if q.box_chamfer else 1
    for k in range(1, nt + 1):
        ang = math.pi / 2.0 * k / (nt + 1)
        dd = rcn * (1.0 - math.sin(ang))
        ww = rcn * (1.0 - math.cos(ang))
        f = 1.0 - dd / seg
        secs.append((xa + (xe - xa) * f, za + (ze - za) * f, txe, tze, yp_l - ww, ym_l + ww, s[-1] - dd))
    last_w = rcn * 0.92 if nt > 1 else rcn * 0.6
    secs.append((xe, ze, txe, tze, yp_l - last_w, ym_l + last_w, s[-1]))

    def section(x, z, tx, tz, yp, ym):
        n = np.array([-tz, 0.0, tx])                 # +n = the web's OUTER face (away from body / knuckle)
        o = np.array([x, 0.0, z])
        Y = np.array([0.0, 1.0, 0.0])
        sec2 = _lever_section(q, t, F, yp, ym)
        pts = [o + n * a + Y * b for a, b in sec2]
        return pts, n, sec2

    S = [section(*sc[:6]) + (sc[6],) for sc in secs]
    npt = len(S[0][0])
    # outward normal of each 2-D section edge (the polygon is CCW in (n, y): outward = (dy, -dn))
    sec0 = S[0][2]
    area = sum(sec0[k][0] * sec0[(k + 1) % npt][1] - sec0[(k + 1) % npt][0] * sec0[k][1] for k in range(npt))
    sgn = 1.0 if area > 0 else -1.0
    for i in range(len(S) - 1):
        A, na, s2a, sa = S[i]
        B, nb_, s2b, sb = S[i + 1]
        ua = np.concatenate([[0.0], np.cumsum([np.linalg.norm(A[(k + 1) % npt] - A[k]) for k in range(npt)])])
        ub = np.concatenate([[0.0], np.cumsum([np.linalg.norm(B[(k + 1) % npt] - B[k]) for k in range(npt)])])
        nm = _unit(na + nb_)
        for k in range(npt):
            k1 = (k + 1) % npt
            vids = [mb.v(A[k], key=("lever", i, k)), mb.v(A[k1], key=("lever", i, k1)),
                    mb.v(B[k1], key=("lever", i + 1, k1)), mb.v(B[k], key=("lever", i + 1, k))]
            dn = s2a[k1][0] - s2a[k][0]
            dy = s2a[k1][1] - s2a[k][1]
            en, ey = sgn * dy, -sgn * dn
            hint = nm * en + np.array([0.0, 1.0, 0.0]) * ey
            mb.f(vids, [(ua[k], -sa), (ua[k + 1], -sa), (ub[k + 1], -sb), (ub[k], -sb)], "lever", "lever",
                 LOOK_LEVER, hint=hint)
    quads = ((0, 1, 4, 5), (1, 2, 3, 4), (5, 6, 7, 0)) if npt == 8 else ((0, 1, 2, 3),)
    for which, idx in ((0, 0), (1, len(S) - 1)):
        A, n, s2, si = S[idx]
        tng = np.array([path[0][2], 0.0, path[0][3]]) if which == 0 else np.array([path[-1][2], 0.0, path[-1][3]])
        hint = -tng if which == 0 else tng
        vids = [mb.v(A[k], key=("lever", idx, k)) for k in range(npt)]
        uvs = [(float(a), float(b)) for a, b in s2]
        for qd in quads:
            mb.f([vids[i] for i in qd], [uvs[i] for i in qd], f"lever_end{which}", "lever", LOOK_LEVER, hint=hint)
    return {"path_len_mm": round(float(s[-1]), 3), "sections": len(S), "section": "channel" if npt == 8 else "box",
            "flange_mm": F, "sheet_mm": t,
            "tip_z_mm": round(float(ze), 3), "upper_inner_x_mm": round(float(path[top_i][0] - t / 2), 3)}


