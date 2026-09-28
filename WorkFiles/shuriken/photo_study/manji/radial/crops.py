"""Save zoomed crops of the original (with optional mask edge) for visual inspection.
usage: blender -b --python crops.py -- name x0 y0 size scale [maskfile]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

args = sys.argv[sys.argv.index('--') + 1:]
rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
mask = None
maskfile = os.path.join(C.OUT, "mask.npy")
if os.path.exists(maskfile):
    mask = np.unpackbits(np.load(maskfile))[:h * w].reshape(h, w).astype(bool)
i = 0
while i < len(args):
    name, x0, y0, size, scale = args[i], int(args[i + 1]), int(args[i + 2]), int(args[i + 3]), int(args[i + 4])
    i += 5
    crop = rgb[y0:y0 + size, x0:x0 + size].copy()
    if mask is not None:
        mc = mask[y0:y0 + size, x0:x0 + size]
        e = mc & ~C.erode(mc, 1)
        crop2 = crop.copy()
        crop2[e] = [1, 0, 0]
        crop = np.concatenate([crop, np.ones((crop.shape[0], 4, 3), np.float32), crop2], axis=1)
    crop = np.repeat(np.repeat(crop, scale, 0), scale, 1)
    C.save_png(crop, os.path.join(C.OUT, "crop_%s.png" % name))
    print("saved", name)
