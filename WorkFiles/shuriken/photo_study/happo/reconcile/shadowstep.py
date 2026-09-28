# Independent re-measurement of shadowed (up-facing) edges.
# Rule: along the outward normal, find the darkest stripe (dark bevel / umbra) near B's line,
# then the first crisp rise after it (max of dL/du >= 0.02/px). Validate on shadowed edges where
# A and B agree; then apply to T0-N0 and T3-N2.
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R
rgb,w,h = R.load_rgb(); L = R.lum(rgb)
A,B,la,lb = R.load_lines()
C = np.array(B['centre']['tip_circle_centre'])
res = {}
def gsmooth(y, sig):
    k = np.arange(-int(4*sig)-1, int(4*sig)+2); g = np.exp(-0.5*(k/sig)**2); g/=g.sum()
    return np.convolve(np.pad(y,len(k)//2,mode='edge'), g, mode='valid')
for name,(pB,dB,rmsB,kB) in lb.items():
    d,nn = R.edge_frame(pB,dB,C)
    t=int(name[1]); n=int(name.split('-N')[1])
    Vt=np.array(B['tips'][str(t)]['vertex']); Vn=np.array(B['notches'][str(n)]['vertex'])
    s_t=(Vt-pB)@d; s_n=(Vn-pB)@d
    pA,dA,_,_ = la[name]
    nA_=np.array([-dA[1],dA[0]]); nA_/=np.linalg.norm(nA_)
    if nA_@(pA-C)<0: nA_=-nA_
    uu = np.arange(-12, 22.01, 0.25)
    fr = np.arange(0.10, 0.905, 0.025)
    rows=[]
    for f in fr:
        s = s_t + f*(s_n-s_t); P = pB + s*d
        acc = 0
        for ds in np.arange(-5,5.01,1.0):
            acc = acc + R.bilinear(L, P[0]+ds*d[0]+uu*nn[0], P[1]+ds*d[1]+uu*nn[1])
        prof = gsmooth(acc/11.0, 1.0)
        dl = np.gradient(prof, 0.25)
        win = (uu>=-6)&(uu<=10)
        imin = np.nonzero(win)[0][np.argmin(prof[win])]
        # first local max of slope after the minimum with slope >= 0.02/px
        cand = [i for i in range(imin+1, len(uu)-1) if dl[i]>=dl[i-1] and dl[i]>=dl[i+1] and dl[i]>=0.02 and uu[i]<=imin*0+uu[imin]+12]
        u_step = uu[cand[0]] if cand else np.nan
        uA = -((P-pA)@nA_)/(nA_@nn)
        rows.append((f, u_step, uu[imin], prof[imin], dl[cand[0]] if cand else np.nan, uA))
    rows=np.array(rows)
    res[name]=dict(normal=nn.tolist(), rows=rows.tolist())
json.dump(res, open(R.BASE+"/reconcile/shadowstep.json","w"))
print('%-6s %6s %-34s | median u_step (B=0)  by f-band [0.1-0.3, 0.3-0.5, 0.5-0.7, 0.7-0.9] | uA mid'%('edge','n_y','kindB'))
for name in sorted(res, key=lambda k: res[k]['normal'][1]):
    r=np.array(res[name]['rows']); ny=res[name]['normal'][1]
    bands=[]
    for a,b in [(0.1,0.3),(0.3,0.5),(0.5,0.7),(0.7,0.91)]:
        m=(r[:,0]>=a)&(r[:,0]<b)&~np.isnan(r[:,1]); bands.append(np.median(r[m,1]) if m.sum() else np.nan)
    print('%-6s %+6.2f %-34s | %s  | %+.1f'%(name, ny, lb[name][3], '  '.join('%+5.1f'%v for v in bands), np.median(r[:,5])))
