p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)
rep('''    def obj(p):
        fs = FoldSolver(spec, p.reshape(2, 2))''', '''    def shift(p):
        # bounded: a fold point may move at most OFFSET_LIMIT_MM (radially and in Z) - the shape of the
        # leaf (its radii, its scallop, its pleat depth) must not change; unbounded, the search collapses
        # the mid-gap folds to points
        return OFFSET_LIMIT_MM * np.tanh(np.asarray(p, np.float64))

    def obj(p):
        fs = FoldSolver(spec, shift(p).reshape(2, 2))''')
rep('''    k = int(np.argmin(Fv))
    return X[k].reshape(2, 2), {"iterations": iters, "worst_before_mm": float(f0), "worst_after_mm": float(Fv[k]),
                                "samples": list(samples), "offsets_radial_z_mm": np.round(X[k].reshape(2, 2), 6).tolist()}''',
'''    k = int(np.argmin(Fv))
    off = shift(X[k]).reshape(2, 2)
    return off, {"iterations": iters, "worst_before_mm": float(f0), "worst_after_mm": float(Fv[k]),
                 "samples": list(samples), "offset_limit_mm": OFFSET_LIMIT_MM,
                 "offsets_radial_z_mm": np.round(off, 6).tolist()}''')
rep('''def optimise_bind(spec: FanSpec = FAN,''', '''OFFSET_LIMIT_MM = 0.6


def optimise_bind(spec: FanSpec = FAN,''')
rep("    X = [np.zeros(n)] + [np.eye(n)[k] * 0.3 for k in range(n)]", "    X = [np.zeros(n)] + [np.eye(n)[k] * 0.8 for k in range(n)]")
open(p, "w", encoding="utf-8").write(s)
print("ok")
