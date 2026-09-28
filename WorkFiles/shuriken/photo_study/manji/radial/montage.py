"""QA montage: crops of the original with the final (red) and colour-threshold (yellow) boundaries,
sampled at evenly spaced points along the final contour. usage: -- n_crops crop_size out_name"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
args = sys.argv[sys.argv.index('--') + 1:]
n, sz, name = int(args[0]), int(args[1]), args[2]
rgb, info = C.load_rgb(C.IMG); h, w = rgb.shape[:2]
fm = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
cm = np.unpackbits(np.load(os.path.join(C.OUT, "mask_colour.npy")))[:h * w].reshape(h, w).astype(bool)
ov = rgb.copy()
ov[cm & ~C.erode(cm, 1)] = [1.0, 0.85, 0.0]
ov[fm & ~C.erode(fm, 1)] = [1, 0, 0]
cont = C.trace_contour(fm)
idx = np.linspace(0, len(cont), n, endpoint=False).astype(int)
cols = int(np.ceil(np.sqrt(n))); rows = int(np.ceil(n / cols))
M = np.ones((rows * (sz + 4), cols * (sz + 4), 3), np.float32)
for k, i in enumerate(idx):
    x, y = cont[i]
    x0 = int(np.clip(x - sz // 2, 0, w - sz)); y0 = int(np.clip(y - sz // 2, 0, h - sz))
    r, c = divmod(k, cols)
    M[r * (sz + 4):r * (sz + 4) + sz, c * (sz + 4):c * (sz + 4) + sz] = ov[y0:y0 + sz, x0:x0 + sz]
    print("crop", k, "centre", int(x), int(y))
C.save_png(M, os.path.join(C.OUT, name))
