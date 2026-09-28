import sys, json; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
ref = np.load(D+"ref_rgb.npy"); lum = ref.mean(2); sat = ref.max(2)-ref.min(2)
rfg = (lum < 0.93) | (sat > 0.06)
panels = {"guard": (0, 515, 808, 1200), "blade": (576, 852, 808, 1200), "pommel": (900, 1190, 808, 1200)}
scales = {"guard": np.linspace(0.3, 0.75, 46), "blade": np.linspace(0.3, 0.75, 46), "pommel": np.linspace(0.3, 0.75, 46)}
def xcorr(a, b):
    # full correlation c[dy,dx] = sum a[y,x]*b[y-dy,x-dx]  for dy in (-hb+1 .. ha-1)
    ha, wa = a.shape; hb, wb = b.shape
    H, W = ha+hb, wa+wb
    fa = np.fft.rfft2(a, (H, W)); fb = np.fft.rfft2(b[::-1, ::-1], (H, W))
    c = np.fft.irfft2(fa*fb, (H, W))
    # index k corresponds to shift dy = k - (hb-1)
    return c[:ha+hb-1, :wa+wb-1]
res = {}
for name, (y0, y1, x0, x1) in panels.items():
    Mr = rfg[y0:y1, x0:x1].astype(np.float64)
    ours = load(D+"ours_"+name+".png")
    best = None
    for s in scales[name]:
        h, w = int(round(ours.shape[0]*s)), int(round(ours.shape[1]*s))
        al = resize(ours[..., 3:4], h, w)[..., 0]
        Mo = (al > 0.5).astype(np.float64)
        ov = xcorr(Mr, Mo)
        ao = xcorr(np.ones_like(Mr), Mo)
        iou = ov / np.maximum(1, Mr.sum() + ao - ov)
        k = np.unravel_index(np.argmax(iou), iou.shape)
        if best is None or iou[k] > best[0]:
            best = (float(iou[k]), s, k[0]-(h-1), k[1]-(w-1), h, w)
    iou, s, dy, dx, h, w = best
    col = resize(over(ours), h, w)
    P = np.full((y1-y0, x1-x0, 3), BG, np.float32)
    for yy in range(y1-y0):
        sy = yy - dy
        if 0 <= sy < h:
            xs0 = max(0, dx); xs1 = min(x1-x0, dx+w)
            if xs1 > xs0: P[yy, xs0:xs1] = col[sy, xs0-dx:xs1-dx]
    np.save(D+"ours_panel_"+name+".npy", P)
    savepng(D+"reg_"+name+".png", np.concatenate([ref[y0:y1, x0:x1], P], 1))
    res[name] = {"iou": round(iou, 3), "scale": round(float(s), 3), "dy": int(dy), "dx": int(dx)}
    print("REG", name, res[name])
json.dump(res, open(D+"ms_register.json", "w"), indent=1)
