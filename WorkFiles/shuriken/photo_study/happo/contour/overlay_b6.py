# debug overlay for b6 results: silhouette lines (yellow), face lines (cyan), notch ray points (red),
# tip vertices (green), notch vertices (magenta), tip/notch circles (blue). Full image + crops per tip/notch.
# args: -- results.json tag [full]
import bpy, sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
a = sys.argv[sys.argv.index("--") + 1:]
res = json.load(open(os.path.join(OUT, a[0]))); tag = a[1]
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float32)
H, W, _ = rgb.shape
def save(img, path):
    h, w, _ = img.shape
    im = bpy.data.images.new("o", w, h, alpha=True)
    aa = np.ones((h, w, 4), np.float32); aa[..., :3] = np.clip(img, 0, 1)
    im.pixels.foreach_set(aa[::-1].ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

# primitives in image coords (float); rendered per crop at scale
prims = []   # (kind, data, colour)
for name, e in res["edges"].items():
    for key, col in (("sil_line", (1, 1, 0)), ("face_line", (0, 1, 1))):
        if key in e and e[key]:
            m, d = np.array(e[key][0]), np.array(e[key][1])
            prims.append(("line", (m, d), col))
for k, t in res["tips"].items():
    prims.append(("pt", np.array(t["vertex"]), (0, 1, 0)))
    if t.get("end_pt"): prims.append(("pt", np.array(t["end_pt"]), (1, 0.5, 0)))
for k, t in res["notches"].items():
    prims.append(("pt", np.array(t["vertex"]), (1, 0, 1)))
    for p in t.get("ray_pts", []): prims.append(("dot", np.array(p), (1, 0, 0)))
    if t.get("bottom_pt"): prims.append(("pt", np.array(t["bottom_pt"]), (1, 0.5, 0)))
c = res["centre"]
prims.append(("circle", (np.array(c["tip_circle_centre"]), c["tip_circle_R"]), (0.3, 0.5, 1)))
prims.append(("circle", (np.array(c["notch_circle_centre"]), c["notch_circle_R"]), (0.3, 0.5, 1)))
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
        if kind == "line":
            m, d = dat
            for s in np.arange(-2000, 2000, 0.5 / sc):
                X, Y = tr(m + d * s)
                if 0 <= X < w and 0 <= Y < h: put(X, Y, col)
        elif kind == "circle":
            C, r = dat
            for th in np.arange(0, 2 * np.pi, 0.5 / (r * sc)):
                X, Y = tr(C + r * np.array([np.cos(th), np.sin(th)]))
                if 0 <= X < w and 0 <= Y < h: put(X, Y, col)
        elif kind == "pt":
            X, Y = tr(dat); put(X, Y, col, r=max(1, sc // 2 + 1))
        elif kind == "dot":
            X, Y = tr(dat); put(X, Y, col, r=max(0, sc // 3))
    return img
os.makedirs(os.path.join(OUT, "crops"), exist_ok=True)
if len(a) > 2 and a[2] == "full":
    save(render(0, 0, W, H, 1, 0.9), os.path.join(OUT, "debug_overlay.png"))
for k, t in res["tips"].items():
    V = np.array(t["vertex"]); x0 = int(V[0]) - 45; y0 = int(V[1]) - 45
    x0 = min(max(x0, 0), W - 90); y0 = min(max(y0, 0), H - 90)
    save(render(x0, y0, x0 + 90, y0 + 90, 5), os.path.join(OUT, "crops", "%s_tip%s.png" % (tag, k)))
for k, t in res["notches"].items():
    V = np.array(t["vertex"]); x0 = int(V[0]) - 40; y0 = int(V[1]) - 40
    x0 = min(max(x0, 0), W - 80); y0 = min(max(y0, 0), H - 80)
    save(render(x0, y0, x0 + 80, y0 + 80, 5), os.path.join(OUT, "crops", "%s_notch%s.png" % (tag, k)))
