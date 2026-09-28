"""Top arm: dark slit along the axis measured as a luminance valley across the arm (colour segmentation fails there)."""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load().astype(float); L = rgb @ np.array([0.2126, 0.7152, 0.0722])
O = json.load(open(ROOT + "outline_measurements.json")); c0 = np.array(O["centre_px"])
Q = np.load(ROOT + "contour_refined.npy")
for name in ("top", "bottom", "right"):
    v = O["axes"][name]; d = np.array([np.cos(np.radians(v["dir_deg_imagecoords"])), np.sin(np.radians(v["dir_deg_imagecoords"]))]); p = np.array([-d[1], d[0]])
    print(name)
    for u in range(300, 650, 20):
        t = line_poly_intersections(Q, c0 + u * d, p); neg = t[t < 0]; pos = t[t > 0]
        if not len(neg) or not len(pos): continue
        vs = np.arange(neg.max() + 3, pos.min() - 3, 0.5)
        prof = bilinear(L, c0[0] + u * d[0] + vs * p[0], c0[1] + u * d[1] + vs * p[1])
        k = np.exp(-np.arange(-4, 5) ** 2 / 4.0); k /= k.sum(); ps = np.convolve(np.pad(prof, 4, mode="edge"), k, "valid")
        c = np.abs(vs) < 35
        j = np.nonzero(c)[0][np.argmin(ps[c])]
        side = np.median(ps[(np.abs(vs) > 25) & (np.abs(vs) < 55)]) if ((np.abs(vs) > 25) & (np.abs(vs) < 55)).any() else np.nan
        depth = side - ps[j]; half = ps[j] + depth / 2
        a = j
        while a > 0 and ps[a] < half: a -= 1
        b = j
        while b < len(ps) - 1 and ps[b] < half: b += 1
        print(f"  u={u} ({u/660.5:.2f}R) valley v={vs[j]:.1f} Lmin={ps[j]:.3f} sideL={side:.3f} depth={depth:.3f} width@half={(b-a)*0.5:.1f}px")
