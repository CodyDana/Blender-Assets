"""Overlays: (1) photo + reconciled outline, (2) photo + SPEC outline scaled to the
same tip-to-tip span. Written to the roppo/ folder."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
OUTDIR = os.path.dirname(HERE)   # .../roppo

rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape

# ---------------- reconciled parameters (px, image coords) ----------------
S = 1177.0                 # reconciled observed tip-to-tip span
C = np.array([629.0, 528.3])   # reconciled centre (hub/hole/tip circles agree within ~3 px)
R_HUB = 0.2440 * S             # 287.2
R_HOLE = 0.1140 * S            # 134.2  (bore)
R_RING = 0.1175 * S            # outer edge of the rounded hole rim
R_APEX = 0.5140 * S            # sharp-point radius from the flank-line intersections
R_TIP = 0.4995 * S             # observed (blunted) tip radius
ALPHA = np.radians(25.1)       # tip included angle
ROT = 1.595                    # math-convention rotation of point 0 (deg)

# ---------------- spec parameters (mm) ----------------
SPEC_SPAN = 98.0
K = S / SPEC_SPAN              # px per mm, spans matched
SPEC_HUB_R = 18.0 * K          # study 2.4 "18 mm hub" = hub RADIUS (builder convention,
SPEC_ARM_W = 11.0 * K          #  confirmed by the 1668 mm2 / 2486 mm2 area cross-checks)
SPEC_TIP_R = 49.0 * K
SPEC_TIP_DEG = 38.0
SPEC_HOLE_R = 4.0 * K


def put(img, x, y, col, w=1):
    for dx in range(-(w // 2), w // 2 + 1):
        for dy in range(-(w // 2), w // 2 + 1):
            i, j = int(round(y + dy)), int(round(x + dx))
            if 0 <= i < img.shape[0] and 0 <= j < img.shape[1]:
                img[i, j] = col


def seg(img, p0, p1, col, w=1):
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    n = int(max(2, np.linalg.norm(p1 - p0) * 12))
    for t in np.linspace(0, 1, n):
        p = p0 + (p1 - p0) * t
        put(img, p[0], p[1], col, w)


def arc(img, c, r, a0, a1, col, w=1):
    if a1 < a0:
        a1 += 360
    n = int(max(4, (a1 - a0) * r * 0.25))
    for a in np.linspace(a0, a1, n):
        th = np.radians(a)
        put(img, c[0] + np.cos(th) * r, c[1] + np.sin(th) * r, col, w)


def circle(img, c, r, col, w=1):
    arc(img, c, r, 0, 360, col, w)


def line_circle_near(apex, u, c, R):
    """Intersection of ray apex+t*u (t>0) with circle(c,R): the nearer one."""
    f = apex - c
    b = 2 * (f @ u)
    cc = f @ f - R * R
    disc = b * b - 4 * cc
    if disc < 0:
        return None
    ts = sorted([(-b - np.sqrt(disc)) / 2, (-b + np.sqrt(disc)) / 2])
    ts = [t for t in ts if t > 0]
    return apex + ts[0] * u if ts else None


CYAN = (0.0, 1.0, 1.0)
MAG = (1.0, 0.1, 0.9)
YEL = (1.0, 0.95, 0.1)
RED = (1.0, 0.15, 0.15)
ORA = (1.0, 0.6, 0.0)
GRN = (0.2, 1.0, 0.2)

# ================= overlay 1: reconciled outline =================
img = np.clip(rgb.copy(), 0, 1) * 0.92
roots = []
apexes = []
for k in range(6):
    th = np.radians(-(ROT + 60 * k))          # image coords (y down)
    a = np.array([np.cos(th), np.sin(th)])
    apex = C + a * R_APEX
    apexes.append(apex)
    rr = []
    for s in (+1, -1):
        ang = np.radians(-(ROT + 60 * k)) + s * ALPHA / 2 + np.pi
        u = np.array([np.cos(ang), np.sin(ang)])   # from apex inward
        p = line_circle_near(apex, u, C, R_HUB)
        rr.append(p)
        seg(img, apex, p, CYAN, 2)
    roots.append(rr)
# exposed hub arcs between neighbouring roots
for k in range(6):
    p1 = roots[k][0]
    p2 = roots[(k + 1) % 6][1]
    a1 = np.degrees(np.arctan2(p1[1] - C[1], p1[0] - C[0])) % 360
    a2 = np.degrees(np.arctan2(p2[1] - C[1], p2[0] - C[0])) % 360
    arc(img, C, R_HUB, a1, a2, CYAN, 2)
circle(img, C, R_HOLE, MAG, 2)
circle(img, C, R_RING, (1.0, 0.55, 0.9), 1)
# observed tip ticks
for k in range(6):
    th = np.radians(-(ROT + 60 * k))
    a = np.array([np.cos(th), np.sin(th)])
    q = np.array([-a[1], a[0]])
    p = C + a * R_TIP
    seg(img, p - q * 9, p + q * 9, YEL, 2)
put(img, C[0], C[1], YEL, 5)
rio.save_rgb(os.path.join(OUTDIR, "roppo_overlay_reconciled.png"), img)

# ================= overlay 2: spec outline =================
img2 = np.clip(rgb.copy(), 0, 1) * 0.92
half = SPEC_ARM_W / 2
taper_len = half / np.tan(np.radians(SPEC_TIP_DEG / 2))
t_start = SPEC_TIP_R - taper_len
t_root = np.sqrt(SPEC_HUB_R ** 2 - half ** 2)
spec_roots = []
for k in range(6):
    th = np.radians(-(ROT + 60 * k))
    a = np.array([np.cos(th), np.sin(th)])
    q = np.array([-a[1], a[0]])
    apex = C + a * SPEC_TIP_R
    rr = []
    for s in (+1, -1):
        p_root = C + a * t_root + q * (s * half)
        p_sh = C + a * t_start + q * (s * half)
        seg(img2, p_root, p_sh, RED, 2)
        seg(img2, p_sh, apex, RED, 2)
        rr.append(p_root)
    spec_roots.append(rr)
for k in range(6):
    p1 = spec_roots[k][0]
    p2 = spec_roots[(k + 1) % 6][1]
    a1 = np.degrees(np.arctan2(p1[1] - C[1], p1[0] - C[0])) % 360
    a2 = np.degrees(np.arctan2(p2[1] - C[1], p2[0] - C[0])) % 360
    arc(img2, C, SPEC_HUB_R, a1, a2, RED, 2)
circle(img2, C, SPEC_HOLE_R, ORA, 2)
# bevel start (last 16 mm) marks on the spec arms
for k in range(6):
    th = np.radians(-(ROT + 60 * k))
    a = np.array([np.cos(th), np.sin(th)])
    q = np.array([-a[1], a[0]])
    p = C + a * t_start
    seg(img2, p - q * half, p + q * half, (1.0, 0.8, 0.4), 1)
put(img2, C[0], C[1], YEL, 5)
rio.save_rgb(os.path.join(OUTDIR, "roppo_overlay_spec.png"), img2)

# ================= overlay 3: both, for the delta read =================
img3 = np.clip(rgb.copy(), 0, 1) * 0.85
for k in range(6):
    th = np.radians(-(ROT + 60 * k))
    a = np.array([np.cos(th), np.sin(th)])
    q = np.array([-a[1], a[0]])
    apex = C + a * R_APEX
    for s in (+1, -1):
        ang = np.radians(-(ROT + 60 * k)) + s * ALPHA / 2 + np.pi
        u = np.array([np.cos(ang), np.sin(ang)])
        p = line_circle_near(apex, u, C, R_HUB)
        seg(img3, apex, p, CYAN, 2)
    apex2 = C + a * SPEC_TIP_R
    for s in (+1, -1):
        p_root = C + a * t_root + q * (s * half)
        p_sh = C + a * t_start + q * (s * half)
        seg(img3, p_root, p_sh, RED, 2)
        seg(img3, p_sh, apex2, RED, 2)
for k in range(6):
    p1, p2 = roots[k][0], roots[(k + 1) % 6][1]
    arc(img3, C, R_HUB, np.degrees(np.arctan2(p1[1] - C[1], p1[0] - C[0])) % 360,
        np.degrees(np.arctan2(p2[1] - C[1], p2[0] - C[0])) % 360, CYAN, 2)
    p1, p2 = spec_roots[k][0], spec_roots[(k + 1) % 6][1]
    arc(img3, C, SPEC_HUB_R, np.degrees(np.arctan2(p1[1] - C[1], p1[0] - C[0])) % 360,
        np.degrees(np.arctan2(p2[1] - C[1], p2[0] - C[0])) % 360, RED, 2)
circle(img3, C, R_HOLE, MAG, 2)
circle(img3, C, SPEC_HOLE_R, ORA, 2)
rio.save_rgb(os.path.join(OUTDIR, "roppo_overlay_spec_vs_photo.png"), img3)

info = dict(span_px=S, centre=C.tolist(), R_hub=R_HUB, R_hole=R_HOLE, R_ring=R_RING,
            R_apex=R_APEX, R_tip=R_TIP, alpha_deg=float(np.degrees(ALPHA)), rot_deg=ROT,
            spec=dict(k_px_per_mm=K, hub_r_px=SPEC_HUB_R, arm_w_px=SPEC_ARM_W,
                      tip_r_px=SPEC_TIP_R, hole_r_px=SPEC_HOLE_R,
                      taper_len_mm=float(taper_len / K), t_start_mm=float(t_start / K),
                      root_axial_mm=float(t_root / K),
                      arm_half_angle_at_hub_deg=float(np.degrees(np.arcsin(half / SPEC_HUB_R))),
                      exposed_arc_deg=float(60 - 2 * np.degrees(np.arcsin(half / SPEC_HUB_R)))),
            recon=dict(base_chord_px=float(np.linalg.norm(roots[0][0] - roots[0][1])),
                       base_chord_ratio=float(np.linalg.norm(roots[0][0] - roots[0][1]) / S)))
json.dump(info, open(os.path.join(HERE, "overlay_info.json"), "w"), indent=1)
print(json.dumps(info, indent=1))
