# Method B step 2: edge-magnitude map (Sobel on Gaussian-smoothed luminance) for inspection
import bpy, numpy as np, os
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
L = np.load(os.path.join(OUT, "L.npy")).astype(np.float64)

def gauss1d(s):
    r = int(3 * s + 0.5); x = np.arange(-r, r + 1); k = np.exp(-x * x / (2 * s * s)); return k / k.sum()
def conv_sep(A, k):
    r = len(k) // 2
    P = np.pad(A, r, mode='edge')
    T = sum(k[i] * P[:, i:i + A.shape[1]] for i in range(len(k)))[r:-r or None, :] if False else None
    T = np.zeros((P.shape[0], A.shape[1]))
    for i in range(len(k)): T += k[i] * P[:, i:i + A.shape[1]]
    U = np.zeros(A.shape)
    for i in range(len(k)): U += k[i] * T[i:i + A.shape[0], :]
    return U
Ls = conv_sep(L, gauss1d(1.2))
P = np.pad(Ls, 1, mode='edge')
gx = (P[:-2, 2:] + 2 * P[1:-1, 2:] + P[2:, 2:] - P[:-2, :-2] - 2 * P[1:-1, :-2] - P[2:, :-2]) / 8
gy = (P[2:, :-2] + 2 * P[2:, 1:-1] + P[2:, 2:] - P[:-2, :-2] - 2 * P[:-2, 1:-1] - P[:-2, 2:]) / 8
G = np.hypot(gx, gy)
np.save(os.path.join(OUT, "Ls.npy"), Ls.astype(np.float32))
np.save(os.path.join(OUT, "grad.npy"), G.astype(np.float32))
print("grad percentiles", np.percentile(G, [50, 90, 95, 99, 99.5, 99.9]))
H, W = L.shape
im = bpy.data.images.new("g", W, H, alpha=True)
v = np.clip(G / 0.08, 0, 1).astype(np.float32)
a = np.ones((H, W, 4), np.float32); a[..., 0] = v; a[..., 1] = v; a[..., 2] = v
im.pixels.foreach_set(a[::-1].ravel())
im.filepath_raw = os.path.join(OUT, "grad.png"); im.file_format = 'PNG'; im.save()
