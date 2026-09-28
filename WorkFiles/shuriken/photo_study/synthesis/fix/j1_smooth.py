import numpy as np, math
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
raw = np.load(P + "synthesis/juji_profile_raw.npy"); g, h8 = raw[:, 0], raw[:, 1]; ok = np.isfinite(h8)
def gs(sig):
    k = np.arange(-4 * sig, 4 * sig + 1); w = np.exp(-k ** 2 / (2.0 * sig ** 2))
    return np.convolve(np.where(ok, h8, 0.0), w, 'same') / np.maximum(np.convolve(ok.astype(float), w, 'same'), 1e-9)
base = gs(12)
lo, hi = 0.19, 0.91
m = (g >= lo) & (g <= hi)
def nchg(y):
    d2 = np.gradient(np.gradient(y, g[m]), g[m])
    kb = 10; d2 = np.convolve(d2, np.ones(2*kb+1)/(2*kb+1), 'same')[kb:-kb]
    s = np.sign(d2); s = s[s != 0]; idx = np.where(np.diff(s) != 0)[0]
    return len(idx), [round(float(g[m][kb:-kb][s != 0][i]), 3) for i in idx]
for sig in (12, 20, 30, 40, 50):
    y = gs(sig)[m]; n, where = nchg(y)
    print("gauss sig %d: changes %d at %s  maxdev %.4f R  width@0.3 %.4f  max %.4f" % (sig, n, where, np.abs(y - base[m]).max(), y[np.argmin(np.abs(g[m]-0.3))], y.max()))
C = np.polynomial.chebyshev
for deg in range(4, 13):
    c = C.chebfit(g[m], base[m], deg); y = C.chebval(g[m], c); n, where = nchg(y)
    print("cheb deg %d: changes %d at %s  maxdev %.4f R  rms %.5f  min %.4f@%.3f max %.4f@%.3f" % (deg, n, where, np.abs(y - base[m]).max(), np.sqrt(np.mean((y-base[m])**2)), y.min(), g[m][np.argmin(y)], y.max(), g[m][np.argmax(y)]))
