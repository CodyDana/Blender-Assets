"""Stage 18: fit circles-on-the-sphere to every traced edge and joint parallel-circle fits to band edge pairs.
Orthographic back-projection about the stage-1 circle. Writes sb_s18_fits.json."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

tr = json.load(open(os.path.join(L.D, "sb_trace.json")))['edges']


def dense(pts, step=4.0):
    P = np.asarray(pts, float)
    seg = np.diff(P, axis=0); sl = np.hypot(*seg.T); cum = np.r_[0, np.cumsum(sl)]
    s = np.arange(0, cum[-1] + 1e-6, step)
    return np.c_[np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])]


def desc(a, d):
    lat, lon = S.latlon(a[None, :])
    return dict(normal=[round(float(v), 4) for v in a], d=round(float(d), 4),
                pole_lat_deg=round(float(lat[0]), 1), pole_lon_deg=round(float(lon[0]), 1),
                circle_angular_radius_deg=round(float(np.degrees(np.arccos(np.clip(d, -1, 1)))), 2),
                limb_crossings_deg=[round(v, 1) for v in S.limb_crossings(a, d)])


out = {'edges': {}, 'bands': {}}
for k, e in tr.items():
    p = dense(e['pts'])
    P = S.to_sphere(p)
    a, d, rms = S.fit_plane(P)
    ag, dg, rmsg = S.fit_plane(P, great=True)
    lat, lon = S.latlon(P)
    rec = dict(n_pts=len(p), length_px=float(np.hypot(*np.diff(p, axis=0).T).sum()),
               small=dict(desc(a, d), rms_px=round(rms * S.R, 2)),
               great=dict(desc(ag, dg), rms_px=round(rmsg * S.R, 2)),
               start_img=[round(v, 1) for v in e['pts'][0]], end_img=[round(v, 1) for v in e['pts'][-1]],
               start_latlon=[round(float(lat[0]), 1), round(float(lon[0]), 1)],
               end_latlon=[round(float(lat[-1]), 1), round(float(lon[-1]), 1)])
    out['edges'][k] = rec
    print(f"{k:4s} len={rec['length_px']:6.0f} small: d={d:+.3f} rms={rms * S.R:5.2f}px pole=({rec['small']['pole_lat_deg']},{rec['small']['pole_lon_deg']}) "
          f"| great rms={rmsg * S.R:5.2f}px pole=({rec['great']['pole_lat_deg']},{rec['great']['pole_lon_deg']}) limb={rec['great']['limb_crossings_deg']}")

PAIRS = {"W": ("WUP", "WLO"), "B": ("BUP", "BLO"), "C": ("CUP", "CLO"), "A_vis": ("WLO", "ALO"),
         "L3_vis": ("L3L", "ALO"), "X_vis": ("BLO", "WUP")}
for band, (e1, e2) in PAIRS.items():
    P1 = S.to_sphere(dense(tr[e1]['pts'])); P2 = S.to_sphere(dense(tr[e2]['pts']))
    C = np.cov((P1 - P1.mean(0)).T) * len(P1) + np.cov((P2 - P2.mean(0)).T) * len(P2)
    w, v = np.linalg.eigh(C)
    a = v[:, 0]
    d1, d2 = float(P1.mean(0) @ a), float(P2.mean(0) @ a)
    if d1 + d2 < 0:
        a, d1, d2 = -a, -d1, -d2
    r1 = np.arcsin(np.clip(P1 @ a, -1, 1)) - np.arcsin(d1)
    r2 = np.arcsin(np.clip(P2 @ a, -1, 1)) - np.arcsin(d2)
    rms = float(np.sqrt(np.mean(np.r_[r1, r2] ** 2))) * S.R
    wdeg = float(np.degrees(abs(np.arcsin(d1) - np.arcsin(d2))))
    dc = float(np.sin(0.5 * (np.arcsin(d1) + np.arcsin(d2))))
    rec = dict(edges=[e1, e2], centre=desc(a, dc), d_edges=[round(d1, 4), round(d2, 4)],
               width_deg=round(wdeg, 2), width_frac_D=round(np.radians(wdeg) / 2, 4),
               width_px_true_scale=round(np.radians(wdeg) * S.R, 1), joint_rms_px=round(rms, 2))
    out['bands'][band] = rec
    print(f"BAND {band:7s} width={wdeg:5.2f}deg = {rec['width_frac_D']:.3f} D (arc) centre d={dc:+.3f} "
          f"pole=({rec['centre']['pole_lat_deg']},{rec['centre']['pole_lon_deg']}) rms={rms:.2f}px limb={rec['centre']['limb_crossings_deg']}")
L.dump("sb_s18_fits.json", out)
