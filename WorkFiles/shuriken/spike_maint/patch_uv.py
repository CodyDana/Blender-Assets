from pathlib import Path
p = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib\uv.py")
s = p.read_text(encoding="utf-8")
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)
rep('''    return {
        "method": "LOD0 island affine maps (Smart UV planar projection + pack transform, fitted by least squares)",''',
'''    # 3.8.1 (spike geometry review): how far every final loop UV sits from the affine map of the LOD0 island its
    # face was matched to - the clamps above and the unit-square clamp are the only things that move a loop off
    # it, so this is the true per-loop figure (the cross_lod_uv gate samples centroids and top-plate points only)
    exact = np.empty_like(uv)
    for f, (s, t) in enumerate(zip(mt["start"], mt["total"])):
        loops = np.arange(s, s + t)
        P = np.column_stack([mt["co"][mt["loop_vert"][loops]], np.ones(t)])
        exact[loops] = P @ islands["maps"][face_island[f]]
    dev = np.linalg.norm(uv - exact, axis=1)
    worst = int(np.argmax(dev)) if len(dev) else 0
    island_map_deviation = {
        "max_uv": float(f"{float(dev.max()) if len(dev) else 0.0:.3e}"),
        "max_px_at_2048": round(float(dev.max()) * 2048.0, 4) if len(dev) else 0.0,
        "loops_over_0_01_px_at_2048": int(np.count_nonzero(dev * 2048.0 > 0.01)),
        "worst_loop_uv": [round(float(v), 6) for v in uv[worst]] if len(dev) else None,
        "metric": ("per loop: |final UV - the affine map of the LOD0 island its face was matched to| (UV units; px "
                   "at 2048 along u)"),
    }
    return {
        "method": "LOD0 island affine maps (Smart UV planar projection + pack transform, fitted by least squares)",
        "island_map_deviation": island_map_deviation,''')
p.write_text(s, encoding="utf-8")
print("patched uv.py")
