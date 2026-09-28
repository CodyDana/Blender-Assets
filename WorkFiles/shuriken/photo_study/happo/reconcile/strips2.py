import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R
rgb,w,h = R.load_rgb(); L = R.lum(rgb)
A,B,la,lb = R.load_lines()
C = (np.array(A['centre'])+np.array(B['centre']['tip_circle_centre']))/2
def make(name, NS=700, UMAX=40, vs=3):
    pB,dB,rmsB,kB = lb[name]; pA,dA,rmsA,nA = la[name]
    t=int(name[1]); n=int(name.split('-N')[1])
    Vt=np.array(B['tips'][str(t)]['vertex']); Vn=np.array(B['notches'][str(n)]['vertex'])
    d,nn = R.edge_frame(pB,dB,C)
    s_t=(Vt-pB)@d; s_n=(Vn-pB)@d; tip_first = s_t<s_n
    ss=np.linspace(min(s_t,s_n)-15, max(s_t,s_n)+15, NS)
    uu=np.arange(-UMAX,UMAX+1,1.0)
    SS,UU=np.meshgrid(ss,uu)
    strip=R.bilinear(L, pB[0]+SS*d[0]+UU*nn[0], pB[1]+SS*d[1]+UU*nn[1])
    tile=np.repeat(strip[:,:,None],3,axis=2)
    Px=pB[0]+ss*d[0]; Py=pB[1]+ss*d[1]
    nA_=np.array([-dA[1],dA[0]]); nA_/=np.linalg.norm(nA_)
    if nA_@(pA-C)<0: nA_=-nA_
    uA=-((np.stack([Px,Py],1)-pA)@nA_)/max(1e-6,nA_@nn)
    cols=np.arange(NS); ridx=np.round(uA+UMAX).astype(int)
    ok=(ridx>=0)&(ridx<len(uu))
    tile[ridx[ok],cols[ok]]=[1,0,0]
    tile[int(UMAX),:]=[0,1,0]
    tile=np.flipud(tile)
    if not tip_first: tile=tile[:,::-1]
    tile=np.repeat(tile,vs,axis=0)
    bar=np.zeros((14,NS,3),dtype=np.float32); bar[:,:,0]=0.4
    return np.vstack([bar,tile])
for grp,names in [('contested',['T0-N0','T3-N2','T4-N3','T5-N4','T5-N5','T6-N6']),
                  ('agreeing',['T1-N0','T3-N3','T4-N4','T7-N6','T2-N1','T7-N7'])]:
    m=np.vstack([make(n) for n in names])
    R.save_png(m, R.BASE+"/reconcile/strips_%s.png"%grp)
    print(grp, names, m.shape)
