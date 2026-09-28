"""Residual of rigid faces with stacked rib lines, for several bind mid-line designs and a general
6-DOF face fit (faces may leave their rib line: cracks shared between valley and mountain folds)."""
import numpy as np
from math import radians, sin, cos, tan, acos, sqrt
np.set_printoptions(precision=4, suppress=True)
alpha0 = radians(6.528); beta = radians(3.472)
t = 0.6144
R = np.array([82.0, 109.0, 136.0, 163.0, 190.0])
def rz(ang):
    c, s = cos(ang), sin(ang); return np.array([[c,-s,0],[s,c,0],[0,0,1.0]])
def rot_about_line(P, p0, u, th):
    u = u/np.linalg.norm(u); c, s = cos(th), sin(th); X = P - p0
    return p0 + X*c + np.cross(u, X)*s + np.outer(X@u, u)*(1-c)
def unstacked_mid_dir(alpha):
    g = acos(cos(beta)/cos(alpha/2)); return np.array([cos(g), 0.0, sin(g)])   # bisector along +x
def bind(design):
    uA = np.array([cos(-alpha0/2), sin(-alpha0/2), 0]); uB = np.array([cos(alpha0/2), sin(alpha0/2), 0])
    A = R[:,None]*uA; B = R[:,None]*uB + np.array([0,0,-t])
    v = unstacked_mid_dir(alpha0)
    if design == "b":     # straight line through the axis midpoint
        M = R[:,None]*v + np.array([0,0,-t/2])
    elif design == "c":   # through rib A's axis point
        M = R[:,None]*v
    return A, B, M
def solve(A0, B0, M0, alpha, mode, x0):
    """mode 'hinge': faces rotate about their rib lines (2 unknowns); mismatch only at mid.
       mode 'free': each face a rigid 6-DOF body; residual = its rib copies vs the rib line points +
       its mid copies vs the other face's mid copies."""
    dA = (-alpha/2) - (-alpha0/2); dB = (alpha/2) - (alpha0/2)
    A = A0 @ rz(dA).T; B = B0 @ rz(dB).T
    uA = A[1]-A[0]; uB = B[1]-B[0]
    MA = M0 @ rz(dA).T; MB = M0 @ rz(dB).T
    if mode == "hinge":
        def res(x):
            return (rot_about_line(MA, A[0], uA, x[0]) - rot_about_line(MB, B[0], uB, x[1])).ravel()
    else:
        def rv(w):
            th = np.linalg.norm(w)
            if th < 1e-15: return np.eye(3)
            k = w/th; K = np.array([[0,-k[2],k[1]],[k[2],0,-k[0]],[-k[1],k[0],0]])
            return np.eye(3) + sin(th)*K + (1-cos(th))*K@K
        def res(x):
            RA = rv(x[0:3]); RB = rv(x[6:9])
            # face A rigid body posed: pivot on its first rib point
            fa_r = (A - A[0]) @ RA.T + A[0] + x[3:6]
            fa_m = (MA - A[0]) @ RA.T + A[0] + x[3:6]
            fb_r = (B - B[0]) @ RB.T + B[0] + x[9:12]
            fb_m = (MB - B[0]) @ RB.T + B[0] + x[9:12]
            return np.concatenate([(fa_r - A).ravel(), (fb_r - B).ravel(), (fa_m - fb_m).ravel()])
    x = np.array(x0, float)
    for it in range(80):
        r = res(x); J = np.zeros((len(r), len(x))); e = 1e-7
        for i in range(len(x)):
            d = x.copy(); d[i] += e; J[:, i] = (res(d)-r)/e
        step = np.linalg.lstsq(J, -r, rcond=None)[0]; x += step
        if np.abs(step).max() < 1e-13: break
    r = res(x)
    if mode == "hinge":
        return x, np.linalg.norm(r.reshape(-1,3), axis=1).max()
    rr = r.reshape(-1,3)
    return x, np.linalg.norm(rr, axis=1).max()
ss = list(np.linspace(1, 0.2, 9)) + list(np.linspace(0.18, 0.0, 19))
for design in ("b", "c"):
    for mode in ("hinge", "free"):
        A0, B0, M0 = bind(design)
        x = np.zeros(2 if mode == "hinge" else 12); worst = 0; rows = []
        for s in ss:
            x, m = solve(A0, B0, M0, alpha0*s, mode, x); worst = max(worst, m); rows.append((25*np.degrees(alpha0*s), m))
        print(design, mode, "worst %.4f" % worst, " ".join("%.1f:%.3f" % r for r in rows[::3]))
