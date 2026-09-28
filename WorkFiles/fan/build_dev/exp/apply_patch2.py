p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
old = '''            mid[i, k] = _equidistant(p, rib[i, 0], rib[i, 1], rib[i + 1, 0], rib[i + 1, 1])
            if mid_offsets is not None:
                mid[i, k] = mid[i, k] + apply(rotz(lam[i] - lam[0]), np.asarray(mid_offsets)[k][None])[0]'''
new = '''            if mid_offsets is not None:
                # (radial, z) shift of gap 0's fold point, turned with the gap; the equidistance below
                # then fixes its angle, so the two faces of every gap stay the same width
                d_r, d_z = np.asarray(mid_offsets, np.float64)[k]
                p = p + np.array([math.cos(mu) * d_r, math.sin(mu) * d_r, d_z])
            mid[i, k] = _equidistant(p, rib[i, 0], rib[i, 1], rib[i + 1, 0], rib[i + 1, 1])'''
assert old in s
s = s.replace(old, new)
s = s.replace('''    """``mid_offsets`` (2, 3): the optimised shift of gap 0's inner and outer mid-gap fold points
    (``optimise_bind``), applied to every gap turned about Z with it."""''', '''    """``mid_offsets`` (2, 2): the optimised (radial, z) shift of every gap's inner and outer mid-gap
    fold points (``optimise_bind``); the fold's angle is always re-solved for equal face widths."""''')
s = s.replace("np.asarray(mid_offsets, np.float64).reshape(2, 3)", "np.asarray(mid_offsets, np.float64).reshape(2, 2)")
s = s.replace('''    def obj(p):
        fs = FoldSolver(spec, p.reshape(2, 3))''', '''    def obj(p):
        fs = FoldSolver(spec, p.reshape(2, 2))''')
s = s.replace("    n = 6\n    X = [np.zeros(n)] + [np.eye(n)[k] * 0.3 for k in range(n)]", "    n = 4\n    X = [np.zeros(n)] + [np.eye(n)[k] * 0.3 for k in range(n)]")
s = s.replace('''    return X[k].reshape(2, 3), {"iterations": iters, "worst_before_mm": float(f0), "worst_after_mm": float(Fv[k]),
                                "samples": list(samples), "offsets_mm": np.round(X[k].reshape(2, 3), 6).tolist()}''', '''    return X[k].reshape(2, 2), {"iterations": iters, "worst_before_mm": float(f0), "worst_after_mm": float(Fv[k]),
                                "samples": list(samples), "offsets_radial_z_mm": np.round(X[k].reshape(2, 2), 6).tolist()}''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
