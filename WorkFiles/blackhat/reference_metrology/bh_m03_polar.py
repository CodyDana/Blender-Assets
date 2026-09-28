"""Stage 3: polar unwrap about the virtual apex (debug image) and angular profile for rib detection."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
im = load_srgb(); L = lum(im)
ap = load('bh_s02_lines.json')['apex']; xa, ya = ap
phis = np.radians(np.linspace(-66, 66, 1321))    # 0.1 deg steps; phi from straight down, + = image right
rs = np.arange(0, 420, 0.5)
P, R = np.meshgrid(phis, rs)
X = xa + R * np.sin(P); Y = ya + R * np.cos(P)
pol = bilinear(L, X, Y)
inside = (X >= 0) & (X < L.shape[1] - 1) & (Y >= 0) & (Y < L.shape[0] - 1)
pol[~inside] = 1.0
np.save(os.path.join(D, 'bh_polar.npy'), pol)
save_png(os.path.join(DBG, 'dbg_polar_unwrap_apex.png'), stretch(pol, 0, 0.45))
