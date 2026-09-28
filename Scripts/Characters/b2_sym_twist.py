"""b2_sym_twist.py - PRIVATE / DO NOT SHIP. Twist-aware mirror average of the 2B skin (used by b2_sym_build.py).
Writes nothing by itself.

Why: on the limbs (and the base of the neck) the skin's topological twin of a vertex sits rotated around the bone
axis from its mirrored geometric partner (upper arm ~84 deg median at the step C1 rest, forearm ~18, thigh ~17,
calf ~22): the two sides have the same shape but their vertex layouts are twisted against each other. A plain chord
average p' = (p + M p_twin) / 2 then cuts through the limb and shrinks it (upper arm radius -24 %).

Fix: per bone, the rigid "ring twist" theta(t) (median signed twin angle around the averaged bone axis, per axial bin,
interpolated along the bone) is estimated. Per vertex the angle and the axis are blended by the vertex's bone weights
(symmetric, mirror-averaged weights), then
    q  = R(-theta) M p_twin                  twin rotated back onto the vertex's own angle (the geometric partner)
    p' = R(+theta / 2) ((p + q) / 2)          average shape, vertex layout moved half way (both sides share the twist)
Only the rigid per-ring rotation is taken out; everything else (real shape differences, side shifts, the face) is
averaged exactly like before. Bones whose twist is negligible (|theta| < TH_MIN everywhere) and the head / hands /
feet (twin already on the geometric partner) keep theta = 0, so p' there is the plain chord average.
"""
import math, os
import numpy as np

M3 = np.array([-1.0, 1.0, 1.0])
NBINS = 8
TH_MIN_DEG = 3.0
# bones whose skin is a ring around the bone axis; the twist is estimated and removed on these
# (probe b2_sym_twistprobe.py -> checks_sym/twist_probe.json, then build + b2_sym_gate.py + b2_sym_detail.py per
# candidate set: on the four limb bones and spine_05 (base of the neck / upper chest, twin up to ~100 deg around at the
# top) the per-ring angle is coherent along the bone and de-twisting restores the girth / volume (volume change -0.52 %
# -> -0.10 % with spine_05); adding neck_01 / neck_02 (profiles change sign along the neck) left a lumpy neck, the
# torso bones (pelvis, spine_01..04: rings not centred on the spine axis) shrank pelvis faces, the clavicle made the
# shoulder section worse; those keep the plain chord average)
TWIST_BONES = ("upperarm", "lowerarm", "thigh", "calf", "spine_05")
if os.environ.get("B2_SYM_TWIST_BONES"):  # experiments only (the build uses the default)
    TWIST_BONES = tuple(os.environ["B2_SYM_TWIST_BONES"].split(","))


def other(n):
    return n[:-2] + "_r" if n.endswith("_l") else (n[:-2] + "_l" if n.endswith("_r") else n)


CHILD = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot", "clavicle": "upperarm",
         "pelvis": "spine_01", "spine_01": "spine_02", "spine_02": "spine_03", "spine_03": "spine_04",
         "spine_04": "spine_05", "spine_05": "neck_01", "neck_01": "neck_02", "neck_02": "head", "foot": "ball"}


def child_head(B, n):
    """the limb / spine axis runs from the bone's head to its chain child's head (MH bone tails do not follow the limb)."""
    base, sfx = (n[:-2], n[-2:]) if n.endswith(("_l", "_r")) else (n, "")
    c = CHILD.get(base)
    if c is not None:
        cn = c + sfx if (c + sfx) in B else c
        return np.array(B[cn].head_local)
    return np.array(B[n].tail_local)


def bone_axes(arm):
    """Symmetric (averaged) bone axis lines: name -> (point on axis = averaged head, unit axis, length)."""
    B = arm.data.bones
    out = {}
    for b in B:
        n = b.name
        h = np.array(b.head_local); t = child_head(B, n)
        o = B[other(n)]
        ho = np.array(o.head_local) * M3; to = child_head(B, other(n)) * M3
        c = (h + ho) / 2
        a = (t - h) / np.linalg.norm(t - h) + (to - ho) / np.linalg.norm(to - ho)
        a /= np.linalg.norm(a)
        L = (np.linalg.norm(t - h) + np.linalg.norm(to - ho)) / 2
        out[n] = (c, a, L)
    return out


def ref_dir(a):
    r = np.array([0.0, -1.0, 0.0]) if abs(a[2]) > 0.7 else np.array([0.0, 0.0, 1.0])
    u = r - (r @ a) * a
    return u / np.linalg.norm(u)


def cyl(P, c, a):
    """cylindrical coordinates about the line (c, a): axial t, radius r, angle (reference ref_dir(a))."""
    D = P - c
    t = D @ a
    V = D - t[:, None] * a
    u = ref_dir(a); w = np.cross(a, u)
    return t, np.linalg.norm(V, axis=1), np.arctan2(V @ w, V @ u)


def rot_about(P, c, a, th):
    """rotate points P about the line (c, a) by angle th (scalar or per point), right-handed (Rodrigues)."""
    th = np.broadcast_to(np.asarray(th, dtype=float), (len(P),)) if np.ndim(th) else np.full(len(P), float(th))
    a = np.broadcast_to(a, P.shape) if a.ndim == 1 else a
    c = np.broadcast_to(c, P.shape) if c.ndim == 1 else c
    D = P - c
    ct = np.cos(th)[:, None]; st = np.sin(th)[:, None]
    ad = (a * D).sum(axis=1)[:, None]
    return c + D * ct + np.cross(a, D) * st + a * ad * (1 - ct)


def estimate_twist(Xn, Q, W, order, axes, rep_mask, log=print):
    """Per twist bone: bin centres (t) and median twin angle (rad) per bin, from the vertices dominated by the bone
    (her left side + midline for pairs). Returns name -> (t_centres, theta) for her LEFT / midline bones, and a report."""
    dom = W.argmax(axis=1)
    bi = {n: i for i, n in enumerate(order)}
    prof = {}; rep = {}
    for base in TWIST_BONES:
        n = base + "_l" if base + "_l" in bi else base
        if n not in bi:
            continue
        c, a, L = axes[n]
        sel = np.nonzero((dom == bi[n]) & rep_mask)[0]
        if len(sel) < 30:
            continue
        tP, _, angP = cyl(Xn[sel], c, a)
        tQ, _, angQ = cyl(Q[sel], c, a)
        dang = (angQ - angP + np.pi) % (2 * np.pi) - np.pi
        tt = (tP + tQ) / 2
        edges = np.linspace(np.percentile(tt, 1), np.percentile(tt, 99) + 1e-9, NBINS + 1)
        tc = []; th = []
        for k in range(NBINS):
            m = (tt >= edges[k]) & (tt < edges[k + 1])
            if m.sum() < 8:
                continue
            tc.append((edges[k] + edges[k + 1]) / 2)
            th.append(float(np.median(dang[m])))
        tc = np.array(tc); th = np.array(th)
        # light smoothing along the bone (1-2-1), ends kept
        if len(th) >= 3:
            th = np.concatenate([[th[0]], (th[:-2] + 2 * th[1:-1] + th[2:]) / 4, [th[-1]]])
        if np.abs(np.degrees(th)).max() < TH_MIN_DEG:
            th = np.zeros_like(th)
        prof[n] = (tc, th)
        rep[n] = {"n": int(len(sel)), "t_mm": [round(float(x) * 1000, 1) for x in tc],
                  "twist_deg": [round(math.degrees(float(x)), 2) for x in th]}
        log("twist", n, rep[n]["twist_deg"])
    return prof, rep


def twist_field(Xn, Q, Wsym, order, axes, prof):
    """Per vertex (both sides): blended angle theta (weighted over all bones, 0 on non-twist bones), and the axis point c
    / unit axis a blended over the twist bones only (left bones: the averaged left axis, right bones: its mirror)."""
    nv = len(Xn)
    TH = np.zeros(nv); C = np.zeros((nv, 3)); A = np.zeros((nv, 3)); WS = np.zeros(nv); WT = np.zeros(nv)
    P = (Xn + Q) / 2
    for j, n in enumerate(order):
        w = Wsym[:, j]
        nz = np.nonzero(w > 0)[0]
        if len(nz) == 0:
            continue
        # a right bone's column uses the profile of its left twin about the mirrored axis
        nl = other(n) if n.endswith("_r") else n
        WS[nz] += w[nz]
        if nl not in prof:
            continue  # theta = 0 there; the axis is blended over the twist bones only
        c, a, L = axes[nl]
        if n.endswith("_r"):
            c = c * M3; a = a * M3
        tc, th = prof[nl]
        t = (P[nz] - c) @ a
        thv = np.interp(t, tc, th) if len(tc) > 1 else np.full(len(nz), th[0] if len(th) else 0.0)
        # a right bone uses the same angle about the mirrored axis: M R(a, th) M = R(Ma, -th) and the twin relation
        # M p_j = R(a, th) p_i mirrors to M p_i = R(Ma, th) p_j
        TH[nz] += w[nz] * thv
        C[nz] += w[nz, None] * c
        A[nz] += w[nz, None] * a
        WT[nz] += w[nz]
    WS[WS == 0] = 1
    tw = WT > 0
    C[tw] /= WT[tw, None]
    A[~tw] = np.array([0.0, 0.0, 1.0])
    A /= np.maximum(np.linalg.norm(A, axis=1), 1e-12)[:, None]
    TH /= WS
    return TH, C, A


def twist_average(Xn, mv, Wsym, order, axes, rep_mask, log=print):
    """Twist-aware mirror average. Returns (Xs, report). Exactly symmetric: the right side is the mirror of the left."""
    nv = len(Xn)
    selfm = mv == np.arange(nv)
    Q = Xn[mv] * M3
    prof, rep = estimate_twist(Xn, Q, Wsym, order, axes, rep_mask, log)
    TH, C, A = twist_field(Xn, Q, Wsym, order, axes, prof)
    Qd = rot_about(Q, C, A, -TH)
    Xs = rot_about((Xn + Qd) / 2, C, A, TH / 2)
    # the construction is mirror-equivariant (right vertices use the mirrored axis and the same angle), so evaluating it
    # on both sides must give mirror images up to float noise: checked, then made exact by mirroring one of each pair
    pre_err = float(np.linalg.norm(Xs - Xs[mv] * M3, axis=1).max())
    one = selfm | (Xn[:, 0] > Xn[mv, 0]) | ((Xn[:, 0] == Xn[mv, 0]) & (np.arange(nv) < mv))
    assert (one ^ one[mv] | selfm).all()
    Xs[~one] = Xs[mv[~one]] * M3
    Xs[selfm, 0] = 0.0
    chord = (Xn + Q) / 2
    chord[selfm, 0] = 0.0
    dn = np.linalg.norm(Xs - chord, axis=1)
    out = {"method": "twist-aware mirror average: per-ring twin twist theta(t) per bone (median, %d axial bins, 1-2-1 "
                     "smoothed, |theta| < %.0f deg -> 0), blended by the mirror-averaged bone weights; p' = R(theta/2) "
                     "((p + R(-theta) M p_twin) / 2); twist bones: %s" % (NBINS, TH_MIN_DEG, ", ".join(TWIST_BONES)),
           "profiles_left": rep,
           "both_sides_evaluated_mirror_err_mm_before_snap": round(pre_err * 1000, 6),
           "vertex_theta_deg": {"abs_mean": round(float(np.degrees(np.abs(TH[rep_mask])).mean()), 3),
                                "abs_max": round(float(np.degrees(np.abs(TH[rep_mask])).max()), 3)},
           "diff_from_plain_chord_average_mm": {"mean": round(float(dn.mean()) * 1000, 3),
                                                "p95": round(float(np.percentile(dn, 95)) * 1000, 3),
                                                "max": round(float(dn.max()) * 1000, 3)}}
    return Xs, out


