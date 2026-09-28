"""Fillet/bluntness from where the traced outline departs from the fitted edge lines."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(OUT, "results.json")))
G = json.load(open(os.path.join(OUT, "geom.json")))
EJ = json.load(open(os.path.join(OUT, "edges_v3.json")))["edges"]
span = res["span_px"]
by_name = {ge["name"]: (np.array(ge["c"]), np.array(ge["d"]), e) for ge, e in zip(G["edges"], EJ)}
vedges = {v["name"]: v["edges"] for v in G["vertices"]}
print("vertex   kind   angle  |  departure distance L from the vertex on each edge (px)  -> fillet radius rho = L*tan(angle/2)")
for v in res["notches"] + res["tips"]:
    X = np.array(v["X"]); Ls = []
    for en in vedges[v["name"]]:
        c, d, e = by_name[en]
        n = np.array(e["n"]); nn = np.array([-d[1], d[0]])
        if np.dot(nn, n) < 0: nn = -nn
        # distance along the line from the vertex, and deviation of each traced point
        rec = []
        for r in e["rows"]:
            s = r.get("s_edge", float("nan"))
            if not np.isfinite(s): continue
            p = np.array(r["P"]) + s*n
            al = float((p - X) @ d); dev = float((p - c) @ nn)
            rec.append((abs(al), dev))
        rec.sort()
        rec = [z for z in rec if z[0] < 90]
        if not rec: Ls.append(float("nan")); continue
        # smooth deviation vs distance, find the largest L where |dev| > 1.5 px for all points closer than L
        arr = np.array(rec)
        bad = np.abs(arr[:,1]) > 1.5
        LL = 0.0
        for i in range(len(arr)):
            if bad[i]: LL = arr[i,0]
            elif arr[i,0] > LL + 6: break
        Ls.append(LL)
    b2 = math.radians(v["angle"]/2)
    rho = [l*math.tan(b2) for l in Ls]
    kind = "notch" if v in res["notches"] else "tip"
    print("%-8s %-6s %5.1f  L = %6.1f %6.1f  -> rho = %5.1f %5.1f px  (%.4f %.4f of span)" %
          (v["name"], kind, v["angle"], Ls[0], Ls[1], rho[0], rho[1], rho[0]/span, rho[1]/span))
