import sys, os, numpy as np, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R

rgb,w,h = R.load_rgb(); L = R.lum(rgb)
A,B,la,lb = R.load_lines()
CA = np.array(A['centre']); CB = np.array(B['centre']['tip_circle_centre'])
C = (CA+CB)/2

order = ['T0-N0','T0-N7','T1-N0','T1-N1','T2-N1','T2-N2','T3-N2','T3-N3',
         'T4-N3','T4-N4','T5-N4','T5-N5','T6-N5','T6-N6','T7-N6','T7-N7']
UMAX = 45; NS = 360
tiles = []
for name in order:
    pB,dB,rmsB,kB = lb[name]; pA,dA,rmsA,nA = la[name]
    t = int(name[1]); n = int(name.split('-N')[1])
    # endpoints from B's own vertices (tip, notch)
    Vt = np.array(B['tips'][str(t)]['vertex']); Vn = np.array(B['notches'][str(n)]['vertex'])
    d, nn = R.edge_frame(pB, dB, C)
    # project vertices on B line
    s_t = (Vt-pB)@d; s_n = (Vn-pB)@d
    s0, s1 = (s_t, s_n) if s_t < s_n else (s_n, s_t)
    tip_first = s_t < s_n
    ss = np.linspace(s0, s1, NS)
    uu = np.arange(-UMAX, UMAX+1, 1.0)
    SS, UU = np.meshgrid(ss, uu)
    X = pB[0] + SS*d[0] + UU*nn[0]; Y = pB[1] + SS*d[1] + UU*nn[1]
    strip = R.bilinear(L, X, Y)                  # rows: u from -UMAX..+UMAX
    tile = np.repeat(strip[:,:,None], 3, axis=2)
    # A's line offset at each s:  point on B line at s -> perp dist to A line
    Px = pB[0]+ss*d[0]; Py = pB[1]+ss*d[1]
    nA_ = np.array([-dA[1],dA[0]]); nA_ = nA_/np.linalg.norm(nA_)
    if nA_ @ (pA-C) < 0: nA_ = -nA_
    hA = (np.stack([Px,Py],1)-pA) @ nA_          # signed dist to A line along A normal
    uA = -hA / max(1e-6, nA_@nn)                 # offset of A line along B normal (+ = A outside B)
    ridx = np.clip(np.round(uA+UMAX).astype(int), 0, len(uu)-1)
    ok = (uA>-UMAX+1)&(uA<UMAX-1)
    cols = np.arange(NS)
    tile[ridx[ok], cols[ok]] = [1,0,0]           # A = RED
    tile[int(UMAX), :] = [0,1,0]                 # B = GREEN (u=0)
    tile = np.flipud(tile)                       # outward (+u) at TOP
    if not tip_first: tile = tile[:, ::-1]        # always tip on the LEFT
    tile = np.repeat(np.repeat(tile, 2, axis=0), 1, axis=1)
    lab = np.ones((10, tile.shape[1], 3), dtype=np.float32)*0.15
    tiles.append(np.vstack([lab, tile]))
    print(name, 'kindB=%-34s rmsA=%.2f rmsB=%.2f  uA(tip)=%+.1f uA(mid)=%+.1f uA(notch)=%+.1f'
          % (kB, rmsA, rmsB, uA[0] if tip_first else uA[-1], uA[NS//2], uA[-1] if tip_first else uA[0]))
mont = np.vstack(tiles)
R.save_png(mont, R.BASE+"/reconcile/strips_all.png")
print('saved', mont.shape)
