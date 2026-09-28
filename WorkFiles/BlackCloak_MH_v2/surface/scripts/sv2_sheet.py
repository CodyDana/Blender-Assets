# Contact sheet at matched scale (2.73 mm/px): photo vs test drape (1x ortho) vs flat swatch (1x), plus x4 fabric crops
# shown two ways (as rendered with a x3 linear display gain, and per-crop stretched), plus the 0.5 mm/px close swatch.
# args: tag out_png
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import sv2_imgmetrics as M

tag, out = sys.argv[sys.argv.index("--") + 1:][:2]
S = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/"
ref = M.load("C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")
dr = M.load(S + "renders/%s_drape_1x.png" % tag)
sw = M.load(S + "renders/%s_swatch_1x.png" % tag)
cl = M.load(S + "renders/%s_swatch_close_0p5mm.png" % tag)
dj = json.load(open(S + "logs/%s_drape.json" % tag))
pj = json.load(open(S + "logs/sv2_photo_probe.json"))


def mag(a, f):
    return np.repeat(np.repeat(a, f, 0), f, 1)


def gain(c, g=3.0):
    return M.l2s(np.clip(M.s2l(c / 255.0) * g, 0, 1)) * 255


def stretch(c):
    L = M.lum(c)
    lo, hi = np.percentile(L, [1, 99])
    return np.stack([np.clip((L - lo) / max(hi - lo, 1e-6), 0, 1) * 255] * 3, -1)


def pad_to(a, h, w, v=255.0):
    o = np.full((h, w, 3), v)
    o[:min(h, a.shape[0]), :min(w, a.shape[1])] = a[:h, :w]
    return o


def label_bar(w, h=6, v=0.0):
    return np.full((h, w, 3), v)


# row 1: whole images at 1x, same pixel scale
H = max(ref.shape[0], dr.shape[0])
row1 = np.concatenate([pad_to(ref, H, ref.shape[1]), np.full((H, 8, 3), 200.0), pad_to(dr, H, dr.shape[1]),
                       np.full((H, 8, 3), 200.0), pad_to(sw, H, sw.shape[1])], 1)
# row 2: 96 px fabric crops (26 cm) x3: photo (flattest patch region), drape (its flattest patch), swatch centre
pxy = pj["flat_patches"][0]["xy"]
dxy = dj["drape_1x"]["flat_patches_xy"][0]


def crop(im, x, y, n=96):
    x = int(np.clip(x - 32, 0, im.shape[1] - n))
    y = int(np.clip(y - 32, 0, im.shape[0] - n))
    return im[y:y + n, x:x + n]


cr = [crop(ref, *pxy), crop(dr, *dxy), sw[144:240, 144:240]]
row2 = np.concatenate(sum([[mag(gain(c), 3), np.full((288, 8, 3), 200.0)] for c in cr], [])[:-1], 1)
row3 = np.concatenate(sum([[mag(stretch(c), 3), np.full((288, 8, 3), 200.0)] for c in cr], [])[:-1], 1)
W = max(row1.shape[1], row2.shape[1], 512 + 8 + 288)
rows = [pad_to(row1, row1.shape[0], W), np.full((8, W, 3), 200.0), pad_to(row2, 288, W), np.full((8, W, 3), 200.0),
        pad_to(row3, 288, W), np.full((8, W, 3), 200.0), pad_to(np.concatenate([gain(cl, 2.0), np.full((512, 8, 3), 200.0),
                                                                                  stretch(cl)], 1), 512, W)]
M.save(out, np.concatenate(rows, 0))
print("sheet", out)
