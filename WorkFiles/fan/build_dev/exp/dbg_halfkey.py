import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
fs = F.FoldSolver(FAN)
ease = lambda u: u*u*(3-2*u)
def quat(R):
    t = np.trace(R)
    w = math.sqrt(max(0, 1 + t)) / 2
    x = (R[2,1]-R[1,2])/(4*w); y = (R[0,2]-R[2,0])/(4*w); z = (R[1,0]-R[0,1])/(4*w)
    return np.array([w, x, y, z])
def slerp(q0, q1, u):
    d = q0 @ q1
    if d < 0: q1 = -q1; d = -d
    th = math.acos(min(1, d))
    if th < 1e-9: return q0
    return (math.sin((1-u)*th)*q0 + math.sin(u*th)*q1)/math.sin(th)
def qmat(q):
    w,x,y,z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],[2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],[2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
for fa, fb in ((8, 9), (1, 2)):
    sa, sb = ease(fa/15), ease(fb/15)
    sm = 0.5*(sa+sb)
    Fa, Fb, Fm = fs.face_T(sa), fs.face_T(sb), fs.face_T(sm)
    for j in (0, 1, 2, 24, 25):
        k = j//2 + j%2
        head = np.array([0, 0, fs.tpl.z[k]])
        H = np.eye(4); H[:3,3] = head; Hi = np.linalg.inv(H)
        A, B = Hi@Fa[j]@H, Hi@Fb[j]@H
        qa, qb = quat(A[:3,:3]), quat(B[:3,:3])
        ang = 2*math.degrees(math.acos(min(1, abs(qa@qb))))
        M = np.eye(4); M[:3,:3] = qmat(slerp(qa, qb, 0.5)); M[:3,3] = 0.5*(A[:3,3]+B[:3,3])
        Ti = H@M@Hi
        q = np.vstack([fs.tpl.rib_pts[k], fs.tpl.mid_pts[j//2]])
        err = np.linalg.norm(F.apply(Ti, q) - F.apply(Fm[j], q), axis=1).max()
        print(f"frames {fa}-{fb} face {j}: key-to-key rotation {ang:.2f} deg, translation at head {np.linalg.norm(A[:3,3]):.4f} {np.linalg.norm(B[:3,3]):.4f}, half-key error {err:.4f} mm")
