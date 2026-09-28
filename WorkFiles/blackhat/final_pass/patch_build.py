from pathlib import Path
p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_black_hat.py")
s = p.read_text(encoding="utf8")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('''LIB_VERSION = "1.0.0"''', '''LIB_VERSION = "1.1.0"      # final pass (2026-09-26): engineering fixes, see WorkFiles/blackhat/BLACKHAT_REPORT.md''')
rep('''MATS = {"straw": BLACK_HAT.straw_material, "cloth": BLACK_HAT.cloth_material}''',
    '''MATS = {"straw": BLACK_HAT.straw_material, "cloth": BLACK_HAT.cloth_material}
#: ORM.G clip per part (final pass): no near-mirror straw (round 1 reached 0.05), matte cloth
ROUGH_RANGE = {"straw": (0.35, 1.0), "cloth": (0.85, 0.95)}
#: REFERENCE_SPEC 8's measured tip pixels (the torn ends' points) and the gate on them (x AND y)
TAIL_TIPS_PX = {"A": (591.0, 534.0), "B": (643.0, 520.0)}
TAIL_TIP_TOL_PX = 6.0''')
# textures
rep('''    for k in chs:
        maps[k] = BP.finish(chs[k], CHROMA[k])
        paths[k] = {kk: LK.write_png(TEXTURES / f"{STEMS[k]}_{kk}.png", maps[k][kk]) for kk in ("BC", "ORM", "N", "Detail")}
    tmp_mats = [LK.make_material("__bake_straw", paths["straw"], maps["straw"]["tint_linear"], pack=False),
                LK.make_material("__bake_cloth", paths["cloth"], maps["cloth"]["tint_linear"], pack=False)]''',
    '''    for k in chs:
        maps[k] = BP.finish(chs[k], CHROMA[k], rough_range=ROUGH_RANGE[k])
        paths[k] = {kk: LK.write_png(TEXTURES / f"{STEMS[k]}_{kk}.png", maps[k][kk]) for kk in ("BC", "ORM", "N", "Detail")}
    tmp_mats = [_material(f"__bake_{k}", paths[k], maps[k], k, pack=False) for k in ("straw", "cloth")]''')
rep('''        chs[k]["ao"] = chs[k]["ao"] * a
        maps[k] = BP.finish(chs[k], CHROMA[k])''', '''        chs[k]["ao"] = chs[k]["ao"] * a
        maps[k] = BP.finish(chs[k], CHROMA[k], rough_range=ROUGH_RANGE[k])''')
rep('''    mats = {k: LK.make_material(MATS[k], paths[k], maps[k]["tint_linear"], pack=True) for k in ("straw", "cloth")}''',
    '''    mats = {k: _material(MATS[k], paths[k], maps[k], k, pack=True) for k in ("straw", "cloth")}''')
rep('''           "L_ref": {k: round(maps[k]["L_ref"], 6) for k in maps},''', '''           "L_ref": {k: round(maps[k]["L_ref"], 6) for k in maps},
           "detail_bias": {k: maps[k]["detail_bias"] for k in maps},
           "detail_scale": {k: maps[k]["detail_scale"] for k in maps},
           "spec_scale": dict(LK.SPEC_SCALE), "roughness_range": {k: list(v) for k, v in ROUGH_RANGE.items()},
           "roughness_stats": {k: maps[k]["roughness_stats"] for k in maps},
           "spec_mask_min_max": {k: maps[k]["spec_mask_min_max"] for k in maps},''')
rep('''           "unreal_material": {k: LK.unreal_material_spec(STEMS[k], maps[k]) for k in maps}}''',
    '''           "unreal_material": {k: LK.unreal_material_spec(STEMS[k], maps[k], k) for k in maps}}''')
rep('''    log(f"  tints {tex['tint_linear']}; detail levels "''', '''    log(f"  tints (mean colour) {tex['tint_linear']}; bias {tex['detail_bias']} scale {tex['detail_scale']}; detail levels "''')
rep('''def _png_chunks(path):''', '''def _material(name, paths, m, part, pack):
    return LK.make_material(name, paths, m["tint_linear"], pack=pack, detail_bias=m["detail_bias"],
                            detail_scale=m["detail_scale"], spec_scale=LK.SPEC_SCALE[part])


def _png_chunks(path):''')
# mip parity
i0 = s.index("def mip_parity(m) -> dict:")
i1 = s.index("# =========================================================================== objects")
s = s[:i0] + '''def mip_parity(m) -> dict:
    """The recolour graph against BC through Unreal-style mips (2x2 box in LINEAR light: Detail and
    BC are both sRGB, decoded before filtering), each level re-quantised to 8 bits:
    lum(Tint) x (Bias + Scale x Detail) vs BC, mean over the map, mips 0-8 (and the far mip's value
    against lum(Tint): with Tint = the mean colour the far mips converge on the Tint)."""
    d = BP.srgb_decode(m["Detail"].astype(np.float64) / 255.0)
    bc = BP.srgb_decode(m["BC"].astype(np.float64) / 255.0) @ BP.LUMA
    tl = float(np.asarray(m["tint_linear"]) @ BP.LUMA)
    b, sc = m["detail_bias"], m["detail_scale"]
    out, per_texel = [], []
    for lvl in range(9):
        a8 = np.rint(BP.srgb_encode(d) * 255) / 255.0
        b8 = np.rint(BP.srgb_encode(bc) * 255) / 255.0
        a_lin = np.clip(tl * (b + sc * BP.srgb_decode(a8)), 0, 1)
        b_lin = BP.srgb_decode(b8)
        out.append(round(float(a_lin.mean() / max(b_lin.mean(), 1e-12) - 1.0) * 100.0, 3))
        per_texel.append(round(float(np.percentile(np.abs(a_lin - b_lin), 99)), 5))
        d = 0.25 * (d[0::2, 0::2] + d[1::2, 0::2] + d[0::2, 1::2] + d[1::2, 1::2])
        bc = 0.25 * (bc[0::2, 0::2] + bc[1::2, 0::2] + bc[0::2, 1::2] + bc[1::2, 1::2])
    return {"graph_vs_bc_mean_pct_mip0_8": out, "max_abs_pct": round(max(abs(x) for x in out), 3),
            "graph_vs_bc_p99_abs_linear_mip0_8": per_texel,
            "note": "the mean over the WHOLE map (padding texels hold the median) at each mip"}


''' + s[i1:]
# collision
i0 = s.index("def stage_collision(spec, builders, objs, report):")
i1 = s.index("def _outside(V, F, P):")
s = s[:i0] + '''def _hanging_tail_mask(spec, mb):
    P = np.asarray(mb.P)
    ids = np.array(sorted({v for fi in mb.parts.get("tails", []) for v in mb.F[fi]}), int)
    is_tail = np.zeros(len(P), bool)
    is_tail[ids] = True
    r = np.hypot(P[:, 0], P[:, 1])
    return is_tail & ((r > spec.rim_centre_radius) | (P[:, 2] < -0.5))


def stage_collision(spec, builders, objs, report):
    """ONE tight convex hull round the hat's body (cone, crown cap, rim, lashings, band, knot and the
    tails where they lie on the cone): support planes 1 mm out, at most 50 vertices.

    The hanging tails get NO collision (final pass; round 1 boxed them in a second hull): a limp
    cloth tail on a worn hat should not block or snag the wearer's capsule and shoulders, and on a
    hat lying on the ground they are a 9 cm strip of cloth.  Round 1's hulls stood 15 mm above the
    crown and 30 mm below the tail tips."""
    lod0 = objs[0]
    body, hang = [], []
    for mb in builders:
        P = np.asarray(mb.P)
        m = _hanging_tail_mask(spec, mb)
        body.append(P[~m])
        hang.append(P[m])
    body_pts = np.concatenate(body)
    Vb, hrep = LK.support_hull(body_pts)
    Vb2, Fb = LK.convex_faces(Vb)
    h0 = LK._hull_object(f"UCX_{lod0.name}_00", Vb2 * 0.001, Fb, lod0)
    worst = [float(_outside(Vb2, Fb, P).max()) for P in body]
    dw = _outside(Vb2, Fb, body_pts)
    worst_pt = body_pts[int(np.argmax(dw))].round(2).tolist()
    hang_all = np.concatenate(hang)
    lo = np.asarray(builders[0].P)
    report["collision"] = {"hulls": [h0.name], "vertices": [len(Vb2)], "faces": [len(Fb)],
                           "worst_point_mm": worst_pt,
                           "shape": "support-plane polytope: down, up, 13 horizontal (rim), 13 at the cone normal, "
                                    "plus greedy planes at the band / knot; each plane 1 mm outside the body",
                           "fit": hrep,
                           "body_worst_vertex_outside_mm_per_lod": [round(w, 4) for w in worst],
                           "contains_body_of_every_lod": bool(max(worst) <= 1e-6),
                           "hanging_tails": {"collision": "none (by design)",
                                             "vertices_per_lod": [int(len(h)) for h in hang],
                                             "lowest_z_mm": round(float(hang_all[:, 2].min()), 2),
                                             "lod0_mesh_z_range_mm": [round(float(lo[:, 2].min()), 2),
                                                                      round(float(lo[:, 2].max()), 2)]},
                           "naming": "UCX_<render mesh NODE name>_00, renamed with the node by make_lod_group"}
    log(f"  hull {len(Vb2)} vertices, gap mean {hrep['gap_to_points_convex_hull_mm']['mean']} mm; "
        f"worst body vertex outside {max(worst):.4f} mm")
    return [h0]


''' + s[i1:]
# sidecar
rep('''        payload["materials"] = {
            MATS[k]: {"slot": i, "part": k, "textures": {kk: f"{STEMS[k]}_{kk}" for kk in ("BC", "ORM", "N", "Detail")},
                      "tint_default_linear": (tex.get("tint_linear") or {}).get(k),
                      "tint_default_srgb": (tex.get("tint_srgb") or {}).get(k),
                      "graph": (tex.get("unreal_material") or {}).get(k)}
            for i, k in enumerate(("straw", "cloth"))}
        payload["materials_note"] = ("BaseColor = Detail.R x Tint (Detail sRGB ON, TC_Grayscale); equals BC at the default "
                                     "Tint at every mip. Specular = %g x ORM.A; Roughness = ORM.G; Metallic 0; "
                                     "N DirectX (flip green OFF). The cloth's UV0 lies in the second tile (U + 1): "
                                     "keep the textures' address mode Wrap." % LK.SPEC_SCALE)''',
    '''        payload["materials"] = {
            MATS[k]: {"slot": i, "part": k, "textures": {kk: f"{STEMS[k]}_{kk}" for kk in ("BC", "ORM", "N", "Detail")},
                      "tint_default_linear": (tex.get("tint_linear") or {}).get(k),
                      "tint_default_srgb": (tex.get("tint_srgb") or {}).get(k),
                      "tint_is": "the part's MEAN colour: edit Tint to recolour",
                      "detail_bias_default": (tex.get("detail_bias") or {}).get(k),
                      "detail_scale_default": (tex.get("detail_scale") or {}).get(k),
                      "specular_scale": LK.SPEC_SCALE[k],
                      "orm_texture_settings": {**LK.ORM_COMPOSITE, "composite_texture": f"{STEMS[k]}_N"},
                      "graph": (tex.get("unreal_material") or {}).get(k)}
            for i, k in enumerate(("straw", "cloth"))}
        payload["materials_note"] = (
            "BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail.R)) (Detail sRGB ON, TC_Grayscale). "
            "Tint is the part's MEAN colour: set it to the colour the part should read as. At the defaults the graph "
            "equals BC at every mip at the source (8-bit PNG) level; in Unreal BC is BC1-compressed and Detail is "
            "uncompressed G8, so they differ by BC1 block error. Specular = specular_scale x ORM.A; Roughness = ORM.G "
            "(set the ORM texture's Composite Texture to the part's _N, mode CTM_NormalRoughnessToGreen); Metallic 0; "
            "N DirectX (flip green OFF). The cloth's UV0 lies in the second tile (U + 1): keep the address mode Wrap.")
        geo = (report.get("geometry") or {}).get("lods") or {}
        payload["triangle_budget"] = {
            "lod_triangles": report.get("lod_triangles"),
            "lod0_by_part": (geo.get("LOD0") or {}).get("parts"),
            "why_lod0_is_over_10k": "a 600 mm hat whose signature details are real geometry: 26 lashings of three "
                                    "cords, the rolled rim tube, its binding cord, 13 ribs, the band and two torn tails "
                                    "with walls; the pack's LOD rule switches LOD1 in at screen size 0.70, LOD2 at 0.25"}
        payload["collision_note"] = ("one convex hull (UCX_..._00, <= 50 vertices) round the hat's body; the hanging "
                                     "cloth tails have no collision by design")''')
# fidelity: tail tips
rep('''         "bottom_outline_rms_px": float(np.sqrt(np.nanmean((n["_bot"][40:540] - r["_bot"][40:540]) ** 2)))}''',
    '''         "bottom_outline_rms_px": float(np.sqrt(np.nanmean((n["_bot"][40:540] - r["_bot"][40:540]) ** 2)))}
    # the tails' pointed tips, in x AND y (round 1 gated y only): A = the lowest silhouette pixel,
    # B = the lowest one at least 25 px right of A
    for nm, d in (("reference", r), ("render", n)):
        d["tail_tips_px"] = _tail_tips(d["_mask"])
    g["tail_tip_dev_px"] = {k: [round(n["tail_tips_px"][k][0] - TAIL_TIPS_PX[k][0], 2),
                                round(n["tail_tips_px"][k][1] - TAIL_TIPS_PX[k][1], 2)] for k in ("A", "B")}
    g["tail_tip_reference_measured_px"] = r["tail_tips_px"]''')
rep('''def fidelity(render_png) -> dict:''', '''def _tail_tips(mask):
    ys, xs = np.nonzero(mask[:, 520:])
    xs = xs + 520
    ia = int(np.argmax(ys + 1e-3 * xs))
    a = (float(xs[ia]), float(ys[ia]))
    sel = xs > a[0] + 25
    ib = int(np.argmax(np.where(sel, ys, -1)))
    return {"A": [a[0], a[1]], "B": [float(xs[ib]), float(ys[ib])]}


def fidelity(render_png) -> dict:''')
rep('''         "F7_chroma_r_within_0.012": abs(n["object_chroma"][0] - r["object_chroma"][0]) <= 0.012}''',
    '''         "F7_chroma_r_within_0.012": abs(n["object_chroma"][0] - r["object_chroma"][0]) <= 0.012,
         "F8_tail_tips_x_and_y_within_6px": all(abs(v) <= TAIL_TIP_TOL_PX for xy in d["tail_tip_dev_px"].values()
                                                 for v in xy)}''')
# gates
rep('''    g["7_hulls_contain_every_lod"] = bool((report.get("collision") or {}).get("contains_every_lod"))''',
    '''    col = report.get("collision") or {}
    g["7_hull_contains_body_of_every_lod"] = bool(col.get("contains_body_of_every_lod"))
    g["7b_one_hull_at_most_50_vertices_1mm_over_crown_and_rim"] = bool(
        len(col.get("hulls") or []) == 1 and (col.get("vertices") or [99])[0] <= 50
        and abs((col.get("fit") or {}).get("above_highest_vertex_mm", 99) - 1.0) < 0.05
        and abs((col.get("fit") or {}).get("below_lowest_vertex_mm", 99) - 1.0) < 0.05)''')
rep('''    ok9b = bool(tex)
    for k, rc in (tex.get("recolour") or {}).items():
        p = rc["detail_percentiles_of_255"]
        ok9b = ok9b and rc["detail_levels_used"] >= 120 and p["99.9"] >= 230 and p["10"] >= 12
    g["9b_recolour_detail_full_range"] = ok9b
    g["9c_mip_parity_within_1pct"] = bool(tex) and all(v["max_abs_pct"] <= 1.0 for v in tex["mip_parity"].values())''',
    '''    ok9b = bool(tex)
    for k, rc in (tex.get("recolour") or {}).items():
        mm = rc["detail_min_max_code"]
        ok9b = (ok9b and rc["detail_levels_used"] >= 200 and mm[0] == 0 and mm[1] == 255
                and abs(rc["mean_of_bias_plus_scale_x_detail"] - 1.0) <= 0.002 and rc["max_abs_err_linear"] <= 0.0035)
    g["9b_recolour_detail_full_range_both_ends_tint_is_mean"] = ok9b
    g["9c_mip_parity_within_1pct"] = bool(tex) and all(v["max_abs_pct"] <= 1.0 for v in tex["mip_parity"].values())
    rs = tex.get("roughness_stats") or {}
    g["9d_roughness_floors_straw_0.35_cloth_0.85_0.95"] = bool(
        rs and rs["straw"]["min"] >= 0.345 and rs["cloth"]["min"] >= 0.845 and rs["cloth"]["max"] <= 0.955)''')
rep('''    names += [v.get("object") for v in lods.values()] + list((report.get("collision") or {}).get("hulls") or [])''',
    '''    names += [v.get("object") for v in lods.values()] + list(col.get("hulls") or [])''')
p.write_text(s, encoding="utf8")
print("ok")
