import json, sys
import numpy as np
exec(open('fit_study.py').read().split("out = {}")[0].replace("if row < 169: return 97.0", "if row < 143: return 147.0 if row > 40 else 999.0\n    if row < 169: return 102.0"))
res = {}
for swept in (False, True):
    for wall, clr in ((2.0, 0.75), (1.5, 0.75), (1.5, 0.5)):
        rows = []
        for th in np.arange(0.0, 1.01, 0.1):
            b = max((margins(c0, th, wall, clr, swept) + (c0,) for c0 in np.arange(-6, 6.01, 0.25)), key=lambda t: t[0])
            rows.append((round(th, 2), round(b[0], 2), b[2], round(b[1], 0)))
        key = f"{'swept' if swept else 'static'}_w{wall}_c{clr}"
        res[key] = rows
        print(key, rows, flush=True)
json.dump(res, open('fit_study2.json', 'w'), indent=0)
