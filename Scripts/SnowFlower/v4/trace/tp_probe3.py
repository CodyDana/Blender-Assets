import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_crown as C
T = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work/trace.json"))
cr = C.Crown(T["silhouette_rows"], T["silhouette_sub"])
rows = np.arange(84, 130, 0.25)
for x in (10.0, 25.0, 35.0):
    P = cr.map(np.full(len(rows), x), rows, np.full(len(rows), 2.0))
    y = P[:, 1]; dz = np.gradient(y, rows)
    print("x", x, "dy/drow:", np.round(dz[::4], 3))
A, B, c, b = cr.params(rows, np.ones_like(rows))
print("A", np.round(A[::4], 2))
