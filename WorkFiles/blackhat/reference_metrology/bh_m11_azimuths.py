"""Stage 11: convert rib image angles (from the apex) and lashing image points to 3D azimuth theta for several cameras.
theta: 0 = rim point nearest the camera, + = toward image right (world +X)."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
J = load('bh_s07_joint.json')
heavy = [-56.3, -35.3, 12.0, 39.6]
thin = [-63.0, -59.75, -51.5, -46.3, -40.5, -31.0, -25.25, -14.5, -0.25, 27.5, 33.5, 56.0, 59.0, 62.5]
lash = [(9.6, 350.3), (85.4, 398.2), (158.2, 417.9), (252.0, 431.0), (395.0, 433.0), (472.2, 427.5), (625.9, 382.2), (660.0, 337.4)]
th = np.radians(np.linspace(-179.9, 179.9, 35981))
for key in ['2.2', '2.6', '3.0', 'inf']:
    c = J[key]; d = float(key); H = c['H']; e = np.radians(c['e_deg']); f = c['f']; u0, v0, roll = c['u0'], c['v0'], np.radians(c['roll_deg'])
    pr = lambda P: project(P, e, d, f, u0, v0, roll)
    apex = pr(np.array([[0, 0, H]]))[0]
    # generator point at rho=0.7
    rho = 0.7
    P = np.stack([rho * np.sin(th), -rho * np.cos(th), np.full_like(th, H * (1 - rho))], -1)   # theta=0 -> -Y (camera side)
    uv = pr(P)
    phi = np.degrees(np.arctan2(uv[:, 0] - apex[0], uv[:, 1] - apex[1]))
    # use the visible (front) branch: |theta| <= theta at max |phi|
    front = np.abs(th) <= np.radians(100)
    def phi2th(p):
        s = front & (np.abs(phi - p) < 0.2)
        cand = th[s]
        if not len(cand): return np.nan
        return float(np.degrees(cand[np.argmin(np.abs(np.degrees(cand)))]))  # front-most solution
    hv = [phi2th(p) for p in heavy]; tn = [phi2th(p) for p in thin]
    # lashings: rim circle radius 0.985, z = -0.01
    Pr = np.stack([0.985 * np.sin(th), -0.985 * np.cos(th), np.full_like(th, -0.01)], -1)
    ur = pr(Pr)
    ls = []
    for (x, y) in lash:
        dd = np.hypot(ur[:, 0] - x, ur[:, 1] - y); i = np.argmin(dd); ls.append((round(float(np.degrees(th[i])), 1), round(float(dd[i]), 1)))
    print('cam', key, 'apex img', apex.round(2), 'phi range max', round(float(np.max(np.abs(phi[front]))), 2))
    print('  heavy', np.round(hv, 1).tolist(), 'diffs', np.round(np.diff(hv), 1).tolist())
    print('  thin ', np.round(tn, 1).tolist())
    allr = sorted(hv + tn); print('  all diffs', np.round(np.diff(allr), 1).tolist())
    print('  lash', ls, 'diffs', np.round(np.diff([a for a, b in ls]), 1).tolist())
