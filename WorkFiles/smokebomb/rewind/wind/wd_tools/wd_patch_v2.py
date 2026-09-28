"""one-off patch: smokebomb_wind v2 (crossing-local tucks, pass reversal)."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("patch anchor not found:\n" + old[:200])
    s = s.replace(old, new)


# 1. PassSpec.reversed + covers
rep('''    def coords(self, p) -> Tuple[np.ndarray, np.ndarray]:
        """(phi deg, lam rad) of camera-frame unit vectors p in this pass's own frame."""
        e1, e2, n = self.frame()
        p = np.asarray(p, np.float64)
        return (np.degrees(np.arctan2(p @ e2, p @ e1)), np.arcsin(np.clip(p @ n, -1.0, 1.0)))
''', '''    def coords(self, p) -> Tuple[np.ndarray, np.ndarray]:
        """(phi deg, lam rad) of camera-frame unit vectors p in this pass's own frame."""
        e1, e2, n = self.frame()
        p = np.asarray(p, np.float64)
        return (np.degrees(np.arctan2(p @ e2, p @ e1)), np.arcsin(np.clip(p @ n, -1.0, 1.0)))

    def reversed(self) -> "PassSpec":
        """the same tape laid the other way round: n -> -n flips phi and lam, so the spline
        coefficients run backwards and beta changes sign."""
        import dataclasses
        return dataclasses.replace(
            self, n=tuple(float(v) for v in -np.asarray(self.n, float)), phi_a=-self.phi_b, phi_b=-self.phi_a,
            beta=tuple(-v for v in self.beta[::-1]), width=tuple(self.width[::-1]),
            gather=tuple(self.gather[::-1]))

    def covers(self, p) -> np.ndarray:
        """does this pass's front arc cover the unit points p (footprint approximated in the
        pass frame)?"""
        ph, lam = self.coords(p)
        inside = (ph >= self.phi_a) & (ph <= self.phi_b)
        be = self.beta_rad(ph)
        hw = 0.5 * (self.width_rad(ph) * (1 - self.gather_at(ph)) + CORD_W * self.gather_at(ph))
        return inside & (np.abs(lam - be) <= hw)
''')

# 2. Tuck
rep('''@dataclass
class Tuck:
    """A stretch of pass ``pass_name`` (its own phi range, deg; +-inf allowed on the tail)
    threaded UNDER pass ``under``: its key drops to just below that pass's first sample."""
    pass_name: str
    phi_from: float
    phi_to: float
    under: str
    why: str = ""
    #: "front" = the pass's front arc; "tail" = the connector after it (arc length from the
    #: end of the front arc, deg)
    where: str = "front"''', '''@dataclass
class Tuck:
    """A stretch of pass ``pass_name`` threaded UNDER the passes ``under``.  CROSSING-LOCAL:
    only the part of the stretch lying inside their footprint drops below them, so the
    boundary anyone sees is always the covering pass's own edge, never a cut across the
    tape.  The stretch is the pass's own phi range (deg) on its front arc, or arc length
    past the end of the front arc (deg) on the connector after it (where="tail")."""
    pass_name: str
    phi_from: float
    phi_to: float
    under: Tuple[str, ...]
    why: str = ""
    where: str = "front"

    def __post_init__(self):
        if isinstance(self.under, str):
            self.under = (self.under,)
        self.under = tuple(self.under)''')

# 3. Winding fields + effective key
rep('''    key: np.ndarray          # layer order key (s, dropped on a tuck)
    passes: List[PassSpec]
    tucks: List[Tuck]
    notes: Dict[str, object] = field(default_factory=dict)
''', '''    key: np.ndarray          # layer order key (= s: later is on top)
    passes: List[PassSpec]
    tucks: List[Tuck]
    notes: Dict[str, object] = field(default_factory=dict)
    tuck_id: np.ndarray = None           # per sample: index into ``tucks`` (-1 = none)
    tuck_key: np.ndarray = None          # per tuck: the key a tucked point takes
    tuck_mask: List[np.ndarray] = None   # per tuck: cube-map cells the covering passes occupy
    mask_face: int = 512

    def effective_key(self, P: np.ndarray, sid: np.ndarray) -> np.ndarray:
        """key of the tape at points P (lying on samples sid): the sample's key, dropped
        below the covering passes where a tucked sample's point lies inside their footprint."""
        sid = np.asarray(sid)
        k = self.key[sid].copy()
        if self.tuck_id is None or not len(self.tucks):
            return k
        tid = self.tuck_id[sid]
        m = tid >= 0
        if np.any(m):
            cells = _cube_index(np.asarray(P)[m], self.mask_face)
            tm = tid[m]
            ins = np.zeros(tm.size, bool)
            for t in np.unique(tm):
                sel = tm == t
                ins[sel] = self.tuck_mask[t][cells[sel]]
            kk = k[m]
            kk[ins] = self.tuck_key[tm[ins]]
            k[m] = kk
        return k
''')

# 4. apply_tucks with masks
rep('''def apply_tucks(wd: Winding) -> None:
    names = wd.names
    for tk in wd.tucks:
        k = names.index(tk.pass_name)
        ku = names.index(tk.under)
        if tk.where == "tail":
            sel = (wd.pass_idx == k) & ~np.isnan(wd.tail) & (wd.tail >= tk.phi_from) & (wd.tail <= tk.phi_to)
        else:
            sel = (wd.pass_idx == k) & (wd.phi >= tk.phi_from) & (wd.phi <= tk.phi_to)
        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        s_under = wd.s[wd.pass_idx == ku].min()
        # just below the pass it is threaded under, above everything laid before that pass
        wd.key[sel] = s_under - 0.5 * wd.ds''', '''def apply_tucks(wd: Winding) -> None:
    """per tuck: the samples it covers, the key a tucked point takes (just below the
    earliest covering pass: above everything laid before it) and the covering passes'
    footprint as a cube-map cell mask (dilated one cell so the edge itself is covered)."""
    names = wd.names
    N = wd.s.size
    wd.tuck_id = np.full(N, -1, np.int64)
    wd.tuck_key = np.zeros(len(wd.tucks))
    wd.tuck_mask = []
    nf = wd.mask_face
    cell = (math.pi / 2) / nf
    for ti, tk in enumerate(wd.tucks):
        k = names.index(tk.pass_name)
        if tk.where == "tail":
            sel = (wd.pass_idx == k) & ~np.isnan(wd.tail) & (wd.tail >= tk.phi_from) & (wd.tail <= tk.phi_to)
        else:
            sel = (wd.pass_idx == k) & (wd.phi >= tk.phi_from) & (wd.phi <= tk.phi_to)
        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        wd.tuck_id[sel] = ti
        under_idx = [names.index(u) for u in tk.under]
        s_under = min(wd.s[wd.pass_idx == u].min() for u in under_idx)
        wd.tuck_key[ti] = s_under - 0.5 * wd.ds
        mask = np.zeros(6 * nf * nf, bool)
        cov = np.nonzero(np.isin(wd.pass_idx, under_idx))[0]
        for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=cov):
            mask[_cube_index(P, nf)] = True
        wd.tuck_mask.append(_dilate_cells(mask, nf))


def _dilate_cells(mask: np.ndarray, nf: int) -> np.ndarray:
    """grow a cube-map cell mask by one cell (neighbours through the cell centres)."""
    out = mask.copy()
    on = np.nonzero(mask)[0]
    if on.size == 0:
        return out
    P = _cube_centres(nf)[on]
    d = (math.pi / 2) / nf
    ref = np.where(np.abs(P[:, :1]) < 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    a = normalize(np.cross(P, ref))
    b = np.cross(P, a)
    for va in (a, -a, b, -b):
        out[_cube_index(normalize(P + d * va), nf)] = True
    return out''')

# 5. render_labels with effective keys
rep('''    step = 0.6 / R
    order = np.argsort(wd.key, kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(order.size)
    buf = np.full(size * size, -1, np.int64)
    VQ = 1024
    for P, sid, vv in splat_tape(wd, step, facing=d):
        f = P @ d
        m = f > 0
        P, sid, vv = P[m], sid[m], vv[m]
        rad = 1.0 if lift is None else (1.0 + lift[sid])[:, None]
        Q = P * rad
        x = np.floor(cx + R * (Q @ r)).astype(np.int64)
        y = np.floor(cy - R * (Q @ u)).astype(np.int64)
        ok = (x >= 0) & (x < size) & (y >= 0) & (y < size)
        pix = y[ok] * size + x[ok]
        val = rank[sid[ok]] * VQ + np.clip(((vv[ok] + 1) * 0.5 * (VQ - 1)).astype(np.int64), 0, VQ - 1)
        np.maximum.at(buf, pix, val)
    has = buf >= 0
    sample = np.full(size * size, -1, np.int64)
    sample[has] = order[buf[has] // VQ]''', '''    step = 0.6 / R
    # ranks over every key a point can take: the samples' keys, then the tuck keys
    tk = wd.tuck_key if wd.tuck_key is not None else np.zeros(0)
    allk = np.concatenate([wd.key, tk])
    korder = np.argsort(allk, kind="stable")
    krank = np.empty_like(korder)
    krank[korder] = np.arange(korder.size)
    N = wd.key.size
    VQ = 1024
    buf = np.full(size * size, -1, np.int64)
    for P, sid, vv in splat_tape(wd, step, facing=d):
        f = P @ d
        m = f > 0
        P, sid, vv = P[m], sid[m], vv[m]
        rad = 1.0 if lift is None else (1.0 + lift[sid])[:, None]
        Q = P * rad
        x = np.floor(cx + R * (Q @ r)).astype(np.int64)
        y = np.floor(cy - R * (Q @ u)).astype(np.int64)
        ok = (x >= 0) & (x < size) & (y >= 0) & (y < size)
        P, sid, vv, x, y = P[ok], sid[ok], vv[ok], x[ok], y[ok]
        pix = y * size + x
        kr = krank[sid]
        if wd.tuck_id is not None and len(wd.tucks):
            tid = wd.tuck_id[sid]
            m2 = tid >= 0
            if np.any(m2):
                ek = wd.effective_key(P[m2], sid[m2])
                dropped = ek != wd.key[sid[m2]]
                kk = kr[m2]
                kk[dropped] = krank[N + tid[m2][dropped]]
                kr[m2] = kk
        # key rank major, then the sample (so the winner's sample is known), then v
        val = (kr * (N + 1) + sid) * VQ + np.clip(((vv + 1) * 0.5 * (VQ - 1)).astype(np.int64), 0, VQ - 1)
        np.maximum.at(buf, pix, val)
    has = buf >= 0
    sample = np.full(size * size, -1, np.int64)
    sample[has] = (buf[has] // VQ) % (N + 1)''')

open(p, "w", encoding="utf-8").write(s)
print("patched")
