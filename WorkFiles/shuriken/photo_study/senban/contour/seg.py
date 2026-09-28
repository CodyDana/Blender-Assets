# Method B segmentation for Senban.jpg: Otsu on luminance + Otsu on a yellowness
# (olive-metal vs neutral-grey backing) channel, flood fill of background from the image
# border, hole = enclosed backing-like component.  Writes mask PNG + npy.
import sys, json, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from pngio import write_png
from geom import otsu, flood, label, binary_open, binary_close

def segment(tL=None, tY=None, tag=""):
    a = np.load(D + "cache/senban_rgb.npy").astype(float)
    H, W, _ = a.shape
    L = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    Yw = (a[..., 0] + a[..., 1]) / 2 - a[..., 2]
    oL = otsu(L, rng=(0, 255)); oY = otsu(Yw, rng=(-20, 60))
    if tL is None: tL = oL
    if tY is None: tY = oY
    bglike = (L > tL) & (Yw < tY)
    border = [(0, x) for x in range(W)] + [(H - 1, x) for x in range(W)] + \
             [(y, 0) for y in range(H)] + [(y, W - 1) for y in range(H)]
    outside = flood(bglike, border)
    inner = bglike & ~outside
    # remove thin bright highlight lines / specks inside the plate, keep the see-through hole
    inner_o = binary_open(inner, 3)
    lab, n = label(inner_o)
    sizes = np.bincount(lab.ravel())[1:] if n else np.array([])
    hole = np.zeros_like(inner)
    comps = []
    for i, s in enumerate(sizes, 1):
        ys, xs = np.nonzero(lab == i)
        comps.append(dict(id=i, area=int(s), bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]))
    if n:
        k = int(np.argmax(sizes)) + 1
        hole = lab == k
        # restore pixels lost to the opening at the hole border (geodesic: within original inner)
        hole = flood(inner, list(zip(*np.nonzero(hole))))
    plate = ~outside & ~hole
    # fill small enclosed specks in the plate that are not the hole
    plate |= (inner & ~hole)
    return dict(L=L, Yw=Yw, tL=tL, tY=tY, otsuL=oL, otsuY=oY, outside=outside, hole=hole, plate=plate, comps=comps)

if __name__ == "__main__":
    r = segment()
    print("Otsu L", r["otsuL"], "Otsu Yw", r["otsuY"])
    print("inner comps (after opening)", sorted(r["comps"], key=lambda c: -c["area"])[:6])
    m = np.zeros(r["plate"].shape, np.uint8); m[r["plate"]] = 255; m[r["hole"]] = 96
    write_png(D + "senban_mask.png", m)
    np.save(D + "cache/plate_mask.npy", r["plate"]); np.save(D + "cache/hole_mask.npy", r["hole"])
    print("plate px", int(r["plate"].sum()), "hole px", int(r["hole"].sum()))
