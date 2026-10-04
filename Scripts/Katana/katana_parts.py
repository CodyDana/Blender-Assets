"""Katana part generators (mm, sword frame). ``build_lod(lod)`` -> {part: MB}.

LOD0 is the game mesh at full resolution (every form is real geometry with crisp bevels: the blade's shinogi-zukuri
section with iori-mune and yokote, the tsuba rim, fuchi/kashira lips, and the tsuka-ito as crowned ribbons with
over/under crossings, hineri fold ridges and hishigami lift). LOD1 is the same generators coarser; LOD2 replaces the
wrapped tsuka by a shell whose texture is ray-cast from LOD0.

attr[3] of every corner is a part code the texture painter reads (see CODES).
"""
from __future__ import annotations

import math

import numpy as np

import katana_spec as K
from katana_mesh import MB, cap_fill, grid, profile_loft_uv, arclen

CODES = {"blade": 0, "habaki": 1, "seppa": 2, "tsuba": 3, "fuchi": 4, "kashira": 5, "menuki": 6, "eyelet": 7,
         "mekugi": 8, "band": 9, "core": 10, "cord": 11, "shell": 12, "blade_cap": 13}
SP = K.SP


def A(code, *vals):
    v = list(vals) + [0.0] * (3 - len(vals))
    return (v[0], v[1], v[2], float(code))


# ============================================================================================ blade
def build_blade(lod):
    mb = MB("blade")
    st = K.blade_stations(lod)
    code = CODES["blade"]
    rings = []
    meta = []
    for s in st:
        sec, prm = K.blade_section_uv(s, lod)
        rings.append(sec)
        meta.append(prm)
    m = len(rings[0])
    # region of the face between section points j and j+1
    if lod < 2:
        reg = [0] + [1] + [2] * (m - 4) + [3]
    else:
        reg = [1] + [2] * (m - 3) + [3]
    # vertex table: omote j=0..m-1 (0 = peak, m-1 = edge mid, shared), ura j=1..m-2
    idx = []
    for r, s in enumerate(st):
        row_o = []
        row_u = {}
        for j, (u, y, V) in enumerate(rings[r]):
            row_o.append(mb.v(K.blade_xyz(s, u, y)))
        for j in range(1, m - 1):
            u, y, V = rings[r][j]
            row_u[j] = mb.v(K.blade_xyz(s, u, -y))
        idx.append((row_o, row_u))

    def vid(r, j, side):
        row_o, row_u = idx[r]
        if side < 0 or j == 0 or j == m - 1:
            return row_o[j]
        return row_u[j]

    tx, tz = K.mune_pt(K.S_TIP)
    tip = mb.v((tx, 0.0, tz))
    s_split = K.S_Y / 2.0          # 334.05: a station of every LOD (LOD0 i 28/56, LOD1 13/26, LOD2 6/12)
    assert any(abs(x - s_split) < 1e-6 for x in st), "blade island split must be a station"
    for side, isl0 in ((-1, "blade_om"), (1, "blade_ur")):
        for r in range(len(st) - 1):
            s0, s1 = st[r], st[r + 1]
            isl = isl0 + ("_a" if s1 <= s_split + 1e-6 else "_b")
            for j in range(m - 1):
                a, b = vid(r, j, side), vid(r, j + 1, side)
                c, d = vid(r + 1, j + 1, side), vid(r + 1, j, side)
                uv = [(s0, rings[r][j][2]), (s0, rings[r][j + 1][2]), (s1, rings[r + 1][j + 1][2]), (s1, rings[r + 1][j][2])]
                at = [A(code, s0, rings[r][j][0], reg[j]), A(code, s0, rings[r][j + 1][0], reg[j]),
                      A(code, s1, rings[r + 1][j + 1][0], reg[j]), A(code, s1, rings[r + 1][j][0], reg[j])]
                q = [a, b, c, d]
                if side < 0:     # omote: section runs toward -x with y < 0 -> reverse for an outward normal
                    q, uv, at = q[::-1], uv[::-1], at[::-1]
                mb.f(q, uv, isl, K.SLOT_BLADE, at)
        # tip fan
        r = len(st) - 1
        for j in range(m - 1):
            a, b = vid(r, j, side), vid(r, j + 1, side)
            Vm = 0.5 * (rings[r][j][2] + rings[r][j + 1][2])
            uv = [(st[r], rings[r][j][2]), (st[r], rings[r][j + 1][2]), (K.S_TIP, Vm)]
            at = [A(code, st[r], rings[r][j][0], reg[j]), A(code, st[r], rings[r][j + 1][0], reg[j]), A(code, K.S_TIP, 0.0, reg[j])]
            q = [a, b, tip]
            if side < 0:
                q, uv, at = q[::-1], uv[::-1], at[::-1]
            mb.f(q, uv, isl0 + "_b", K.SLOT_BLADE, at)
    # sharp edges: peak, shoulders, shinogi, edge corners (all along); yokote (across, shinogi -> edge corner)
    jsh = [0] + ([1, 2] if lod < 2 else [1]) + [m - 2]
    for r in range(len(st) - 1):
        for side in (-1, 1):
            for j in jsh:
                mb.mark_sharp(vid(r, j, side), vid(r + 1, j, side))
    ry = st.index(K.S_Y)
    jshin = 2 if lod < 2 else 1
    for side in (-1, 1):
        for j in range(jshin, m - 2):
            mb.mark_sharp(vid(ry, j, side), vid(ry, j + 1, side))
    # machi cap (hidden under the habaki)
    ring = [vid(0, j, -1) for j in range(m)] + [vid(0, j, 1) for j in range(m - 2, 0, -1)]
    pts2 = [(u, y) for (u, y, V) in rings[0]] + [(rings[0][j][0], -rings[0][j][1]) for j in range(m - 2, 0, -1)]
    cap_fill(mb, ring, None, pts2, "blade_cap", K.SLOT_BLADE, flip=False,
             attrs=[A(CODES["blade_cap"])] * len(ring))
    return mb



# ============================================================================================ generic lofts
def loft_rings(mb, rings, island, mat, code, closed_top=None, closed_bot=None, cap_islands=("", ""), flip_caps=(False, False)):
    """rings: list of (N,3) arrays (CCW about +z, consecutive rows). Side faces + optional caps."""
    P = np.array(rings)
    uv = profile_loft_uv(P)
    nr, nc = P.shape[:2]
    at = np.zeros((nr, nc + 1, 4))
    at[..., 3] = code
    idx = grid(mb, P, True, island, mat, uv, at)
    for which, ring_i, isl, fl in (("bot", 0, cap_islands[0], flip_caps[0]), ("top", nr - 1, cap_islands[1], flip_caps[1])):
        if not isl:
            continue
        pts = P[ring_i]
        uv2 = [(float(p[0]), float(p[1])) for p in pts]
        cap_fill(mb, list(idx[ring_i]), pts, uv2, isl, mat, flip=fl, attrs=[A(code)] * nc)
    return idx


def se_ring(cx, a, b, n, z, N, cy=0.0, phase=0.0):
    return np.array([(cx + x, cy + y, z) for (x, y) in K.se_pts(a, b, n, N, phase)])




# ============================================================================================ habaki
def build_habaki(lod):
    mb = MB("habaki")
    H = SP["habaki"]
    z0, z1 = H["z"]
    N = {0: 48, 1: 24, 2: 16}[lod]
    bev = 0.4
    segs = {0: 2, 1: 1, 2: 1}[lod]

    def sec(z):
        t = (z - z0) / (z1 - z0)
        xa = K.lerp(H["section_base"]["x"][0], H["section_top"]["x"][0], t)
        xb = K.lerp(H["section_base"]["x"][1], H["section_top"]["x"][1], t)
        yh = K.lerp(H["section_base"]["y_half"], H["section_top"]["y_half"], t)
        return (xa + xb) / 2, (xb - xa) / 2, yh

    rings = []
    zs = [z0, z0 + 0.15] + ([K.lerp(z0, z1 - bev, 0.5)] if lod == 0 else []) + [z1 - bev]
    for z in zs:
        cx, a, b = sec(z)
        ins = 0.12 if z == z0 else 0.0     # small break on the lower edge
        rings.append(se_ring(cx, a - ins, b - ins, 4.0, z, N))
    for i in range(1, segs + 1):
        t = (math.pi / 2) * i / segs
        z = z1 - bev + bev * math.sin(t)
        ins = bev * (1 - math.cos(t))
        cx, a, b = sec(z)
        rings.append(se_ring(cx, a - ins, b - ins, 4.0, z, N))
    loft_rings(mb, rings, "habaki", K.SLOT_FIT, CODES["habaki"], cap_islands=("", "habaki_top"))
    return mb


# ============================================================================================ seppa
def build_seppa(lod, which):
    mb = MB("seppa_" + which)
    S = SP["seppa"]
    o = S["outline"]
    z0, z1 = S["z_blade_side"] if which == "blade" else S["z_tsuka_side"]
    N = {0: 48, 1: 24, 2: 16}[lod]
    r = S["edge_round"]
    a0, b0 = o["depth_x"] / 2, o["width_y"] / 2
    n = o["superellipse_n"]
    rings = []
    if lod == 2:
        prof = [(z0, 0.0), (z1, 0.0)]
    else:
        segs = 2 if lod == 0 else 1
        prof = []
        for i in range(segs + 1):
            t = (math.pi / 2) * i / segs
            prof.append((z0 + r - r * math.sin(t), r - r * math.cos(t)))
        prof = prof[::-1]
        for i in range(segs + 1):
            t = (math.pi / 2) * i / segs
            prof.append((z1 - r + r * math.sin(t), r - r * math.cos(t)))
    for z, ins in prof:
        rings.append(se_ring(0.0, a0 - ins, b0 - ins, n, z, N, phase=0.013))
    loft_rings(mb, rings, "seppa_" + which, K.SLOT_FIT, CODES["seppa"],
               cap_islands=("seppa_%s_bot" % which, "seppa_%s_top" % which), flip_caps=(True, False))
    return mb


# ============================================================================================ revolve helper
def revolve(mb, prof, N, island_fn, mat, code, axis_center=(0.0, 0.0), phase=0.0):
    """Revolve profile [(r, z), ...] about the z axis (through axis_center). Rows = profile points, columns =
    around (CCW). Normal = around x profile direction. island_fn(row) -> island; UV = (around arclength at the
    max radius, profile arclength)."""
    cx, cy = axis_center
    P = []
    for (r, z) in prof:
        P.append([(cx + r * math.cos(2 * math.pi * i / N + phase), cy + r * math.sin(2 * math.pi * i / N + phase), z)
                  for i in range(N)])
    P = np.array(P)
    pl = arclen(np.array([(r, 0.0, z) for r, z in prof]))
    rmax = max(r for r, z in prof)
    uv = np.zeros((len(prof), N + 1, 2))
    for k in range(len(prof)):
        uv[k, :, 0] = np.linspace(0, 2 * math.pi * rmax, N + 1)
        uv[k, :, 1] = pl[k]
    at = np.zeros((len(prof), N + 1, 4))
    at[..., 3] = code
    return grid(mb, P, True, island_fn, mat, uv, at), P


# ============================================================================================ tsuba
def build_tsuba(lod):
    mb = MB("tsuba")
    T = SP["tsuba"]
    R0 = T["diameter"] / 2
    zp0, zp1 = T["z_plate"]
    zr0, zr1 = T["mimi"]["z"]
    rw = T["mimi"]["width"]
    ri = R0 - rw
    zc = (zr0 + zr1) / 2
    hz = (zr1 - zr0) / 2
    N = {0: 60, 1: 32, 2: 24}[lod]
    narc = {0: 11, 1: 5, 2: 3}[lod]
    r_in = 22.0
    bot = [(r_in, zp0), (ri - 0.6, zp0), (ri, zr0 + 0.15), (ri + 0.6, zr0)] if lod < 2 else [(r_in, zp0), (ri, zp0), (ri + 0.6, zr0)]
    arc = []
    for i in range(1, narc + 1):
        a = -math.pi / 2 + math.pi * i / (narc + 1)
        arc.append((R0 - 1.2 + 1.2 * math.cos(a), zc + hz * math.sin(a)))
    top = [(ri + 0.6, zr1), (ri, zr1 - 0.15), (ri - 0.6, zp1), (r_in, zp1)] if lod < 2 else [(ri + 0.6, zr1), (ri, zp1), (r_in, zp1)]
    prof = bot + arc + top
    nb = len(bot)
    na = len(arc)

    def isl(row):
        if row < nb - 1:
            return "tsuba_bot"
        if row >= nb + na:
            return "tsuba_top"
        return "tsuba_rim"
    idx, P = revolve(mb, prof, N, isl, K.SLOT_BLADE, CODES["tsuba"])
    # UV for the flat faces: planar (x, y) instead of the revolve's (around, profile) -> rewrite those faces
    for fi, (f, isln) in enumerate(zip(mb.faces, mb.fisl)):
        if isln in ("tsuba_bot", "tsuba_top"):
            sg = -1.0 if isln == "tsuba_bot" else 1.0
            mb.fuv[fi] = tuple((sg * mb.verts[v][0], mb.verts[v][1]) for v in f)
    # inner discs (mostly under the seppa)
    for row, isln, fl in ((0, "tsuba_bot", True), (len(prof) - 1, "tsuba_top", False)):
        sg = -1.0 if isln == "tsuba_bot" else 1.0
        ring = list(idx[row])
        uv2 = [(sg * P[row][i][0], P[row][i][1]) for i in range(N)]
        cap_fill(mb, ring, None, uv2, isln, K.SLOT_BLADE, flip=fl,
                 attrs=[A(CODES["tsuba"])] * N)
    return mb


# ============================================================================================ fuchi
def build_fuchi(lod):
    mb = MB("fuchi")
    F = SP["fuchi"]
    z0, z1 = F["z"]
    ob, ot = F["outline_bottom"], F["outline_top"]
    n = F["superellipse_n"]
    N = {0: 48, 1: 28, 2: 16}[lod]
    wall = F["wall"]

    def outline(z):
        t = (z - z0) / (z1 - z0)
        t = min(max(t, 0.0), 1.0)
        return K.lerp(ob["depth_x"], ot["depth_x"], t) / 2, K.lerp(ob["width_y"], ot["width_y"], t) / 2

    prof = []                          # (z, inset) from the inner wall over the lower lip, up the outside, to the top
    if lod < 2:
        prof.append((z0 + 3.0, wall))
        nr = 4 if lod == 0 else 2
        rr = wall / 2
        for i in range(nr + 1):
            th = math.pi * i / nr
            prof.append((z0 + rr - rr * math.sin(th), rr + rr * math.cos(th)))
        prof.append((z1 - 0.5, 0.0))
        nb = 2 if lod == 0 else 1
        for i in range(1, nb + 1):
            t = (math.pi / 2) * i / nb
            prof.append((z1 - 0.5 + 0.5 * math.sin(t), 0.5 * (1 - math.cos(t))))
    else:
        prof = [(z0 + 2.0, wall), (z0, wall / 2), (z0 + 0.3, 0.0), (z1 - 0.3, 0.0), (z1, 0.4)]
    rings = []
    for z, ins in prof:
        a, b = outline(z)
        rings.append(se_ring(0.0, a - ins, b - ins, n, z, N, phase=0.021))
    loft_rings(mb, rings, "fuchi", K.SLOT_BLADE, CODES["fuchi"], cap_islands=("", "fuchi_top"))
    return mb


# ============================================================================================ kashira
def kashira_profile(lod):
    Kd = SP["kashira"]
    z_end, z_top = Kd["z"]
    o = Kd["base_outline"]
    D, W = o["depth_x"], o["width_y"]
    out = []   # (z, depth, width) from the end crown up the outside, over the lip, down the inner wall
    nd = {0: 8, 1: 4, 2: 2}[lod]
    dome = []
    for i in range(nd, 0, -1):
        t = i / nd
        shrink = 1 - (1 - math.cos(t * math.pi / 2)) * 0.62
        dome.append((z_end + 4.0 - 3.5 * math.sin(t * math.pi / 2) - 0.5 * t, D * shrink, W * shrink))
    out += dome
    out.append((z_end + 4.0, D, W))
    out.append((z_top - 0.45, D, W))
    if lod < 2:
        rr = 0.4
        nr = 3 if lod == 0 else 2
        for i in range(1, nr + 1):
            th = math.pi * i / nr
            ins = rr - rr * math.cos(th)
            out.append((z_top - 0.45 + 0.45 * math.sin(th), D - 2 * ins, W - 2 * ins))
        out.append((z_top - 3.0, D - 1.6, W - 1.6))
    else:
        out.append((z_top, D - 1.0, W - 1.0))
    return out


def kashira_halfwidth(z, dx):
    """|y| of the kashira's outer surface at height z and x offset dx from its centre (0 outside)."""
    Kd = SP["kashira"]
    prof = [p for p in kashira_profile(0)][:-5]          # outer part only (end crown .. straight side top)
    zs = [p[0] for p in prof]
    if z < zs[0] - 1e-9:
        return 0.0
    if z >= zs[-1]:
        D, W = prof[-1][1], prof[-1][2]
    else:
        for i in range(len(prof) - 1):
            if prof[i][0] <= z <= prof[i + 1][0]:
                t = (z - prof[i][0]) / max(prof[i + 1][0] - prof[i][0], 1e-9)
                D = K.lerp(prof[i][1], prof[i + 1][1], t)
                W = K.lerp(prof[i][2], prof[i + 1][2], t)
                break
    n = Kd["base_outline"]["superellipse_n"]
    a = D / 2
    if abs(dx) >= a:
        return 0.0
    return W / 2 * (1 - abs(dx / a) ** n) ** (1.0 / n)


def build_kashira(lod):
    mb = MB("kashira")
    Kd = SP["kashira"]
    cx = Kd["centre_x"]
    n = Kd["base_outline"]["superellipse_n"]
    N = {0: 40, 1: 24, 2: 16}[lod]
    prof = kashira_profile(lod)
    rings = [se_ring(cx, d / 2, w / 2, n, z, N, phase=0.017) for (z, d, w) in prof]
    loft_rings(mb, rings, "kashira", K.SLOT_BLADE, CODES["kashira"], cap_islands=("kashira_end", ""), flip_caps=(True, False))
    return mb


# ============================================================================================ eyelets (kashira shitodome)
def build_eyelets(lod):
    mb = MB("eyelets")
    if lod == 2:
        return mb
    Kd = SP["kashira"]
    E = Kd["eyelets"]
    cx = Kd["centre_x"]
    W = Kd["base_outline"]["width_y"]
    ro, ri = E["diameter_outer"] / 2, E["diameter_inner"] / 2
    N = {0: 24, 1: 12}[lod]
    prof = [(ri, -0.8), (ri, 0.15), (ri + 0.2, 0.33), (ro - 0.25, 0.36), (ro, 0.18), (ro + 0.03, -0.35)]
    for face, ysg in (("om", -1), ("ur", 1)):
        y0 = ysg * W / 2
        P = []
        for (r, h) in prof:
            ring = []
            for i in range(N):
                a = 2 * math.pi * i / N
                ring.append((cx + r * math.cos(a), y0 + ysg * h, E["z"] + r * math.sin(a)))
            P.append(ring)
        P = np.array(P)
        pl = arclen(np.array([(r, 0, h) for r, h in prof]))
        uv = np.zeros((len(prof), N + 1, 2))
        for k in range(len(prof)):
            uv[k, :, 0] = np.linspace(0, 2 * math.pi * ro, N + 1)
            uv[k, :, 1] = pl[k]
        at = np.zeros((len(prof), N + 1, 4))
        at[..., 3] = CODES["eyelet"]
        at[..., 0] = np.array([0, 0, 1, 1, 1, 1])[:, None]       # 0 = hole wall (dark), 1 = ring face
        eidx = grid(mb, P, True, "eyelet_" + face, K.SLOT_FIT, uv, at, flip=(ysg < 0))
        # floor of the hole (dark)
        cap_fill(mb, list(eidx[0]), None, [(r_[0] - cx + 20.0, r_[2] - E["z"]) for r_ in P[0]], "eyelet_" + face,
                 K.SLOT_FIT, flip=(ysg > 0),
                 attrs=[A(CODES["eyelet"], 0.0)] * N)
    return mb


# ============================================================================================ tsuka core (same)
def build_core(lod):
    mb = MB("core")
    N = {0: 36, 1: 24}[lod]
    dz = {0: 8.0, 1: 14.0}[lod]
    z_top, z_bot = 45.0, -206.0
    zs = list(np.arange(z_bot, z_top, dz)) + [z_top]
    rows = []
    for z in zs:
        cx, a, b = K.core_axes(z)
        rows.append([(cx + x, y, z) for (x, y) in K.se_pts(a, b, K.NT, N)])
    P = np.array(rows)
    uv = np.zeros((len(zs), N + 1, 2))
    for r in range(len(zs)):
        s = arclen(P[r], closed=True)
        uv[r, :, 0] = s
        uv[r, :, 1] = zs[r]
    at = np.zeros((len(zs), N + 1, 4))
    at[..., 3] = CODES["core"]
    grid(mb, P, True, "core", K.SLOT_GRIP, uv, at)
    return mb


# ============================================================================================ tsuka-ito
Z_CORD_START = 39.0
Z_CORD_END = -204.3


def _cord_dense(sign, cname):
    """Dense samples of the cord centre line (dz 0.02): z, alpha, ell, face, crown arclength."""
    zs = np.arange(Z_CORD_START, Z_CORD_END - 1e-9, -0.02)
    out = []
    prev = None
    L = 0.0
    for z in zs:
        alpha, ell, face = K.cord_centre(z, sign)
        p, nrm = K.core_point(z, alpha, 1.4 + 0.8 * abs(ell) ** 1.5)
        if prev is not None:
            L += float(np.linalg.norm(p - prev))
        prev = p
        out.append((z, alpha, ell, face, L))
    return np.array(out)


def _height_scale(z):
    """Taper the cords under the fuchi and into the kashira lip so they never break through those walls."""
    s = 1.0
    s -= 0.75 * K.smoothstep(35.0, 37.0, z)
    s -= 0.6 * (1.0 - K.smoothstep(-204.3, -202.0, z))
    return s


def build_cords(lod):
    mb = MB("cords")
    code = CODES["cord"]
    nper = {0: 18, 1: 8}[lod]
    # segment ends = the edge passes (every half pitch in the wrap-phase coordinate z'; real z by K.unwarp_z)
    zpe = K.warp_z(Z_CORD_END)
    apex_p = [K.warp_z(Z_CORD_START)] + [K.Z_FB - k * K.PITCH / 2 for k in range(0, 40)
                                         if K.Z_FB - k * K.PITCH / 2 > zpe] + [zpe]
    for cname, sign, cid in (("A", +1, 0.0), ("B", -1, 1.0)):
        dense = _cord_dense(sign, cname)
        zd = dense[:, 0][::-1]
        Ld = dense[:, 4][::-1]
        prev_last = None
        for si in range(len(apex_p) - 1):
            za, zb = apex_p[si], apex_p[si + 1]
            span = za - zb
            nseg = max(3, int(round(nper * span / (K.PITCH / 2))))
            taus = np.linspace(0, 1, nseg + 1)
            f = taus - (0.55 / (2 * math.pi)) * np.sin(2 * math.pi * taus)
            zsamp = [K.unwarp_z(zp) for zp in za - span * f]     # sampled evenly in wrap phase, placed at real z
            rows, uvr, atr = [], [], []
            for z in zsamp:
                alpha, ell, face = K.cord_centre(z, sign)
                c0, n0 = K.core_point(z, alpha, 0.0)
                cxz = K.core_axes(z)[0]
                hb, ht, ridge = K.cord_heights(z, cname, ell, face, c0[0] - cxz)
                w = min(K.cord_width(ell), K.cord_width_cap(z)) * K.hineri_pinch(z, cname, face)
                # tangent from neighbouring centre points
                e = 0.05
                pa, _ = K.core_point(z + e, K.cord_centre(z + e, sign)[0], 0.0)
                pb, _ = K.core_point(z - e, K.cord_centre(z - e, sign)[0], 0.0)
                t = pb - pa
                t /= np.linalg.norm(t)
                bvec = np.cross(n0, t)
                bvec /= np.linalg.norm(bvec)
                # finaliser: a w-wide strip meets the edge line over w / |bvec_z|, so neighbouring edge folds (spaced
                # half a pitch along z) overlapped where the cord crosses the edge obliquely; cap the width to fit
                w = min(w, K.cord_width_cap(z) * max(abs(float(bvec[2])), 0.35))
                if lod == 0:
                    sec = [(-w / 2, hb), (-w / 2, ht - 0.36), (-w / 2 + 0.75, ht - 0.05), (0.0, ht + ridge),
                           (w / 2 - 0.75, ht - 0.05), (w / 2, ht - 0.36), (w / 2, hb)]
                else:
                    sec = [(-w / 2, hb), (-w / 2 + 0.6, ht - 0.25), (0.0, ht + ridge), (w / 2 - 0.6, ht - 0.25), (w / 2, hb)]
                row = []
                for (a, h) in sec:
                    q = c0 + bvec * a
                    zq = q[2]
                    cxq = K.core_axes(zq)[0]
                    alq = math.atan2(q[1], q[0] - cxq)
                    p, _ = K.core_point(zq, alq, h * _height_scale(zq) if h > 0 else h)
                    row.append(p)
                rows.append(row)
                # across V = section arclength centred on the crown
                sa = arclen(np.array([(a, 0.0, h) for a, h in sec]))
                crown = len(sec) // 2
                V = sa - sa[crown]
                Lz = float(np.interp(z, zd, Ld))
                uvr.append([(Lz, v) for v in V])
                atr.append([A(code, Lz, a, cid) for (a, h) in sec])
            P = np.array(rows)
            uv = np.array(uvr)
            at = np.array(atr)
            isl = "cord%s_%02d" % (cname, si)
            grid(mb, P, False, isl, K.SLOT_GRIP, uv, at, flip=False)
    return mb


# ============================================================================================ kashira band (ito over the end)
def _kashira_inside(x, y, z):
    Kd = SP["kashira"]
    if z < Kd["z"][0]:
        return False
    return abs(y) <= kashira_halfwidth(z, x - Kd["centre_x"])


def build_band(lod):
    """The double ito band over the kashira end (2 x 8 mm, from under the omote eyelet over the end to under the ura
    eyelet). The centre line follows the kashira's Y-Z outline; every across sample is projected onto the kashira
    surface along the centre line's normal, so the band hugs the dome and the flat crown."""
    mb = MB("band")
    Kd = SP["kashira"]
    cx = Kd["centre_x"]
    E = Kd["eyelets"]
    z_end = Kd["z"][0]
    code = CODES["band"]
    z_hi = E["z"] - E["diameter_outer"] / 2 - 0.25
    M = {0: 40, 1: 18, 2: 10}[lod]
    if lod < 2:
        subs = [(-4.0, "band_a"), (4.0, "band_b")]
        secA = [(-4.0, -0.3), (-3.55, 0.7), (-2.0, 1.05), (0.0, 1.15), (2.0, 1.05), (3.55, 0.7), (4.0, -0.3)] if lod == 0 else                [(-4.0, -0.3), (-3.3, 0.85), (0.0, 1.1), (3.3, 0.85), (4.0, -0.3)]
    else:
        subs = [(0.0, "band_lod2")]
        secA = [(-8.0, -0.2), (-7.0, 1.0), (7.0, 1.0), (8.0, -0.2)]
    # centre outline (dx = 0)
    zs = list(np.linspace(z_hi, z_end + 4.0, 6)) + list(np.linspace(z_end + 4.0, z_end, 40))[1:]
    half = [(-kashira_halfwidth(z, 0.0), z) for z in zs]
    yb = kashira_halfwidth(z_end, 0.0)
    bottom = [(-yb + 2 * yb * i / 16.0, z_end) for i in range(1, 16)]
    path = np.array(half + bottom + [(-y, z) for (y, z) in reversed(half)])
    sl = arclen(np.c_[path[:, 0], np.zeros(len(path)), path[:, 1]])
    tt = np.linspace(0, sl[-1], M + 1)
    ys = np.interp(tt, sl, path[:, 0])
    zz = np.interp(tt, sl, path[:, 1])
    for xo, isl in subs:
        rows, uvr, atr = [], [], []
        sa = arclen(np.array([(a, 0.0, h) for a, h in secA]))
        V = sa - sa[len(secA) // 2]
        for i in range(M + 1):
            i0_, i1_ = max(i - 1, 0), min(i + 1, M)
            ty, tz = ys[i1_] - ys[i0_], zz[i1_] - zz[i0_]
            L = math.hypot(ty, tz) or 1e-9
            ny, nz = tz / L, -ty / L
            frac = tt[i] / sl[-1]
            taper = K.smoothstep(0.0, 0.05, frac) * K.smoothstep(0.0, 0.05, 1 - frac)
            row = []
            for (a, h) in secA:
                x = cx + xo + a
                lo, hi = -9.0, 4.0                 # t along the outward normal: inside .. outside
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    if _kashira_inside(x, ys[i] + ny * mid, zz[i] + nz * mid):
                        lo = mid
                    else:
                        hi = mid
                hh = (h * taper + (-0.25) * (1 - taper)) if h > 0 else h
                t_s = lo + hh
                row.append((x, ys[i] + ny * t_s, zz[i] + nz * t_s))
            rows.append(row)
            uvr.append([(tt[i], v) for v in V])
            atr.append([A(code, tt[i], a, 2.0) for (a, h) in secA])
        grid(mb, np.array(rows), False, isl, K.SLOT_GRIP, np.array(uvr), np.array(atr))
    return mb


# ============================================================================================ menuki
def build_menuki(lod):
    mb = MB("menuki")
    if lod == 2:
        return mb
    Ms = SP["menuki"]
    L, Wd, Hh, rg = Ms["size"]["length"], Ms["size"]["width"], Ms["size"]["height"], Ms["size"]["ridge"]
    NR = {0: 7, 1: 4}[lod]
    NO = {0: 28, 1: 16}[lod]
    for face, ysg in (("om", -1), ("ur", 1)):
        zc = Ms["omote" if face == "om" else "ura"]["z_centre"]
        cx, a, b = K.core_axes(zc)
        y0 = ysg * (b - 0.3)
        rings = []
        for i in range(NR + 1):
            t = i / NR
            sc = math.cos(t * math.pi / 2) if i < NR else 0.12
            hgt = Hh * math.sin(t * math.pi / 2) if i < NR else Hh + rg * 0.6
            ring = []
            for (ox, oz) in K.se_pts(Wd / 2, L / 2, 1.6, NO):
                xr, zr = ox * sc, oz * sc
                ridge = rg * max(0.0, 1 - abs(xr) / (Wd * 0.18)) * t
                ring.append((cx + xr, y0 + ysg * (hgt + ridge), zc + zr))
            rings.append(ring)
        P = np.array(rings)
        uvp = profile_loft_uv(P)
        at = np.zeros((NR + 1, NO + 1, 4))
        at[..., 3] = CODES["menuki"]
        midx = grid(mb, P, True, "menuki_" + face, K.SLOT_FIT, uvp, at, flip=(ysg > 0))
        top = P[-1]
        cap_fill(mb, list(midx[-1]), None,
                 [(p[0] * 1.0, p[2]) for p in top], "menuki_%s_top" % face, K.SLOT_FIT, flip=(ysg > 0),
                 attrs=[A(CODES["menuki"])] * NO)
    return mb


# ============================================================================================ mekugi
def build_mekugi(lod):
    mb = MB("mekugi")
    if lod == 2:
        return mb
    Mk = SP["mekugi"]
    zc, x0 = Mk["z"], Mk["x"]
    r = Mk["diameter"] / 2
    N = {0: 20, 1: 10}[lod]
    cx, a, b = K.core_axes(zc)
    prof = [(r, -0.7), (r, 0.12), (r - 0.35, 0.3)]
    for face, ysg in (("om", -1), ("ur", 1)):
        ycore = b * (1 - abs((x0 - cx) / a) ** K.NT) ** (1 / K.NT)
        P = []
        for (rr, h) in prof:
            P.append([(x0 + rr * math.cos(2 * math.pi * i / N), ysg * (ycore + h), zc + rr * math.sin(2 * math.pi * i / N)) for i in range(N)])
        P = np.array(P)
        uv = np.zeros((len(prof), N + 1, 2))
        pl = arclen(np.array([(rr, 0, h) for rr, h in prof]))
        for k in range(len(prof)):
            uv[k, :, 0] = np.linspace(0, 2 * math.pi * r, N + 1)
            uv[k, :, 1] = pl[k]
        at = np.zeros((len(prof), N + 1, 4))
        at[..., 3] = CODES["mekugi"]
        # finaliser: the bamboo peg moved to the Fittings slot / steel atlas (M_Steel_Master, metallic 0 from ORM).
        # On the Grip slot (M_Fabric_Master, Metal From ORM) its mid-dark bamboo would have been recoloured with the ito.
        idx = grid(mb, P, True, "mekugi_" + face, K.SLOT_FIT, uv, at, flip=(ysg < 0))
        cap_fill(mb, list(idx[-1]), None, [((p[0] - x0) + 25.0, p[2] - zc) for p in P[-1]], "mekugi_" + face, K.SLOT_FIT,
                 flip=(ysg < 0), attrs=[A(CODES["mekugi"])] * N)
    return mb


# ============================================================================================ LOD2 tsuka shell
def build_shell():
    mb = MB("shell")
    N = 16
    zs = list(np.linspace(-205.0, 38.5, 17))
    rows = []
    for z in zs:
        cx, D, W = K.tsuka_dims(z)
        rows.append([(cx + x, y, z) for (x, y) in K.se_pts(D / 2 + 0.25, W / 2 - 0.1, K.NT, N, phase=math.pi / N)])
    P = np.array(rows)
    uv = np.zeros((len(zs), N + 1, 2))
    for r in range(len(zs)):
        s = arclen(P[r], closed=True)
        uv[r, :, 0] = s
        uv[r, :, 1] = zs[r]
    at = np.zeros((len(zs), N + 1, 4))
    at[..., 3] = CODES["shell"]
    grid(mb, P, True, "shell", K.SLOT_GRIP, uv, at)
    return mb


# ============================================================================================ assembly
def build_lod(lod):
    parts = {}
    parts["blade"] = build_blade(lod)
    parts["habaki"] = build_habaki(lod)
    parts["seppa_blade"] = build_seppa(lod, "blade")
    parts["seppa_tsuka"] = build_seppa(lod, "tsuka")
    parts["tsuba"] = build_tsuba(lod)
    parts["fuchi"] = build_fuchi(lod)
    parts["kashira"] = build_kashira(lod)
    if lod < 2:
        parts["eyelets"] = build_eyelets(lod)
        parts["core"] = build_core(lod)
        parts["cords"] = build_cords(lod)
        parts["menuki"] = build_menuki(lod)
        parts["mekugi"] = build_mekugi(lod)
    else:
        parts["shell"] = build_shell()
    # the kashira band (2 x 8 mm over the end) is dropped: the wrap ends under the kashira lip (finaliser, review
    # option B: the band's two stub ends read as rubber bumpers beside empty eyelets)
    for v in parts.values():
        v.weld(1e-4)
    return {k: v for k, v in parts.items() if v.faces}


SMOOTH_ANGLE = {"blade": 70.0, "cords": 75.0, "band": 75.0, "core": 60.0, "shell": 70.0}
GRIP_PARTS = ("core", "cords", "band", "shell")


STEEL_FIT_SCALE_EXCLUDE = ()


def island_scale(name):
    """Texel density per island relative to the blade (finaliser re-pack: the blade was 28.9 px/cm while fittings had
    3.6x that; now the blade is the reference, fittings ~1.9x, the tsuba ~1.25x, faces hidden by a neighbour 0.12-0.3)."""
    if name in ("blade_cap", "fuchi_top", "seppa_blade_bot", "seppa_tsuka_top"):
        return 0.12                       # fully covered (machi cap, under the seppa / tsuba)
    if name == "seppa_tsuka_bot":
        return 0.3                        # against the fuchi top: only a ~1 mm rim shows
    if name.endswith("_top") and name.startswith("menuki"):
        return 1.0
    if name.startswith("tsuba_"):
        return 1.25
    if name.split("_")[0] in ("habaki", "seppa", "fuchi", "kashira", "menuki", "eyelet"):
        return 1.9
    if name == "core":
        return 0.7
    if name == "shell":
        return 0.45
    if name.startswith("mekugi"):
        return 1.9
    return 1.0
