"""Stage 23: local scales at the tails, vertical drop scale, band/knot back-projection helpers, camera in Blender terms."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
out = {}
for key in ['2.2', '2.6', '3.0']:
    c = load('bh_s07_joint.json')[key]; d = float(key)
    H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
    F, Rv, U = cam_basis(e, roll); C = -d * F
    pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
    r = {}
    for nm, t in (('tailA', 31.0), ('tailB', 40.0)):
        tr = np.radians(t); P0 = np.array([1.02 * np.sin(tr), -1.02 * np.cos(tr), 0.0])
        z = (P0 - C) @ F; r[nm + '_px_per_R'] = float(f / z)
        a = pr([P0])[0]; b = pr([P0 + [0, 0, -0.1]])[0]; r[nm + '_vertical_px_per_R'] = float(np.hypot(*(b - a)) / 0.1)
        r[nm + '_rim_img'] = a.round(1).tolist()
    # knot: back-project image point (462,222) to the cone surface
    def backproj(u, v):
        x = (u - u0) / f; y = -(v - v0) / f
        dirv = F + x * Rv + y * U; dirv /= np.linalg.norm(dirv)
        best = None
        for s in np.linspace(0.5, 4, 3501):
            P = C + s * dirv; rho = np.hypot(P[0], P[1]); zc = H * (1 - rho)
            if P[2] <= zc: best = P; break
        if best is None: return None
        th = np.degrees(np.arctan2(best[0], -best[1])); return float(th), float(np.hypot(best[0], best[1])), best.tolist()
    for nm, (u, v) in dict(knot_centre=(462, 222), knot_top=(455, 200), knot_bottom=(470, 245), band_left_end=(216, 201), band_front_mid=(330, 222), tails_leave_knot=(492, 238), cap_top=(334, 142.5)).items():
        r[nm] = backproj(u, v)
    # blender camera: sensor 36 mm horizontal, 670 px wide
    fmm = f * 36 / 670
    r['blender'] = dict(focal_mm_sensor36_fitH670=fmm, shift_x=(u0 - 335) / 670, shift_y=-(v0 - 299.5) / 670,
                        cam_pos_R=(C).tolist(), look_at=[0, 0, 0], elev_deg=c['e_deg'], roll_deg=c['roll_deg'],
                        hfov_deg=float(2 * np.degrees(np.arctan(335 / f))))
    out[key] = r
    print(key, json.dumps(r, indent=None)[:1500])
dump('bh_s23_misc.json', out)
