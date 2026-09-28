"""Stage 4: fit circle (free centre) and ellipse (free conic) to the outer leaf edge; compare centre to rivet."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
rng = {1: (18, 158), 2: (12, 170)}
res = {}
for i in (1, 2):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    rout = np.load(os.path.join(OUT, f"fm_rout{i}.npy"))
    th = -20 + 0.1*np.arange(len(rout))
    m = (th >= rng[i][0]) & (th <= rng[i][1]) & ~np.isnan(rout)
    t = np.radians(th[m]); r = rout[m] + 0.5
    x = cx + r*np.cos(t); y = cy - r*np.sin(t)
    # circle fixed at rivet
    rc = r.mean(); res_c0 = r - rc
    # free circle (Kasa)
    A = np.c_[2*x, 2*y, np.ones_like(x)]; b = x*x + y*y
    sol = np.linalg.lstsq(A, b, rcond=None)[0]; x0, y0 = sol[0], sol[1]; R = np.sqrt(sol[2] + x0*x0 + y0*y0)
    res_c = np.hypot(x-x0, y-y0) - R
    # axis-aligned ellipse centred free: (x-x0)^2/a^2 + (y-y0)^2/b^2 = 1 -> linear in [x^2,y^2,x,y,1]
    D = np.c_[x*x, x*y, y*y, x, y, np.ones_like(x)]
    _, _, Vt = np.linalg.svd(D); cA, cB, cC, cD, cE, cF = Vt[-1]
    M = np.array([[cA, cB/2], [cB/2, cC]]); ctr = np.linalg.solve(2*M, [-cD, -cE])
    Fc = cF + 0.5*(cD*ctr[0] + cE*ctr[1])
    ev, evec = np.linalg.eigh(M); axes = np.sqrt(-Fc/ev)
    ang = np.degrees(np.arctan2(evec[1, 0], evec[0, 0]))
    # algebraic residual in px: approx via radial scaling
    def ell_res(px, py):
        out = []
        for X, Y in zip(px, py):
            d = np.array([X-ctr[0], Y-ctr[1]]); q = d @ M @ d
            s = np.sqrt(-Fc/q); out.append(np.linalg.norm(d)*(1-s))
        return np.array(out)
    res_e = ell_res(x, y)
    res[i] = dict(rivet=[cx, cy], n=int(m.sum()),
                  circle_at_rivet=dict(R=round(rc, 2), rms=round(float(np.sqrt((res_c0**2).mean())), 2), minmax=[round(float(r.min()), 1), round(float(r.max()), 1)]),
                  circle_free=dict(centre=[round(x0, 2), round(y0, 2)], R=round(float(R), 2), rms=round(float(np.sqrt((res_c**2).mean())), 2),
                                   centre_minus_rivet=[round(x0-cx, 2), round(y0-cy, 2)]),
                  ellipse_free=dict(centre=[round(float(ctr[0]), 2), round(float(ctr[1]), 2)], semi_axes=[round(float(v), 2) for v in axes],
                                    axis0_angle_deg=round(float(ang), 2), rms=round(float(np.sqrt((res_e**2).mean())), 2),
                                    centre_minus_rivet=[round(float(ctr[0]-cx), 2), round(float(ctr[1]-cy), 2)]))
json.dump(res, open(os.path.join(OUT, "fm_s04_arcfit.json"), "w"), indent=1)
print("FMRES", json.dumps(res))
