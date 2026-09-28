"""Method A radial-profile geometry of the Juji silhouette.

usage: blender -b --factory-startup --python s10_geometry.py -- <mask.npy basename> <tag>
Angles: theta measured counter-clockwise from image +x with image y pointing DOWN, i.e.
theta = atan2(-(y-cy), x-cx): right arm ~0 deg, top ~90, left ~180, bottom ~270.
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

args = sys.argv[sys.argv.index("--") + 1:]
mname = args[0]
tag = args[1] if len(args) > 1 else mname
a = jlib.load_image()
H, W, _ = a.shape
m = np.load(os.path.join(jlib.OUT, mname + ".npy")).astype(bool)
# smooth jagged watershed steps: Gaussian of the binary mask, re-threshold
mf = jlib.gblur(m.astype(np.float32), 2.0)
m = mf > 0.5
m = jlib.largest_component(m)
m, holes = jlib.fill_holes(m)
mf = jlib.gblur(m.astype(np.float32), 1.0)  # float version for sub-pixel boundary sampling
res = {"mask": mname, "image_size": [W, H], "mask_px": int(m.sum()), "enclosed_holes_px": int(holes.sum())}
touch = {"top_row": int(m[0].sum()), "bottom_row": int(m[-1].sum()), "left_col": int(m[:, 0].sum()), "right_col": int(m[:, -1].sum())}
res["mask_pixels_on_image_border"] = touch
ys, xs = np.nonzero(m)
res["bbox_xywh"] = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
c_centroid = np.array([xs.mean(), ys.mean()])

# ---- symmetry centre: maximise overlap of the mask with its 90-deg and 180-deg rotations ----
sub = np.stack([xs[::4], ys[::4]], 1).astype(np.float64)


def overlap(cx, cy, quarter):
    dx = sub[:, 0] - cx; dy = sub[:, 1] - cy
    if quarter == 2:
        rx, ry = cx - dx, cy - dy
    else:  # rotate 90 deg
        rx, ry = cx - dy, cy + dx
    rxi = np.rint(rx).astype(int); ryi = np.rint(ry).astype(int)
    ok = (rxi >= 0) & (rxi < W) & (ryi >= 0) & (ryi < H)
    hit = np.zeros(len(rx), bool)
    hit[ok] = m[ryi[ok], rxi[ok]]
    return hit.mean()


best = {}
for q in (2, 1):
    bb = (-1, None)
    for cy in np.arange(c_centroid[1] - 20, c_centroid[1] + 20.1, 1.0):
        for cx in np.arange(c_centroid[0] - 20, c_centroid[0] + 20.1, 1.0):
            v = overlap(cx, cy, q)
            if v > bb[0]:
                bb = (v, (cx, cy))
    # refine at 0.25 px
    v0, (bx, by) = bb
    for cy in np.arange(by - 1, by + 1.01, 0.25):
        for cx in np.arange(bx - 1, bx + 1.01, 0.25):
            v = overlap(cx, cy, q)
            if v > bb[0]:
                bb = (v, (cx, cy))
    best[q] = bb
c_sym180 = np.array(best[2][1]); c_sym90 = np.array(best[1][1])
res["centre_candidates_px"] = {"centroid": c_centroid.round(2).tolist(),
                               "sym180": c_sym180.tolist(), "sym180_overlap": round(best[2][0], 4),
                               "sym90": c_sym90.tolist(), "sym90_overlap": round(best[1][0], 4)}

# ---- radial profile r(theta) ----
def radial_profile(c, step_deg=0.1, rmax=900.0, dr=0.25):
    th = np.deg2rad(np.arange(0, 360, step_deg))
    rr = np.arange(0, rmax, dr)
    X = c[0] + np.cos(th)[:, None] * rr[None, :]
    Y = c[1] - np.sin(th)[:, None] * rr[None, :]
    inside_img = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
    v = jlib.bilinear(mf, X, Y)
    v[~inside_img] = 0
    ins = v > 0.5
    # outermost inside sample
    idx_last = ins.shape[1] - 1 - np.argmax(ins[:, ::-1], axis=1)
    has = ins.any(1)
    r_out = np.where(has, rr[idx_last], 0.0)
    # sub-pixel refine: linear interpolation between last inside and next sample
    i2 = np.minimum(idx_last + 1, len(rr) - 1)
    v1 = v[np.arange(len(th)), idx_last]; v2 = v[np.arange(len(th)), i2]
    frac = np.clip((v1 - 0.5) / np.maximum(v1 - v2, 1e-6), 0, 1)
    r_out = r_out + frac * dr
    # first exit (from centre)
    first_out = np.argmax(~ins, axis=1)
    r_in = rr[first_out]
    # does the ray leave the object then re-enter? (non star-shaped)
    reenter = (idx_last > first_out)
    clipped = ~inside_img[np.arange(len(th)), np.minimum(idx_last + 2, len(rr) - 1)]
    return np.rad2deg(th), r_out, r_in, reenter, clipped


c = c_sym90.copy()
thd, r_out, r_in, reenter, clipped = radial_profile(c)
np.savez(os.path.join(jlib.OUT, "radial_%s.npz" % tag), theta=thd, r_out=r_out, r_in=r_in, reenter=reenter, clipped=clipped, centre=c)
# periodicity
F = np.fft.rfft(r_out - r_out.mean())
amp = np.abs(F)[:25] / len(r_out) * 2
res["rtheta_harmonic_amplitude_px"] = {str(k): round(float(amp[k]), 2) for k in range(1, 13)}
res["dominant_harmonic"] = int(np.argmax(amp[1:25]) + 1)
# autocorrelation peak
rc = r_out - r_out.mean()
ac = np.array([np.dot(rc, np.roll(rc, s)) for s in range(0, 1800)]) / np.dot(rc, rc)
# first strong peak after lag 30 deg
lag = np.argmax(ac[300:1500]) + 300
res["autocorr_peak_lag_deg"] = round(lag * 0.1, 1)
res["autocorr_peak_value"] = round(float(ac[lag]), 3)

# ---- tips: maxima of r_out in 4 sectors around the dominant directions ----
tips = []
for k in range(4):
    centre_ang = 90.0 * k  # right, top, left, bottom
    sel = np.nonzero(((thd - centre_ang + 180) % 360 - 180 >= -45) & ((thd - centre_ang + 180) % 360 - 180 < 45))[0]
    i = sel[np.argmax(r_out[sel])]
    tips.append(i)
tip_info = []
for k, i in enumerate(tips):
    th = thd[i]; R = r_out[i]
    tx, ty = c[0] + R * math.cos(math.radians(th)), c[1] - R * math.sin(math.radians(th))
    tip_info.append({"arm": ["right", "top", "left", "bottom"][k], "theta_deg": round(float(th), 2), "r_px": round(float(R), 2),
                     "xy": [round(tx, 1), round(ty, 1)], "ray_clipped_by_image_edge": bool(clipped[i])})
# local maxima count (prominence) as independent point count
from_peaks = []
sm = np.convolve(np.r_[r_out[-50:], r_out, r_out[:50]], np.ones(21) / 21, mode='same')[50:-50]
for i in range(len(sm)):
    if sm[i] == max(sm[(i + j) % len(sm)] for j in range(-150, 151, 5)) and sm[i] > np.median(sm) * 1.3:
        from_peaks.append(round(float(thd[i]), 1))
res["local_maxima_theta_deg"] = from_peaks
# notches: minima of r_out between consecutive tips
notches = []
for k in range(4):
    t0 = thd[tips[k]]; t1 = thd[tips[(k + 1) % 4]]
    span = (t1 - t0) % 360
    rel = (thd - t0) % 360
    sel = np.nonzero((rel > 5) & (rel < span - 5))[0]
    i = sel[np.argmin(r_out[sel])]
    notches.append({"between": [tip_info[k]["arm"], tip_info[(k + 1) % 4]["arm"]], "theta_deg": round(float(thd[i]), 2),
                    "r_px": round(float(r_out[i]), 2)})
res["tips"] = tip_info
res["notches"] = notches
json.dump(res, open(os.path.join(jlib.OUT, "geom_%s_part1.json" % tag), "w"), indent=1)
print(json.dumps(res, indent=1))

# overlay
ov = a.copy() * 0.8
ov[jlib.boundary(m)] = [0, 1, 0]
for t in tip_info:
    x, y = t["xy"]
    ov[max(0, int(y) - 4):int(y) + 5, max(0, int(x) - 4):int(x) + 5] = [1, 0, 0]
for n in notches:
    th = math.radians(n["theta_deg"]); R = n["r_px"]
    x, y = c[0] + R * math.cos(th), c[1] - R * math.sin(th)
    ov[int(y) - 3:int(y) + 4, int(x) - 3:int(x) + 4] = [0, 0.5, 1]
ov[int(c[1]) - 3:int(c[1]) + 4, int(c[0]) - 3:int(c[0]) + 4] = [1, 1, 0]
jlib.save_png(os.path.join(jlib.OUT, "dbg_geom_%s_p1.png" % tag), ov)
# radial profile plot (theta on x, r on y) as an image
PW, PH = 1800, 500
plot = np.ones((PH, PW, 3), np.float32)
rmaxp = max(r_out.max(), 1)
for i in range(len(thd)):
    x = int(i * PW / len(thd))
    y = int(PH - 1 - r_out[i] / rmaxp * (PH - 20))
    plot[max(0, y - 1):y + 2, x] = [0, 0, 0]
    y2 = int(PH - 1 - r_in[i] / rmaxp * (PH - 20))
    plot[max(0, y2 - 1):y2 + 1, x] = [0.9, 0.3, 0.3]
for gx in range(0, 360, 45):
    plot[:, int(gx / 360 * PW)] = [0.6, 0.6, 1.0]
jlib.save_png(os.path.join(jlib.OUT, "dbg_rtheta_%s.png" % tag), plot)
np.save(os.path.join(jlib.OUT, "mask_final_%s.npy" % tag), m)
