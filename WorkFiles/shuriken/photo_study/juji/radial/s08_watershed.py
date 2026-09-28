"""Marker-controlled watershed on the colour-gradient magnitude.

Object marker : strong warm chromaticity (well above the background's 99.9th pct, 0.065) -> opened,
                largest component, enclosed dark panels filled, eroded 3 px.
Background mk : everything farther than 30 px from a generous rough mask (warm>0.06 | dark>0.12).
The unknown band between them is flooded in order of gradient magnitude, so the boundary settles on
the highest gradient ridge separating object from background (soft shadow/halo gradients are low and
get flooded by the background label).
"""
import sys, os, heapq
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
seg = np.load(os.path.join(jlib.OUT, "seg.npz"))
feat = np.load(os.path.join(jlib.OUT, "feat.npz"))
warm = feat["warm"]
grad = feat["grad"]
rough = np.load(os.path.join(jlib.OUT, "rough_mask.npy"))
sigma_tag = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else "g15"


def box(img, r):
    k = 2 * r + 1
    p = np.pad(img, r, mode='edge').astype(np.float64)
    c = np.cumsum(p, 0); c = np.concatenate([np.zeros_like(c[:1]), c], 0); v = (c[k:] - c[:-k]) / k
    c = np.cumsum(v, 1); c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)


warm_s = box(warm, 2)
om = warm_s > 0.10
om = jlib.opening(om, 2)
om = jlib.largest_component(om)
om, _ = jlib.fill_holes(om)
om = jlib.erode(om, 3)
bm = ~jlib.dilate(rough, 30)
# the image border row 0 at the top tip: do not force background there (tip is clipped by the scan edge)
print("object marker px", om.sum(), "bg marker px", bm.sum())

lab = np.zeros((H, W), np.int8)
lab[om] = 1
lab[bm] = 2
g = grad
# priority flood
heap = []
cnt = 0
seed = (lab > 0)
edge_seed = seed & ~jlib.erode(seed, 1)  # only boundary pixels of markers need to be in the heap initially
ys, xs = np.nonzero(edge_seed)
inq = np.zeros((H, W), bool)
inq[seed] = True
for y, x in zip(ys.tolist(), xs.tolist()):
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W and not inq[ny, nx]:
            inq[ny, nx] = True
            heapq.heappush(heap, (float(g[ny, nx]), cnt, ny, nx))
            cnt += 1
gl = g.tolist()
labl = lab  # numpy access in loop is slow-ish but fine
while heap:
    v, _, y, x = heapq.heappop(heap)
    # assign label of neighbouring labelled pixel (prefer object if tie? take the first labelled neighbour)
    L = 0
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W:
            l2 = labl[ny, nx]
            if l2:
                L = l2
                break
    labl[y, x] = L
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W and not inq[ny, nx]:
            inq[ny, nx] = True
            heapq.heappush(heap, (max(v, gl[ny][nx]) if False else gl[ny][nx], cnt, ny, nx))
            cnt += 1

obj = labl == 1
obj = jlib.largest_component(obj)
obj, holes = jlib.fill_holes(obj)
print("watershed object px", obj.sum(), "enclosed holes px", holes.sum())
np.save(os.path.join(jlib.OUT, "mask_ws.npy"), obj)
np.save(os.path.join(jlib.OUT, "marker_obj.npy"), om)
jlib.save_png(os.path.join(jlib.OUT, "mask_ws.png"), obj)
ov = a.copy()
ov[jlib.boundary(obj)] = [0, 1, 0]
ov[jlib.boundary(om)] = [1, 0, 1]
ov[jlib.boundary(~bm)] = [0, 0.6, 1]
jlib.save_png(os.path.join(jlib.OUT, "dbg_ws_overlay.png"), ov)
