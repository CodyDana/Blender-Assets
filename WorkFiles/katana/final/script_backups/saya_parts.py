"""Saya part generators (mm, SWORD frame; the game stage moves them into the saya frame). ``build_lod(lod)`` ->
{"body": MB, "kurikata": MB}.

body      ONE closed solid: the outer skin (koiguchi with its 0.4 mm mouth round, seam groove 0.3 x 0.2, lacquered body,
          seam groove, kojiri with a 4 mm round-over and a flat end), the flat mouth face, and the cavity from the fit
          stage (habaki pocket + blade cavity, end cap 10 mm past the tip). Everything concentric with the blade's
          mune arc (sections are radial planes).
kurikata  the horn knob on the omote, 80 mm from the mouth: rounded-rectangle footprint 30 x 11 (r 4 corners), domed
          9 mm proud, flat side walls with 0.6 mm rounds; a 14 x 4.5 cord hole through it along the radial axis,
          lined with brass shitodome (flange 18 x 8, 0.6 proud, on both walls). No cord (spec: sageo omitted).

Every face carries a local UV in mm, an island id and per-corner attributes (s, around, extra, code) for the painter.
"""
from __future__ import annotations

import math

import numpy as np

import saya_spec as S
from katana_mesh import MB, cap_fill

CODES = {"lacquer": 0, "koiguchi": 1, "kojiri": 2, "mouth": 3, "pocket": 4, "cavity": 5, "kurikata": 6,
         "brass": 7, "kojiri_end": 8, "groove": 9}
SMOOTH_ANGLE = {"body": 35.0, "kurikata": 35.0}
FIT_DIR = S.ROOT / "WorkFiles" / "katana" / "saya_build" / "fit"


def island_scale(isl):
    if isl.startswith("cav_deep"):
        return 0.12
    if isl.startswith("cav_pocket"):
        return 0.6
    if isl.startswith("kuri_tunnel"):
        return 0.6
    return 1.0


def A(code, s=0.0, around=0.0, extra=0.0):
    return (float(s), float(around), float(extra), float(CODES[code]))


def tri_ccw(p2):
    (a0, b0), (a1, b1), (a2, b2) = p2
    return (a1 - a0) * (b2 - b0) - (a2 - a0) * (b1 - b0) > 0


def bridge(oi, o2, ii, i2, centre):
    """Triangles joining two closed CCW loops (different vertex counts) around a common ``centre``, merged by angle.
    Returns index triples (the caller fixes the orientation)."""
    def unwrap(p, start):
        a = np.arctan2(p[:, 1] - centre[1], p[:, 0] - centre[0])
        a = np.roll(a, -start)
        d = np.mod(np.diff(a), 2 * math.pi)
        return np.concatenate([[a[0]], a[0] + np.cumsum(d)])
    o2, i2 = np.asarray(o2), np.asarray(i2)
    no, ni = len(oi), len(ii)
    ao = unwrap(o2, 0)
    ai_raw = np.arctan2(i2[:, 1] - centre[1], i2[:, 0] - centre[0])
    i0 = int(np.argmin(np.abs(np.angle(np.exp(1j * (ai_raw - ao[0]))))))
    ai = unwrap(i2, i0)
    ai += ao[0] + float(np.angle(np.exp(1j * (ai[0] - ao[0])))) - ai[0]
    ao = np.append(ao, ao[0] + 2 * math.pi)
    ai = np.append(ai, ai[0] + 2 * math.pi)
    O = lambda k: oi[k % no]
    I = lambda k: ii[(i0 + k) % ni]
    tris = []
    o = i = 0
    while o < no or i < ni:
        na = ao[o + 1] if o < no else np.inf
        nb = ai[i + 1] if i < ni else np.inf
        if na <= nb:
            tris.append((O(o), O(o + 1), I(i)))
            o += 1
        else:
            tris.append((O(o), I(i + 1), I(i)))
            i += 1
    return tris


def fan_cap(mb, ring_idx, pts2, centre3, island, mat, normal_minus_t, attr):
    """Flat cap of a convex ring as a fan from a centre vertex (no sliver triangles: ear clipping of a dense ring
    produced 0.009 mm-high slivers that Unreal's build drops as degenerate). ``pts2`` (rho, y) of the ring (CCW);
    normal_minus_t: True -> triangles CCW in (rho, y) (normal -t), False -> CW (normal +t)."""
    c = mb.v(centre3)
    cen2 = np.asarray(pts2).mean(axis=0)
    n = len(ring_idx)
    for k in range(n):
        k2 = (k + 1) % n
        tri = (c, ring_idx[k], ring_idx[k2]) if normal_minus_t else (c, ring_idx[k2], ring_idx[k])
        p2 = {c: cen2, ring_idx[k]: pts2[k], ring_idx[k2]: pts2[k2]}
        mb.f(tri, [tuple(np.asarray(p2[v]) - cen2) for v in tri], island, mat, [attr] * 3)


# ============================================================================================ body
def skin_rows(lod):
    """Rows of the outer skin, mouth -> kojiri end: (s, shrink, V, island_after, code_after). The band between row r
    and r + 1 takes row r's island and code. V is the analytic along-UV (mm), the same function for every LOD (the
    0.2 mm groove walls add 0.2 each to V, so the seams of all LODs sample the same texels)."""
    rows = []
    nrd = {0: 3, 1: 2, 2: 1}[lod]
    for i in range(nrd + 1):
        th = math.pi / 2 * i / nrd
        s = S.S_MO + S.MOUTH_ROUND * (1 - math.cos(th))
        sh = S.MOUTH_ROUND * (1 - math.sin(th))
        rows.append((s, sh, S.S_MO + (S.MOUTH_ROUND - sh) + (s - S.S_MO), "kg_skin", "koiguchi"))
    off = S.MOUTH_ROUND
    h, d = S.SEAM_W / 2, S.SEAM_D

    def groove(s0, off, wall0, after):
        """wall0 = (island, code) of the wall on the near side; after = (island, code) beyond the groove."""
        if lod == 0:
            near_is_lacquer = wall0[1] == "lacquer"
            bottom = (after[0], "groove") if near_is_lacquer else (wall0[0], "groove")
            far_wall = (after[0], "groove") if near_is_lacquer else after
            return [(s0 - h, 0.0, s0 - h + off, *wall0), (s0 - h, d, s0 - h + off + d, *bottom),
                    (s0 + h, d, s0 + h + off + d, *far_wall), (s0 + h, 0.0, s0 + h + off + 2 * d, *after)]
        return [(s0, 0.0, s0 + off + d, *after)]
    rows += groove(S.S_KG1, off, ("kg_skin", "groove"), ("body_a", "lacquer"))
    off += 2 * d
    s_mid = 0.5 * (S.S_KG1 + S.S_KJ0)
    step = S.BODY_STEP[lod]
    for a_, b_, isl_next in ((S.S_KG1, s_mid, "body_a"), (s_mid, S.S_KJ0, "body_b")):
        n = max(1, int(math.ceil((b_ - a_) / step)))
        for i in range(1, n):
            s = a_ + (b_ - a_) * i / n
            rows.append((s, 0.0, s + off, isl_next, "lacquer"))
        if b_ == s_mid:
            rows.append((s_mid, 0.0, s_mid + off, "body_b", "lacquer"))
    rows += groove(S.S_KJ0, off, ("body_b", "lacquer"), ("kj_skin", "kojiri"))
    off += 2 * d
    s = S.S_EN - S.KOJIRI_ROUND
    rows.append((s, 0.0, s + off, "kj_skin", "kojiri"))
    nro = {0: 6, 1: 3, 2: 2}[lod]
    for i in range(1, nro + 1):
        th = math.pi / 2 * i / nro
        s = S.S_EN - S.KOJIRI_ROUND + S.KOJIRI_ROUND * math.sin(th)
        sh = S.KOJIRI_ROUND * (1 - math.cos(th))
        rows.append((s, sh, s + off + sh, "kj_skin", "kojiri"))
    return rows


def build_body(lod):
    mb = MB("body")
    N = S.OUTER_N[lod]
    rows = skin_rows(lod)
    # ---- outer skin rings
    ring_idx, ring_rho_y, ring_s = [], [], []
    for (s, shrink, V, isl, code) in rows:
        pts = S.outer_ring(s, N, shrink)
        P = S.arc_to_xyz(np.full(N, s), pts[:, 0], pts[:, 1])
        ring_idx.append(mb.vs(P))
        ring_rho_y.append(pts)
        ring_s.append(s)
    for r in range(len(rows) - 1):
        s0, sh0, V0, isl, code = rows[r]
        s1, sh1, V1, _, _ = rows[r + 1]
        P0 = S.outer_perimeter(s0) if sh0 == 0 else S.outer_perimeter(s0) - 2 * math.pi * sh0
        P1 = S.outer_perimeter(s1) if sh1 == 0 else S.outer_perimeter(s1) - 2 * math.pi * sh1
        slot = S.SLOT_LACQUER if code == "lacquer" else S.SLOT_FIT
        for c in range(N):
            c2 = (c + 1) % N
            f0, f1 = c / N, (c + 1) / N
            q = [ring_idx[r][c], ring_idx[r + 1][c], ring_idx[r + 1][c2], ring_idx[r][c2]]
            uv = [((f0 - 0.5) * P0, V0), ((f0 - 0.5) * P1, V1), ((f1 - 0.5) * P1, V1), ((f1 - 0.5) * P0, V0)]
            at = [A(code, s0, f0, sh0), A(code, s1, f0, sh1), A(code, s1, f1, sh1), A(code, s0, f1, sh0)]
            mb.f(q, uv, isl, slot, at)
        if abs(s0 - s1) < 1e-9:        # groove walls are radial planes: crisp edges both sides
            for c in range(N):
                mb.mark_sharp(ring_idx[r][c], ring_idx[r][(c + 1) % N])
                mb.mark_sharp(ring_idx[r + 1][c], ring_idx[r + 1][(c + 1) % N])
    # ---- kojiri end cap (outward normal +t: clockwise in (rho, y))
    last = ring_idx[-1]
    pts = ring_rho_y[-1]
    cen = pts.mean(axis=0)
    fan_cap(mb, last, pts, S.arc_to_xyz(S.S_EN, cen[0], cen[1]), "kj_cap", S.SLOT_FIT, False,
            A("kojiri_end", S.S_EN, 0.0, 0.0))
    for c in range(N):
        mb.mark_sharp(last[c], last[(c + 1) % N])
    # ---- cavity (from the fit stage): normals toward the cavity axis = CCW quads
    cv = np.load(FIT_DIR / f"cavity_L{lod}.npz")
    st, polys = cv["stations"], cv["polys"]
    M = polys.shape[1]
    cav_idx = []
    for s, poly in zip(st, polys):
        P = S.arc_to_xyz(np.full(M, s), poly[:, 0], poly[:, 1])
        cav_idx.append(mb.vs(P))
    s_pocket_mat = {0: 20.3, 1: 20.3, 2: 18.3}[lod]
    for k in range(len(st) - 1):
        pocket = st[k + 1] <= s_pocket_mat + 1e-6
        code = "pocket" if pocket else "cavity"
        slot = S.SLOT_FIT if pocket else S.SLOT_LACQUER
        isl = "cav_pocket" if st[k + 1] <= S.S_POCKET_END + 0.6 else "cav_deep"
        L0 = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.vstack([polys[k], polys[k][:1]]), axis=0), axis=1))])
        L1 = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.vstack([polys[k + 1], polys[k + 1][:1]]), axis=0), axis=1))])
        for c in range(M):
            c2 = (c + 1) % M
            q = [cav_idx[k][c], cav_idx[k][c2], cav_idx[k + 1][c2], cav_idx[k + 1][c]]
            uv = [(L0[c], st[k]), (L0[c + 1], st[k]), (L1[c + 1], st[k + 1]), (L1[c], st[k + 1])]
            at = [A(code, st[k], c / M), A(code, st[k], (c + 1) / M), A(code, st[k + 1], (c + 1) / M), A(code, st[k + 1], c / M)]
            mb.f(q, uv, isl, slot, at)
    # cavity end cap (normal toward the mouth, -t: CCW in (rho, y))
    pe = polys[-1]
    cen = pe.mean(axis=0)
    fan_cap(mb, cav_idx[-1], pe, S.arc_to_xyz(st[-1], cen[0], cen[1]), "cav_deep_end", S.SLOT_LACQUER, True,
            A("cavity", st[-1]))
    # ---- mouth face: annulus between the first skin ring (s_mouth, shrink 0.4) and the first cavity ring.
    o2 = ring_rho_y[0]
    i2 = polys[0]
    cen = i2.mean(axis=0)
    tris = bridge(ring_idx[0], o2, cav_idx[0], i2, cen)
    pos2 = {}
    for j, vi in enumerate(ring_idx[0]):
        pos2[vi] = o2[j]
    for j, vi in enumerate(cav_idx[0]):
        pos2[vi] = i2[j]
    for t in tris:
        p2 = [pos2[v] for v in t]
        if not tri_ccw(p2):                 # outward normal of the mouth face is -t: CCW in (rho, y)
            t = (t[0], t[2], t[1])
            p2 = [pos2[v] for v in t]
        mb.f(t, [tuple(p) for p in p2], "mouth_face", S.SLOT_FIT, [A("mouth", S.S_MO, p[0], p[1]) for p in p2])
    for c in range(N):
        mb.mark_sharp(ring_idx[0][c], ring_idx[0][(c + 1) % N])
    for c in range(M):
        mb.mark_sharp(cav_idx[0][c], cav_idx[0][(c + 1) % M])
    # skin ring at the end of the pocket region: nothing to mark (smooth by angle)
    return mb


# ============================================================================================ kurikata
def kuri_frame():
    K = S.KURI
    sk = K["s_centre"]
    rho_c = S.centre_rho(sk) + K["radial_offset_toward_ha"]
    D, W = S.dims(sk)
    O = S.arc_to_xyz(sk, rho_c, -W / 2)          # on the omote face line (the section's |y| maximum is at its centre)
    t = S.tangent(sk)
    r = S.radial(sk)
    h = np.array([0.0, -1.0, 0.0])
    return O, t, r, h


def kuri_xyz(a, b, hh):
    O, t, r, h = kuri_frame()
    a, b, hh = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(hh, float))
    return O[None, :] + a.reshape(-1, 1) * t + b.reshape(-1, 1) * r + hh.reshape(-1, 1) * h


BASE_H = -1.5        # the knob's base sinks 1.5 mm into the body (hidden, open)
KH = None


def kuri_dims():
    K = S.KURI
    return K["size"]["along"] / 2, K["size"]["radial_x"] / 2, K["size"]["proud_of_face"]


def plan_half_along(b, rc=4.0):
    A0, B0, _ = kuri_dims()
    bb = abs(b)
    if bb <= B0 - rc:
        return A0
    return A0 - rc + math.sqrt(max(rc * rc - (bb - (B0 - rc)) ** 2, 0.0))


def arch(Ah, H, n_pts, n_exp=2.6):
    """Chestnut profile in (a, h): from (+Ah, BASE_H) up over a domed top (height H) to (-Ah, BASE_H). CCW."""
    th = np.linspace(0.0, math.pi, n_pts)
    c, s = np.cos(th), np.sin(th)
    a = Ah * np.sign(c) * np.abs(c) ** (2.0 / n_exp)
    hh = BASE_H + (H - BASE_H) * np.abs(s) ** (2.0 / n_exp)
    return np.stack([a, hh], 1)


def ellipse(a, b, hc, n, phase=0.0):
    th = phase + 2 * math.pi * np.arange(n) / n
    return np.stack([a * np.cos(th), hc + b * np.sin(th)], 1)


def build_kurikata(lod):
    K = S.KURI
    mb = MB("kurikata")
    A0, B0, H = kuri_dims()
    n_pts = {0: 25, 1: 15, 2: 9}[lod]
    n_hole = {0: 28, 1: 16, 2: 10}[lod]
    hc = H * 0.45                                      # hole / shitodome centre height above the face (4.05)
    hole_a, hole_h = K["hole"]["slot"][0] / 2, K["hole"]["slot"][1] / 2
    fl_a, fl_h = K["shitodome"]["outer"][0] / 2, K["shitodome"]["outer"][1] / 2
    fl_p = K["shitodome"]["flange_proud"]
    rd = 0.6                                           # wall round
    if lod == 0:
        bst = [(-B0, rd), (-B0 + 0.15, 0.25), (-B0 + 0.4, 0.05), (-4.5, 0), (-3.5, 0), (-2.5, 0), (-1.5, 0), (0, 0),
               (1.5, 0), (2.5, 0), (3.5, 0), (4.5, 0), (B0 - 0.4, 0.05), (B0 - 0.15, 0.25), (B0, rd)]
    elif lod == 1:
        bst = [(-B0, rd), (-B0 + 0.3, 0.12), (-3.5, 0), (-1.5, 0), (1.5, 0), (3.5, 0), (B0 - 0.3, 0.12), (B0, rd)]
    else:
        bst = [(-B0, 0.0), (-3.0, 0), (3.0, 0), (B0, 0.0)]
    s_k = K["s_centre"]
    rings = []
    for b, d in bst:
        Ah = plan_half_along(b) - d
        prof = arch(Ah, H - d, n_pts)
        rings.append((b, prof))
    idx = []
    for b, prof in rings:
        idx.append(mb.vs(kuri_xyz(prof[:, 0], b, prof[:, 1])))
    # shell (outward: flipped quads); UV: around = profile arclength (centred), along = b
    for j in range(len(rings) - 1):
        b0, p0 = rings[j]
        b1, p1 = rings[j + 1]
        L0 = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p0, axis=0), axis=1))])
        L1 = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p1, axis=0), axis=1))])
        L0 -= L0[-1] / 2
        L1 -= L1[-1] / 2
        for k in range(n_pts - 1):
            q = [idx[j][k], idx[j + 1][k], idx[j + 1][k + 1], idx[j][k + 1]]
            uv = [(L0[k], b0), (L1[k], b1), (L1[k + 1], b1), (L0[k + 1], b0)]
            at = [A("kurikata", s_k + p0[k, 0], b0, p0[k, 1]), A("kurikata", s_k + p1[k, 0], b1, p1[k, 1]),
                  A("kurikata", s_k + p1[k + 1, 0], b1, p1[k + 1, 1]), A("kurikata", s_k + p0[k + 1, 0], b0, p0[k + 1, 1])]
            mb.f(q, uv, "kuri_shell", S.SLOT_FIT, at)
    # walls + shitodome + tunnel
    tunnel_rings = {}
    for side, j in ((+1, len(rings) - 1), (-1, 0)):
        b_w, prof = rings[j]
        wall_idx = idx[j]
        if lod < 2:
            # flange: outer ellipse on the wall, a bevel ring, the top annulus, the hole
            e_out = ellipse(fl_a, fl_h, hc, n_hole)
            e_bev = ellipse(fl_a - 0.15, fl_h - 0.15, hc, n_hole)
            e_hole = ellipse(hole_a, hole_h, hc, n_hole)
            levels = [(b_w, e_out), (b_w + side * (fl_p - 0.15), e_out), (b_w + side * fl_p, e_bev)] if lod == 0 else \
                     [(b_w, e_out), (b_w + side * fl_p, e_out)]
            fidx = [mb.vs(kuri_xyz(e[:, 0], bb, e[:, 1])) for bb, e in levels]
            hole_top = mb.vs(kuri_xyz(e_hole[:, 0], levels[-1][0], e_hole[:, 1]))
            inner_loop, inner2 = fidx[0], e_out
        else:
            e_hole = ellipse(hole_a, hole_h, hc, n_hole)
            hole_top = mb.vs(kuri_xyz(e_hole[:, 0], b_w, e_hole[:, 1]))
            inner_loop, inner2 = hole_top, e_hole
        # wall annulus between the closed profile (its base edge, subdivided, closes it) and the flange ellipse / hole
        nb = {0: 12, 1: 8, 2: 5}[lod]
        base = np.stack([np.linspace(prof[-1, 0], prof[0, 0], nb + 2)[1:-1], np.full(nb, BASE_H)], 1)
        base_idx = mb.vs(kuri_xyz(base[:, 0], b_w, base[:, 1]))
        loop_idx = list(wall_idx) + list(base_idx)
        loop2 = np.vstack([prof, base])
        tris = bridge(loop_idx, loop2, inner_loop, inner2, np.array([0.0, hc]))
        pos2 = {v: loop2[k] for k, v in enumerate(loop_idx)}
        pos2.update({v: inner2[k] for k, v in enumerate(inner_loop)})
        for t in tris:
            p2 = [pos2[v] for v in t]
            # outward normal +b on the +side wall -> clockwise in (a, h); -b side -> CCW
            if tri_ccw(p2) == (side > 0):
                t = (t[0], t[2], t[1])
                p2 = [pos2[v] for v in t]
            mb.f(t, [(side * p[0], p[1]) for p in p2], f"kuri_wall_{'u' if side > 0 else 'o'}", S.SLOT_FIT,
                 [A("kurikata", s_k + p[0], b_w, p[1]) for p in p2])
        for k in range(len(wall_idx) - 1):
            mb.mark_sharp(wall_idx[k], wall_idx[k + 1])
        if lod < 2:
            # flange side wall + bevel (outward from the ellipse: flipped order relative to +side growth)
            for li in range(len(levels) - 1):
                (bb0, e0), (bb1, e1) = levels[li], levels[li + 1]
                for k in range(n_hole):
                    k2 = (k + 1) % n_hole
                    if side > 0:
                        q = [fidx[li][k], fidx[li + 1][k], fidx[li + 1][k2], fidx[li][k2]]
                    else:
                        q = [fidx[li][k], fidx[li][k2], fidx[li + 1][k2], fidx[li + 1][k]]
                    uv = [(k * 1.0, abs(bb0 - b_w)), (k * 1.0, abs(bb1 - b_w)), ((k + 1) * 1.0, abs(bb1 - b_w)), ((k + 1) * 1.0, abs(bb0 - b_w))]
                    if side <= 0:
                        uv = [uv[0], uv[3], uv[2], uv[1]]
                    mb.f(q, uv, f"kuri_flange_side_{'u' if side > 0 else 'o'}", S.SLOT_FIT,
                         [A("brass", s_k, bb0, 0.0)] * 4)
            # flange top annulus (outward +side*b): between the last flange ring and the hole ring
            top = fidx[-1]
            e_top = levels[-1][1]
            for k in range(n_hole):
                k2 = (k + 1) % n_hole
                if side > 0:
                    q = [top[k], hole_top[k], hole_top[k2], top[k2]]
                else:
                    q = [top[k], top[k2], hole_top[k2], hole_top[k]]
                p2 = {top[k]: e_top[k], top[k2]: e_top[k2], hole_top[k]: e_hole[k], hole_top[k2]: e_hole[k2]}
                mb.f(q, [(side * p2[v][0], p2[v][1]) for v in q], f"kuri_flange_{'u' if side > 0 else 'o'}",
                     S.SLOT_FIT, [A("brass", s_k + p2[v][0], b_w, p2[v][1]) for v in q])
            for k in range(n_hole):
                mb.mark_sharp(fidx[0][k], fidx[0][(k + 1) % n_hole])
                mb.mark_sharp(hole_top[k], hole_top[(k + 1) % n_hole])
        tunnel_rings[side] = (hole_top, levels[-1][0] if lod < 2 else b_w)
    # tunnel (brass lining): normals toward the hole axis
    (i_m, b_m), (i_p, b_p) = tunnel_rings[-1], tunnel_rings[+1]
    e_hole = ellipse(hole_a, hole_h, hc, n_hole)
    Lh = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.vstack([e_hole, e_hole[:1]]), axis=0), axis=1))])
    for k in range(n_hole):
        k2 = (k + 1) % n_hole
        q = [i_m[k], i_m[k2], i_p[k2], i_p[k]]
        uv = [(Lh[k], b_m), (Lh[k + 1], b_m), (Lh[k + 1], b_p), (Lh[k], b_p)]
        mb.f(q, uv, "kuri_tunnel", S.SLOT_FIT, [A("brass", s_k + e_hole[k, 0], 0.0, e_hole[k, 1])] * 4)
    return mb


def build_lod(lod):
    return {"body": build_body(lod), "kurikata": build_kurikata(lod)}
