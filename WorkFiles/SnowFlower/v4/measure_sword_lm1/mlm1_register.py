# register our detail renders onto the sheet's detail panels (silhouette IoU over scale + shift)
import sys, json, os; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1")
from mlm1_lib import *
args = sys.argv[sys.argv.index('--')+1:]
names = args[0].split(',')              # e.g. guard,guard_e20
save = len(args) > 1 and args[1] == 'save'
ref = np.load(D+"mlm1_ref_rgb.npy"); lum = ref.mean(2); sat = ref.max(2)-ref.min(2)
rfg = (lum < 0.93) | (sat > 0.06)
panels = {"guard": (0, 515, 808, 1200), "blade": (576, 852, 808, 1200), "pommel": (900, 1190, 808, 1200)}
def xcorr(a, b):
    ha, wa = a.shape; hb, wb = b.shape
    H, W = ha+hb, wa+wb
    c = np.fft.irfft2(np.fft.rfft2(a, (H, W))*np.fft.rfft2(b[::-1, ::-1], (H, W)), (H, W))
    return c[:ha+hb-1, :wa+wb-1]
res = json.load(open(D+"mlm1_register.json")) if os.path.exists(D+"mlm1_register.json") else {}
for nm in names:
    base = nm.split('_')[0]
    y0, y1, x0, x1 = panels[base]
    Mr = rfg[y0:y1, x0:x1].astype(np.float64)
    ours = load(D+"mlm1_ours_"+nm+".png")
    best = None
    for s in np.linspace(0.25, 0.8, 56):
        h, w = int(round(ours.shape[0]*s)), int(round(ours.shape[1]*s))
        Mo = (resize(ours[..., 3:4], h, w)[..., 0] > 0.5).astype(np.float64)
        ov = xcorr(Mr, Mo); ao = xcorr(np.ones_like(Mr), Mo)
        iou = ov / np.maximum(1, Mr.sum() + ao - ov)
        k = np.unravel_index(np.argmax(iou), iou.shape)
        if best is None or iou[k] > best[0]:
            best = (float(iou[k]), float(s), int(k[0]-(h-1)), int(k[1]-(w-1)), h, w)
    iou, s, dy, dx, h, w = best
    print("REG", nm, round(iou, 4), round(s, 3), dy, dx)
    if save:
        col = resize(over(ours), h, w)
        P = np.full((y1-y0, x1-x0, 3), BG, np.float32)
        for yy in range(y1-y0):
            sy = yy - dy
            if 0 <= sy < h:
                a0 = max(0, dx); a1 = min(x1-x0, dx+w)
                if a1 > a0: P[yy, a0:a1] = col[sy, a0-dx:a1-dx]
        np.save(D+"mlm1_panel_"+base+".npy", P)
        savepng(D+"mlm1_reg_"+base+".png", np.concatenate([ref[y0:y1, x0:x1], P], 1))
        res[base] = {"render": nm, "iou": round(iou, 3), "scale": round(s, 3), "dy": dy, "dx": dx}
        json.dump(res, open(D+"mlm1_register.json", "w"), indent=1)
