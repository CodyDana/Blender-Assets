import json, numpy as np
SPEC = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/reference_spec.json"))
CX, CY, R = 627.38, 628.92, 464.11
E = {}
for s in SPEC["strips"]:
    for e, v in s.get("edge_control_points", {}).items():
        E.setdefault(e, np.array(v["control_img"], float))
def i2s(p):
    x = (p[:, 0] - CX) / R; y = -(p[:, 1] - CY) / R
    r2 = np.clip(x * x + y * y, 0, 0.99999)
    return np.stack([x, y, np.sqrt(1 - r2)], 1)
def s2i(v): return np.stack([CX + R * v[:, 0], CY - R * v[:, 1]], 1)
N = {}
for e, pts in E.items():
    v = i2s(pts); u, s, vt = np.linalg.svd(v); n = vt[2]
    if n[1] > 0: n = -n
    N[e] = n
    proj = v - np.outer(v @ n, n); proj /= np.linalg.norm(proj, axis=1, keepdims=True)
    res = np.linalg.norm(s2i(proj) - pts, axis=1)
    print(f"{e:4s} n=({n[0]:+.3f},{n[1]:+.3f},{n[2]:+.3f}) gc_rms {np.sqrt((res**2).mean()):5.1f}px max {res.max():5.1f}")
T = np.array([0.135, 0.812, 0.568]); T /= np.linalg.norm(T)
fams = {"U": ["UA","UC","UD","UE","UF"], "U123": ["UA","UC","UD"], "R": ["LA","LC"], "D": ["D14","D57","D9","D19","D27"], "D3": ["D14","D57","D9"],
        "belt": ["WUP","WLO","BUP","BLO","CUP"], "BC": ["BUP","BLO","CUP"], "W": ["WUP","WLO","WTW"], "L": ["L3L","LIN"]}
for f, es in fams.items():
    M = np.array([N[e] for e in es]); u, s, vt = np.linalg.svd(M); p = vt[2]
    if p[2] < 0: p = -p
    ang = np.degrees(np.arcsin(np.clip(np.abs(M @ p), 0, 1)))
    im = s2i(p[None])[0]
    print(f"family {f:5s} conv point ({p[0]:+.3f},{p[1]:+.3f},{p[2]:+.3f}) img ({im[0]:.0f},{im[1]:.0f}) z={p[2]:+.2f} offsets deg {np.round(ang,1)}  ang-to-T {np.degrees(np.arccos(abs(p@T))):.1f}")
# pairwise angles between normals
names = list(N)
print("pairwise angle between edge planes (deg):")
for a in ["WUP","WLO","BUP","BLO","CUP","UA","UC","UD","UE","UF","LA","LC","L3L","D14","D57","D9","D19","D27"]:
    print(a.ljust(4), " ".join(f"{np.degrees(np.arccos(min(1,abs(N[a]@N[b])))):5.0f}" for b in ["WUP","WLO","BUP","BLO","CUP","UA","UC","UD","UE","UF","LA","LC","L3L","D14","D57","D9","D19","D27"]))
