"""wd_overlay - the spec's edge control polylines drawn on the reference (measurement/preview only)."""
import sys, json, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
from wd_png import write_png
REF = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/sb_ref_srgb.npy")
SPEC = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/reference_spec.json"))
EDGES = {}
for s in SPEC["strips"]:
    for e, v in s.get("edge_control_points", {}).items():
        EDGES.setdefault(e, np.array(v["control_img"], float))
PAL = [(1,0,0),(0,1,0),(0,0.5,1),(1,1,0),(1,0,1),(0,1,1),(1,0.5,0),(0.6,0.3,1),(0.5,1,0.5),(1,0.6,0.6),(0.2,0.8,0.4),(0.9,0.9,0.9)]
def draw_poly(img, pts, col, k, x0, y0, rad=1):
    h, w = img.shape[:2]
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(*(b - a)) * k * 2) + 2
        for t in np.linspace(0, 1, n):
            x = int(round(((a[0] + (b[0]-a[0])*t) - x0) * k)); y = int(round(((a[1] + (b[1]-a[1])*t) - y0) * k))
            if x < 0 or y < 0 or x >= w or y >= h: continue
            img[max(0,y-rad):min(h,y+rad+1), max(0,x-rad):min(w,x+rad+1)] = col
    for p in pts:
        x = int(round((p[0]-x0)*k)); y = int(round((p[1]-y0)*k))
        if x < 0 or y < 0 or x >= w or y >= h: continue
        img[max(0,y-3):min(h,y+4), max(0,x-3):min(w,x+4)] = col
def overlay(x0, y0, x1, y1, k, name, gamma=0.5, edges=None):
    a = np.clip(REF[y0:y1, x0:x1, :3].astype(np.float64), 0, 1) ** gamma
    a = np.repeat(np.repeat(a, k, 0), k, 1)
    names = sorted(EDGES) if edges is None else edges
    legend = []
    for i, e in enumerate(names):
        col = PAL[i % len(PAL)]
        draw_poly(a, EDGES[e], col, k, x0, y0)
        legend.append((e, col))
    write_png(rf"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_crops/{name}.png", a)
    print(name, [(e, c) for e, c in legend])
if __name__ == "__main__":
    x0, y0, x1, y1, k = map(int, sys.argv[1:6]); name = sys.argv[6]
    edges = sys.argv[7].split(",") if len(sys.argv) > 7 else None
    overlay(x0, y0, x1, y1, k, name, 0.5, edges)
