p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor not found: " + old[:120])
    s = s.replace(old, new)


rep('''        mask = _dilate_cells(mask, nf)
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
        wd.tuck_mask.append(mask)''', '''        mask = _dilate_cells(mask, nf)
        # run the stretch on, both ways, while its section still lies inside the covering
        # footprint - the key may only change where the tape is clear of it (so the only
        # boundary anyone sees is the covering pass's own edge) or where a pass laid LATER
        # than this one hides the change completely
        later = later_masks.get(k)
        if later is None:
            later = np.zeros(6 * nf * nf, bool)
            li = np.nonzero(wd.pass_idx > k)[0]
            for P, sid, _v in splat_tape(wd, 0.45 * cell, idx=li):
                later[_cube_index(P, nf)] = True
            later_masks[k] = later
        own = np.nonzero(wd.pass_idx == k)[0]
        lo, hi = int(own[0]), int(own[-1])
        idx = np.nonzero(sel)[0]
        i0, i1 = int(idx[0]), int(idx[-1])
        v = np.linspace(-1.0, 1.0, 9)

        def needs_more(i):
            c = _cube_index(wd.points(v, idx=[i])[0], nf)
            return bool(mask[c].any()) and not bool(later[c].all())
        while i0 > lo and wd.tuck_id[i0 - 1] < 0 and needs_more(i0 - 1):
            i0 -= 1
        while i1 < hi and wd.tuck_id[i1 + 1] < 0 and needs_more(i1 + 1):
            i1 += 1
        seg = slice(i0, i1 + 1)
        wd.tuck_id[seg] = np.where(wd.tuck_id[seg] < 0, ti, wd.tuck_id[seg])
        wd.tuck_mask.append(mask)''')
rep('''    wd.tuck_mask = []
    nf = wd.mask_face
    cell = (math.pi / 2) / nf
    for ti, tk in enumerate(wd.tucks):''', '''    wd.tuck_mask = []
    nf = wd.mask_face
    cell = (math.pi / 2) / nf
    later_masks = {}
    for ti, tk in enumerate(wd.tucks):''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''        js = [j for j in js if names[j] != "core" or True]''', '''        js = [j for j in js if wd.passes[j].role != "core"]''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
