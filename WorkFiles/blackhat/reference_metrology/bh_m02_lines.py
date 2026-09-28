"""Stage 2: fit the two cone-generator silhouette lines, their intersection (virtual apex), residuals; crown top."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
top = np.load(os.path.join(D, 'bh_top.npy'))
res = {}
for side, (a, b) in dict(left=(70, 285), right=(385, 545)).items():
    x = np.arange(a, b); y = top[a:b]
    p = np.polyfit(x, y, 1); r = y - np.polyval(p, x)
    p2 = np.polyfit(x, y, 2)
    res[side] = dict(slope=p[0], icpt=p[1], rms=float(r.std()), maxabs=float(abs(r).max()), quad=p2[0])
    print(side, p, 'rms', r.std(), 'max', abs(r).max(), 'quad coef', p2[0])
    # show residual sampled
    print('  resid', np.round(r[::10], 2).tolist())
m1, c1 = res['left']['slope'], res['left']['icpt']; m2, c2 = res['right']['slope'], res['right']['icpt']
xa = (c2 - c1) / (m1 - m2); ya = m1 * xa + c1
print('apex', xa, ya)
ang1 = np.degrees(np.arctan(-m1)); ang2 = np.degrees(np.arctan(m2))
print('generator angles below horizontal: left', ang1, 'right', ang2, 'apparent apex angle', 180 - ang1 - ang2)
print('bisector tilt from vertical (deg, + = leans right at bottom)', (ang1 - ang2) / 2)
# where the silhouette leaves the lines (crown cap and the rim tips)
for x in range(0, 70, 5): print('L', x, round(top[x] - (m1 * x + c1), 2))
for x in range(545, 665, 5): print('R', x, round(top[x] - (m2 * x + c2), 2))
for x in range(280, 395, 5): print('C', x, round(top[x], 2), round(top[x] - min(m1 * x + c1, m2 * x + c2), 2))
res['apex'] = [xa, ya]
dump('bh_s02_lines.json', res)
