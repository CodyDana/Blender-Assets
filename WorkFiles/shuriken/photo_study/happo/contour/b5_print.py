import json, numpy as np
R = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour/b5_edges.json"))
for k, e in R.items():
    st = e["stations"]
    row = []
    for f0 in (0.12, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        sel = [s for s in st if abs(s["f"] - f0) < 0.026]
        b = [s["band"] for s in sel]
        nout = sum(1 for s in sel if s["outer_t"] is not None)
        sg = [s["face_sign"] for s in sel]
        row.append("%.2f:%4.1f(%s,%d)" % (f0, np.median(b) if b else -1, "+" if np.mean(sg) > 0.3 else ("-" if np.mean(sg) < -0.3 else "0"), nout))
    print("%-6s" % k, " ".join(row))
