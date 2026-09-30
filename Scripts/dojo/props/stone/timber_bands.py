"""Kit-side helper for the shared dojo timber (r2, stone + modern prop groups): keep every member's V offset inside
the library texture's MID-TONE bands.

The library timber tiles carry a large-scale tone band across the grain (V; the README notes it repeats every 4 m)
and grain_uv gives each member a random V offset, so on a small prop one board can land in the darkest band and its
neighbour in the lightest: the r2 well roof read near-black next to orange. This measures the band profile of the
set's BC map (row luminance, smoothed over 12 cm) and moves each member's side-grain V so the member's centre sits
on the nearest row within +-tol of the median tone. U (the grain) and the end-grain faces are untouched; the texture
and the library are untouched. Blender-side (bpy, bmesh, numpy)."""
import bmesh
import bpy
import numpy as np

_PROFILES = {}


def band_profile(set_name, smooth_m=0.12):
    if set_name in _PROFILES:
        return _PROFILES[set_name]
    img = next(i for i in bpy.data.images if i.name.startswith(f"T_DJ_{set_name}_BC"))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]
    lum = (0.2126 * px[..., 0] + 0.7152 * px[..., 1] + 0.0722 * px[..., 2]).mean(1)       # per row (V)
    import dojo_tex_gen as tg
    tile_v = tg.SETS[set_name]["tile_m"][1]
    k = max(1, int(round(smooth_m / tile_v * h)))
    ker = np.ones(k) / k
    sm = np.convolve(np.concatenate([lum[-k:], lum, lum[:k]]), ker, mode="same")[k:-k]
    _PROFILES[set_name] = sm
    return sm


def calm_bands(obj, mat_name, set_name, tol=0.12, uv_map="UV0"):
    """Shift each island's V (faces of slot mat_name) onto a mid-tone row. Returns (islands, mean |shift|)."""
    prof = band_profile(set_name)
    h = len(prof)
    med = float(np.median(prof))
    good = np.where(np.abs(prof - med) <= tol * med)[0] / h
    me = obj.data
    mi = [m.name for m in me.materials].index(mat_name)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    lay = bm.loops.layers.uv[uv_map]
    faces = [f for f in bm.faces if f.material_index == mi]
    fset = {f.index for f in faces}
    seen, n, shifts = set(), 0, []
    for f0 in faces:
        if f0.index in seen:
            continue
        st, isl = [f0], []
        seen.add(f0.index)
        while st:
            f = st.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index in fset and g.index not in seen:
                        seen.add(g.index)
                        st.append(g)
        vs = [lp[lay].uv.y for f in isl for lp in f.loops]
        vc = (min(vs) + max(vs)) / 2
        frac = vc % 1.0
        d = good - frac
        d = (d + 0.5) % 1.0 - 0.5
        dv = float(d[np.argmin(np.abs(d))]) if len(d) else 0.0
        for f in isl:
            for lp in f.loops:
                lp[lay].uv.y += dv
        shifts.append(abs(dv))
        n += 1
    bm.to_mesh(me)
    bm.free()
    return n, (sum(shifts) / len(shifts) if shifts else 0.0), round(len(good) / h, 3)
