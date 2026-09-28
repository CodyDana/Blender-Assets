# final debug overlay for b7 results.
#  yellow  = silhouette edge segments (tip vertex -> notch vertex), fitted lines
#  cyan    = bevel crease lines (flat-face boundary) where a separate band was detected
#  green   = sharp-tip vertices (line intersections); orange = measured tip ends / notch bottoms
#  magenta = sharp-notch vertices; red dots = notch boundary points; white = fitted notch fillet arcs
#  blue    = tip-vertex circle and notch-vertex circle + centre
import bpy, sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
res = json.load(open(os.path.join(OUT, "b7_results.json")))
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float32)
H, W, _ = rgb.shape
def save(img, path):
    h, w, _ = img.shape
    im = bpy.data.images.new("o", w, h, alpha=True)
    aa = np.ones((h, w, 4), np.float32); aa[..., :3] = np.clip(img, 0, 1)
    im.pixels.foreach_set(aa[::-1].ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
prims = []
T = {int(k): v for k, v in res["tips"].items()}; N = {int(k): v for k, v in res["notches"].items()}
for name, e in res["edges"].items():
    tk, nk = int(name[1]), int(name.split("-N")[1])
    A = np.array(T[tk]["vertex"]); B = np.array(N[nk]["vertex"])
    prims.append(("seg", (A, B), (1, 1, 0)))
    if e.get("crease_line"):
        m, d = np.array(e["crease_line"][0]), np.array(e["crease_line"][1])
        # draw crease from near the tip over 70% of the edge
        sA = np.dot(A - m, d); sB = np.dot(B - m, d)
        prims.append(("seg", (m + d * sA, m + d * (sA + 0.7 * (sB - sA))), (0, 1, 1)))
for k, t in T.items():
    prims.append(("pt", np.array(t["vertex"]), (0, 1, 0)))
    if t.get("end_pt"): prims.append(("pt", np.array(t["end_pt"]), (1, 0.55, 0)))
for k, t in N.items():
    prims.append(("pt", np.array(t["vertex"]), (1, 0, 1)))
    for p in t["boundary_pts"]: prims.append(("dot", np.array(p), (1, 0, 0)))
    if t.get("bottom_pt"): prims.append(("pt", np.array(t["bottom_pt"]), (1, 0.55, 0)))
    rho = t["fillet_radius_px"]
    if rho > 0:
        V = np.array(t["vertex"]); bis = np.array(t["bisector"]); half = np.radians(t["opening_deg"] / 2)
        C = V + bis * rho / np.sin(half)
        a0 = np.arctan2(*(V - C)[::-1]); sweep = (np.pi - 2 * half) / 2
        prims.append(("arc", (C, rho, a0 - sweep, a0 + sweep), (1, 1, 1)))
c = res["centre"]
prims.append(("circle", (np.array(c["tip_circle_centre"]), c["tip_circle_R_px"]), (0.3, 0.5, 1)))
prims.append(("circle", (np.array(c["notch_circle_centre"]), c["notch_circle_R_px"]), (0.3, 0.5, 1)))
prims.append(("pt", np.array(c["tip_circle_centre"]), (0.3, 0.5, 1)))

def render(x0, y0, x1, y1, sc, dim=1.0):
    img = np.repeat(np.repeat(rgb[y0:y1, x0:x1], sc, 0), sc, 1).copy() * dim
    h, w, _ = img.shape
    def put(X, Y, col, r=0):
        X = int(round(X)); Y = int(round(Y))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if 0 <= X + dx < w and 0 <= Y + dy < h: img[Y + dy, X + dx] = col
    tr = lambda p: ((p[0] - x0 + 0.5) * sc - 0.5, (p[1] - y0 + 0.5) * sc - 0.5)
    for kind, dat, col in prims:
        if kind == "seg":
            A, B = dat; Ln = np.hypot(*(B - A))
            for s in np.arange(0, 1, 0.4 / (Ln * sc)):
                X, Y = tr(A + (B - A) * s); put(X, Y, col)
        elif kind in ("circle", "arc"):
            if kind == "circle": C, r = dat; a0, a1 = 0, 2 * np.pi
            else: C, r, a0, a1 = dat
            for th in np.arange(a0, a1, 0.4 / (r * sc)):
                X, Y = tr(C + r * np.array([np.cos(th), np.sin(th)])); put(X, Y, col)
        elif kind == "pt":
            X, Y = tr(dat); put(X, Y, col, r=max(1, sc // 2 + 1))
        elif kind == "dot":
            X, Y = tr(dat); put(X, Y, col, r=max(0, sc // 4))
    return img
os.makedirs(os.path.join(OUT, "crops"), exist_ok=True)
save(render(0, 0, W, H, 1, 0.85), os.path.join(OUT, "debug_overlay.png"))
for k, t in T.items():
    V = np.array(t["vertex"]); x0 = int(V[0]) - 45; y0 = int(V[1]) - 45
    x0 = min(max(x0, 0), W - 90); y0 = min(max(y0, 0), H - 90)
    save(render(x0, y0, x0 + 90, y0 + 90, 5), os.path.join(OUT, "crops", "final_tip%d.png" % k))
for k, t in N.items():
    V = np.array(t["vertex"]); x0 = int(V[0]) - 40; y0 = int(V[1]) - 40
    x0 = min(max(x0, 0), W - 80); y0 = min(max(y0, 0), H - 80)
    save(render(x0, y0, x0 + 80, y0 + 80, 5), os.path.join(OUT, "crops", "final_notch%d.png" % k))
