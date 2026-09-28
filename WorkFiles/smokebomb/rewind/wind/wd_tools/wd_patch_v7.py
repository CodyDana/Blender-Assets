p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:120])
    s = s.replace(old, new)


rep('''        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        wd.tuck_id[sel] = ti
        under_idx = [names.index(u) for u in tk.under]
        s_under = min(wd.s[wd.pass_idx == u].min() for u in under_idx)
        wd.tuck_key[ti] = s_under - 0.5 * wd.ds
        mask = np.zeros(6 * nf * nf, bool)
        cov = np.nonzero(np.isin(wd.pass_idx, under_idx))[0]
        for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=cov):
            mask[_cube_index(P, nf)] = True
        wd.tuck_mask.append(_dilate_cells(mask, nf))''', '''        if not np.any(sel):
            raise ValueError(f"tuck {tk} selects no samples")
        under_idx = [names.index(u) for u in tk.under]
        s_under = min(wd.s[wd.pass_idx == u].min() for u in under_idx)
        wd.tuck_key[ti] = s_under - 0.5 * wd.ds
        mask = np.zeros(6 * nf * nf, bool)
        cov = np.nonzero(np.isin(wd.pass_idx, under_idx))[0]
        for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=cov):
            mask[_cube_index(P, nf)] = True
        mask = _dilate_cells(mask, nf)
        # run the stretch on, both ways, while any of its section still lies inside the
        # covering footprint: the key may only change where the tape is clear of it, so
        # the only boundary anyone can see is the covering pass's own edge
        idx = np.nonzero(sel)[0]
        i0, i1 = int(idx[0]), int(idx[-1])
        v = np.linspace(-1.0, 1.0, 9)
        lim = N - 1 if tk.where == "tail" else N - 1

        def inside(i):
            return bool(mask[_cube_index(wd.points(v, idx=[i])[0], nf)].any())
        while i0 > 0 and wd.tuck_id[i0 - 1] < 0 and inside(i0 - 1):
            i0 -= 1
        while i1 < lim and wd.tuck_id[i1 + 1] < 0 and inside(i1 + 1):
            i1 += 1
        wd.tuck_id[i0:i1 + 1] = np.where(wd.tuck_id[i0:i1 + 1] < 0, ti, wd.tuck_id[i0:i1 + 1])
        wd.tuck_mask.append(mask)''')

rep('''def coverage(wd: "Winding", n_face: int = 128) -> Dict[str, object]:''', '''def end_cap_cover(wd: "Winding", tail_idx: np.ndarray, n_face: int = 512):
    """for each candidate end sample on the tail: the passes whose footprint holds the whole
    cap (the tape's section there) - the free end can be tucked under any of them."""
    out = {}
    v = np.linspace(-1.0, 1.0, 11)
    masks = {}
    cell = (math.pi / 2) / n_face
    for j in range(len(wd.passes) - 1):
        m = np.zeros(6 * n_face * n_face, bool)
        for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=np.nonzero(wd.pass_idx == j)[0]):
            m[_cube_index(P, n_face)] = True
        masks[j] = m
    for i in tail_idx:
        cells = _cube_index(wd.points(v, idx=[i])[0], n_face)
        out[int(i)] = [j for j, m in masks.items() if m[cells].all()]
    return out


def coverage(wd: "Winding", n_face: int = 128) -> Dict[str, object]:''')
rep('''"core_axes", "core_path", "coverage",''', '''"core_axes", "core_path", "coverage", "end_cap_cover",''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
