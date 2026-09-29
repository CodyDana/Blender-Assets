"""entryfix measurements: CX courtyard regions (display sRGB mean, luminance) and whole-frame mean."""
import sys
import numpy as np
from PIL import Image
REG = {"court_whole": (665, 245, 935, 500), "court_ground": (700, 400, 930, 490), "gate_opening": (755, 330, 850, 410),
       "court_wall": (860, 330, 935, 390)}
def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
for p in sys.argv[1:]:
    a = np.asarray(Image.open(p).convert("RGB"), dtype=float) / 255
    out = [f"whole L{lum(a).mean():.3f}"]
    for k, (x0, y0, x1, y1) in REG.items():
        r = a[y0:y1, x0:x1]
        m = r.reshape(-1, 3).mean(0)
        out.append(f"{k} ({m[0]:.2f},{m[1]:.2f},{m[2]:.2f}) L{lum(r).mean():.3f}")
    print(p, " | ".join(out))
