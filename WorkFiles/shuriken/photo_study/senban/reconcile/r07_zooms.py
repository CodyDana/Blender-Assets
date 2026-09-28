import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bpy
from rc_common import save_png, OUT

def load_png(p):
    img = bpy.data.images.load(p, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[:, :, :3][::-1].copy()
    bpy.data.images.remove(img)
    return a

src = load_png(os.path.join(OUT, 'senban_reconciled_outline.png'))
crops = {
    'zoom_right_mid':  (830, 380, 990, 580),
    'zoom_left_mid':   (100, 380, 260, 580),
    'zoom_hole_bot':   (400, 520, 640, 640),
    'zoom_hole_left':  (350, 400, 470, 560),
    'zoom_top_mid':    (420, 60, 620, 180),
    'zoom_corner_br':  (880, 820, 990, 930),
}
for name, (x0, y0, x1, y1) in crops.items():
    c = src[y0:y1, x0:x1]
    f = 4
    big = np.repeat(np.repeat(c, f, axis=0), f, axis=1)
    save_png(os.path.join(OUT, 'reconcile', name + '.png'), big)
    print("wrote", name, big.shape)
