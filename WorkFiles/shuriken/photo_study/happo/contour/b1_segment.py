# Method B step 1: independent segmentation of Happo.JPG
# Otsu on luminance + Otsu on saturation, largest component, border flood fill for holes.
# Run: blender -b --factory-startup --python b1_segment.py
import bpy, numpy as np, os, json, sys
from collections import deque

SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Happo.JPG"
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"

img = bpy.data.images.load(SRC, check_existing=False)
W, H = img.size
px = np.empty(W * H * 4, dtype=np.float32)
img.pixels.foreach_get(px)
rgb = px.reshape(H, W, 4)[::-1, :, :3].copy()   # top-origin rows
np.save(os.path.join(OUT, "rgb.npy"), rgb)

R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
L = 0.2126 * R + 0.7152 * G + 0.0722 * B
mx = rgb.max(axis=2); mn = rgb.min(axis=2)
S = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)

def otsu(v, bins=256):
    h, e = np.histogram(v.ravel(), bins=bins, range=(0, 1))
    c = (e[:-1] + e[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0
    m0 = np.cumsum(h * c); mt = m0[-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        mu0 = m0 / w0; mu1 = (mt - m0) / w1
        sb = w0 * w1 * (mu0 - mu1) ** 2
    sb = np.nan_to_num(sb)
    return c[np.argmax(sb)], h, c

tL, hL, cL = otsu(L)
tS, hS, cS = otsu(S)
print("image", W, H)
print("otsu L", tL, "otsu S", tS)
# border statistics (background sample)
bd = np.concatenate([L[:5].ravel(), L[-5:].ravel(), L[:, :5].ravel(), L[:, -5:].ravel()])
bs = np.concatenate([S[:5].ravel(), S[-5:].ravel(), S[:, :5].ravel(), S[:, -5:].ravel()])
print("border L mean/min/max", bd.mean(), bd.min(), bd.max(), " S mean/max", bs.mean(), bs.max())
# histogram summary
for name, h, c in (("L", hL, cL), ("S", hS, cS)):
    hh = h.reshape(32, 8).sum(1)
    print(name, "hist32", list(hh))

fg = (L < tL) | (S > tS)
print("fg frac L-only", (L < tL).mean(), "S-only extra", (fg & ~(L < tL)).mean())

# connected components (4-conn) of fg -> keep largest
def largest_component(m):
    Hh, Ww = m.shape
    lab = np.zeros(m.shape, np.int32)
    cur = 0; sizes = {}
    ys, xs = np.nonzero(m)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        q = deque([(y0, x0)]); lab[y0, x0] = cur; n = 0
        while q:
            y, x = q.popleft(); n += 1
            if y > 0 and m[y-1, x] and not lab[y-1, x]: lab[y-1, x] = cur; q.append((y-1, x))
            if y < Hh-1 and m[y+1, x] and not lab[y+1, x]: lab[y+1, x] = cur; q.append((y+1, x))
            if x > 0 and m[y, x-1] and not lab[y, x-1]: lab[y, x-1] = cur; q.append((y, x-1))
            if x < Ww-1 and m[y, x+1] and not lab[y, x+1]: lab[y, x+1] = cur; q.append((y, x+1))
        sizes[cur] = n
    return lab, sizes

lab, sizes = largest_component(fg)
big = max(sizes, key=sizes.get)
ss = sorted(sizes.values(), reverse=True)
print("n fg components", len(sizes), "largest sizes", ss[:6])
piece = lab == big

# holes: background components not connected to the image border
bg = ~piece
blab, bsizes = largest_component(bg)
border_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]]))) - {0}
holes = {k: v for k, v in bsizes.items() if k not in border_labels}
print("background components", len(bsizes), "touching border", len(border_labels), "enclosed holes (sizes)", sorted(holes.values(), reverse=True)[:10])
hole_info = []
for k, v in holes.items():
    yy, xx = np.nonzero(blab == k)
    hole_info.append(dict(area=int(v), cx=float(xx.mean()), cy=float(yy.mean())))
filled = piece | np.isin(blab, list(holes.keys())) if holes else piece.copy()
np.save(os.path.join(OUT, "mask_raw.npy"), piece)
np.save(os.path.join(OUT, "mask_filled.npy"), filled)
np.save(os.path.join(OUT, "L.npy"), L.astype(np.float32))
np.save(os.path.join(OUT, "S.npy"), S.astype(np.float32))
json.dump(dict(W=W, H=H, otsu_L=float(tL), otsu_S=float(tS), holes=hole_info,
               n_fg_components=len(sizes), largest=int(ss[0]), second=int(ss[1]) if len(ss) > 1 else 0),
          open(os.path.join(OUT, "b1_segment.json"), "w"), indent=1)

# save mask png (white piece, black bg; holes red)
def save_png(arr_rgb_top, path):
    h, w, _ = arr_rgb_top.shape
    im = bpy.data.images.new("out", w, h, alpha=True)
    a = np.ones((h, w, 4), np.float32)
    a[..., :3] = arr_rgb_top
    im.pixels.foreach_set(a[::-1].ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()

m = np.zeros((H, W, 3), np.float32)
m[piece] = 1.0
if holes:
    hm = np.isin(blab, list(holes.keys()))
    m[hm] = (1, 0, 0)
save_png(m, os.path.join(OUT, "mask.png"))
print("done")
