p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:70]
    s = s.replace(old, new, 1)
rep('''LOD_PLANS = [LodPlan(0, 6, 3, 3, 12, 3, 8, True, 12),
             LodPlan(1, 3, 1, 2, 6, 1, 0, False, 10),
             LodPlan(2, 1, 0, 1, 3, 0, 0, False, 6, rib_box=True)]''', '''LOD_PLANS = [LodPlan(0, 6, 3, 3, 12, 3, 8, True, 12),
             LodPlan(1, 2, 1, 1, 6, 1, 0, False, 8),
             LodPlan(2, 1, 0, 1, 3, 0, 0, False, 6, rib_box=True)]''')
rep('''        return np.array([[-butt, -hw0 * 0.6], [-butt + hw0, -hw0], [r_end - 0.8, -hw_top - extra],
                         [r_end, 0.0], [r_end - 0.8, hw_top], [-butt + hw0, hw0], [-butt, hw0 * 0.6]])''',
    '''        return np.array([[-butt + 0.3 * hw0, -hw0], [r_end - 0.5, -hw_top - extra], [r_end - 0.5, hw_top],
                         [-butt + 0.3 * hw0, hw0]])''')
rep('''    poly = _insert_cuts(poly, n_chunks)''', '''    per_full = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
    poly = _insert_cuts(poly, n_chunks)''')
rep('''            clen = per[-1] / n_chunks
            ch = min(n_chunks - 1, int((per[i] + 1e-7) // clen))
            base = ch * clen
            uva, uvb = uv_wall(ch, per[i] - base, za), uv_wall(ch, per[i + 1] - base, za)
            uvc, uvd = uv_wall(ch, per[i + 1] - base, zb), uv_wall(ch, per[i] - base, zb)''', '''            clen = per[-1] / n_chunks
            ch = min(n_chunks - 1, int((per[i] + 1e-7) // clen))
            base = ch * clen
            k = wall_scale
            uva, uvb = uv_wall(ch, k * (per[i] - base), za), uv_wall(ch, k * (per[i + 1] - base), za)
            uvc, uvd = uv_wall(ch, k * (per[i + 1] - base), zb), uv_wall(ch, k * (per[i] - base), zb)''')
rep('''             bone: str, group: str, chamfer: float, uv_top, uv_bot, uv_wall, n_chunks: int = 1, uv_hole=None):''',
    '''             bone: str, group: str, chamfer: float, uv_top, uv_bot, uv_wall, n_chunks: int = 1, uv_hole=None,
             wall_scale: float = 1.0):''')
rep('''        _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                 uv_top, uv_bot, uv_wall, n_chunks=at["chunks"][i], uv_hole=uv_hole)''', '''        nch = at["chunks"][i]
        if lod == 0:
            _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                     uv_top, uv_bot, uv_wall, n_chunks=nch, uv_hole=uv_hole)
        else:
            # coarse LODs: the whole wall squeezed into LOD0's first wall island (no extra cut vertices)
            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)))
            _extrude(mb, poly, hole_r, hole_seg, z0, z1, deg, f"stick_{i:02d}", f"stick_{i:02d}", chamfer,
                     uv_top, uv_bot, uv_wall, n_chunks=1, uv_hole=uv_hole,
                     wall_scale=(at["wall_len"][i] / nch) / per)''')
rep('''        stick_atlas["chunks"] = {i: sum(1 for k in stick_atlas["pos"] if k.startswith(f"s{i}_wall")) for i in outlines}''',
    '''        stick_atlas["chunks"] = {i: sum(1 for k in stick_atlas["pos"] if k.startswith(f"s{i}_wall")) for i in outlines}
        stick_atlas["wall_len"] = {i: float(np.sum(np.linalg.norm(np.diff(np.vstack([outlines[i], outlines[i][:1]]),
                                                                            axis=0), axis=1))) for i in outlines}''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
