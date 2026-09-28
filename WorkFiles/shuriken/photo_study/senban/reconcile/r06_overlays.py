"""Draw the reconciled outline and the SPEC outline on Senban.jpg."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import load_rgb, save_png, OUT

# ---------------------------------------------------------- reconciled numbers
CX, CY = 505.3, 476.8
ROT = np.radians(-2.45)
SIDE = 852.3                     # apex-to-apex chord, px
SAG_OVER_C = 0.0616
SAG = SIDE * SAG_OVER_C          # 52.5 px
HOLE = 225.5                     # hole side, px
HOLE_R = 10.0                    # hole corner fillet radius, px
BEVEL = 14.0                     # plan-view bevel width, px

# spec (study 2.3): side 76.2 mm, sagitta 6 mm, square hole 12.7 mm
SPEC_SIDE_MM, SPEC_SAG_MM, SPEC_HOLE_MM = 76.2, 6.0, 12.7
SCALE = (SIDE * np.sqrt(2)) / (SPEC_SIDE_MM * np.sqrt(2))   # px per mm, tip-to-tip matched


def concave_square(cx, cy, rot, side, sag, n=900):
    """C4 square on its diagonals with four concave circular-arc sides."""
    Rd = side * np.sqrt(2) / 2.0
    pts = []
    for k in range(4):
        a0 = rot + k * np.pi / 2 - np.pi / 4
        a1 = rot + (k + 1) * np.pi / 2 - np.pi / 4
        P0 = np.array([cx + Rd * np.cos(a0), cy + Rd * np.sin(a0)])
        P1 = np.array([cx + Rd * np.cos(a1), cy + Rd * np.sin(a1)])
        d = (P1 - P0) / side
        nrm = np.array([-d[1], d[0]])
        if np.dot(nrm, np.array([cx, cy]) - P0) < 0:
            nrm = -nrm
        R = side * side / (8 * sag) + sag / 2
        cen = 0.5 * (P0 + P1) + nrm * sag - nrm * R
        v0, v1 = P0 - cen, P1 - cen
        t0 = np.arctan2(v0[1], v0[0]); t1 = np.arctan2(v1[1], v1[0])
        while t1 - t0 > np.pi: t1 -= 2 * np.pi
        while t1 - t0 < -np.pi: t1 += 2 * np.pi
        tt = np.linspace(t0, t1, n // 4, endpoint=False)
        pts.append(np.stack([cen[0] + R * np.cos(tt), cen[1] + R * np.sin(tt)], 1))
    p = np.concatenate(pts, 0)
    return np.vstack([p, p[:1]])


def rounded_square(cx, cy, rot, side, r, n=600):
    """Axis-square (sides parallel to the plate's sides) with filleted corners."""
    h = side / 2.0
    loc = []
    cs = [(h - r, h - r), (-(h - r), h - r), (-(h - r), -(h - r)), (h - r, -(h - r))]
    starts = [0, 90, 180, 270]
    for (ccx, ccy), s0 in zip(cs, starts):
        tt = np.radians(np.linspace(s0, s0 + 90, max(n // 4, 8)))
        loc.append(np.stack([ccx + r * np.cos(tt), ccy + r * np.sin(tt)], 1))
    loc = np.concatenate(loc, 0)
    if r <= 0.01:
        loc = np.array([[h, h], [-h, h], [-h, -h], [h, -h]], float)
    c, s = np.cos(rot), np.sin(rot)
    M = np.array([[c, -s], [s, c]])
    p = loc @ M.T + np.array([cx, cy])
    return np.vstack([p, p[:1]])


def offset_inward(poly, w, cx, cy):
    v = poly - np.array([cx, cy])
    r = np.hypot(v[:, 0], v[:, 1])[:, None]
    return poly - v / r * w          # radial shrink: fine for a crease guide


def stamp(img, poly, colour, rad=1.6, dash=None):
    H, W = img.shape[:2]
    P = []
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        L = np.hypot(*(b - a))
        k = max(int(L / 0.4) + 1, 2)
        for t in np.linspace(0, 1, k, endpoint=False):
            P.append(a + t * (b - a))
    P = np.array(P)
    if dash:
        keep = (np.arange(len(P)) // dash) % 2 == 0
        P = P[keep]
    rr = int(np.ceil(rad))
    for dx in range(-rr, rr + 1):
        for dy in range(-rr, rr + 1):
            if dx * dx + dy * dy > rad * rad:
                continue
            xs = np.clip((P[:, 0] + dx).astype(int), 0, W - 1)
            ys = np.clip((P[:, 1] + dy).astype(int), 0, H - 1)
            img[ys, xs] = colour


def marker(img, p, colour, s=5):
    H, W = img.shape[:2]
    x, y = int(round(p[0])), int(round(p[1]))
    for dx in range(-s, s + 1):
        for dy in range(-s, s + 1):
            if max(abs(dx), abs(dy)) <= s:
                img[np.clip(y + dy, 0, H - 1), np.clip(x + dx, 0, W - 1)] = colour


GREEN = (0.0, 1.0, 0.25)
CYAN = (0.1, 0.85, 1.0)
RED = (1.0, 0.1, 0.1)
MAG = (1.0, 0.1, 0.9)
YEL = (1.0, 0.95, 0.1)

base = load_rgb()

# ---------------------------------------------------------- 1. reconciled
img = base.copy()
outer = concave_square(CX, CY, ROT, SIDE, SAG)
crease = offset_inward(outer, BEVEL, CX, CY)
hole = rounded_square(CX, CY, ROT, HOLE, HOLE_R)
stamp(img, crease, CYAN, 1.0, dash=9)
stamp(img, outer, GREEN, 1.7)
stamp(img, hole, GREEN, 1.7)
Rd = SIDE * np.sqrt(2) / 2
for k in range(4):
    a = ROT + k * np.pi / 2 - np.pi / 4
    marker(img, (CX + Rd * np.cos(a), CY + Rd * np.sin(a)), RED, 4)
marker(img, (CX, CY), RED, 3)
save_png(os.path.join(OUT, 'senban_reconciled_outline.png'), img)
print("wrote senban_reconciled_outline.png")

# ---------------------------------------------------------- 2. spec outline
img2 = base.copy()
spec_side = SPEC_SIDE_MM * SCALE
spec_sag = SPEC_SAG_MM * SCALE
spec_hole = SPEC_HOLE_MM * SCALE
spec_outer = concave_square(CX, CY, ROT, spec_side, spec_sag)
spec_holep = rounded_square(CX, CY, ROT, spec_hole, 0.0)
stamp(img2, spec_outer, MAG, 1.9)
stamp(img2, spec_holep, MAG, 1.9)
for k in range(4):
    a = ROT + k * np.pi / 2 - np.pi / 4
    marker(img2, (CX + Rd * np.cos(a), CY + Rd * np.sin(a)), YEL, 4)
save_png(os.path.join(OUT, 'senban_spec_outline.png'), img2)
print("wrote senban_spec_outline.png")

# ---------------------------------------------------------- 3. both together
img3 = base.copy()
stamp(img3, spec_outer, MAG, 1.9)
stamp(img3, spec_holep, MAG, 1.9)
stamp(img3, outer, GREEN, 1.5)
stamp(img3, hole, GREEN, 1.5)
for k in range(4):
    a = ROT + k * np.pi / 2 - np.pi / 4
    marker(img3, (CX + Rd * np.cos(a), CY + Rd * np.sin(a)), YEL, 4)
save_png(os.path.join(OUT, 'senban_reconciled_vs_spec.png'), img3)
print("wrote senban_reconciled_vs_spec.png")

print(f"\nscale used: {SCALE:.4f} px/mm (tip-to-tip matched: "
      f"{SIDE*np.sqrt(2):.1f} px = {SPEC_SIDE_MM*np.sqrt(2):.2f} mm)")
print(f"spec sagitta {spec_sag:.1f} px vs photo {SAG:.1f} px")
print(f"spec hole    {spec_hole:.1f} px vs photo {HOLE:.1f} px")
json.dump(dict(centre=[CX, CY], rot_deg=np.degrees(ROT), side_px=SIDE,
               diagonal_px=SIDE * np.sqrt(2), sagitta_px=SAG,
               sag_over_chord=SAG_OVER_C, hole_side_px=HOLE,
               hole_fillet_px=HOLE_R, bevel_px=BEVEL,
               scale_px_per_mm_if_spec_side=SCALE,
               spec_sagitta_px=spec_sag, spec_hole_px=spec_hole),
          open(os.path.join(OUT, 'senban_reconciled.json'), 'w'), indent=1)
print("wrote senban_reconciled.json")
