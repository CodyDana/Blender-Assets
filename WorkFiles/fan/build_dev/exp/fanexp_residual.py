"""Experiment: residual of rigid-face folding with stacked rib lines (one gap, translation-invariant)."""
import numpy as np
from math import radians, sin, cos
np.set_printoptions(precision=4, suppress=True)

alpha0 = radians(6.528); beta = radians(3.472)
t = 0.6144                       # leaf-line z pitch (mm)
R = np.array([82.0, 109.0, 136.0, 163.0, 190.0])

def rib_pts(phi, z):
    return np.stack([R*cos(phi), R*sin(phi), np.full_like(R, z)], 1)

def bind_mid(A, B, up):
    """point at chord w from A and B, on the 'up' side"""
    out = []
    for a, b, r in zip(A, B, R):
        w = 2*r*sin(beta/2)
        m = 0.5*(a+b); d = b-a; L = np.linalg.norm(d); dh = d/L
        h = np.sqrt(max(w*w - L*L/4, 0))
        # perpendicular within plane spanned by up and the radial direction removed
        rad = m/np.linalg.norm(m[:2]).clip(1e-9); rad[2] = 0; rad/=np.linalg.norm(rad)
        # candidate direction: component of 'up' orthogonal to d and to rad
        n = np.cross(dh, rad); n /= np.linalg.norm(n)
        if n @ up < 0: n = -n
        out.append(m + h*n)
    return np.array(out)

def rot_about_line(P, p0, u, th):
    u = u/np.linalg.norm(u); c, s = cos(th), sin(th)
    X = P - p0
    return p0 + X*c + np.cross(u, X)*s + np.outer(X@u, u)*(1-c)

# bind
A0 = rib_pts(-alpha0/2, 0.0); B0 = rib_pts(alpha0/2, -t)
M0 = bind_mid(A0, B0, np.array([0, 0, 1.0]))
print("bind depth (mm):", (M0[:,2] - 0.5*(A0[:,2]+B0[:,2])))
# per-face-bone: face A = (A0, M0) rotates about rib line A; face B about rib B
def solve_faces(alpha, thA0, thB0):
    uA = np.array([cos(-alpha/2), sin(-alpha/2), 0]); uB = np.array([cos(alpha/2), sin(alpha/2), 0])
    # map bind faces to new rib directions: rotate about z by the rib's rotation first
    def rz(P, ang):
        c, s = cos(ang), sin(ang); Rm = np.array([[c,-s,0],[s,c,0],[0,0,1]]); return P@Rm.T
    MA = rz(M0, (-alpha/2) - (-alpha0/2)); MB = rz(M0, (alpha/2) - (alpha0/2))
    pA = np.array([0,0,0.0]); pB = np.array([0,0,-t])
    def resid(th):
        a = rot_about_line(MA, pA, uA, th[0]); b = rot_about_line(MB, pB, uB, th[1])
        return (a-b).ravel()
    th = np.array([thA0, thB0], float)
    for it in range(60):
        r = resid(th); J = np.zeros((len(r), 2)); e = 1e-7
        for i in range(2):
            d = th.copy(); d[i] += e; J[:, i] = (resid(d)-r)/e
        step = np.linalg.lstsq(J, -r, rcond=None)[0]
        th += step
        if np.abs(step).max() < 1e-12: break
    r = resid(th).reshape(-1,3)
    return th, np.linalg.norm(r, axis=1)

th = np.zeros(2)
print(" total_open  alpha_gap  thA  thB   max_mismatch_mm  per-ring")
for s in list(np.linspace(1, 0.2, 9)) + list(np.linspace(0.18, 0.0, 19)):
    a = alpha0*s
    th, mis = solve_faces(a, *th)
    print(f"{25*np.degrees(a):8.3f} {np.degrees(a):8.4f} {np.degrees(th[0]):7.2f} {np.degrees(th[1]):7.2f}  {mis.max():.4f}  {mis}")
