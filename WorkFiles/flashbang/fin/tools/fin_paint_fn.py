def _erode(mask, iters):
    m = mask.copy()
    for _ in range(iters):
        m = (m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    return m


def paint(bk: Dict[str, np.ndarray], spec: FlashbangSpec, packing, look: Look = LOOK, log=print):
    """Compose linear albedo, roughness, metallic, height (mm) from the bakes.  Arrays bottom-up (v up)."""
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

    # ------------------------------------------------ noise fields (3-D, seam-free)
    n_big = fbm(p, 9.0, 4, sd + 1)
    n_mid = fbm(p, 2.4, 4, sd + 2)
    n_fine = fbm(p, 0.45, 3, sd + 3)
    n_speck = value_noise(p, 0.18, sd + 4)
    n_grime = fbm(p, 5.0, 3, sd + 5)
    n_blot = fbm(p, 7.0, 3, sd + 21)              # FINALISE: grime blotches 3-15 mm
    n_light = fbm(p, 6.0, 3, sd + 22)             # FINALISE: lighter worn / dusty paint patches
    n_dash = value_noise(p, 1.6, sd + 31)         # FINALISE: breaks every bright arris into dashes

    is_paint = (L == 0)
    is_wall = (L == 6)
    zone = np.zeros(len(idx), np.float32)
    on_body = is_paint & (r_xy < spec.body_r + 0.05) & (z > spec.body_z0) & (z < spec.sleeve_z0 + 0.01)
    on_sleeve = is_paint & (z >= spec.sleeve_z0 - 0.01)
    for zl in spec.ring_lines_z:
        zone += 0.40 * np.exp(-((z - zl) / 0.30) ** 2) * on_body
    # FINALISE: the sleeve's top chamfer keeps 50-70 % of its paint (round 1 forced it bare: a chrome band)
    zone += 0.22 * smoothstep(spec.sleeve_z1 - 0.3, spec.sleeve_z1 + 0.8, z) * on_sleeve
    zone += 0.35 * np.exp(-((z - spec.sleeve_z0) / 0.7) ** 2) * is_paint                     # sleeve step
    zone += 0.30 * np.exp(-((z - spec.body_z0) / 1.6) ** 2) * on_body                        # body bottom
    pm = is_paint
    near = pm & (e_s > 0.45)
    n_fleck = value_noise(p, 0.32, sd + 11)
    # FINALISE: chips are 1-3 mm blotches (mid noise) more than fine flecks
    base_sc = (zone + 0.60 * (n_mid - 0.5) + 0.30 * (n_fine - 0.5) + 0.25 * (n_big - 0.5)
               + 0.35 * (n_speck > 0.965) + 0.25 * (n_fleck > 0.92))
    best = None
    for w_e in np.linspace(0.0, 1.6, 33):
        sc_ = base_sc + w_e * e_s + 0.25 * w_e * e_l
        t_ = float(np.quantile(sc_[pm], 1.0 - look.chip_frac))
        f_ = float((sc_[near] > t_).mean()) if near.any() else 0.0
        if best is None or abs(f_ - look.chip_near_hole_frac) < abs(best[2] - look.chip_near_hole_frac):
            best = (w_e, t_, f_)
    w_edge, thr, chip_near = best
    score = base_sc + w_edge * e_s + 0.25 * w_edge * e_l
    chip = pm & (score > thr)
    log(f"  chips: edge weight {w_edge:.2f}, threshold {thr:.3f}, chipped {chip[pm].mean():.3f} of paint, "
        f"near-edge texels bare {chip_near:.3f}")
    # chip core vs its thin bright edge: erode the chip mask 2 texels (~0.23 mm) in the atlas
    chip_img = np.zeros(H * W, bool)
    chip_img[idx] = chip
    chip_img = chip_img.reshape(H, W)
    core_img = _erode(chip_img, 2)
    chip_core = core_img.ravel()[idx] & chip
    chip_edge = chip & ~chip_core

    # ------------------------------------------------ albedo, roughness, metallic, height
    alb = np.zeros((len(idx), 3), np.float32)
    rough = np.zeros(len(idx), np.float32)
    metal = np.zeros(len(idx), np.float32)
    h = np.zeros(len(idx), np.float32)
    # grime zones: hole rims (the wide bevel mask), the ring lines, the body's bottom, the sleeve step
    gzone = np.clip(0.8 * e_l + sum(np.exp(-((z - zl) / 2.0) ** 2) for zl in spec.ring_lines_z)
                    + np.exp(-((z - spec.body_z0) / 6.0) ** 2) + 0.6 * np.exp(-((z - spec.sleeve_z0) / 2.5) ** 2), 0, 1.5)
    blot = smoothstep(0.60, 0.74, n_blot + 0.14 * gzone)                                   # 3-15 mm blotches
    grime_cav = np.clip((1.0 - a_o) * 1.6, 0, 1) * (0.55 + 0.9 * (n_grime - 0.5))
    grime = np.clip(np.maximum(grime_cav, blot * (0.75 + 0.5 * n_mid)), 0, 1)
    # paint (luminance-only variation: Detail x Colour == BC)
    pc = np.array(look.paint_lin, np.float32)
    lumf = (1.0 + look.paint_mottle * (n_big - 0.5) * 2.0 + look.paint_fine * (n_fine - 0.5) * 2.0)
    lumf *= 1.0 + look.paint_light * smoothstep(0.56, 0.80, n_light) * (1.0 - blot)
    lumf *= (1.0 - look.paint_grime * grime)
    lumf *= np.where(n_speck < 0.05, 0.45, 1.0)                                              # dark flecks
    lumf *= np.where(value_noise(p, 1.1, sd + 12) < 0.12, 0.6, 1.0)                           # grime spots
    edge_band = pm & ~chip & (score > thr - 0.07)
    lumf *= np.where(edge_band, 0.70, 1.0)                                                   # paint lip shadow
    lumf = np.clip(lumf, 0.22, 2.2)                   # dielectric paint luminance stays < 0.18 (gate 12)
    alb[pm] = pc[None, :] * lumf[pm, None]
    rough[pm] = np.clip(look.paint_rough + 0.08 * (n_mid[pm] - 0.5) + 0.14 * grime[pm], 0.4, 0.9)
    # FINALISE: hammered / orange-peel paint surface (low amplitude)
    h[pm] = (0.05 + 0.028 * (value_noise(p[pm], 0.85, sd + 13) - 0.5) + 0.012 * (n_fine[pm] - 0.5)
             + 0.015 * (n_mid[pm] - 0.5))
    # chips: dark oxidised core (a little brown), thin warm bright edge
    brown = np.array([0.055, 0.038, 0.024], np.float32)
    core = (np.array(look.chip_core_lin)[None, :] * (1 - n_mid[:, None] * 0.6) + brown[None, :] * n_mid[:, None] * 0.6)
    core *= (0.8 + 0.45 * n_fine)[:, None]
    edge = np.array(look.chip_edge_lin)[None, :] * (0.7 + 0.6 * n_mid)[:, None]
    alb[chip_core] = core[chip_core]
    alb[chip_edge] = edge[chip_edge]
    rough[chip_core] = np.clip(0.62 + 0.1 * (n_fine[chip_core] - 0.5), 0.45, 0.8)
    rough[chip_edge] = 0.36
    metal[chip] = 1.0
    h[chip] = 0.0
    # hole walls: dark cut steel with grime
    wc = np.array(look.wall_lin)[None, :] * (0.75 + 0.5 * n_mid[is_wall, None])
    alb[is_wall] = wc * (1.0 - 0.45 * grime[is_wall, None])
    rough[is_wall] = 0.58
    metal[is_wall] = 1.0
    # steel families: dark antiqued base, BROKEN bright arrises (thin bevel only, in dashes), bright scratch strokes,
    # bronze specks, grime in the corners and blotches
    for lk, base, rgh in ((1, look.steel_lin, look.steel_rough), (4, look.lever_lin, 0.48), (5, look.ring_lin, 0.42),
                          (3, look.inner_lin, 0.6), (6, look.wall_lin, 0.58)):
        m = (L == lk)
        if not m.any():
            continue
        b = np.array(base, np.float32)[None, :]
        var = (0.75 + 0.5 * n_big[m] * n_mid[m] * 2.0 - 0.25)[:, None]
        col = b * np.clip(var, 0.55, 1.35)
        dash = smoothstep(0.42, 0.62, n_dash[m])
        wear = np.clip(look.edge_wear_steel * 1.5 * e_s[m] * (0.5 + 0.9 * n_fine[m]) - 0.15, 0, 1) * dash
        if lk == 5:
            # the ring: bright wear only on the OUTER arc of the loop
            s_ = spec
            tau = math.radians(s_.ring_tilt_deg)
            zdir = np.array([0.0, math.sin(tau), math.cos(tau)])
            xdir = np.array([1.0, 0.0, 0.0])
            nplane = np.cross(xdir, zdir)
            px_, pz_ = s_.pin_c
            c = np.array([px_, s_.pin_eye_y(), pz_]) - s_.ring_major_r * zdir
            v = p[m] - c
            rp = v - (v @ nplane)[:, None] * nplane[None, :]
            rd = rp / np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-6)
            outer = np.clip(((n[m] * rd).sum(1) - 0.45) / 0.4, 0, 1) * (np.linalg.norm(v, axis=1) > 12.0)
            wear = np.maximum(wear, outer * smoothstep(0.35, 0.65, n_dash[m]) * 0.75)
        if lk in (1, 4, 5):
            scr = strokes(p[m], n[m], 2.6, 0.55, (1.5, 7.0), 0.05, sd + 300 + lk)
            wear = np.maximum(wear, 0.8 * scr)
            wear = np.maximum(wear, 0.7 * (n_speck[m] > 0.965))
        if lk in (3, 6):
            wear *= 0.35
        ecol = np.array(look.steel_edge_lin)[None, :] * (0.65 + 0.6 * n_mid[m])[:, None]
        col = col * (1 - wear[:, None]) + ecol * wear[:, None]
        g2 = np.clip(np.maximum(np.clip((1.0 - a_o[m]) * 1.4, 0, 1), 0.8 * blot[m]), 0, 1)
        col *= (1.0 - 0.55 * g2)[:, None]
        col = col * (1.0 - 0.25 * g2[:, None]) + brown[None, :] * 0.25 * g2[:, None] * (col.mean(1, keepdims=True) / 0.05)
        alb[m] = col
        rough[m] = np.clip(rgh + 0.12 * (n_mid[m] - 0.5) - (rgh - look.steel_edge_rough) * wear + 0.15 * g2, 0.2, 0.85)
        metal[m] = 1.0
        pits = (value_noise(p[m], 0.35, sd + 9) > 0.93).astype(np.float32)
        h[m] -= 0.03 * pits
        if lk in (1, 4, 5):
            h[m] -= 0.02 * scr
    # the lever's stamped diagonal cross-hatch (v4 / pair 7): two line families +-35 deg from vertical, 1.5 mm pitch
    m = (L == 4)
    if m.any():
        y_, z_ = p[m, 1], p[m, 2]
        hat = np.zeros(int(m.sum()), np.float32)
        for sg in (-1.0, 1.0):
            a = math.radians(35.0)
            w_ = -math.cos(a) * y_ * sg + math.sin(a) * z_
            f = w_ / 1.5 - np.round(w_ / 1.5)
            hat = np.maximum(hat, np.exp(-((f * 1.5) / 0.13) ** 2))
        hat *= (0.45 + 0.55 * (value_noise(p[m], 2.0, sd + 77) > 0.35))
        ecol = np.array(look.steel_edge_lin)[None, :] * 0.55
        alb[m] = alb[m] * (1 - 0.45 * hat[:, None]) + ecol * 0.45 * hat[:, None]
        rough[m] -= 0.08 * hat
        h[m] -= 0.03 * hat
    # brass cans: brighter, pitted, vertical scratches, grime in the lower third of each window, the seam and the
    # shoulder just above it (a light band + a height rise)
    m = (L == 2)
    if m.any():
        b = np.array(look.brass_lin, np.float32)[None, :]
        tarn = 0.82 + 0.3 * (n_big[m] - 0.5) * 2 + 0.12 * (n_fine[m] - 0.5)
        col = b * np.clip(tarn, 0.5, 1.1)[:, None]
        vs = strokes(p[m], n[m], 1.4, 0.7, (2.5, 9.0), 0.045, sd + 401, vertical=0.9)
        col *= (1.0 + 0.22 * vs)[:, None]
        pit = value_noise(p[m], 0.22, sd + 402) > 0.9
        col[pit] *= 0.45
        zc = np.array(sorted(spec.hole_rows_z))
        dzr = z[m] - zc[np.argmin(np.abs(z[m][:, None] - zc[None, :]), axis=1)]
        low = smoothstep(-2.5, -8.0, dzr) * (0.6 + 0.6 * n_mid[m])
        col *= (1.0 - 0.5 * np.clip(low, 0, 1))[:, None]
        rgh = np.clip(look.brass_rough + 0.12 * (n_big[m] - 0.5) + 0.12 * np.clip(low, 0, 1) - 0.1 * vs, 0.28, 0.6)
        hh = np.zeros(int(m.sum()), np.float32)
        for zs in spec.tube_seam_z:
            g = np.exp(-((z[m] - zs) / 0.16) ** 2)
            sh = np.exp(-((z[m] - zs - 0.9) / 0.45) ** 2)
            col *= (1.0 - 0.65 * g + 0.25 * sh)[:, None]
            hh += -0.10 * g + 0.20 * smoothstep(zs, zs + 1.2, z[m]) * (z[m] < zs + 12.0)
        col *= (0.55 + 0.45 * a_o[m])[:, None]
        alb[m] = col
        rough[m] = rgh
        metal[m] = 1.0
        h[m] = hh - 0.02 * pit
    # ring lines: the engraved groove, a lighter upper lip (luminance only on the paint)
    for zl in spec.ring_lines_z:
        g = np.exp(-((z - zl) / (spec.ring_line_w * 0.5)) ** 2)
        lip = np.exp(-((z - zl - spec.ring_line_w * 0.8) / (spec.ring_line_w * 0.35)) ** 2)
        sel = on_body | (is_paint & (np.abs(z - zl) < 1.0))
        h[sel] += (-0.16 * g[sel] + 0.03 * lip[sel])
        alb[sel] *= (1.0 - 0.5 * g[sel] + 0.22 * lip[sel] * (~chip[sel]))[:, None]
    # the collar line (the round-1 housing panel lines are gone: the front panel is geometry now)
    m = (L == 1)
    col_sel = m & (np.abs(r_xy - spec.collar_r) < 0.15) & (np.abs(z - spec.collar_groove_z) < 1.0)
    g = np.exp(-((z - spec.collar_groove_z) / 0.22) ** 2)
    h[col_sel] -= 0.12 * g[col_sel]
    # scratches through the paint: thin bright strokes (steel shows), a few
    sp = pm & ~chip
    scr_p = strokes(p[sp], n[sp], 4.0, 0.30, (2.0, 8.0), 0.055, sd + 500)
    hit = scr_p > 0.5
    ii = np.nonzero(sp)[0][hit]
    alb[ii] = np.array(look.chip_edge_lin)[None, :] * 0.85
    metal[ii] = 1.0
    rough[ii] = 0.38
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
    stats = {"chip_threshold": thr, "chipped_fraction_of_paint": float(chip[pm].mean()) if pm.any() else 0,
             "near_edge_bare_fraction": chip_near, "edge_weight": float(w_edge), "paint_texels": int(pm.sum()),
             "chip_core_fraction_of_chips": float(chip_core.sum() / max(chip.sum(), 1)),
             "paint_scratch_texels": int(len(ii)), "grime_blot_fraction_of_paint": float((blot[pm] > 0.5).mean()),
             "texels_covered": int(cover.sum())}
    return out, stats


