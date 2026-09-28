from pathlib import Path
p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/blackhat_paint.py")
s = p.read_text(encoding="utf8")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('''Channels (float, linear): alb (albedo luminance; the hue is the slot's Tint), rough, spec (the
specular mask: Specular = 0.5 x spec), ao (analytic cavities; the Cycles bake multiplies in
later), hgt (mm, for the normal map).
"""''', '''Channels (float, linear): alb (albedo luminance; the hue is the slot's Tint), rough, spec (the
specular mask: Specular = SPEC_SCALE[part] x spec, blackhat_look), ao (analytic cavities; the
Cycles bake multiplies in later), hgt (mm, for the normal map).

Final pass (engineering, 2026-09-26): roughness floors so no straw texel is near-mirror (round 1
reached 0.05: the cap and ribs read metallic and the ribs' highlights crawled), matte cloth
(roughness 0.85 - 0.95, Specular 0.25 - 0.35), the inner skin's weave faded into a plain seat disc
at the apex (the strands converged to sub-texel size and swirled), and the recolour convention
changed so the Tint IS the part's mean colour (finish()).
"""''')
rep('''    rough = 0.15 + 0.13 * hash01(c, ks, cell, seed=seed + 4) + 0.35 * (gap + cline + seam) + 0.10 * (1 - dome)''',
    '''    rough = 0.38 + 0.13 * hash01(c, ks, cell, seed=seed + 4) + 0.30 * (gap + cline + seam) + 0.10 * (1 - dome)''')
rep('''        rough = rough - 0.08 * zone''', '''        rough = rough - 0.03 * zone''')
rep('''    else:
        alb *= 0.95
    return {"alb": alb, "rough": rough, "spec": spec, "ao": ao, "hgt": hgt}''', '''    else:
        alb *= 0.95
        # the inner skin fades into a plain seat disc at the apex (rho < ~0.1): toward the apex the
        # strands converge below a texel and swirled in round 1's underside view
        f = smooth(0.05, 0.13, rho)
        alb = STRAW_BASE * 0.70 + (alb - STRAW_BASE * 0.70) * f
        hgt = hgt * f
        spec = 0.55 + (spec - 0.55) * f
        rough = 0.55 + (rough - 0.55) * f
        ao = 1.0 + (ao - 1.0) * f
    return {"alb": alb, "rough": rough, "spec": spec, "ao": ao, "hgt": hgt}''')
rep('''    return {"alb": alb, "rough": 0.30 + 0.2 * groove + 0.1 * fl, "spec": (0.6 + 0.4 * dome) * (1 - 0.7 * groove),''',
    '''    # rougher than round 1 (0.30): a highlight spreads along the rod instead of breaking into
    # bright dashes that crawl as the view turns
    return {"alb": alb, "rough": 0.58 + 0.15 * groove + 0.1 * fl, "spec": (0.6 + 0.4 * dome) * (1 - 0.7 * groove),''')
rep('''    return {"alb": alb, "rough": 0.42 + 0.12 * fline + 0.15 * fl, "spec": (1 - 0.4 * fline) * (1 - 0.3 * fl),''',
    '''    return {"alb": alb, "rough": 0.52 + 0.12 * fline + 0.15 * fl, "spec": (1 - 0.4 * fline) * (1 - 0.3 * fl),''')
rep('''    return {"alb": alb, "rough": 0.36 + 0.15 * groove, "spec":''', '''    return {"alb": alb, "rough": 0.52 + 0.15 * groove, "spec":''')
rep('''    return {"alb": alb, "rough": 0.40 + 0.1 * gap - 0.1 * rl, "spec": 1 - 0.5 * gap,''',
    '''    return {"alb": alb, "rough": 0.58 + 0.1 * gap - 0.05 * rl, "spec": 0.8 - 0.4 * gap,''')
rep('''    rough = 0.86 + 0.05 * (1 - h)
    spec = 0.35 + 0.25 * h''', '''    # matte cloth (final pass): roughness 0.85 - 0.95 and a specular mask of 0.5 - 0.7, which at
    # SPEC_SCALE cloth 0.5 is Unreal Specular 0.25 - 0.35 (F0 0.020 - 0.028); round 1's 0.35 - 0.90 at
    # scale 1.0 gave the tails a satin / patent sheen
    rough = 0.86 + 0.05 * (1 - h)
    spec = 0.50 + 0.20 * h''')
rep('''        rough = rough - 0.25 * q
        spec = spec + 0.3 * q''', '''        rough = rough - 0.02 * q''')
i0 = s.index("def finish(ch, chroma, ref_percentile=99.95):")
i1 = s.index("__all__ = [")
s = s[:i0] + '''def finish(ch, chroma, lo_percentile=0.05, hi_percentile=99.95, rough_range=(0.0, 1.0)):
    """Float channels -> the shipped maps (8-bit), the detail and the default recolour parameters.

    Detail  sRGB-ENCODED LINEAR detail d, FULL RANGE at BOTH ends: d = (albedo - a_lo) / (a_hi - a_lo)
            (a_lo / a_hi the albedo at the lo / hi percentile of the written texels), quantised
            ONCE from float data.  Import sRGB ON: Unreal decodes before filtering, so a filtered
            sample is the average LINEAR d, and the affine map below commutes with the filter.
    Tint    the part's MEAN colour (linear): mean albedo x chroma / lum(chroma), the mean taken
            over the written texels of what the quantised Detail reproduces.  A buyer who sets Tint
            to a colour gets that colour as the part's average (and at the far mips).
    DetailBias, DetailScale  a_lo / lum(Tint), (a_hi - a_lo) / lum(Tint): mean(Bias + Scale x d) = 1.
    BC      sRGB8( Tint x (DetailBias + DetailScale x sRGBdecode(Detail8)) ) from the QUANTISED
            Detail and the ROUNDED sidecar numbers, so BC = the recolour graph at the default Tint
            to BC's own 8-bit rounding (source level; Unreal's BC1 compression of BC adds its own
            block error, the uncompressed G8 Detail does not)
    ORM     R AO, G roughness (clipped to ``rough_range``), B metallic 0, A the SPECULAR MASK
            (linear, Specular = SPEC_SCALE x ORM.A): a linear quantity, so mip-safe
    N       DirectX
    Texels outside every island take the median values so no mip ever pulls a foreign value in."""
    wr = ch["written"]
    alb = ch["alb"].astype(np.float64).copy()
    med = float(np.median(alb[wr]))
    alb[~wr] = med
    a_lo = float(np.percentile(alb[wr], lo_percentile))
    a_hi = float(np.percentile(alb[wr], hi_percentile))
    d = np.clip((alb - a_lo) / (a_hi - a_lo), 0.0, 1.0)
    D8 = np.rint(srgb_encode(d) * 255.0).astype(np.uint8)
    dq = srgb_decode(D8.astype(np.float64) / 255.0)
    mean_d = float(dq[wr].mean())
    mean_alb = a_lo + (a_hi - a_lo) * mean_d
    chroma = np.asarray(chroma, np.float64)
    tint = np.round(mean_alb * chroma / float(chroma @ LUMA), 6)
    t_l = float(tint @ LUMA)
    bias = round(a_lo / t_l, 6)
    scale = round((a_hi - a_lo) / t_l, 6)
    bc_lin = (bias + scale * dq)[..., None] * tint[None, None, :]
    BC8 = np.rint(srgb_encode(bc_lin) * 255.0).astype(np.uint8)
    ao = np.where(wr, ch["ao"], 1.0)
    rough = np.clip(np.where(wr, ch["rough"], float(np.median(ch["rough"][wr]))), *rough_range)
    spec = np.where(wr, ch["spec"], float(np.median(ch["spec"][wr])))
    orm = np.stack([ao, rough, np.zeros_like(ao), spec], -1)
    ORM8 = np.rint(np.clip(orm, 0, 1) * 255.0).astype(np.uint8)
    n = normal_dx(ch)
    N8 = np.rint((n * 0.5 + 0.5) * 255.0).astype(np.uint8)
    err = np.abs(srgb_decode(BC8.astype(np.float64) / 255.0) - np.clip(bc_lin, 0, 1))[wr]
    dw = D8[wr]
    r8 = ORM8[..., 1][wr] / 255.0
    return {"BC": BC8, "ORM": ORM8, "N": N8, "Detail": D8, "tint_linear": tint.tolist(),
            "tint_srgb": srgb_encode(tint).tolist(), "L_ref": a_hi, "detail_bias": bias, "detail_scale": scale,
            "recolour": {"bc_is_recolour_graph": "BC8 = sRGB8(Tint x (DetailBias + DetailScale x sRGBdecode(Detail8/255))) "
                                                 "from the quantised Detail and the rounded sidecar numbers",
                         "tint_is": "the part's MEAN linear colour over the written texels",
                         "detail_bias": bias, "detail_scale": scale,
                         "albedo_lo_hi": [round(a_lo, 6), round(a_hi, 6)],
                         "mean_of_bias_plus_scale_x_detail": round(float((bias + scale * dq[wr]).mean()), 6),
                         "max_abs_err_linear": float(err.max()), "detail_levels_used": int(len(np.unique(dw))),
                         "detail_clipped_share_low_high": [float(np.mean(alb[wr] < a_lo)), float(np.mean(alb[wr] > a_hi))],
                         "detail_min_max_code": [int(dw.min()), int(dw.max())],
                         "detail_percentiles_of_255": {str(p): float(np.percentile(dw, p))
                                                       for p in (0.1, 1, 10, 50, 90, 99, 99.9)}},
            "albedo_stats": {"mean": float(ch["alb"][wr].mean()), "p10": float(np.percentile(ch["alb"][wr], 10)),
                             "p50": float(np.percentile(ch["alb"][wr], 50)),
                             "p90": float(np.percentile(ch["alb"][wr], 90)), "max": float(ch["alb"][wr].max())},
            "roughness_stats": {"min": round(float(r8.min()), 4), "p1": round(float(np.percentile(r8, 1)), 4),
                                "p50": round(float(np.percentile(r8, 50)), 4), "max": round(float(r8.max()), 4)},
            "spec_mask_mean": float(spec[wr].mean()),
            "spec_mask_min_max": [round(float(spec[wr].min()), 4), round(float(spec[wr].max()), 4)]}


''' + s[i1:]
p.write_text(s, encoding="utf8")
print("ok")
