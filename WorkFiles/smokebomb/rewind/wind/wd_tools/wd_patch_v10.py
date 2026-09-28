"""tucks v3: plain per-sample key drops whose ends are placed where the switch is invisible."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:120])
    s = s.replace(old, new)


def cut_between(start_anchor, end_anchor, new):
    global s
    a = s.index(start_anchor)
    b = s.index(end_anchor, a)
    s = s[:a] + new + s[b:]


# Tuck docstring
rep('''    """A stretch of pass ``pass_name`` threaded UNDER the passes ``under``.  CROSSING-LOCAL:
    only the part of the stretch lying inside their footprint drops below them, so the
    boundary anyone sees is always the covering pass's own edge, never a cut across the
    tape.  The stretch is the pass's own phi range (deg) on its front arc, or arc length
    past the end of the front arc (deg) on the connector after it (where="tail")."""''', '''    """A stretch of pass ``pass_name`` threaded UNDER the passes ``under`` (the winder
    pushed the tape beneath them): over the stretch the tape's key drops to just below the
    earliest of them, keeping its order against every other tucked stretch.  The stretch
    given (its own phi range on the front arc, deg, or arc length past the end of the front
    arc, deg, where="tail") is run on at both ends until the change of key is INVISIBLE -
    no other stretch there lies between the two keys - so no one ever sees the tape change
    layer except at a covering pass's own edge."""''')

# Winding fields
rep('''    tuck_id: np.ndarray = None           # per sample: 1 if any tuck covers it (fast skip), else -1
    tuck_key: np.ndarray = None          # per tuck: the key a tucked point takes
    tuck_mask: List[np.ndarray] = None   # per tuck: cube-map cells the covering pass occupies
    tuck_range: np.ndarray = None        # per tuck: [first, last] sample it covers (after extension)
    mask_face: int = 512
''', '''    base_key: np.ndarray = None          # the key before any tuck (= s)
    tuck_range: np.ndarray = None        # per tuck: [first, last] sample after the run-on
    tuck_key: np.ndarray = None          # per tuck: the key its samples took
''')
cut_between('''    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:''', '''    @property
    def ds(self) -> float:''', '''    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:
        """the key at points on samples ``sid`` (tucks are per sample: the points do not matter)."""
        return self.key[np.asarray(sid)]

''')

# StackGrid: keep sample identity; build from wd.key
rep('''        cells_all, sid_all, ek_all = [], [], []
        for P, sid, _v in splat_tape(wd, step):
            cells_all.append(_cube_index(P, n_face))
            sid_all.append(sid)
            ek_all.append(wd.effective_key(P, sid))
        cells = np.concatenate(cells_all)
        sid = np.concatenate(sid_all)
        ek = np.concatenate(ek_all)
        # one entry per (cell, sample): the lowest effective key a point of it takes there
        o = np.lexsort((ek, sid, cells))
        cells, sid, ek = cells[o], sid[o], ek[o]
        first = np.ones(len(cells), bool)
        first[1:] = (cells[1:] != cells[:-1]) | (sid[1:] != sid[:-1])
        pair = np.stack([cells[first], sid[first]], 1)
        pek = ek[first]''', '''        cells_all, sid_all = [], []
        for P, sid, _v in splat_tape(wd, step):
            cells_all.append(_cube_index(P, n_face))
            sid_all.append(sid)
        cells = np.concatenate(cells_all)
        sid = np.concatenate(sid_all)
        pair = np.unique(np.stack([cells, sid], 1), axis=0)
        pek = wd.key[pair[:, 1]]''')
rep('''        K = np.full((ncell, M), np.inf)
        K[run_cell, rank] = run_key
        top = np.full(ncell, -1, np.int64)
        last = start[1:] - 1
        has = cnt > 0
        top[has] = run_sample[last[has]]
        return StackGrid(n_face, K, cnt, top)''', '''        K = np.full((ncell, M), np.inf)
        K[run_cell, rank] = run_key
        S = np.full((ncell, M), -1, np.int64)
        S[run_cell, rank] = run_sample
        top = np.full(ncell, -1, np.int64)
        last = start[1:] - 1
        has = cnt > 0
        top[has] = run_sample[last[has]]
        g = StackGrid(n_face, K, cnt, top)
        g.samples = S
        g.run_len = max(3, int(3 * cell / ds) + 2)
        return g''')
rep('''    n_face: int
    keys: np.ndarray        # (cells, M) float64 sorted ascending, +inf padded
    count: np.ndarray       # (cells,) int
    top_sample: np.ndarray  # (cells,) sample index of the top stretch (-1 = bare)
''', '''    n_face: int
    keys: np.ndarray        # (cells, M) float64 sorted ascending, +inf padded
    count: np.ndarray       # (cells,) int
    top_sample: np.ndarray  # (cells,) sample index of the top stretch (-1 = bare)
    samples: np.ndarray = None   # (cells, M) a sample of each stretch (-1 padded)
    run_len: int = 3
''')

# apply_tucks: per-sample drops with invisible ends
cut_between('''def apply_tucks(wd: Winding) -> None:''', '''def _dilate_cells(mask: np.ndarray, nf: int) -> np.ndarray:''', '''def apply_tucks(wd: Winding, rounds: int = 2, n_face: int = 256) -> None:
    """Every tuck: the samples of its stretch take the key just below the earliest pass it
    goes under (plus 1e-9 x their own key, so tucked stretches keep their order among
    themselves).  Each end of the stretch is then run on, sample by sample, until the change
    of key there is invisible: at every point of the tape's section no OTHER stretch has a
    key strictly between the old key and the new one (the same stretch is on top of that
    point before and after).  Two rounds, because one tuck's keys change what another's
    ends can see."""
    names = wd.names
    N = wd.s.size
    if wd.base_key is None:
        wd.base_key = wd.s.copy()
    wd.key = wd.base_key.copy()
    if not wd.tucks:
        wd.tuck_range = np.zeros((0, 2), np.int64)
        wd.tuck_key = np.zeros(0)
        return
    v = np.linspace(-1.0, 1.0, 11)
    init = []
    for tk in wd.tucks:
        k = names.index(tk.pass_name)
        if tk.where == "tail":
            sel = (wd.pass_idx == k) & ~np.isnan(wd.tail) & (wd.tail >= tk.phi_from) & (wd.tail <= tk.phi_to)
        else:
            sel = (wd.pass_idx == k) & (wd.phi >= tk.phi_from) & (wd.phi <= tk.phi_to)
        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        idx = np.nonzero(sel)[0]
        own = np.nonzero(wd.pass_idx == k)[0]
        s_under = min(wd.s[wd.pass_idx == names.index(u)].min() for u in tk.under)
        init.append((int(idx[0]), int(idx[-1]), int(own[0]), int(own[-1]), s_under - 0.5 * wd.ds))
    ranges = [(a, b) for a, b, _, _, _ in init]
    for rnd in range(rounds):
        g = StackGrid.build(wd, n_face=n_face)
        self_win = 3 * g.run_len
        new_ranges = []
        for ti, (a, b, lo, hi, kt) in enumerate(init):
            k_new = kt + 1e-9 * wd.base_key[a]

            def visible_switch(i, k_old):
                """would changing sample i's key from k_old to k_new show?"""
                c = _cube_index(wd.points(v, idx=[i])[0], n_face)
                K = g.keys[c]
                Sm = g.samples[c]
                other = (Sm >= 0) & (np.abs(Sm - i) > self_win)
                lo_k, hi_k = min(k_old, k_new), max(k_old, k_new)
                between = other & (K > lo_k) & (K < hi_k)
                return bool(between.any())
            i0, i1 = a, b
            while i0 > lo and visible_switch(i0 - 1, wd.base_key[i0 - 1]):
                i0 -= 1
            while i1 < hi and visible_switch(i1 + 1, wd.base_key[i1 + 1]):
                i1 += 1
            new_ranges.append((i0, i1))
        # apply (later tucks never lift a sample above an earlier drop)
        wd.key = wd.base_key.copy()
        for (i0, i1), (_, _, _, _, kt) in zip(new_ranges, init):
            kk = kt + 1e-9 * wd.base_key[i0:i1 + 1]
            wd.key[i0:i1 + 1] = np.minimum(wd.key[i0:i1 + 1], kk)
        ranges = new_ranges
    wd.tuck_range = np.array(ranges, np.int64).reshape(-1, 2)
    wd.tuck_key = np.array([kt for _, _, _, _, kt in init])
    wd.notes["tuck_ranges"] = [dict(pass_name=t.pass_name, under=list(t.under), samples=[int(a), int(b)],
                                    phi=[float(wd.phi[a]), float(wd.phi[b])], tail=[float(wd.tail[a]), float(wd.tail[b])])
                               for t, (a, b) in zip(wd.tucks, ranges)]


''')

# render: plain keys
rep('''        kr = krank[sid]
        if wd.tuck_id is not None and wd.tuck_range is not None and len(wd.tuck_range):
            m2 = wd.tuck_id[sid] >= 0
            if np.any(m2):
                ek = wd.effective_key(P[m2], sid[m2])
                dropped = ek != wd.key[sid[m2]]
                if np.any(dropped):
                    # the dropped keys are tuck keys: their rank among all keys
                    tpos = np.searchsorted(tk_sorted, ek[dropped])
                    kk = kr[m2]
                    kk[dropped] = krank[N + tk_order[tpos]]
                    kr[m2] = kk''', '''        kr = krank[sid]''')
rep('''    # ranks over every key a point can take: the samples' keys, then the tuck keys
    tk = wd.tuck_key if wd.tuck_key is not None else np.zeros(0)
    allk = np.concatenate([wd.key, tk])
    korder = np.argsort(allk, kind="stable")
    krank = np.empty_like(korder)
    krank[korder] = np.arange(korder.size)
    N = wd.key.size
    tk_order = np.argsort(tk, kind="stable")
    tk_sorted = tk[tk_order]''', '''    korder = np.argsort(wd.key, kind="stable")
    krank = np.empty_like(korder)
    krank[korder] = np.arange(korder.size)
    N = wd.key.size''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
