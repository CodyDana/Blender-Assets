import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L
OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT,"lum.npy")); bg = np.load(os.path.join(OUT,"bg_lum.npy")); tex = np.load(os.path.join(OUT,"tex.npy"))
G = json.load(open(os.path.join(OUT,"geom.json")))
C = np.array(G["centre"])
want = sys.argv[sys.argv.index("--")+1:]
for v in G["vertices"]:
    if v["name"] not in want: continue
    X = np.array(v["X"])
    u = (X - C)/np.linalg.norm(X - C)   # outward
    print("%s  virtual X=(%.1f,%.1f) r=%.1f  (d>0 = beyond the virtual vertex, outward)" % (v["name"], X[0], X[1], v["r"]))
    for d in np.arange(-45, 25.01, 2.5):
        p = X + d*u
        if not (0 <= p[0] < 1216 and 0 <= p[1] < 1223):
            print("   d %+6.1f  outside image"); continue
        lu = L.bilinear(lum, np.array([p[0]]), np.array([p[1]]))[0]
        b = L.bilinear(bg, np.array([p[0]]), np.array([p[1]]))[0]
        tx = L.bilinear(tex, np.array([p[0]]), np.array([p[1]]))[0]
        print("   d %+6.1f  (%6.1f,%6.1f) lum %.3f bg %.3f  dark %+.3f  tex %.4f  %s" % (d, p[0], p[1], lu, b, b-lu, tx, "MAT" if (lu < b-0.10 and tx > 0.012) else ""))
