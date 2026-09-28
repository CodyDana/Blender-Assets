"""Round 2: splice the new Look + painter into props_lib/flashbang_paint.py (replaces the Look dataclass and paint())."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_paint.py"
s = open(p, encoding="utf-8").read()

LOOK = '''@dataclass
class Look:
    """ROUND 2 (the blind tells + the reference's micro-texture, studied at 4-5x in WorkFiles/flashbang/r2/look/):
    glossier olive paint with a hammered / leathery surface that shows in the highlight; small dark brown-black grime
    specks and smudges (no large camouflage blotches); chips with a dark oxidised core and a thin light tan-bronze
    rim; a ragged bare-metal ring round every hole; light tan lips on the ring-line grooves; darker antiqued steel with
    scattered bright bronze specks and broken bright arrises; a mid-grey etched lever (mottled light swirls, a faint
    irregular diamond stamp); pitted grimy brass with vertical scratches and no painted shoulder band (it is geometry)."""
    paint_lin: Tuple[float, float, float] = (0.080, 0.080, 0.038)     # olive (lit p50 71,71,54 in the reference)
    paint_mottle: float = 0.16
    paint_fine: float = 0.10
    paint_hammer: float = 0.10          # albedo response of the hammered texture
    paint_hammer_h: float = 0.045       # its height (mm): the leathery sheen in the highlight
    paint_grime: float = 0.60
    paint_rough: float = 0.30           # ROUND 2: glossier (0.46): the reference's highlight stripe (paint p90)
    chip_frac: float = 0.143            # spec 9
    chip_near_hole_frac: float = 0.577
    chip_core_lin: Tuple[float, float, float] = (0.030, 0.024, 0.018)  # oxidised dark brown-black steel (sRGB ~45)
    chip_edge_lin: Tuple[float, float, float] = (0.30, 0.22, 0.14)    # light tan-bronze rim (sRGB ~140)
    rim_lin: Tuple[float, float, float] = (0.28, 0.23, 0.17)           # the ragged bare rim round the holes
    steel_lin: Tuple[float, float, float] = (0.040, 0.037, 0.034)      # dark antiqued steel (housing p50 42-50)
    cap_lin: Tuple[float, float, float] = (0.046, 0.042, 0.037)
    steel_edge_lin: Tuple[float, float, float] = (0.46, 0.37, 0.26)
    bronze_lin: Tuple[float, float, float] = (0.36, 0.27, 0.17)        # the bright bronze specks
    steel_rough: float = 0.40
    steel_edge_rough: float = 0.30
    lever_lin: Tuple[float, float, float] = (0.072, 0.069, 0.064)      # mid-grey etched steel (lighter than the housing)
    ring_lin: Tuple[float, float, float] = (0.050, 0.047, 0.043)       # darker antiqued ring wire (sRGB ~60-75 lit)
    inner_lin: Tuple[float, float, float] = (0.018, 0.017, 0.016)
    brass_lin: Tuple[float, float, float] = (0.50, 0.36, 0.18)
    brass_rough: float = 0.38
    wall_lin: Tuple[float, float, float] = (0.040, 0.036, 0.032)       # hole walls: dark cut steel, grimy
    seed: int = 20260927


LOOK = Look()
'''

PAINT = '''def paint(bk: Dict[str, np.ndarray], spec: FlashbangSpec, packing, look: Look = LOOK, log=print):
    """Compose linear albedo, roughness, metallic, height (mm) from the bakes.  Arrays bottom-up (v up).  ROUND 2."""
    H, W = bk["pos"].shape[:2]
    cover = bk["cover"][..., 0] > 0.5
    looks = np.rint(bk["look"][..., 0] * 256.0).astype(np.int32)
    isl = np.rint(bk["island"][..., 0] * 256.0).astype(np.int32)
    P = (bk["pos"] - 0.5) / POS_SCALE * 1000.0                    # mm
    N = bk["nrm"] * 2.0 - 1.0
    es = np.clip(bk["edge_s"][..., 0] * 6.0, 0, 1)                # ~1 at a 90 deg arris
    el = np.clip(bk["edge_l"][..., 0] * 4.0, 0, 1)
    ao = np.clip(bk["ao"], 0, 1)
    idx = np.nonzero(cover.ravel())[0]
    p = P.reshape(-1, 3)[idx]
    n = N.reshape(-1, 3)[idx]
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
    L = looks.ravel()[idx]
    e_s, e_l, a_o = es.ravel()[idx], el.ravel()[idx], ao.ravel()[idx]
    sd = look.seed
    r_xy = np.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]
    th = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
    NT = len(idx)

    # ------------------------------------------------ noise fields (3-D, seam-free)
    n_big = fbm(p, 9.0, 4, sd + 1)
    n_mid = fbm(p, 2.4, 4, sd + 2)
    n_fine = fbm(p, 0.45, 3, sd + 3)
    n_speck = value_noise(p, 0.18, sd + 4)
    n_grime = fbm(p, 2.2, 3, sd + 5)              # small grime smudges (1-4 mm), not camouflage blotches
    n_chip = fbm(p, 1.0, 3, sd + 6)               # chip outlines 0.5-3 mm
    n_ham = 0.65 * value_noise(p, 0.55, sd + 7) + 0.35 * value_noise(p, 0.27, sd + 8)   # hammered paint
    n_dash = value_noise(p, 1.6, sd + 31)         # breaks every bright arris into dashes
    n_br = value_noise(p, 0.26, sd + 32)          # bronze specks
    n_cl = fbm(p, 3.5, 2, sd + 33)                # their clusters

    is_paint = (L == 0)
    is_wall = (L == 6)
    pm = is_paint
    on_body = is_paint & (r_xy < spec.body_r + 0.05) & (r_xy > spec.body_r - 0.6) & (z > spec.body_z0) & \\
        (z < spec.sleeve_z0 + 0.01)
    on_sleeve = is_paint & (z >= spec.sleeve_z0 - 0.01)
    on_chamfer = on_sleeve & (z > spec.sleeve_z1 - 0.05)

    # distance (mm) from each body texel to the nearest hole edge (the ellipse in the unrolled surface)
    a_mm = spec.body_r * math.radians(spec.hole_ang_w_deg / 2.0)
    b_mm = spec.hole_h / 2.0
    d_hole = np.full(NT, 99.0, np.float32)
    bi = np.nonzero(on_body | (is_wall))[0]
    for hc in spec.hole_thetas():
        du = ((th[bi] - hc + 180.0) % 360.0 - 180.0) * math.pi / 180.0 * spec.body_r
        for zc in spec.hole_rows_z:
            dv = z[bi] - zc
            rho = np.sqrt((du / a_mm) ** 2 + (dv / b_mm) ** 2)
            # radial distance along the ellipse ray (scaled by the local radius)
            loc = np.sqrt((du / np.maximum(rho, 1e-6)) ** 2 + (dv / np.maximum(rho, 1e-6)) ** 2)
            d_hole[bi] = np.minimum(d_hole[bi], (rho - 1.0) * loc)
    d_line = np.min(np.abs(z[:, None] - np.array(spec.ring_lines_z)[None, :]), axis=1)

    # ------------------------------------------------ chips (bare metal): zones + noise, calibrated to spec 9
    zone = np.zeros(NT, np.float32)
    zone += 1.00 * np.exp(-(np.maximum(d_hole, 0.0) / 0.9) ** 2) * on_body          # hole rims
    zone += 0.55 * np.exp(-(np.maximum(d_line - spec.groove_w, 0.0) / 0.8) ** 2) * on_body   # the groove lips
    zone += 0.55 * np.exp(-((z - spec.sleeve_z0) / 0.9) ** 2) * is_paint              # sleeve step
    zone += 0.40 * np.exp(-((z - spec.body_z0) / 1.8) ** 2) * on_body                 # body bottom
    zone += 0.42 * on_chamfer                                                         # sleeve chamfer ~40 % bare
    zone += 0.20 * smoothstep(spec.sleeve_z1 - 1.5, spec.sleeve_z1, z) * on_sleeve     # the chamfer's lower edge
    near = pm & (d_hole < 0.75) & on_body
    base_sc = (zone + 0.55 * (n_chip - 0.5) + 0.25 * (n_mid - 0.5) + 0.15 * (n_big - 0.5)
               + 0.30 * (n_speck > 0.975))
    best = None
    for w_e in np.linspace(0.0, 1.2, 25):
        sc_ = base_sc + w_e * e_s
        t_ = float(np.quantile(sc_[pm], 1.0 - look.chip_frac))
        f_ = float((sc_[near] > t_).mean()) if near.any() else 0.0
        if best is None or abs(f_ - look.chip_near_hole_frac) < abs(best[2] - look.chip_near_hole_frac):
            best = (w_e, t_, f_)
    w_edge, thr, chip_near = best
    score = base_sc + w_edge * e_s
    chip = pm & (score > thr)
    log(f"  chips: edge weight {w_edge:.2f}, threshold {thr:.3f}, chipped {chip[pm].mean():.3f} of paint, "
        f"near-edge texels bare {chip_near:.3f}")
    # a chip's thin light rim (the paint's broken edge catching light) round a dark oxidised core: erode 2 texels
    chip_img = np.zeros(H * W, bool)
    chip_img[idx] = chip
    chip_img = chip_img.reshape(H, W)
    core_img = _erode(chip_img, 2)
    chip_core = core_img.ravel()[idx] & chip
    chip_edge = chip & ~chip_core
    # the ragged bare ring round every hole (0.3-1.1 mm, noise-driven), part of the chips
    rim = on_body & (d_hole < 0.30 + 0.80 * n_fine * (0.5 + n_mid)) & (d_hole > -1.0)
    chip = chip | rim

    # ------------------------------------------------ albedo, roughness, metallic, height
    alb = np.zeros((NT, 3), np.float32)
    rough = np.zeros(NT, np.float32)
    metal = np.zeros(NT, np.float32)
    h = np.zeros(NT, np.float32)
    # grime: small dark smudges collecting at the rims, groove lips, the bottom and the step; cavity grime from AO
    gzone = np.clip(1.2 * np.exp(-(np.maximum(d_hole, 0) / 2.0) ** 2) + np.exp(-(d_line / 2.5) ** 2)
                    + np.exp(-((z - spec.body_z0) / 5.0) ** 2) + 0.6 * np.exp(-((z - spec.sleeve_z0) / 2.0) ** 2),
                    0, 1.5)
    smudge = smoothstep(0.60, 0.70, n_grime + 0.10 * gzone) * (0.6 + 0.8 * n_fine)
    cav = np.clip((1.0 - a_o) * 1.5, 0, 1) * (0.5 + 0.8 * (n_mid - 0.5) + 0.3)
    grime = np.clip(np.maximum(smudge, cav), 0, 1)
    # paint (luminance-only variation: Detail x Colour == BC)
    pc = np.array(look.paint_lin, np.float32)
    lumf = (1.0 + look.paint_mottle * (n_big - 0.5) * 2.0 + look.paint_fine * (n_fine - 0.5) * 2.0
            + look.paint_hammer * (n_ham - 0.5) * 2.0)
    lumf *= (1.0 - look.paint_grime * grime)
    lumf *= np.where(n_speck < 0.045, 0.45, 1.0)                                              # dark specks
    edge_band = pm & ~chip & (score > thr - 0.05)
    lumf *= np.where(edge_band, 0.72, 1.0)                                                  # paint lip shadow
    # light hairline scuffs in the paint (the reference's fine light scratches), still paint (dielectric)
    scuff = strokes(p, n, 2.2, 0.55, (0.8, 3.5), 0.03, sd + 501)
    lumf *= 1.0 + 0.55 * scuff * (1.0 - grime)
    lumf = np.clip(lumf, 0.22, 2.1)                   # dielectric paint luminance stays < 0.18 (gate 12)
    alb[pm] = pc[None, :] * lumf[pm, None]
    rough[pm] = np.clip(look.paint_rough + 0.07 * (n_mid[pm] - 0.5) + 0.06 * (n_ham[pm] - 0.5) + 0.22 * grime[pm],
                        0.22, 0.75)
    h[pm] = 0.06 + look.paint_hammer_h * (n_ham[pm] - 0.5) + 0.012 * (n_fine[pm] - 0.5) - 0.012 * scuff[pm]
    # chips: dark oxidised core (brown), thin light tan-bronze rim; the hole rims bright bare steel
    brown = np.array([0.050, 0.034, 0.021], np.float32)
    core = (np.array(look.chip_core_lin)[None, :] * (1 - 0.5 * n_mid[:, None]) + brown[None, :] * 0.5 * n_mid[:, None])
    core *= (0.8 + 0.5 * n_fine)[:, None]
    edge = np.array(look.chip_edge_lin)[None, :] * (0.65 + 0.7 * n_mid)[:, None]
    alb[chip_core] = core[chip_core]
    alb[chip_edge] = edge[chip_edge]
    rc = np.array(look.rim_lin)[None, :] * (0.6 + 0.8 * n_fine * n_mid * 2.0)[:, None]
    rimc = rim & ~chip_core
    alb[rimc] = rc[rimc] * (1.0 - 0.35 * grime[rimc, None])
    rough[chip_core] = np.clip(0.55 + 0.1 * (n_fine[chip_core] - 0.5), 0.45, 0.75)
    rough[chip_edge | rimc] = 0.32
    metal[chip] = 1.0
    h[chip] = 0.0
    # steel families: dark antiqued base, oxidised darker patches, BROKEN bright arrises (thin bevel only, in
    # dashes), bright bronze specks in clusters, fine light scratches, grime in the corners
    is_cap = (L == 1) & (z < spec.body_z0 + 0.3)
    for lk, base, rgh in ((1, look.steel_lin, look.steel_rough), (4, look.lever_lin, 0.40),
                          (5, look.ring_lin, 0.30), (3, look.inner_lin, 0.6), (6, look.wall_lin, 0.55)):
        m = (L == lk)
        if not m.any():
            continue
        b = np.tile(np.array(base, np.float32)[None, :], (int(m.sum()), 1))
        if lk == 1:
            b[is_cap[m]] = np.array(look.cap_lin, np.float32)
        var = np.clip(0.62 + 0.75 * n_big[m] * n_mid[m] * 2.0 - 0.25 + 0.25 * (n_fine[m] - 0.5), 0.45, 1.4)
        col = b * var[:, None]
        dash = smoothstep(0.38, 0.60, n_dash[m])
        wear = np.clip(1.5 * e_s[m] * (0.5 + 0.9 * n_fine[m]) - 0.15, 0, 1) * dash
        if lk == 5:
            # the ring: bright wear only on the OUTER arc of the loop
            from .flashbang_geom import ring_frame
            _top, xdir, zdir, c = ring_frame(spec)                  # ROUND 2: the fitted ring pose
            nplane = np.cross(xdir, zdir)
            v = p[m] - c
            rp = v - (v @ nplane)[:, None] * nplane[None, :]
            rd = rp / np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-6)
            outer = np.clip(((n[m] * rd).sum(1) - 0.45) / 0.4, 0, 1) * (np.linalg.norm(v, axis=1) > 12.0)
            wear = np.maximum(wear, outer * smoothstep(0.35, 0.65, n_dash[m]) * 0.75)
        scr = np.zeros(int(m.sum()), np.float32)
        if lk in (1, 4, 5):
            scr = strokes(p[m], n[m], 1.4, 0.55, (0.5, 2.4), 0.025, sd + 300 + lk)
            wear = np.maximum(wear, 0.38 * scr * (0.5 + n_mid[m]))
            # bronze specks, clustered (the cap and housing's bright dots)
            spk = (n_br[m] > np.where(is_cap[m], 0.905, 0.93)) & (n_cl[m] > 0.42)
            wear = np.maximum(wear, 0.85 * spk)
        if lk in (3, 6):
            wear *= 0.35
        ecol = np.array(look.steel_edge_lin)[None, :] * (0.6 + 0.7 * n_mid[m])[:, None]
        if lk in (1, 4, 5):
            bz = np.array(look.bronze_lin)[None, :] * (0.7 + 0.6 * n_fine[m])[:, None]
            ecol = np.where((n_br[m] > 0.9)[:, None], bz, ecol)
        col = col * (1 - wear[:, None]) + ecol * wear[:, None]
        g2 = np.clip(np.maximum(np.clip((1.0 - a_o[m]) * 1.3, 0, 1), 0.6 * smudge[m]), 0, 1)
        col *= (1.0 - 0.45 * g2)[:, None]
        col = col * (1.0 - 0.25 * g2[:, None]) + brown[None, :] * 0.25 * g2[:, None] * (col.mean(1, keepdims=True) / 0.05)
        alb[m] = col
        rough[m] = np.clip(rgh + 0.10 * (n_mid[m] - 0.5) - (rgh - look.steel_edge_rough) * wear + 0.15 * g2, 0.18, 0.85)
        metal[m] = 1.0
        pits = (value_noise(p[m], 0.35, sd + 9) > 0.93).astype(np.float32)
        h[m] -= 0.03 * pits
        h[m] -= 0.02 * scr
    # the hole walls' outer lip: the cut edge, bright and ragged (the wall texels within ~0.6 mm of the outside)
    m = is_wall & (r_xy > spec.body_r - 0.35 - 0.5 * n_fine)
    alb[m] = np.array(look.rim_lin)[None, :] * (0.55 + 0.7 * n_mid[m])[:, None]
    rough[m] = 0.34
    # the lever: an ETCHED mid-grey face - mottled light swirls (a warped value-noise iso-band) and larger light
    # patches, a faint diamond stamp that is broken and irregular (pitch and angle wander), bright flange arrises
    m = (L == 4)
    if m.any():
        pw = p[m] + 1.2 * np.stack([fbm(p[m], 2.0, 2, sd + 81) - 0.5, fbm(p[m], 2.0, 2, sd + 82) - 0.5,
                                    fbm(p[m], 2.0, 2, sd + 83) - 0.5], 1)
        swirl = np.exp(-((value_noise(pw, 1.3, sd + 84) - 0.5) / 0.035) ** 2)
        patch = smoothstep(0.55, 0.75, fbm(p[m], 2.6, 3, sd + 85))
        y_, z_ = pw[:, 1], pw[:, 2]
        hat = np.zeros(int(m.sum()), np.float32)
        web = np.abs(n[m, 1]) < 0.5
        for sg in (-1.0, 1.0):
            a = math.radians(38.0)
            w_ = -math.cos(a) * y_ * sg + math.sin(a) * z_
            f = w_ / 1.6 - np.round(w_ / 1.6)
            hat = np.maximum(hat, np.exp(-((f * 1.6) / 0.16) ** 2))
        hat *= smoothstep(0.35, 0.65, value_noise(p[m], 2.4, sd + 77)) * web
        lite = np.array([0.15, 0.14, 0.125], np.float32)[None, :]
        k_ = np.clip(0.55 * swirl + 0.45 * patch + 0.35 * hat, 0, 1)[:, None] * (0.6 + 0.6 * n_mid[m, None])
        alb[m] = alb[m] * (1 - k_) + lite * k_
        rough[m] = np.clip(rough[m] - 0.06 * k_[:, 0], 0.18, 0.85)
        h[m] -= 0.02 * hat + 0.015 * swirl
    # brass cans: pitted, grimy, vertical scratches, grime in the lower third of each window; the seam and the
    # shoulder are GEOMETRY now (a dark line only at the seam, no painted light band)
    m = (L == 2)
    if m.any():
        b = np.array(look.brass_lin, np.float32)[None, :]
        tarn = 0.80 + 0.30 * (n_big[m] - 0.5) * 2 + 0.15 * (n_fine[m] - 0.5)
        col = b * np.clip(tarn, 0.45, 1.1)[:, None]
        vs = strokes(p[m], n[m], 1.2, 0.75, (2.0, 8.0), 0.04, sd + 401, vertical=0.9)
        col *= (1.0 + 0.30 * vs)[:, None]
        pit = value_noise(p[m], 0.22, sd + 402) > 0.88
        col[pit] *= 0.40
        dk = smoothstep(0.62, 0.75, fbm(p[m], 1.4, 3, sd + 403))            # dark tarnish smudges
        col *= (1.0 - 0.55 * dk)[:, None]
        zc = np.array(sorted(spec.hole_rows_z))
        dzr = z[m] - zc[np.argmin(np.abs(z[m][:, None] - zc[None, :]), axis=1)]
        low = smoothstep(-2.0, -8.5, dzr) * (0.6 + 0.6 * n_mid[m])
        col *= (1.0 - 0.45 * np.clip(low, 0, 1))[:, None]
        rgh = np.clip(look.brass_rough + 0.12 * (n_big[m] - 0.5) + 0.12 * np.clip(low, 0, 1) + 0.15 * dk - 0.08 * vs,
                      0.25, 0.65)
        hh = np.zeros(int(m.sum()), np.float32)
        for zs in spec.tube_seam_z:
            g = np.exp(-((z[m] - zs) / 0.18) ** 2)
            col *= (1.0 - 0.55 * g)[:, None]
            hh += -0.05 * g
        col *= (0.80 + 0.20 * a_o[m])[:, None]
        alb[m] = col
        rough[m] = rgh
        metal[m] = 1.0
        h[m] = hh - 0.02 * pit - 0.01 * vs
    # ring lines: the groove (geometry at LOD0) darker with grime, its lips light where the paint wore through
    for zl in spec.ring_lines_z:
        g = np.exp(-((z - zl) / 0.30) ** 2)
        sel = on_body & ~chip
        alb[sel] *= (1.0 - 0.35 * g[sel])[:, None]
    # scratches through the paint to the metal: thin light strokes, a few
    sp = pm & ~chip
    scr_p = strokes(p[sp], n[sp], 4.0, 0.30, (2.0, 8.0), 0.05, sd + 500)
    hit = scr_p > 0.5
    ii = np.nonzero(sp)[0][hit]
    alb[ii] = np.array(look.chip_edge_lin)[None, :] * 0.8
    metal[ii] = 1.0
    rough[ii] = 0.34
    h[ii] = 0.0
    chip_all = chip.copy()
    chip_all[ii] = True

    # ------------------------------------------------ to images (bottom-up), extended into the padding
    def to_img(vals, ch):
        a = np.zeros((H * W, ch), np.float32)
        a[idx] = vals.reshape(len(idx), ch)
        a = a.reshape(H, W, ch) if ch > 1 else a.reshape(H, W)
        return a

    out = {"albedo": to_img(alb, 3), "rough": to_img(rough, 1), "metal": to_img(metal, 1), "height": to_img(h, 1),
           "ao": ao, "cover": cover, "look": looks, "island": isl, "chip": to_img(chip_all.astype(np.float32), 1),
           "paint_mask": to_img((pm & ~chip_all).astype(np.float32), 1), "bevel_n": bk["normal"]}
    body_band = on_body & (z > 30.0) & (z < 105.0)
    stats = {"chip_threshold": thr, "chipped_fraction_of_paint": float(chip[pm].mean()) if pm.any() else 0,
             "near_edge_bare_fraction": chip_near, "edge_weight": float(w_edge), "paint_texels": int(pm.sum()),
             "chip_core_fraction_of_chips": float(chip_core.sum() / max(chip.sum(), 1)),
             "hole_rim_bare_texels": int(rim.sum()),
             "paint_scratch_texels": int(len(ii)), "grime_smudge_fraction_of_paint": float((smudge[pm] > 0.5).mean()),
             "bright_bare_fraction_body_band": float((chip_all & body_band & (alb @ np.array([0.2126, 0.7152, 0.0722])
                                                                              > 0.12)).sum() / max(body_band.sum(), 1)),
             "texels_covered": int(cover.sum())}
    return out, stats


'''

a0 = s.index("@dataclass\nclass Look:")
a1 = s.index("LOOK = Look()\n") + len("LOOK = Look()\n")
s = s[:a0] + LOOK + s[a1:]
b0 = s.index("def paint(bk: Dict[str, np.ndarray]")
b1 = s.index("def detail_normal(")
s = s[:b0] + PAINT + s[b1:]
open(p, "w", encoding="utf-8").write(s)
print("painter spliced")
