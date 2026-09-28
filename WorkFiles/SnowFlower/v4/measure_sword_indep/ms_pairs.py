import sys, os; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
sides = sys.argv[sys.argv.index('--')+1]
OUTD = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/blind_sword/"
os.makedirs(OUTD, exist_ok=True)
ref = np.load(D+"ref_rgb.npy")
win = {"front": 215, "back": 600, "side_px": 420}
S = {k: np.load(D+"ours_sheet_%s.npy" % k) for k in win}
Mo = np.load(D+"ours_mask_front.npy")
lum = ref.mean(2); sat = ref.max(2)-ref.min(2); rfg = (lum < 0.9) | (sat > 0.08)
def ortho(view, r0, r1, c0, c1):
    x0 = win[view]
    return ref[r0:r1, c0:c1].copy(), S[view][r0:r1, c0-x0:c1-x0].copy()
from ms_fill import fill_rows
rfg = fill_rows(rfg); Mo = fill_rows(Mo)
def sil(r0, r1, c0, c1):
    a = np.where(rfg[r0:r1, c0:c1, None], 0.08, BG).repeat(3, 2).astype(np.float32)
    b = np.where(Mo[r0:r1, c0-215:c1-215, None], 0.08, BG).repeat(3, 2).astype(np.float32)
    return a, b
def panel(name, y0, y1, x0, x1):
    return ref[y0:y1, x0:x1].copy(), np.load(D+"ours_panel_%s.npy" % name)
specs = [
    (ortho("front", 0, 1225, 215, 397), 1),
    (ortho("back", 0, 1225, 600, 788), 1),
    (ortho("side_px", 0, 1225, 429, 569), 1),
    (ortho("front", 0, 345, 215, 397), 2),
    (ortho("back", 0, 345, 600, 788), 2),
    (ortho("side_px", 0, 345, 440, 570), 2),
    (ortho("front", 0, 60, 247, 327), 5),
    (ortho("front", 60, 240, 247, 327), 3),
    (ortho("front", 235, 345, 222, 352), 4),
    (ortho("front", 330, 620, 250, 330), 2),
    (ortho("front", 620, 910, 250, 330), 2),
    (ortho("front", 900, 1225, 235, 325), 2),
    (sil(0, 1225, 215, 397), 1),
    (panel("guard", 0, 515, 808, 1200), 2),
    (panel("blade", 576, 852, 808, 1200), 2),
    (panel("pommel", 900, 1190, 808, 1200), 2),
]
assert len(specs) == 16 == len(sides)
for i, ((r, o), k) in enumerate(specs):
    assert r.shape == o.shape, (i, r.shape, o.shape)
    h, w = r.shape[:2]
    if k > 1:
        r = resize(r, h*k, w*k); o = resize(o, h*k, w*k)
    L, R = (o, r) if sides[i] == 'L' else (r, o)
    gap = np.full((L.shape[0], 12, 3), BG, np.float32)
    savepng(OUTD + "pair_%02d.png" % (i+1), np.concatenate([L, gap, R], 1))
print("DONE")
