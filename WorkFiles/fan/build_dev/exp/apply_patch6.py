p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:70]
    s = s.replace(old, new, 1)
rep('''             bone: str, group: str, chamfer: float, uv_top, uv_bot, uv_wall):
    """Plate between z0 (bottom) and z1 (top) with optional pivot hole and chamfered top/bottom edges."""
    rot = lambda q: _to_fan(np.atleast_2d(q), frame_deg)''', '''             bone: str, group: str, chamfer: float, uv_top, uv_bot, uv_wall, n_chunks: int = 1, uv_hole=None):
    """Plate between z0 (bottom) and z1 (top) with optional pivot hole and chamfered top/bottom edges.
    The wall's UV strip is cut into ``n_chunks`` equal lengths (points are inserted at the cuts), each
    its own island: ``uv_wall(chunk, distance_along_chunk, z)``."""
    rot = lambda q: _to_fan(np.atleast_2d(q), frame_deg)
    poly = _insert_cuts(poly, n_chunks)''')
rep('''            uva, uvb = uv_wall(per[i], za), uv_wall(per[i + 1] if i + 1 <= n else per[-1], za)
            uvc, uvd = uv_wall(per[i + 1], zb), uv_wall(per[i], zb)''', '''            clen = per[-1] / n_chunks
            ch = min(n_chunks - 1, int((per[i] + 1e-7) // clen))
            base = ch * clen
            uva, uvb = uv_wall(ch, per[i] - base, za), uv_wall(ch, per[i + 1] - base, za)
            uvc, uvd = uv_wall(ch, per[i + 1] - base, zb), uv_wall(ch, per[i] - base, zb)''')
rep('''            u0, u1 = uv_wall(per[-1] + 2.0 + i * 0.5, z1), uv_wall(per[-1] + 2.0 + (i + 1) * 0.5, z1)
            u2, u3 = uv_wall(per[-1] + 2.0 + (i + 1) * 0.5, z0), uv_wall(per[-1] + 2.0 + i * 0.5, z0)''', '''            u0, u1 = uv_hole(i * 0.5, z1), uv_hole((i + 1) * 0.5, z1)
            u2, u3 = uv_hole((i + 1) * 0.5, z0), uv_hole(i * 0.5, z0)''')
rep('''def _rot_n(n, deg):''', '''def _insert_cuts(poly: np.ndarray, n_chunks: int) -> np.ndarray:
    if n_chunks <= 1:
        return poly
    seg = np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)
    per = np.concatenate([[0.0], np.cumsum(seg)])
    clen = per[-1] / n_chunks
    out = []
    cuts = [c * clen for c in range(1, n_chunks)]
    for i in range(len(poly)):
        out.append(poly[i])
        a, b = per[i], per[i + 1]
        for c in cuts:
            if a + 1e-6 < c < b - 1e-6:
                u = (c - a) / (b - a)
                out.append(poly[i] + u * (poly[(i + 1) % len(poly)] - poly[i]))
    return np.array(out)


def _rot_n(n, deg):''')
# build_lod: atlas sizes with chunks
rep('''            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
            z0, z1 = spec.stick_z(i)
            sizes.append((f"s{i}_wall", per + 2.0 + 8 * 0.5 + 1.0, (z1 - z0) + 0.2))''', '''            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
            z0, z1 = spec.stick_z(i)
            nch = int(math.ceil(per * 1.06 / WALL_CHUNK_MM))
            for c in range(nch):
                sizes.append((f"s{i}_wall{c}", per * 1.06 / nch + 1.0, (z1 - z0) + 0.2))
            sizes.append((f"s{i}_hole", 8 * 0.5 + 1.0, (z1 - z0) + 0.2))''')
rep('''        stick_atlas["lo"] = {i: outlines[i].min(0) for i in outlines}''', '''        stick_atlas["lo"] = {i: outlines[i].min(0) for i in outlines}
        stick_atlas["chunks"] = {i: sum(1 for k in stick_atlas["pos"] if k.startswith(f"s{i}_wall")) for i in outlines}''')
rep('''        uv_wall = (lambda perim, zz, kw=kwall, z0=z0: to_uv(kw, 0.5 + perim, 0.1 + (zz - z0)))''',
    '''        uv_wall = (lambda ch, perim, zz, i=i, z0=z0: to_uv(f"s{i}_wall{ch}", 0.5 + perim, 0.1 + (zz - z0)))
        uv_hole = (lambda perim, zz, i=i, z0=z0: to_uv(f"s{i}_hole", 0.5 + perim, 0.1 + (zz - z0)))''')
rep('''        _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                 uv_top, uv_bot, uv_wall)''', '''        _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                 uv_top, uv_bot, uv_wall, n_chunks=at["chunks"][i], uv_hole=uv_hole)''')
rep('''LEAF_BACK_OFFSET_MM = 0.02''', '''LEAF_BACK_OFFSET_MM = 0.02
WALL_CHUNK_MM = 120.0''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
