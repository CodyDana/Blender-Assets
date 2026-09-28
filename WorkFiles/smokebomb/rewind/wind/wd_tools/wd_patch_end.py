"""the free end: pushed under ONE late pass (nothing lies between it and the last pass, so
the crossing cannot flip against a third stretch), crossing-local, from a clear point."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py"
s = open(p, encoding="utf-8").read()
a = s.index("def end_tuck(wd, min_tail=30.0):")
b = s.index("def views(wd, tag, names, size=627):")
new = '''def end_tuck(wd, min_tail=30.0, late=4):
    """the free end: along the far-side tail, the first point (>= min_tail deg) where the
    folded cap lies wholly inside the footprint of one of the ``late`` passes laid just
    before the last (the later the better: fewer stretches lie between them, so the
    crossing is clean), with the tail clear of that pass somewhere before it (where the
    weave starts).  Returns (tail length deg, pass name, (cover, weave start deg))."""
    k_last = len(wd.passes) - 1
    tail = np.nonzero((wd.pass_idx == k_last) & ~np.isnan(wd.tail))[0]
    zc = wd.c[tail, 2] + np.sin(0.5 * wd.w_eff()[tail])
    behind = np.nonzero(zc < -0.02)[0]
    if behind.size:
        front = np.nonzero(zc > -0.02)[0]
        front = front[front > behind[0]]
        if front.size:
            tail = tail[:front[0]]
    tl = wd.tail[tail]
    cand = tail[(tl >= min_tail)][::3]
    wsave, gsave = wd.w.copy(), wd.gather.copy()
    wd.gather[cand] = 0.85
    cover = W.end_cap_cover(wd, cand)
    wd.w[:], wd.gather[:] = wsave, gsave
    names = wd.names
    lates = list(range(k_last - 1, max(0, k_last - 1 - late), -1))
    vv = np.linspace(-1, 1, 9)
    for j in lates:
        m = W.footprint_mask(wd, np.nonzero(wd.pass_idx == j)[0], 256)
        for i in cover:
            if j not in cover[i]:
                continue
            q = i
            while q > tail[0] and m[W._cube_index(wd.points(vv, idx=[q])[0], 256)].any():
                q -= 1
            if q > tail[0] + 10:
                return float(wd.tail[i]), names[j], (cover, float(wd.tail[q]))
    return None, None, (cover, None)


'''
s = s[:a] + new + s[b:]
old = '''    if L is not None:
        t_from = _cov[1]
        others = tuple(n for n in wd.names[1:-1])
        tucks = tucks + [W.Weave(wd.names[-1], (t_from, L + 1.0), others, None, lower_where="tail", upper_where="all",
                                 stop_hidden=False,
                                 why="the free end, folded and pushed under the wraps it crosses on the far side (under %s at its tip)" % jn)]'''
new = '''    if L is not None:
        t_from = _cov[1]
        tucks = tucks + [W.Weave(wd.names[-1], (t_from, L + 1.0), jn, None, lower_where="tail", upper_where="all",
                                 stop_hidden=False,
                                 why="the free end: folded and pushed under %s on the far side" % jn)]'''
assert old in s
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
