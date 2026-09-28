p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_paint.py"
s = open(p, encoding="utf-8").read()
old = s[s.index("def paint_stick("):s.index("def paint_rivet(")]
new = '''def paint_stick(loc: np.ndarray, kind: np.ndarray, stick: np.ndarray, seed: int = 23, half_width=None,
                rounded: Optional[np.ndarray] = None, edge_band_mm: float = 0.9, edge_drop_mm: float = 0.30):
    """loc (M, 2): the stick's own frame (x along it) for faces, (perimeter, z) for walls.

    ``half_width(x)`` (mm) and ``rounded`` (per texel: an inner rib's face) give each rib's rounded long
    edges in the height (so in the normal map): RS 4's 2 - 3 px dark boundary between neighbouring ribs is
    their edges turning away from the light; the plates' own walls are only 0.37 mm tall."""
    x = loc[:, 0]
    y = loc[:, 1]
    s = stick.astype(np.float64)
    along = np.where(kind == 2, loc[:, 0], x)                                     # walls: along the perimeter
    across = np.where(kind == 2, loc[:, 1] * 4.0, y)
    fib = fbm1(across * 3.1 + s * 13.7, seed, 4) * (0.7 + 0.3 * (0.5 + fbm1(along * 0.08 + s, seed + 2, 2)))
    fine = vnoise1(across * 11.0 + s * 3.3, seed + 4)
    lac = fbm2(along * 0.03 + s * 5.1, across * 0.3, seed + 6, 2)
    f = 1.0 + 0.07 * fib + 0.025 * fine + 0.03 * lac
    rough = 0.39 + 0.035 * fib + 0.02 * lac
    spec = 0.50 + 0.05 * fib
    hgt = 0.004 * (fib + 0.4 * fine)
    if half_width is not None and rounded is not None:
        d = np.maximum(half_width(x) - np.abs(y), 0.0)
        u = np.clip(d / edge_band_mm, 0.0, 1.0)
        prof = 1.0 - (1.0 - u) ** 2                                                  # a quarter-round
        hgt = hgt + np.where(rounded, -edge_drop_mm * (1.0 - prof), 0.0)
    return f, rough, spec, hgt


'''
s = s.replace(old, new)
old = '''    f = np.where(kind == 3, 1.0 + 0.16 * strands,'''
s = s.replace(old, '''    f = np.where(kind == 3, 1.0 + 0.26 * strands,''')
s = s.replace('''    hgt = np.where(kind == 3, 0.012 * strands, np.where(kind == 0, 0.02 * twist, 0.015 * knot))''',
              '''    hgt = np.where(kind == 3, 0.06 * strands, np.where(kind == 0, 0.05 * twist, 0.05 * knot))''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_fan.py"
s = open(p, encoding="utf-8").read()
old = '''        "sticks": paint_channels(fan[0], 1, spec.texture_size, lambda L, K, S: FP.paint_stick(L, K, S), lum(spec.sticks_colour_linear)),'''
assert old in s
s = s.replace(old, '''        "sticks": paint_channels(fan[0], 1, spec.texture_size,
                                 lambda L, K, S: FP.paint_stick(L, K, S, half_width=lambda x: 0.5 * np.array([spec.rib_width_mm(v) for v in x]),
                                                                rounded=(K <= 1) & (S > 0) & (S < spec.n_sticks - 1)),
                                 lum(spec.sticks_colour_linear)),''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_tassel.py"
s = open(p, encoding="utf-8").read()
s = s.replace("    seg_skirt = (18, 10, 6)[lod]", "    seg_skirt = (30, 12, 6)[lod]")
old = '''    jit = [(hash01(k, seed=77) - 0.5) * 2.0 * st["ragged"] * 0.5 - 0.5 * st["ragged"] for k in range(seg_skirt)]'''
assert old in s
s = s.replace(old, '''    # ragged thread ends (RS 8: over ~0.015 L): each strand group ends at its own length
    jit = [-(hash01(k, seed=77) ** 0.7) * st["ragged"] for k in range(seg_skirt)]''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
