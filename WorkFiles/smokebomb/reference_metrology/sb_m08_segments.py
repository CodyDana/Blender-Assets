"""Stage 8: extract long line segments from the stage-7 valley (and ridge) response: NMS across the
line, threshold, 8-connected components, keep long ones, order into polylines. Renders them numbered."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

FONT = {'0': "111101101101111", '1': "010110010010111", '2': "111001111100111", '3': "111001111001111",
        '4': "101101111001001", '5': "111100111001111", '6': "111100111101111", '7': "111001001001001",
        '8': "111101111101111", '9': "111101111001111", 'V': "101101101101010", 'R': "110101110101101",
        'A': "010101111101101", 'B': "110101110101110", 'C': "011100100100011", 'D': "110101101101110",
        'E': "111100110100111", 'F': "111100110100100", 'G': "011100101101011", 'H': "101101111101101",
        'I': "111010010010111", 'J': "001001001101010", 'K': "101110100110101", 'L': "100100100100111",
        'M': "101111111101101", 'N': "110101101101101", 'O': "010101101101010", 'P': "110101110100100",
        'Q': "010101101110011", 'S': "011100010001110", 'T': "111010010010010", 'U': "101101101101111",
        'W': "101101111111101", 'X': "101101010101101", 'Y': "101101010010010", 'Z': "111001010100111",
        '-': "000000111000000", '.': "000000000000010", '/': "001001010100100", '+': "000010111010000",
        '>': "100010001010100", '<': "001010100010001", ' ': "000000000000000", '?': "111001011000010"}


def text(img, s, x, y, col, sc=2):
    for ci, ch in enumerate(s.upper()):
        g = FONT.get(ch, FONT['?'])
        for r in range(5):
            for c in range(3):
                if g[r * 3 + c] == '1':
                    yy = y + r * sc; xx = x + ci * 4 * sc + c * sc
                    if 0 <= yy < img.shape[0] - sc and 0 <= xx < img.shape[1] - sc:
                        img[yy:yy + sc, xx:xx + sc] = col


def components(mask):
    ys, xs = np.nonzero(mask)
    idx = -np.ones(mask.shape, int)
    idx[ys, xs] = np.arange(len(ys))
    parent = np.arange(len(ys))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    H, W = mask.shape
    for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):
        y2 = ys + dy; x2 = xs + dx
        ok = (y2 >= 0) & (y2 < H) & (x2 >= 0) & (x2 < W)
        j = np.full(len(ys), -1)
        j[ok] = idx[y2[ok], x2[ok]]
        for a, b in zip(np.nonzero(j >= 0)[0], j[j >= 0]):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    roots = np.array([find(a) for a in range(len(ys))])
    return ys, xs, roots


if __name__ == "__main__":
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    kind = args[0] if args else 'V'
    thr_frac = float(args[1]) if len(args) > 1 else 0.35
    minlen = float(args[2]) if len(args) > 2 else 30
    arr = np.load(os.path.join(L.D, "sb_s7_lines_s2.0_L18.npy"))
    R, A = (arr[0], arr[1]) if kind == 'V' else (arr[2], arr[3])
    rgb = L.load_srgb(); Y = L.lum(rgb)
    ball = Y < 0.6
    # erode ball by 6 px to avoid the silhouette itself
    er = L.box_blur(ball.astype(np.float32), 6) > 0.999
    p = np.percentile(R[er], 99.5)
    th = np.radians(A)
    nx, ny = np.sin(th), np.cos(th)        # normal in image coords (line dir = (cos, -sin))
    H, W = R.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r1 = L.bilinear(R, xx + nx, yy + ny); r2 = L.bilinear(R, xx - nx, yy - ny)
    nms = (R >= r1) & (R >= r2) & (R > thr_frac * p) & er
    ys, xs, roots = components(nms)
    segs = []
    for rt in np.unique(roots):
        sel = roots == rt
        if sel.sum() < 8:
            continue
        px = xs[sel].astype(float); py = ys[sel].astype(float)
        c = np.c_[px, py]; mu = c.mean(0)
        u, s, vt = np.linalg.svd(c - mu, full_matrices=False)
        ax = vt[0]
        t = (c - mu) @ ax
        length = t.max() - t.min()
        if length < minlen:
            continue
        # polyline: bin along principal axis every 8 px
        bins = np.arange(t.min(), t.max() + 8, 8)
        pts = []
        for b0 in bins:
            m = (t >= b0) & (t < b0 + 8)
            if m.any():
                pts.append(c[m].mean(0).round(1).tolist())
        strength = float(R[ys[sel], xs[sel]].mean() / p)
        segs.append(dict(len=float(length), n=int(sel.sum()), strength=strength, pts=pts,
                         dir_deg=float((np.degrees(np.arctan2(-ax[1], ax[0]))) % 180)))
    segs.sort(key=lambda s: -s['len'])
    for i, s in enumerate(segs):
        s['id'] = f"{kind}{i}"
    L.dump(f"sb_s8_segments_{kind}.json", segs)
    print(kind, "segments", len(segs), "p", p)
    for s in segs[:80]:
        print(s['id'], round(s['len']), round(s['strength'], 2), round(s['dir_deg']), s['pts'][0], s['pts'][-1])
    # render
    K = 2 if len(args) > 3 else 1
    x0, y0, T = (int(a) for a in args[3:6]) if len(args) > 5 else (150, 150, 960)
    base = L.stretch(L.gauss_blur(Y, 1.5), 0.02, 0.3)
    vis = np.repeat(base[..., None], 3, 2).astype(np.float32) * 0.55 + 0.2
    rng = np.random.default_rng(3)
    cols = []
    for i, s in enumerate(segs):
        col = np.array(rng.uniform(0.2, 1, 3), np.float32); col[i % 3] = 1.0
        cols.append(col)
        P = np.array(s['pts'])
        for a_, b_ in zip(P[:-1], P[1:]):
            for f in np.linspace(0, 1, 30):
                x = int(round(a_[0] + f * (b_[0] - a_[0]))); y = int(round(a_[1] + f * (b_[1] - a_[1])))
                vis[y - 1:y + 1, x - 1:x + 1] = col
    crop = vis[y0:y0 + T, x0:x0 + T]
    crop = L.upscale(crop, K).copy()
    for i, s in enumerate(segs):
        P = np.array(s['pts']); m = P[len(P) // 2]
        tx, ty = int((m[0] - x0) * K) + 3, int((m[1] - y0) * K) + 3
        text(crop, s['id'][1:], tx + 1, ty + 1, np.zeros(3, np.float32), 2)
        text(crop, s['id'][1:], tx, ty, cols[i], 2)
    L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_s8_segs_{kind}_{x0}_{y0}_K{K}.png"), crop)
    print("done")
