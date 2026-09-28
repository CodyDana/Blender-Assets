"""Photo measurer A: blade cross-section ratios from References/Kunai/kunai_reference2.jpg.
Reads ring_fit.json (ring_fit.py) and detects blade lines (edges, ridge) with sub-pixel threshold crossings."""
from PIL import Image
import numpy as np, json, math

IMG = 'C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg'
im = np.asarray(Image.open(IMG)).astype(float)
L = im.mean(2)


def cross_up(p, y0, y1, thr):
    for y in range(y0, y1 - 1):
        if p[y] < thr <= p[y + 1]:
            return y + (thr - p[y]) / (p[y + 1] - p[y])
    return np.nan


def cross_dn(p, y0, y1, thr):
    for y in range(y0, y1 - 1):
        if p[y] >= thr > p[y + 1]:
            return y + (p[y] - thr) / (p[y] - p[y + 1])
    return np.nan


def detect(frac=0.5):
    """frac = threshold position between the two plateaus (0.5 = half-way); varied for sensitivity."""
    P = {k: [] for k in ('top_front', 'ridge_front', 'bot_front', 'bot_rear', 'ridge_rear', 'top_rear')}
    for x in range(262, 404):
        p = L[:, x]
        yt = 131.7 - 0.182 * (x - 287.5); yr = 159.2 - 0.413 * (x - 300); yb = 189.2 - 0.826 * (x - 314.2)
        if 291 <= x <= 400:
            y0 = int(yt) - 4; bg = np.median(p[y0 - 4:y0]); pk = p[y0:y0 + 7].max()
            P['top_front'].append((x, cross_up(p, y0, y0 + 7, bg + frac * (pk - bg))))
        if 304 <= x <= 400:
            y0 = int(yr) - 4; lit = np.median(p[y0 - 6:y0]); dk = np.median(p[y0 + 5:y0 + 10])
            P['ridge_front'].append((x, cross_dn(p, y0, y0 + 8, lit - frac * (lit - dk))))
        if 318 <= x <= 372:  # beyond ~372 the bark behind the lower edge is as dark as the face
            y0 = int(yb) - 4; dk = np.median(p[y0 - 8:y0 - 2]); bg = np.median(p[y0 + 6:y0 + 11])
            P['bot_front'].append((x, cross_up(p, y0, y0 + 9, dk + frac * (bg - dk))))
        if 268 <= x <= 310:
            dk = np.median(p[176:183]); bg = np.median(p[192:197])
            P['bot_rear'].append((x, cross_up(p, 184, 192, dk + frac * (bg - dk))))
        if 266 <= x <= 296:
            yr2 = 171.7 - 0.375 * (x - 260); y0 = int(yr2) - 4
            lit = np.median(p[y0 - 6:y0]); dk = np.median(p[y0 + 5:y0 + 10])
            P['ridge_rear'].append((x, cross_dn(p, y0, y0 + 8, lit - frac * (lit - dk))))
    for y in range(136, 166):
        p = L[y, :]; xg = 287.5 - (y - 131.7) / 1.3; x0 = int(xg) - 5
        bg = np.median(p[x0 - 5:x0]); pk = p[x0:x0 + 9].max()
        P['top_rear'].append((cross_up(p, x0, x0 + 9, bg + frac * (pk - bg)), y))
    return P


def fitline(P):
    P = np.array([p for p in P if not np.any(np.isnan(p))], float)
    keep = np.ones(len(P), bool)
    for _ in range(5):
        Q = P[keep]; c = Q.mean(0); _, _, V = np.linalg.svd(Q - c); d = V[0]
        if d[0] < 0:
            d = -d
        n = np.array([-d[1], d[0]]); r = (P - c) @ n; sd = np.std(r[keep]); keep = np.abs(r) < max(2.5 * sd, 0.6)
    return dict(c=c, d=d, rms=float(np.std(r[keep])), n=int(keep.sum()), N=len(P), pts=P, keep=keep)


def inter(l1, l2):
    A = np.array([l1['d'], -l2['d']]).T; t = np.linalg.solve(A, l2['c'] - l1['c']); return l1['c'] + t[0] * l1['d']


def inter_pd(p, d, l):
    A = np.array([d, -l['d']]).T; t = np.linalg.solve(A, l['c'] - p); return p + t[0] * d


ring = json.load(open('ring_fit.json'))
ri, ro = ring['inner'], ring['outer']
STATIONS = [0.10, 0.30, 0.45, 0.60, 0.75, 0.90]


def analyse(frac=0.5, ring_ab=None, fits=None, sh_top=(258.5, 167.5), entry_x=404.0):
    F = fits if fits is not None else {k: fitline(v) for k, v in detect(frac).items()}
    top_c = inter(F['top_front'], F['top_rear']); bot_c = inter(F['bot_front'], F['bot_rear'])
    cdir = (bot_c - top_c) / np.linalg.norm(bot_c - top_c)   # image of 3D cross direction (top -> bottom)
    tip = inter(F['top_front'], F['bot_front'])
    mid_c = (top_c + bot_c) / 2
    adir = (tip - mid_c) / np.linalg.norm(tip - mid_c)        # image of blade axis (symmetric plan)
    rj_front = inter_pd(top_c, cdir, F['ridge_front']); rj_rear = inter_pd(top_c, cdir, F['ridge_rear'])
    sh_top = np.array(sh_top, float)
    A = np.array([cdir, -adir]).T; t = np.linalg.solve(A, mid_c - sh_top); sh_axis = sh_top + t[0] * cdir
    sh_bot = inter_pd(sh_top, cdir, F['bot_rear'])
    ent = mid_c + adir * ((entry_x - mid_c[0]) / adir[0])
    Lvis = np.linalg.norm(ent - sh_axis); Lcrease = np.linalg.norm(mid_c - sh_axis); Ltip = np.linalg.norm(tip - sh_axis)
    a_o, b_o, a_i, b_i = (ro['a'], ro['b'], ri['a'], ri['b']) if ring_ab is None else ring_ab
    # works for round-tube and flat-washer rings alike: silhouette offsets cancel in the sums
    cos_th = (b_o + b_i) / (a_o + a_i); th = math.degrees(math.acos(cos_th))
    wo, wi = a_o - b_o, a_i - b_i
    major = math.radians((ro['major_angle_deg'] * wo + ri['major_angle_deg'] * wi) / (wo + wi))
    m = np.array([math.cos(major), math.sin(major)])
    if m @ adir < 0:
        m = -m
    phi = math.degrees(math.atan2(m[0] * adir[1] - m[1] * adir[0], m @ adir))
    alpha = math.degrees(math.atan(math.tan(math.radians(phi)) / cos_th))
    t_roll = math.tan(math.radians(th)) * math.cos(math.radians(alpha))
    al = math.radians(alpha)
    a_img = np.array([math.cos(al), math.sin(al) * cos_th]); c_img = np.array([-math.sin(al), math.cos(al) * cos_th])
    skew_pred = 90 - math.degrees(math.acos(abs(a_img @ c_img) / np.linalg.norm(a_img) / np.linalg.norm(c_img)))
    skew_meas = 90 - math.degrees(math.acos(abs(adir @ cdir)))
    stations = []
    for fr in STATIONS:
        P = sh_axis + adir * fr * Lvis
        s = fr * Lvis
        front = s >= Lcrease
        lt = F['top_front'] if front else F['top_rear']; lb = F['bot_front'] if front else F['bot_rear']
        lr = F['ridge_front'] if front else F['ridge_rear']
        pt = inter_pd(P, cdir, lt); pb = inter_pd(P, cdir, lb); pr = inter_pd(P, cdir, lr)
        ut, ub, ur = (pt - P) @ cdir, (pb - P) @ cdir, (pr - P) @ cdir
        mid = (ut + ub) / 2; hw = (ub - ut) / 2
        f = (mid - ur) / hw   # + = ridge displaced toward the top (far) edge
        mm = 35 * s / Lcrease if s < Lcrease else 35 + 105 * (s - Lcrease) / (Ltip - Lcrease)
        stations.append(dict(frac=fr, section='front' if front else 'rear', our_mm=mm, top=pt.tolist(), bot=pb.tolist(),
                             ridge=pr.tolist(), half_width_px=hw, ridge_offset_px=mid - ur, offset_frac=f,
                             ridge_ratio=f / t_roll, top_face_px=ur - ut, bot_face_px=ub - ur,
                             width_rel_widest=2 * hw / np.linalg.norm(bot_c - top_c)))
    nr = np.array([-F['ridge_front']['d'][1], F['ridge_front']['d'][0]])
    return dict(theta_deg=th, cos_theta=cos_th, alpha_deg=alpha, phi_deg=phi, t_roll=t_roll,
                skew_pred_deg=skew_pred, skew_meas_deg=skew_meas,
                top_corner=top_c.tolist(), bot_corner=bot_c.tolist(), tip=tip.tolist(), mid_crease=mid_c.tolist(),
                rj_front=rj_front.tolist(), rj_rear=rj_rear.tolist(),
                ridge_junction_gap_px=float(np.linalg.norm(rj_front - rj_rear)),
                crease_ridge_frac_from_top=float((rj_front - top_c) @ cdir / np.linalg.norm(bot_c - top_c)),
                shoulder_axis=sh_axis.tolist(), shoulder_top=sh_top.tolist(), shoulder_bot=sh_bot.tolist(), entry=ent.tolist(),
                L_visible_px=Lvis, L_crease_px=Lcrease, L_tip_px=Ltip, crease_frac_of_visible=Lcrease / Lvis,
                axis_angle_deg=math.degrees(math.atan2(adir[1], adir[0])), cross_angle_deg=math.degrees(math.atan2(cdir[1], cdir[0])),
                ridge_front_miss_tip_px=float((tip - F['ridge_front']['c']) @ nr),
                widest_chord_px=float(np.linalg.norm(bot_c - top_c)), shoulder_chord_px=float(np.linalg.norm(sh_bot - sh_top)),
                lines={k: dict(c=v['c'].tolist(), d=v['d'].tolist(), angle_deg=math.degrees(math.atan2(v['d'][1], v['d'][0])),
                               rms_px=v['rms'], n_used=v['n'], n_total=v['N']) for k, v in F.items()},
                stations=stations), F


def r3(v):
    return round(v, 3) if isinstance(v, float) else v


if __name__ == '__main__':
    base, F = analyse(0.5)
    print({k: r3(v) for k, v in base.items() if k not in ('stations', 'lines')})
    for k, v in base['lines'].items():
        print(k, {kk: r3(vv) for kk, vv in v.items() if kk in ('angle_deg', 'rms_px', 'n_used', 'n_total')})
    for s in base['stations']:
        print({k: r3(v) for k, v in s.items() if k not in ('top', 'bot', 'ridge')})
    sens = {}
    for fr in [0.35, 0.65]:
        o, _ = analyse(fr); sens[f'thr_{fr}'] = [round(s['ridge_ratio'], 3) for s in o['stations']]
        print('thr', fr, sens[f'thr_{fr}'], 'crease_frac', round(o['crease_ridge_frac_from_top'], 3))
    for sh in [(256.5, 166.0), (260.5, 169.0)]:
        o, _ = analyse(0.5, sh_top=sh); sens[f'shoulder_{sh}'] = [round(s['our_mm'], 1) for s in o['stations']]
    for ex in [400.0, 407.0]:
        o, _ = analyse(0.5, entry_x=ex); sens[f'entry_{ex}'] = [round(s['our_mm'], 1) for s in o['stations']]
    print(sens)
    rng = np.random.default_rng(1)
    pts = detect(0.5); boots = []; ths = []; offs = []
    for b in range(400):
        fits = {}
        for k, v in pts.items():
            arr = [p for p in v if not np.any(np.isnan(p))]; idx = rng.integers(0, len(arr), len(arr))
            fits[k] = fitline([arr[i] for i in idx])
        ab = (ro['a'] + rng.normal(0, .25), ro['b'] + rng.normal(0, .25), ri['a'] + rng.normal(0, .25), ri['b'] + rng.normal(0, .25))
        try:
            o, _ = analyse(0.5, ring_ab=ab, fits=fits)
        except Exception:
            continue
        boots.append([s['ridge_ratio'] for s in o['stations']]); ths.append(o['theta_deg']); offs.append([s['offset_frac'] for s in o['stations']])
    boots = np.array(boots)
    lo, hi = np.percentile(boots, [16, 84], axis=0)
    print('boot 68% ridge_ratio lo', np.round(lo, 3), 'hi', np.round(hi, 3), 'theta', np.round(np.percentile(ths, [16, 84]), 2))
    base['sensitivity'] = sens
    base['bootstrap'] = dict(n=len(boots), ridge_ratio_p16=lo.tolist(), ridge_ratio_p84=hi.tolist(),
                             offset_frac_p16=np.percentile(offs, 16, axis=0).tolist(), offset_frac_p84=np.percentile(offs, 84, axis=0).tolist(),
                             theta_p16_p84=np.percentile(ths, [16, 84]).tolist())
    base['detected_points'] = {k: dict(pts=v['pts'].tolist(), keep=v['keep'].tolist()) for k, v in F.items()}
    json.dump(base, open('measure_raw.json', 'w'), indent=1, default=float)
