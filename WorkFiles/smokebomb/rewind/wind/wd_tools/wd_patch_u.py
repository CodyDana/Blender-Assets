"""union uppers for weaves (module) + fan/end union weaves (builder)."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor: " + old[:90])
    s = s.replace(old, new)


rep('''    """Where the ``lower`` pass's stretch lies on the ``upper`` pass's stretch, the lower
    lies directly BELOW the upper (crossing-local).  Each stretch is a phi range on the
    pass's front arc (deg), or with *_where="tail" an arc-length range past the end of the
    front arc (deg, the connector after it); ``upper_range=None`` = the whole upper pass."""
    lower: str
    lower_range: Tuple[float, float]
    upper: str''', '''    """Where the ``lower`` pass's stretch lies on the ``upper`` pass's stretch, the lower
    lies directly BELOW the upper (crossing-local).  Each stretch is a phi range on the
    pass's front arc (deg), or with *_where="tail" an arc-length range past the end of the
    front arc (deg, the connector after it).  ``upper`` may be a tuple of passes: the lower
    then lies below whichever of them is lowest at each point (one group - the R strips
    diving under the whole U fan keep their own order while they do)."""
    lower: str
    lower_range: Tuple[float, float]
    upper: object''')
rep('''    #: run the lower stretch on (within its pass) while its section still meets the upper
    #: stretch's footprint, so neither end of it lies under the upper (that would show as a
    #: cut across the tape)
    extend: bool = True
''', '''    #: run the lower stretch on (within its pass) while its section still meets the upper
    #: stretch's footprint, so neither end of it lies under the upper (that would show as a
    #: cut across the tape) ...
    extend: bool = True
    #: ... unless a stretch laid later than the lower hides that end completely
    stop_hidden: bool = True

    def uppers(self) -> Tuple[str, ...]:
        return (self.upper,) if isinstance(self.upper, str) else tuple(self.upper)
''')
rep('''        lo = wd.samples_of(w.lower, w.lower_range, w.lower_where)
        if w.upper_range is None and w.upper_where == "front":
            # by default the upper stretch is the upper pass's FRONT arc (a crossing the
            # viewer sees); its far-side connector is not part of it
            up = wd.passes[wd.names.index(w.upper)]
            hi = wd.samples_of(w.upper, (up.phi_a, up.phi_b), "front")
        else:
            hi = wd.samples_of(w.upper, w.upper_range, w.upper_where)''', '''        lo = wd.samples_of(w.lower, w.lower_range, w.lower_where)
        his = []
        for un in w.uppers():
            if w.upper_range is None and w.upper_where == "front":
                # by default the upper stretch is the upper pass's FRONT arc (a crossing the
                # viewer sees); its far-side connector is not part of it
                up = wd.passes[wd.names.index(un)]
                his.append(wd.samples_of(un, (up.phi_a, up.phi_b), "front"))
            else:
                his.append(wd.samples_of(un, w.upper_range, w.upper_where))
        hi = np.unique(np.concatenate(his)) if his else np.zeros(0, np.int64)''')
rep('''            key = (w.upper, None if w.upper_range is None else tuple(w.upper_range), w.upper_where)''',
    '''            key = (w.uppers(), None if w.upper_range is None else tuple(w.upper_range), w.upper_where)''')
rep('''                P = wd.points(v, idx=[q])[0]
                inside = fp[_cube_index(P, nf)]
                if not inside.any():
                    return False
                ci = _cube_index(P[inside], grid.n_face)''', '''                P = wd.points(v, idx=[q])[0]
                inside = fp[_cube_index(P, nf)]
                if not inside.any():
                    return False
                if not w.stop_hidden:
                    return True
                ci = _cube_index(P[inside], grid.n_face)''')
rep('''        wd.weave_lo[i] = (a, b)
        wd.weave_hi[i] = (hi_idx[i][0], hi_idx[i][-1])''', '''        wd.weave_lo[i] = (a, b)
        wd.weave_hi[i] = (hi_idx[i][0], hi_idx[i][-1]) if len(hi_idx[i]) else (0, -1)''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py"
s = open(p, encoding="utf-8").read()
rep('''    res = []
    for (nm, u), rs in pairs.items():''', '''    res = []
    fan = {}
    for (nm, u), rs in list(pairs.items()):
        if nm in ("R2", "R3", "Rin") and u in FAN:
            fan.setdefault(nm, []).extend(rs)
            del pairs[(nm, u)]
    for nm, rs in fan.items():
        a = min(r[0] for r in rs)
        b = max(r[1] for r in rs)
        res.append(W.Weave(nm, (a, b), tuple(sorted(FAN)), None, upper_where="all", stop_hidden=False,
                           why="the pinwheel: the R strips dive under the U fan at the whorl, as one group"))
    for (nm, u), rs in pairs.items():''')
rep('''    for w in weaves:
        idx = wd0.samples_of(w.lower, w.lower_range, w.lower_where)
        if idx.size == 0:
            continue''', '''    for w in weaves:
        if not isinstance(w.upper, str):
            out.append(w)
            continue
        idx = wd0.samples_of(w.lower, w.lower_range, w.lower_where)
        if idx.size == 0:
            continue''')
rep('''            out.append(W.Weave(w.lower, rng, w.upper, w.upper_range, w.lower_where, w.upper_where, w.why))''',
    '''            out.append(W.Weave(w.lower, rng, w.upper, w.upper_range, w.lower_where, w.upper_where, w.why,
                               w.extend, w.stop_hidden))''')
rep('''    if L is not None:
        t_from = _cov[1]
        tucks = tucks + [W.Weave(wd.names[-1], (t_from, L + 1.0), jn, None, lower_where="tail", upper_where="all",
                                 why="the free end, folded and pushed under a wrap on the far side")]''', '''    if L is not None:
        t_from = _cov[1]
        others = tuple(n for n in wd.names[1:-1])
        tucks = tucks + [W.Weave(wd.names[-1], (t_from, L + 1.0), others, None, lower_where="tail", upper_where="all",
                                 stop_hidden=False,
                                 why="the free end, folded and pushed under the wraps it crosses on the far side (under %s at its tip)" % jn)]''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
