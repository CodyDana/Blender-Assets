import re
def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for old, new in pairs:
        if old not in s:
            raise SystemExit(p + " anchor not found: " + old[:100])
        s = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s)
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/"
patch(D + "wd_passes.py", [('''    ("R2", (648, 238), "after", "@first:U0,U1,U2,U3,U4,U5"),
    ("R3", (640, 192), "before", "@first:U0,U1,U2,U3,U4,U5"),
    ("Rin", (598, 302), "before", "@first:U0,U1,U2,U3,U4,U5"),''', '''    ("R2", (648, 238), "after", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),
    ("R3", (640, 192), "before", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),
    ("Rin", (598, 302), "before", "@all:U0,U1,U2,U3,U4,U5,B,X,W,A"),''')])
patch(D + "wd_run.py", [
('''    for pn, px, side, under in tucks:
        if under.startswith("@first:"):
            cand = under[7:].split(",")
            under = min(cand, key=lambda n: order.index(n))
        k = names.index(pn)''', '''    for pn, px, side, under in tucks:
        if under.startswith("@all:"):
            under = tuple(under[5:].split(","))
        elif under.startswith("@first:"):
            cand = under[7:].split(",")
            under = (min(cand, key=lambda n: order.index(n)),)
        else:
            under = (under,)
        k = names.index(pn)'''),
('''        for (ti, p0, p1, under) in truns:
            if ti == k:
                ui = [p.name for p in passes].index(under)
                ub = ui if order_keys is None else order_keys[ui]
                m = (phi >= p0) & (phi <= p1)
                kk[m] = (ub - 0.5) * 1000.0 + np.arange(m.sum()) * 1e-6''', '''        for (ti, p0, p1, under) in truns:
            if ti == k:
                nms = [p.name for p in passes]
                ub = min((nms.index(u) if order_keys is None else order_keys[nms.index(u)]) for u in under)
                m = (phi >= p0) & (phi <= p1)
                kk[m] = (ub - 0.5) * 1000.0 + np.arange(m.sum()) * 1e-6'''),
('''                for (ti, p0, p1, under) in truns:
                    if ti == i:
                        m = cv & (ph >= p0) & (ph <= p1)
                        if m.any() and under != j:
                            cons[(under, j)] = cons.get((under, j), 0) + int(m.sum())
                        tk |= m''', '''                for (ti, p0, p1, under) in truns:
                    if ti == i:
                        m = cv & (ph >= p0) & (ph <= p1)
                        tk |= m'''),
('''            key_ok = np.zeros(len(ph), bool)
            for (ti, p0, p1, under) in truns:
                if ti == i:
                    key_ok |= (ph >= p0) & (ph <= p1) & (pos[under] <= pos[j])''', '''            key_ok = np.zeros(len(ph), bool)
            for (ti, p0, p1, under) in truns:
                if ti == i:
                    key_ok |= (ph >= p0) & (ph <= p1) & (j in under)'''),
('''        for f0, f1, js in runs:
            under = min(js, key=lambda n: pos[n])
            a, b = f0 - margin, f1 + margin''', '''        for f0, f1, js in runs:
            under = tuple(sorted(js, key=lambda n: pos[n]))
            a, b = f0 - margin, f1 + margin'''),
])
patch(D + "wd_build.py", [
('''        out.append(W.Tuck(nm, float(a), float(b), (under,), why="woven crossing"))''', '''        out.append(W.Tuck(nm, float(a), float(b), tuple(under), why="woven crossing"))'''),
])
print("ok")
