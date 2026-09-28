"""Stage 6: perpendicular luminance profiles across a band direction.
args: cx cy dir_deg(image, CCW from +x, y-up convention) half_len half_width [cx cy dir ...]
Prints the profile (averaged along the band direction over +-half_width px), stored lum and log-lum
second derivative, and lists dark minima (shadow lines) and bright maxima (lit edges)."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

args = [float(a) for a in sys.argv[sys.argv.index('--') + 1:]]
rgb = L.load_srgb()
Y = L.lum(rgb)
Yb = L.gauss_blur(Y, 0.8)
for k in range(0, len(args), 5):
    cx, cy, dd, hl, hw = args[k:k + 5]
    t = np.radians(dd)
    u = np.array([np.cos(t), -np.sin(t)])      # along band, image coords
    n = np.array([np.sin(t), np.cos(t)])        # perpendicular (rotated +90 image-wise, points 'down' for flat bands)
    s = np.arange(-hl, hl + 0.5, 0.5)
    a = np.arange(-hw, hw + 0.5, 1.0)
    X = cx + s[:, None] * n[0] + a[None, :] * u[0]
    Yc = cy + s[:, None] * n[1] + a[None, :] * u[1]
    p = L.bilinear(Yb, X, Yc).mean(1)
    pm = np.convolve(p, np.ones(5) / 5, mode='same')
    print(f"PROFILE c=({cx:.0f},{cy:.0f}) dir={dd} n=({n[0]:.3f},{n[1]:.3f})")
    # local extrema with prominence
    for i in range(4, len(s) - 4, 1):
        w = pm[max(0, i - 12):i + 13]
        if pm[i] == w.min() and (w.max() - pm[i]) > 0.012:
            print(f"   MIN s={s[i]:7.1f} xy=({cx + s[i] * n[0]:.0f},{cy + s[i] * n[1]:.0f}) v={pm[i]:.3f} depth={w.max() - pm[i]:.3f}")
        if pm[i] == w.max() and (pm[i] - w.min()) > 0.012:
            print(f"   MAX s={s[i]:7.1f} xy=({cx + s[i] * n[0]:.0f},{cy + s[i] * n[1]:.0f}) v={pm[i]:.3f} height={pm[i] - w.min():.3f}")
    # coarse print every 5 px
    line = " ".join(f"{s[i]:.0f}:{pm[i]:.3f}" for i in range(0, len(s), 10))
    print("   ", line)
