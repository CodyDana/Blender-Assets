"""Per-arm width profiles from a binary mask.

usage: blender ... --python s11_arms.py -- <mask npy basename> <tag>
For each arm: axis = line from the symmetry centre through the tip, refined by a straight-line fit to
chord midpoints between 0.35 R and 0.95 R. Stations s = distance from the centre along the axis.
At each station the mask is sampled along the perpendicular (0.25 px steps); the run of mask pixels that
contains the medial point gives the edges t_left, t_right (t positive to the arm's left looking outward).
Also the angular extent of the mask on circles of radius r (arc containing the arm direction).
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

args = sys.argv[sys.argv.index("--") + 1:]
mname, tag = args[0], args[1]
m = np.load(os.path.join(jlib.OUT, mname + ".npy")).astype(bool)
mf = jlib.gblur(m.astype(np.float32), 1.0)
H, W = m.shape
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])
if len(args) > 2:
    c = np.array([float(args[2]), float(args[3])])
rad = np.load(os.path.join(jlib.OUT, "radial_ws.npz"))


def arm_frame(theta_deg):
    th = math.radians(theta_deg)
    u = np.array([math.cos(th), -math.sin(th)])       # outward along arm (image coords, y down)
    n = np.array([-math.sin(th), -math.cos(th)])      # u rotated +90 deg in the math (y-up) sense = arm's left
    return u, n


def chord(origin, u, n, s, tmax=260.0, dt=0.25):
    t = np.arange(-tmax, tmax + dt, dt)
    P = origin[None, :] + s * u[None, :] + t[:, None] * n[None, :]
    inimg = (P[:, 0] >= 0) & (P[:, 0] <= W - 1) & (P[:, 1] >= 0) & (P[:, 1] <= H - 1)
    v = jlib.bilinear(mf, P[:, 0], P[:, 1])
    v[~inimg] = 0
    ins = v > 0.5
    return t, v, ins


def run_edges(t, v, ins, t0=0.0):
    """edges of the inside-run containing (or nearest to) t0, sub-pixel by linear interpolation of v-0.5."""
    if not ins.any():
        return None
    i0 = int(np.argmin(np.abs(t - t0)))
    if not ins[i0]:
        idx = np.nonzero(ins)[0]
        i0 = idx[np.argmin(np.abs(idx - i0))]
    j = i0
    while j + 1 < len(t) and ins[j + 1]:
        j += 1
    k = i0
    while k - 1 >= 0 and ins[k - 1]:
        k -= 1
    # sub-pixel
    def interp(ia, ib):
        va, vb = v[ia], v[ib]
        f = (va - 0.5) / (va - vb) if va != vb else 0.5
        return t[ia] + f * (t[ib] - t[ia])
    tl = interp(j, j + 1) if j + 1 < len(t) else t[j]   # positive side
    tr = interp(k, k - 1) if k - 1 >= 0 else t[k]       # negative side
    return tl, tr, (j + 1 >= len(t)) or (k - 1 < 0)


arms_out = {}
names = ["right", "top", "left", "bottom"]
for k, tip in enumerate(g1["tips"]):
    th = tip["theta_deg"]
    R = tip["r_px"]
    u, n = arm_frame(th)
    # refine axis: chord midpoints
    mids = []
    for s in np.arange(0.35 * R, 0.95 * R, 4.0):
        t, v, ins = chord(c, u, n, s)
        e = run_edges(t, v, ins)
        if e:
            mids.append((s, 0.5 * (e[0] + e[1])))
    mids = np.array(mids)
    A = np.stack([mids[:, 0], np.ones(len(mids))], 1)
    (slope, icpt), *_ = np.linalg.lstsq(A, mids[:, 1], rcond=None)
    axis_rot_deg = math.degrees(math.atan(slope))
    offset_at_centre = icpt
    th2 = th + axis_rot_deg
    u2, n2 = arm_frame(th2)
    origin = c + icpt * n  # medial line passes here (point on the line nearest the centre, approx)
    # tip radius along refined axis (outermost mask point along the axis line +-0)
    prof = []
    for s in np.arange(0, R + 30, 1.0):
        t, v, ins = chord(origin, u2, n2, s)
        e = run_edges(t, v, ins, 0.0)
        if e is None:
            prof.append((s, np.nan, np.nan, 1))
            continue
        prof.append((s, e[0], e[1], int(e[2])))
    prof = np.array(prof)
    # angular extent on circles about the centre
    ang = []
    for r in np.arange(40, R + 5, 2.0):
        dth = np.deg2rad(np.arange(-60, 60, 0.05))
        thr = math.radians(th) + dth
        X = c[0] + r * np.cos(thr); Y = c[1] - r * np.sin(thr)
        ok = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
        vv = jlib.bilinear(mf, X, Y); vv[~ok] = 0
        ins = vv > 0.5
        e = run_edges(np.rad2deg(dth), vv, ins, 0.0)
        if e is None:
            ang.append((r, np.nan, np.nan)); continue
        ang.append((r, e[0], e[1]))
    ang = np.array(ang)
    arms_out[names[k]] = {"theta_tip_deg": th, "R_tip_px": R, "axis_rot_from_tip_dir_deg": axis_rot_deg,
                          "medial_offset_at_centre_px": offset_at_centre, "theta_axis_deg": th2,
                          "origin": origin.tolist()}
    np.savez(os.path.join(jlib.OUT, "arm_%s_%s.npz" % (tag, names[k])), prof=prof, ang=ang, u=u2, n=n2, origin=origin)

json.dump({"centre": c.tolist(), "arms": arms_out}, open(os.path.join(jlib.OUT, "arms_%s.json" % tag), "w"), indent=1)

# ---- comparison table: width w(s) per arm at fixed stations ----
print("centre", c)
for nme, d in arms_out.items():
    print(nme, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items() if k != "origin"})
print("\nstation(px)  " + "  ".join("%8s" % n for n in names) + "   (full width, px)")
profs = {n: np.load(os.path.join(jlib.OUT, "arm_%s_%s.npz" % (tag, n)))["prof"] for n in names}
for s in list(range(60, 200, 10)) + list(range(200, 680, 20)):
    row = []
    for n in names:
        p = profs[n]
        i = np.argmin(np.abs(p[:, 0] - s))
        w = p[i, 1] - p[i, 2]
        row.append("%8.1f" % w if np.isfinite(w) else "     nan")
    print("%6d       " % s + "  ".join(row))
print("\nhalf-widths left(+)/right(-) per arm at stations")
for s in [150, 250, 300, 350, 400, 450, 500, 550, 600, 630]:
    row = []
    for n in names:
        p = profs[n]
        i = np.argmin(np.abs(p[:, 0] - s))
        row.append("%6.1f/%6.1f" % (p[i, 1], p[i, 2]))
    print("%6d  " % s + "  ".join(row))
