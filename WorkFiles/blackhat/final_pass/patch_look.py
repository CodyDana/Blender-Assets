from pathlib import Path
p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/blackhat_look.py")
s = p.read_text(encoding="utf8")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('''    BaseColor  = T_BlackHat_<Part>_Detail.R x Tint     (Detail sRGB-encoded, sampled sRGB ON;
                                                          Tint default in the sidecar)
    Specular   = SPEC_SCALE x T_BlackHat_<Part>_ORM.A  (the baked specular mask; SPEC_SCALE 1.0: the
                                                       lacquered strand tops reach F0 0.08)''',
    '''    BaseColor  = Tint x (DetailBias + DetailScale x T_BlackHat_<Part>_Detail.R)
                 (Detail sRGB-encoded, sampled sRGB ON; Tint = the part's MEAN colour; the three
                  defaults per part in the sidecar; BC is this at the default Tint)
    Specular   = SPEC_SCALE[part] x T_BlackHat_<Part>_ORM.A  (the baked specular mask; straw 0.6 -> F0
                 <= 0.048, cloth 0.5 -> Specular 0.25 - 0.35)''')
rep('''#: Specular = SPEC_SCALE x ORM.A (Unreal's Specular pin, F0 = 0.08 x value)
SPEC_SCALE = 1.0''', '''#: Specular = SPEC_SCALE[part] x ORM.A (Unreal's Specular pin, F0 = 0.08 x value).  Final pass: round
#: 1's 1.0 let lacquered straw reach F0 0.08 (IOR ~1.8, the cap read as metal) and gave the cloth
#: a satin sheen; straw now tops out at F0 0.048 (lacquer, IOR ~1.55), cloth at Specular 0.35
SPEC_SCALE = {"straw": 0.6, "cloth": 0.5}
#: ORM.G is roughness; Unreal folds the normal map's per-mip variance into it (Toksvig) when the
#: ORM texture names the N texture as its Composite Texture in this mode.  Applied and verified in
#: the Unreal check; recorded in the sidecar for buyers
ORM_COMPOSITE = {"composite_texture": "<the part's _N>", "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN",
                 "composite_power": 1.0}''')
rep('''def make_material(name: str, paths: Dict[str, str], tint_linear, pack: bool = True, uv_name: str = "UVMap"):''',
    '''def make_material(name: str, paths: Dict[str, str], tint_linear, pack: bool = True, uv_name: str = "UVMap",
                  detail_bias: float = 0.0, detail_scale: float = 1.0, spec_scale: float = 1.0):''')
rep('''    det = tex(paths["Detail"], "sRGB")
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(det.outputs["Color"], mul.inputs["A"])''', '''    det = tex(paths["Detail"], "sRGB")
    # DetailBias + DetailScale x Detail (a grey image: colour -> float is the value itself)
    ma = nt.nodes.new("ShaderNodeMath")
    ma.operation = "MULTIPLY_ADD"
    nt.links.new(det.outputs["Color"], ma.inputs[0])
    ma.inputs[1].default_value = float(detail_scale)
    ma.inputs[2].default_value = float(detail_bias)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    mul.clamp_result = True
    nt.links.new(ma.outputs[0], mul.inputs["A"])''')
rep('''    ms.inputs[1].default_value = SPEC_SCALE''', '''    ms.inputs[1].default_value = float(spec_scale)''')
rep('''    mat["tint_linear"] = [float(x) for x in tint_linear]
    return mat''', '''    mat["tint_linear"] = [float(x) for x in tint_linear]
    mat["detail_bias"] = float(detail_bias)
    mat["detail_scale"] = float(detail_scale)
    mat["spec_scale"] = float(spec_scale)
    return mat''')
i0 = s.index("def unreal_material_spec(")
i1 = s.index("# =========================================================================== AO bake")
s = s[:i0] + '''def unreal_material_spec(stem: str, maps: Dict[str, object], part: str) -> Dict[str, object]:
    return {
        "shading_model": "Default Lit (or Substrate Slab); opaque; no Cloth/Fuzz layer",
        "BaseColor": f"saturate(Tint x (DetailBias + DetailScale x {stem}_Detail.R)); at the default Tint / Bias / "
                     f"Scale it equals {stem}_BC at every mip (source / 8-bit level)",
        "parameters": {
            "Tint": "the part's MEAN colour (linear). Set it to the colour you want the part to read as: the "
                    "average of the part, and its far mips, come out at exactly that colour",
            "DetailBias": "the darkest texel as a fraction of the mean (leave at the default)",
            "DetailScale": "the detail's contrast as a multiple of the mean (leave at the default; lower it toward "
                           "0 with Bias toward 1 for a flatter, lighter recolour whose flecks do not clip)"},
        "Tint_default_linear": [round(float(x), 6) for x in maps["tint_linear"]],
        "Tint_default_srgb": [round(float(x), 6) for x in maps["tint_srgb"]],
        "DetailBias_default": maps["detail_bias"], "DetailScale_default": maps["detail_scale"],
        "BaseColor_alt": f"{stem}_BC (sRGB) directly, for a fixed-colour instance",
        "Detail_encoding": "sRGB-encoded LINEAR detail d = (albedo - a_lo) / (a_hi - a_lo), full range 0..255, "
                           "quantised once from linear float data; import sRGB ON (TC_Grayscale, G8, uncompressed)",
        "bc_equality_note": "BC = the recolour graph at the defaults holds at the source (8-bit PNG) level. In Unreal "
                            "BC is BC1-compressed (TC_Default) and Detail is uncompressed G8, so the two paths differ "
                            "by BC1 block error",
        "Specular": f"{SPEC_SCALE[part]:g} x {stem}_ORM.A (the baked specular mask; linear, mip-safe)",
        "Roughness": f"{stem}_ORM.G (with the ORM texture's Composite Texture = {stem}_N, mode "
                     f"CTM_NormalRoughnessToGreen: Unreal widens roughness per mip by the normal map's variance)",
        "Metallic": "0", "AmbientOcclusion": f"{stem}_ORM.R",
        "Normal": f"{stem}_N (DirectX; TC_Normalmap, flip green OFF)",
        "textures": {"BC": "sRGB, TC_Default", "ORM": "linear (sRGB OFF), TC_Masks, RGBA (A = specular mask), "
                                                   f"CompositeTexture {stem}_N, CTM_NormalRoughnessToGreen",
                     "N": "TC_Normalmap", "Detail": "sRGB ON, TC_Grayscale, R channel",
                     "all": "MipGenSettings TMGS_FROM_TEXTURE_GROUP; 2048, power of two (12 mips)"},
    }


''' + s[i1:]
i0 = s.index("def body_hull_points(")
i1 = s.index("def obb_points(")
s = s[:i0] + '''def support_hull(co_mm: np.ndarray, base_azimuths: int = 13, cone_elevation_deg: float = 64.0,
                 margin: float = 1.0, max_vertices: int = 50, n_test: int = 4000, seed: int = 1):
    """A tight convex hull of at most ``max_vertices`` vertices: the intersection of SUPPORT planes
    (each moved ``margin`` mm out), so it contains every given vertex by construction.

    Planes: straight down, straight up (the crown), ``base_azimuths`` horizontal ones (the rim) and
    as many at the cone's normal elevation (64 deg: slope 26), then greedily the test direction
    where the hull stands furthest from the points' own convex hull (the band and knot), while
    the vertex count stays within ``max_vertices`` (50 = Chaos's p.Chaos.ConvexParticlesWarningThreshold,
    its geometry-complexity line).  Returns the vertices and a report (gap = the hull's support
    minus the points' support, over ``n_test`` random directions = how far it stands proud)."""
    import itertools
    P = np.asarray(co_mm, np.float64)
    rng = np.random.default_rng(seed)
    T = rng.normal(size=(n_test, 3))
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    hp = (P @ T.T).max(0)

    def vertices(dirs):
        h = (P @ dirs.T).max(0) + margin
        tri = np.array(list(itertools.combinations(range(len(dirs)), 3)))
        A, b = dirs[tri], h[tri]
        ok = np.abs(np.linalg.det(A)) > 1e-6
        v = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]
        v = v[(v @ dirs.T <= h + 1e-6).all(1)]
        keep = []
        for q in v[np.lexsort(v.T[::-1])]:
            if all(np.linalg.norm(q - k) > 0.05 for k in keep):
                keep.append(q)
        return np.array(keep)
    d = []
    for e in (0.0, cone_elevation_deg):
        for i in range(base_azimuths):
            ph = (i + 0.5) * 2 * math.pi / base_azimuths
            d.append((math.cos(ph) * math.cos(math.radians(e)), math.sin(ph) * math.cos(math.radians(e)),
                      math.sin(math.radians(e))))
    dirs = np.array(d + [(0.0, 0.0, -1.0), (0.0, 0.0, 1.0)])
    V = vertices(dirs)
    added = 0
    for _ in range(40):
        gap = (V @ T.T).max(0) - hp
        cand = np.vstack([dirs, T[int(np.argmax(gap))]])
        V2 = vertices(cand)
        if len(V2) > max_vertices:
            break
        dirs, V = cand, V2
        added += 1
    gap = (V @ T.T).max(0) - hp
    rep = {"planes": int(len(dirs)), "greedy_planes": added, "vertices": int(len(V)), "margin_mm": margin,
           "max_vertices": max_vertices,
           "gap_to_points_convex_hull_mm": {"mean": round(float(gap.mean()), 3), "p95": round(float(np.percentile(gap, 95)), 3),
                                            "max": round(float(gap.max()), 3)},
           "above_highest_vertex_mm": round(float(V[:, 2].max() - P[:, 2].max()), 3),
           "below_lowest_vertex_mm": round(float(P[:, 2].min() - V[:, 2].min()), 3),
           "beyond_widest_radius_mm": round(float(np.hypot(V[:, 0], V[:, 1]).max() - np.hypot(P[:, 0], P[:, 1]).max()), 3)}
    return V, rep


''' + s[i1:]
rep('''__all__ = ["to_blender", "make_material", "unreal_material_spec", "bake_ao", "body_hull_points", "obb_points",''',
    '''__all__ = ["to_blender", "make_material", "unreal_material_spec", "bake_ao", "support_hull", "obb_points",
           "SPEC_SCALE", "ORM_COMPOSITE",''')
p.write_text(s, encoding="utf8")
print("ok")
