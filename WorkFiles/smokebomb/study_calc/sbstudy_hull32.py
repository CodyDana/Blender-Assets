"""SMOKEBOMB_STUDY.md section 8, collision: a 32-vertex hull whose 60 faces are ALL tangent to the sphere r_max
(the pentakis dodecahedron = the polar dual of a truncated icosahedron), against the geodesic hulls in sbstudy_calc.json.
Pure numpy.  Appends the result to sbstudy_calc.json under hulls.cases.pentakis_dodecahedron_32v."""
import json, math, os, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
p = (1 + 5 ** 0.5) / 2
I = np.array([(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
              (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)], float)
edge = min(np.linalg.norm(I[0] - I[j]) for j in range(1, 12))
N = []
for i, j in itertools.combinations(range(12), 2):
    if abs(np.linalg.norm(I[i] - I[j]) - edge) < 1e-9:
        for t in (1 / 3, 2 / 3):
            q = I[i] + t * (I[j] - I[i]); N.append(q / np.linalg.norm(q))
N = np.array(N)                       # 60 face normals, tangent planes n.x = r_max
r_max = 36.0
# vertices: every triple of planes meeting in a point inside all other half-spaces
verts = []
for a, b, c in itertools.combinations(range(60), 3):
    M = N[[a, b, c]]
    if abs(np.linalg.det(M)) < 1e-9: continue
    x = np.linalg.solve(M, np.full(3, r_max))
    if np.all(N @ x <= r_max + 1e-7) and not any(np.linalg.norm(x - v) < 1e-6 for v in verts):
        verts.append(x)
verts = np.array(verts)
rad = np.linalg.norm(verts, axis=1)
g = np.linspace(-r_max * 1.3, r_max * 1.3, 221)
X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
inside = np.all(pts @ N.T <= r_max, axis=1)
vol = inside.sum() * (g[1] - g[0]) ** 3 / 1000.0
V = lambda r: 4 / 3 * math.pi * r ** 3 / 1000.0
res = {"vertices": len(verts), "faces": 60, "vertex_radius_mm": [round(float(rad.min()), 3), round(float(rad.max()), 3)],
       "max_gap_over_rmax_mm": round(float(rad.max() - r_max), 3), "volume_cm3": round(vol, 1),
       "volume_over_sphere_rmax": round(vol / V(r_max), 3), "volume_over_ball_R35": round(vol / V(35.0), 3)}
d = json.load(open(os.path.join(HERE, "sbstudy_calc.json")))
d["hulls"]["cases"]["pentakis_dodecahedron_32v"] = res
json.dump(d, open(os.path.join(HERE, "sbstudy_calc.json"), "w"), indent=1)
print(json.dumps(res))
