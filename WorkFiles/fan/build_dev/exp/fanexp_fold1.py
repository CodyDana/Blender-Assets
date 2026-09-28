import sys, time, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN, build_to
from props_lib import fan_fold as F
import json
#
t0 = time.time()
fs = F.FoldSolver(FAN)
tpl = fs.tpl
def leaf_quads():
    Q = []
    n = FAN.n_sticks
    for i in range(n - 1):
        Q.append(("A", i, [tpl.rib_pts[i,0], tpl.rib_pts[i,1], tpl.mid_pts[i,1], tpl.mid_pts[i,0]]))
        Q.append(("B", i, [tpl.mid_pts[i,0], tpl.mid_pts[i,1], tpl.rib_pts[i+1,1], tpl.rib_pts[i+1,0]]))
    return Q
Q = leaf_quads()
ss = list(np.linspace(1, 0.1, 46)) + list(np.geomspace(0.1, 1e-4, 60)) + [0.0]
worst = {}
for s in ss:
    Ts = fs.face_T(float(s))
    tris = []; owner = []
    for j, (kind, i, q) in enumerate(Q):
        P = F.apply(Ts[j], np.array(q))
        tris += [[P[0], P[1], P[2]], [P[0], P[2], P[3]]]; owner += [j, j]
    tris = np.array(tris); owner = np.array(owner)
    nhit, ex = F.count_intersections(tris, tris, same=True, exclude=lambda a, b: np.abs(owner[a] - owner[b]) <= 1)
    g = fs.solve(float(s))
    # dihedral at mid fold (face 0|1) and valley (face 1|2) at inner and outer
    P0 = [F.apply(Ts[j], np.array(Q[j][2])) for j in range(3)]
    dm = F.dihedral_deg(P0[0][3], P0[0][2], P0[0][0], P0[1][3])   # mid edge (inner->outer), q: rib0 inner, rib1 inner
    dv = F.dihedral_deg(P0[1][3], P0[1][2], P0[1][0], P0[2][3])
    # pages side: lateral of mid0 outer relative to leaf line 0 direction
    lam0 = FAN.leaf_line_deg(0, s)*math.pi/180
    m = P0[0][2]; lat = -m[0]*math.sin(lam0) + m[1]*math.cos(lam0)
    print(f"s={s:.5f} open={FAN.opening_at(s):7.3f} crack={max(g.crack_mm.values()):.4f} hits={nhit} dih_mid={dm:.1f} dih_val={dv:.1f} mid_z={m[2]-tpl.z[0]:.3f} mid_lat={lat:.3f}")
    worst[s] = max(g.crack_mm.values())
print("worst crack", max(worst.values()), "time", time.time()-t0)
