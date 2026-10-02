"""Iteration-7 patch: KEEP THE SUNSET LIGHT ON THE SAND. The it6 measure showed CAM_Ref2Match falling from mean luma
111 to 79 (under-40 11.6 % -> 25.8 %): the owner's 9.08 deg west sun was blocked by the plan's west ridge (+18 m at
x -80 needs <= 12.6 m) and the FZ2 firs on it. The ridge is lowered under the sun line (slope <= 0.1) and every forest
/ billboard instance whose top would cut the sun ray to the courtyard sand is dropped (a sun-corridor keep-out).
Idempotent."""
from pathlib import Path

D = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\landscape")


def patch(name, pairs):
    p = D / name
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s:
            continue
        assert s.count(old) == 1, (name, old[:90])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


patch("make_terrain.py", [(
    '''    ridge = np.where(X < -7.0, G.interp(-X, [7, 30, 80, 200, 500, 1500, 4000], [0, 4, 18, 40, 70, 120, 220]), -1e3)''',
    '''    # it7: the west ridge stays under the owner's 9.08 deg sun line to the courtyard (tan 9.08 = 0.16; the plan's +18 m
    # at x -80 shaded the sand): slope <= 0.1 near, the same skyline farther out
    ridge = np.where(X < -7.0, G.interp(-X, [7, 30, 80, 200, 500, 1500, 4000], [0, 1.5, 5, 15, 42, 110, 220]), -1e3)''')])

patch("make_world_layout.py", [
    ('''def keepout(X, Y, extra_slots=2.0):''',
     '''SUN_EL = math.radians(9.08)
SUN_H = np.array([math.cos(math.radians(187.29)), math.sin(math.radians(187.29))])   # toward the sun (Blender az)
_SX, _SY = np.meshgrid(np.arange(2.0, 43.0, 3.0), np.arange(1.0, 21.0, 3.0))
SAND = np.c_[_SX.ravel(), _SY.ravel()]                          # the courtyard sand / yards the sun must reach


def sun_blocks(X, Y, top):
    """True where an object at (X, Y) whose top is at `top` (level z, m) cuts the sun ray to any sand point (3 m wide)."""
    X, Y, top = np.atleast_1d(X), np.atleast_1d(Y), np.atleast_1d(top)
    dx = X[:, None] - SAND[None, :, 0]
    dy = Y[:, None] - SAND[None, :, 1]
    t = dx * SUN_H[0] + dy * SUN_H[1]
    lat = np.abs(dx * SUN_H[1] - dy * SUN_H[0])
    return ((t > 0) & (lat < 3.0) & (top[:, None] > t * math.tan(SUN_EL))).any(1)


def keepout(X, Y, extra_slots=2.0):'''),
    ('''        for x, y in pts:
            m = FIRS[int(RNG.choice(8, p=FIR_W))]''',
     '''        if pts:
            P = np.array(pts)
            blk = sun_blocks(P[:, 0], P[:, 1], ground(P[:, 0], P[:, 1]) + 17.0)
            counts[zid + "_sun_dropped"] = int(blk.sum())
            pts = [p for p, b in zip(pts, blk) if not b]
            counts[zid] = len(pts)
        for x, y in pts:
            m = FIRS[int(RNG.choice(8, p=FIR_W))]'''),
    ('''    for zid, poly in FZ:
        ok &= ~G.poly_contains(X, Y, poly)
    for x, y, z in zip(X[ok], Y[ok], Z[ok]):''',
     '''    for zid, poly in FZ:
        ok &= ~G.poly_contains(X, Y, poly)
    sb = np.zeros(ok.shape, bool)
    idx = np.where(ok)[0]
    for s in range(0, len(idx), 4000):
        j = idx[s:s + 4000]
        sb[j] = sun_blocks(X[j], Y[j], Z[j] + 14.0)
    counts["billboards_sun_dropped"] = int(sb.sum())
    ok &= ~sb
    for x, y, z in zip(X[ok], Y[ok], Z[ok]):'''),
    ('''    W["counts"] = {"actors_by_group": counts,''',
     '''    # the terrain itself: march every sand point's sun ray over the two heightmaps to 6 km (terrain-only shadow)
    lit = []
    for sx, sy in SAND:
        tt = np.concatenate([np.arange(2.0, 200.0, 1.0), np.arange(200.0, 6000.0, 8.0)])
        hx, hy = sx + SUN_H[0] * tt, sy + SUN_H[1] * tt
        lit.append(bool((ground(hx, hy) < tt * math.tan(SUN_EL)).all()))
    W["sun_check"] = {"sun_el_deg": 9.08, "sun_az_from_x_deg": 187.29, "sand_points": len(lit),
                      "terrain_lit_pct": round(100.0 * sum(lit) / len(lit), 1),
                      "note": "terrain-only (the compound's own walls / buildings still cast their round-9 shadows)"}
    W["counts"] = {"actors_by_group": counts,'''),
])
print("PATCH_IT7 ok")
