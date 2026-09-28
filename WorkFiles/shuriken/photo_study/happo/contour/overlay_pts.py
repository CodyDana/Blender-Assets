# overlay detected edge points on the photo; writes full image + zoom crops
# args: -- tag spec1 spec2 ...  (spec = name:x0:y0:x1:y1:scale)
import bpy, numpy as np, os, json, sys
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
a = sys.argv[sys.argv.index("--") + 1:]
tag = a[0]
rgb = np.load(os.path.join(OUT, "rgb.npy")).copy()
R = json.load(open(os.path.join(OUT, os.environ.get("EDGEJSON", "b5_edges.json"))))
H, W, _ = rgb.shape
def save(img, path):
    h, w, _ = img.shape
    im = bpy.data.images.new("o", w, h, alpha=True)
    aa = np.ones((h, w, 4), np.float32); aa[..., :3] = np.clip(img, 0, 1)
    im.pixels.foreach_set(aa[::-1].ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
pts = []
for e in R.values():
    for p in e["pts_outer"]:
        if p[0] == p[0]: pts.append((p[0], p[1], (1, 0, 0)))
    for p in e["pts_face"]:
        if p[0] == p[0]: pts.append((p[0], p[1], (0, 1, 1)))
for spec in a[1:]:
    q = spec.split(":"); name = q[0]; x0, y0, x1, y1, sc = map(int, q[1:6])
    c = np.repeat(np.repeat(rgb[y0:y1, x0:x1], sc, 0), sc, 1).copy()
    for (x, y, col) in pts:
        X = int(round((x - x0 + 0.5) * sc - 0.5)); Y = int(round((y - y0 + 0.5) * sc - 0.5))
        if 1 <= X < c.shape[1] - 1 and 1 <= Y < c.shape[0] - 1:
            c[Y, X] = col; c[Y - 1, X] = col; c[Y, X - 1] = col
    save(c, os.path.join(OUT, "crops", tag + "_" + name + ".png"))

