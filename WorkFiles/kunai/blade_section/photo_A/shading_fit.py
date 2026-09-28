"""Shape-from-shading cross-check using the ring as a light probe (matcap), plus hypothesis test of the ring-derived pose.
Face-on frame: image x right, y down, z toward camera. Facets are planes through their edge line (z=0) and the
ridge junction J at height H = r * w (w = half-width at the widest crease). For planar facets r is the face slope
(tan of the face angle) at every station of that facet."""
from PIL import Image
import numpy as np, json, math, itertools

im = np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg')).astype(float)
L = im.mean(2)
R = json.load(open('ring_fit.json')); ri, ro = R['inner'], R['outer']
M = json.load(open('measure_raw.json'))


def ell_r(f, psi):
    th = math.radians(f['major_angle_deg']); u = psi - th
    return 1 / math.sqrt((math.cos(u) / f['a']) ** 2 + (math.sin(u) / f['b']) ** 2)


cx = (ri['cx'] + ro['cx']) / 2; cy = (ri['cy'] + ro['cy']) / 2


def matcap_samples(dcut=0.92, excl=(-75, 20)):
    S = []
    for y in range(200, 268):
        for x in range(88, 158):
            dx, dy = x - cx, y - cy; rr = math.hypot(dx, dy); psi = math.atan2(dy, dx)
            if excl[0] <= math.degrees(psi) <= excl[1]:
                continue
            rin, rout = ell_r(ri, psi), ell_r(ro, psi)
            d = (rr - (rin + rout) / 2) / ((rout - rin) / 2)
            if abs(d) > dcut:
                continue
            S.append((d * math.cos(psi), d * math.sin(psi), L[y, x]))
    return np.array(S)


def lookup(S, n, sig):
    d2 = (S[:, 0] - n[0]) ** 2 + (S[:, 1] - n[1]) ** 2
    w = np.exp(-d2 / (2 * sig ** 2)); return (w * S[:, 2]).sum() / w.sum()


T = np.array(M['top_corner']); B = np.array(M['bot_corner']); J = np.array(M['rj_front'])
tipdir_t = np.array(M['lines']['top_front']['d']); tipdir_b = np.array(M['lines']['bot_front']['d'])
TipT = T + tipdir_t * 100; TipB = B + tipdir_b * 80
Sh = np.array(M['shoulder_top']); Shb = np.array(M['shoulder_bot'])
w_px = np.linalg.norm(B - T) / 2
adir = np.array([math.cos(math.radians(M['axis_angle_deg'])), math.sin(math.radians(M['axis_angle_deg'])), 0.0])
cdir = np.array([math.cos(math.radians(M['cross_angle_deg'])), math.sin(math.radians(M['cross_angle_deg'])), 0.0])
OBS = dict(front_top=144.1, front_bot=38.8, rear_top=164.9, rear_bot=33.5)   # facet means (inner 60% of each facet)


def normal(p0, p1, j, H):
    a = np.r_[p1 - p0, 0.0]; b = np.r_[j - p0, H]; n = np.cross(a, b); n /= np.linalg.norm(n)
    return n if n[2] > 0 else -n


def rot(axis, deg):
    k = axis / np.linalg.norm(axis); t = math.radians(deg)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def facet_normals(r, roll=0.0, pitch=0.0):
    H = r * w_px
    F = dict(front_top=normal(T, TipT, J, H), front_bot=normal(B, TipB, J, H),
             rear_top=normal(T, Sh, J, H), rear_bot=normal(B, Shb, J, H))
    Rm = rot(adir, roll) @ rot(cdir, pitch)   # roll +: top (far) edge rotates away from camera, normals tilt image-up
    return {k: Rm @ v for k, v in F.items()}


def fit(S, sig, keys, gain, roll=0.0, pitch=0.0):
    best = None; curve = []
    for r in np.arange(0.02, 1.2001, 0.01):
        F = facet_normals(r, roll, pitch)
        p = np.array([lookup(S, F[k][:2], sig) for k in keys]); o = np.array([OBS[k] for k in keys])
        g = (p @ o) / (p @ p) if gain else 1.0
        e = float(np.sqrt(np.mean((g * p - o) ** 2))); curve.append((round(float(r), 2), e))
        if best is None or e < best[2]:
            best = (float(r), float(g), e)
    return best, curve


if __name__ == '__main__':
    out = {}
    S0 = matcap_samples()
    # sign check of roll convention: +roll should move the top facet normal toward image-up (negative y)
    n0 = facet_normals(0.3)['front_top']; n1 = facet_normals(0.3, roll=10)['front_top']
    print('roll sign check (ny should drop):', round(n0[1], 3), '->', round(n1[1], 3))
    # 1) ring-coplanar hypothesis: roll = +-theta, r from the ridge offset (~0.04)
    th = M['theta_deg']; r_ring = float(np.median([s['ridge_ratio'] for s in M['stations'] if s['section'] == 'front']))
    hyp = {}
    for sgn in (+1, -1):
        F = facet_normals(max(r_ring, 0.02), roll=sgn * th)
        hyp[f'roll_{sgn * th:+.1f}'] = {k: round(lookup(S0, v[:2], 0.12), 1) for k, v in F.items()}
    out['ring_pose_hypothesis'] = dict(roll_deg=th, ridge_ratio_from_offset=r_ring, predicted_facet_L=hyp, observed_facet_L=OBS)
    print('ring-pose hypothesis predicted', hyp, 'observed', OBS)
    # 2) face-on hypothesis, sensitivity grid
    grid = []
    for dcut, sig, keys, gain, roll, pitch in itertools.product(
            (0.8, 0.92), (0.08, 0.12, 0.16), (('front_top', 'front_bot'), ('front_top', 'front_bot', 'rear_top', 'rear_bot')),
            (False, True), (-5.0, 0.0, 5.0), (-15.0, 0.0, 15.0)):
        S = S0 if dcut == 0.92 else matcap_samples(dcut)
        (r, g, e), _ = fit(S, sig, keys, gain, roll, pitch)
        grid.append(dict(dcut=dcut, sig=sig, facets=len(keys), gain_free=gain, roll=roll, pitch=pitch, r=r, gain=g, rms=e))
    rs = np.array([g['r'] for g in grid])
    for gf in (False, True):
        sub = np.array([g['r'] for g in grid if g['gain_free'] == gf])
        print('gain_free', gf, 'r median %.2f p10 %.2f p90 %.2f' % (np.median(sub), *np.percentile(sub, [10, 90])))
    print('all r median %.2f p10 %.2f p90 %.2f min %.2f max %.2f' % (np.median(rs), *np.percentile(rs, [10, 90]), rs.min(), rs.max()))
    base_nogain, curve_ng = fit(S0, 0.12, ('front_top', 'front_bot', 'rear_top', 'rear_bot'), False)
    base_gain, curve_g = fit(S0, 0.12, ('front_top', 'front_bot', 'rear_top', 'rear_bot'), True)
    out['face_on_fit'] = dict(base_nogain=base_nogain, base_gain=base_gain, grid=grid,
                              r_median=float(np.median(rs)), r_p10=float(np.percentile(rs, 10)), r_p90=float(np.percentile(rs, 90)),
                              curve_nogain=curve_ng, curve_gain=curve_g)
    # 3) per-station inversion from the lit (top) face luminance in bins along the axis, gain from the central fits
    ln = M['lines']
    def at(line, x):
        c = np.array(line['c']); d = np.array(line['d']); return c[1] + (x - c[0]) * d[1] / d[0]
    sh = np.array(M['shoulder_axis']); Lvis = M['L_visible_px']; ax2 = adir[:2]
    st_out = []
    for st in M['stations']:
        if st['section'] != 'front':
            continue
        P = sh + ax2 * st['frac'] * Lvis
        tv = []
        for x in range(int(P[0]) - 5, int(P[0]) + 6):
            yt = at(ln['top_front'], x); yr = at(ln['ridge_front'], x)
            for y in range(int(np.ceil(yt + 2)), int(np.floor(yr - 1.5)) + 1):
                tv.append(L[y, x])
        Lt = float(np.median(tv))
        row = dict(frac=st['frac'], L_top=Lt, n=len(tv))
        for name, g in (('nogain', 1.0), ('gain', base_gain[1])):
            rr = np.arange(0.02, 1.2001, 0.01)
            pred = np.array([g * lookup(S0, facet_normals(r)['front_top'][:2], 0.12) for r in rr])
            row['r_' + name] = float(rr[np.argmin(np.abs(pred - Lt))])
        st_out.append(row); print(row)
    out['per_station_top_face'] = st_out
    json.dump(out, open('shading_fit.json', 'w'), indent=1, default=float)
