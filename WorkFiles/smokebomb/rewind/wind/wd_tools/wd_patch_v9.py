"""multi-tuck: one crossing-local tuck per (stretch, covering pass); effective key = min."""
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


rep('''    tuck_id: np.ndarray = None           # per sample: index into ``tucks`` (-1 = none)
    tuck_key: np.ndarray = None          # per tuck: the key a tucked point takes
    tuck_mask: List[np.ndarray] = None   # per tuck: cube-map cells the covering passes occupy
    mask_face: int = 512
''', '''    tuck_id: np.ndarray = None           # per sample: 1 if any tuck covers it (fast skip), else -1
    tuck_key: np.ndarray = None          # per tuck: the key a tucked point takes
    tuck_mask: List[np.ndarray] = None   # per tuck: cube-map cells the covering pass occupies
    tuck_range: np.ndarray = None        # per tuck: [first, last] sample it covers (after extension)
    mask_face: int = 512
''')

cut_between('''    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:''', '''    @property
    def ds(self) -> float:''', '''    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:
        """key of the tape at points P (lying on samples sid): the sample's key, dropped to
        a tuck's key where the sample lies in that tuck's stretch AND the point lies inside
        its covering pass's footprint (the lowest such key wins)."""
        sid = np.asarray(sid)
        k = self.key[sid].copy()
        if self.tuck_range is None or not len(self.tuck_range):
            return k
        cells = None
        for t in range(len(self.tuck_range)):
            i0, i1 = self.tuck_range[t]
            m = (sid >= i0) & (sid <= i1)
            if not np.any(m):
                continue
            if cells is None:
                cells = _cube_index(np.asarray(P), self.mask_face)
            ins = m.copy()
            ins[m] = self.tuck_mask[t][cells[m]]
            k[ins] = np.minimum(k[ins], self.tuck_key[t])
        return k

''')

cut_between('''def apply_tucks(wd: Winding) -> None:''', '''def _dilate_cells(mask: np.ndarray, nf: int) -> np.ndarray:''', '''def apply_tucks(wd: Winding) -> None:
    """Expand every Tuck into one crossing-local tuck PER covering pass.  For each: the key a
    tucked point takes (just below that pass's first sample: above everything laid before
    it), the pass's footprint as a cube-map cell mask (dilated one cell so its edge itself is
    covered), and the stretch - run on both ways while the tape's section still lies inside
    that footprint and is not hidden by a pass laid later than the tape, so the key only
    ever changes where no one can see it (the covering pass's own edge, or under a later
    pass)."""
    names = wd.names
    N = wd.s.size
    nf = wd.mask_face
    cell = (math.pi / 2) / nf
    keys, masks, ranges, origin = [], [], [], []
    fp_cache, later_cache = {}, {}

    def footprint(j):
        if j not in fp_cache:
            m = np.zeros(6 * nf * nf, bool)
            for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=np.nonzero(wd.pass_idx == j)[0]):
                m[_cube_index(P, nf)] = True
            fp_cache[j] = _dilate_cells(m, nf)
        return fp_cache[j]

    def later(k):
        if k not in later_cache:
            m = np.zeros(6 * nf * nf, bool)
            for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=np.nonzero(wd.pass_idx > k)[0]):
                m[_cube_index(P, nf)] = True
            later_cache[k] = m
        return later_cache[k]

    v = np.linspace(-1.0, 1.0, 9)
    for ti, tk in enumerate(wd.tucks):
        k = names.index(tk.pass_name)
        if tk.where == "tail":
            sel = (wd.pass_idx == k) & ~np.isnan(wd.tail) & (wd.tail >= tk.phi_from) & (wd.tail <= tk.phi_to)
        else:
            sel = (wd.pass_idx == k) & (wd.phi >= tk.phi_from) & (wd.phi <= tk.phi_to)
        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        idx = np.nonzero(sel)[0]
        own = np.nonzero(wd.pass_idx == k)[0]
        lo, hi = int(own[0]), int(own[-1])
        lat = later(k)
        for u in tk.under:
            j = names.index(u)
            mask = footprint(j)
            # does the stretch meet this pass at all?
            c_all = _cube_index(wd.points(v, idx=idx).reshape(-1, 3), nf).reshape(len(idx), -1)
            hit = mask[c_all].any(1)
            if not hit.any():
                continue
            i0, i1 = int(idx[hit][0]), int(idx[hit][-1])

            def needs_more(i):
                c = _cube_index(wd.points(v, idx=[i])[0], nf)
                inside = mask[c]
                return bool(inside.any()) and not bool(lat[c][inside].all())
            while i0 > lo and needs_more(i0 - 1):
                i0 -= 1
            while i1 < hi and needs_more(i1 + 1):
                i1 += 1
            s_under = wd.s[wd.pass_idx == j].min()
            keys.append(s_under - 0.5 * wd.ds)
            masks.append(mask)
            ranges.append((i0, i1))
            origin.append((ti, u))
    wd.tuck_key = np.array(keys, float)
    wd.tuck_mask = masks
    wd.tuck_range = np.array(ranges, np.int64).reshape(-1, 2)
    wd.tuck_id = np.full(N, -1, np.int64)
    for i0, i1 in wd.tuck_range:
        wd.tuck_id[i0:i1 + 1] = 1
    wd.notes["tuck_origin"] = origin


''')

# render: effective keys -> ranks
rep('''        kr = krank[sid]
        if wd.tuck_id is not None and len(wd.tucks):
            tid = wd.tuck_id[sid]
            m2 = tid >= 0
            if np.any(m2):
                ek = wd.effective_key(P[m2], sid[m2])
                dropped = ek != wd.key[sid[m2]]
                kk = kr[m2]
                kk[dropped] = krank[N + tid[m2][dropped]]
                kr[m2] = kk''', '''        kr = krank[sid]
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
                    kr[m2] = kk''')
rep('''    korder = np.argsort(allk, kind="stable")
    krank = np.empty_like(korder)
    krank[korder] = np.arange(korder.size)
    N = wd.key.size''', '''    korder = np.argsort(allk, kind="stable")
    krank = np.empty_like(korder)
    krank[korder] = np.arange(korder.size)
    N = wd.key.size
    tk_order = np.argsort(tk, kind="stable")
    tk_sorted = tk[tk_order]''')

# StackGrid: effective keys for the stretch keys
rep('''        cells_all, sid_all = [], []
        for P, sid, _v in splat_tape(wd, step):
            cells_all.append(_cube_index(P, n_face))
            sid_all.append(sid)
        cells = np.concatenate(cells_all)
        sid = np.concatenate(sid_all)
        pair = np.unique(np.stack([cells, sid], 1), axis=0)     # sorted by cell, then sample''', '''        cells_all, sid_all, ek_all = [], [], []
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
        pek = ek[first]''')
rep('''        run_id = np.cumsum(newrun) - 1
        kk = wd.key[pair[:, 1]]''', '''        run_id = np.cumsum(newrun) - 1
        kk = pek''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
