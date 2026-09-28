"""Ring-as-light-probe: build a matcap (luminance vs view-space normal) from the ring tube (round tube assumed),
then find the blade ridge height whose facet normals reproduce the four facet luminances."""
from PIL import Image, ImageDraw
import numpy as np, json, math
im = np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg')).astype(float)
L = im.mean(2)
R = json.load(open('ring_fit.json')); ri, ro = R['inner'], R['outer']
def ell_r(f, psi):  # radius of ellipse f along ray at angle psi from its centre
    th = math.radians(f['major_angle_deg']); u = psi - th
    return 1 / math.sqrt((math.cos(u) / f['a']) ** 2 + (math.sin(u) / f['b']) ** 2)
cx = (ri['cx'] + ro['cx']) / 2; cy = (ri['cy'] + ro['cy']) / 2
S = []
for y in range(200, 268):
    for x in range(88, 158):
        dx, dy = x - cx, y - cy; rr = math.hypot(dx, dy); psi = math.atan2(dy, dx)
        if -75 <= math.degrees(psi) <= 20: continue      # grip occludes the outer tube here; drop the whole sector
        rin, rout = ell_r(ri, psi), ell_r(ro, psi)
        d = (rr - (rin + rout) / 2) / ((rout - rin) / 2)
        if abs(d) > 0.92: continue
        nx, ny = d * math.cos(psi), d * math.sin(psi)
        S.append((nx, ny, L[y, x], x, y))
S = np.array(S)
print('matcap samples', len(S))
# matcap picture
N = 121; img = np.zeros((N, N, 3), np.uint8); img[:] = (40, 0, 40)
acc = np.zeros((N, N)); cnt = np.zeros((N, N))
for nx, ny, l, _, _ in S:
    i = int(round((ny + 1) / 2 * (N - 1))); j = int(round((nx + 1) / 2 * (N - 1))); acc[i, j] += l; cnt[i, j] += 1
m = cnt > 0; img[m] = np.repeat((acc[m] / cnt[m])[:, None], 3, 1).astype(np.uint8)
Image.fromarray(img).resize((N * 4, N * 4), Image.NEAREST).save('matcap_ring.png')
def lookup(n, sig=0.12):
    """kernel-weighted luminance of ring samples near image-plane normal (nx,ny)."""
    d2 = (S[:, 0] - n[0]) ** 2 + (S[:, 1] - n[1]) ** 2
    w = np.exp(-d2 / (2 * sig ** 2)); return (w * S[:, 2]).sum() / w.sum(), w.sum()
# blade facets (face-on assumption: blade plane = image plane, z toward camera, image y down)
T = np.array([286.5, 131.3]); B = np.array([312.9, 189.8]); J = np.array([299.6, 160.2])
TipT = np.array([404.0, 110.4]); TipB = np.array([399.0, 126.0])     # points on the front edges (tip itself is buried)
Sh = np.array([258.5, 167.5]); Shb = np.array([266.5, 185.2])
w_px = np.linalg.norm(B - T) / 2
obs = dict(front_top=144.1, front_bot=38.8, rear_top=164.9, rear_bot=33.5)
def normal(p0, p1, j, H):
    a = np.r_[p1 - p0, 0.0]; b = np.r_[j - p0, H]; n = np.cross(a, b); n = n / np.linalg.norm(n)
    return n if n[2] > 0 else -n
def facets(r):
    H = r * w_px
    return dict(front_top=normal(T, TipT, J, H), front_bot=normal(B, TipB, J, H),
                rear_top=normal(T, Sh, J, H), rear_bot=normal(B, Shb, J, H))
rows = []
for r in np.arange(0.02, 1.01, 0.02):
    F = facets(r); pred = {k: lookup(v[:2])[0] for k, v in F.items()}
    rows.append((r, pred, F))
def score(keys, gain=True):
    out = []
    for r, pred, F in rows:
        p = np.array([pred[k] for k in keys]); o = np.array([obs[k] for k in keys])
        g = (p @ o) / (p @ p) if gain else 1.0
        out.append((r, g, float(np.sqrt(np.mean((g * p - o) ** 2)))))
    return out
for keys in (['front_top', 'front_bot'], ['front_top', 'front_bot', 'rear_top', 'rear_bot']):
    for gain in (False, True):
        sc = score(keys, gain); best = min(sc, key=lambda t: t[2])
        print(keys, 'gain' if gain else 'nogain', 'best r=%.2f g=%.2f rms=%.1f' % best)
        print('   ', ' '.join('%.2f:%.0f' % (r, e) for r, g, e in sc[::3]))
for r, pred, F in rows[::5]:
    print('r=%.2f' % r, {k: (round(v, 0), np.round(F[k][:2], 3).tolist()) for k, v in pred.items()})
json.dump(dict(samples=S[:, :3].tolist(), obs=obs, w_px=w_px,
               table=[dict(r=r, pred=pred, normals={k: v.tolist() for k, v in F.items()}) for r, pred, F in rows]),
          open('matcap_fit.json', 'w'))
