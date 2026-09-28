import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R
rgb,w,h = R.load_rgb(); L = R.lum(rgb)
Y = (rgb[:,:,0]+rgb[:,:,1])/2 - rgb[:,:,2]          # yellowness
A,B,la,lb = R.load_lines()
C = (np.array(A['centre'])+np.array(B['centre']['tip_circle_centre']))/2
# local texture: |L - box5(L)|
K=5; pad=np.pad(L,K//2,mode='edge')
box=np.zeros_like(L)
for dy in range(K):
    for dx in range(K):
        box += pad[dy:dy+L.shape[0], dx:dx+L.shape[1]]
box/=K*K
TEX = np.abs(L-box)
padT=np.pad(TEX,4,mode='edge'); TEXs=np.zeros_like(TEX)
for dy in range(9):
    for dx in range(9): TEXs += padT[dy:dy+L.shape[0], dx:dx+L.shape[1]]
TEXs/=81
def prof(name, fracs=(0.15,0.35,0.55,0.75)):
    pB,dB,rmsB,kB = lb[name]; pA,dA,rmsA,nA = la[name]
    t=int(name[1]); n=int(name.split('-N')[1])
    Vt=np.array(B['tips'][str(t)]['vertex']); Vn=np.array(B['notches'][str(n)]['vertex'])
    d,nn=R.edge_frame(pB,dB,C)
    s_t=(Vt-pB)@d; s_n=(Vn-pB)@d
    nA_=np.array([-dA[1],dA[0]]); nA_/=np.linalg.norm(nA_)
    if nA_@(pA-C)<0: nA_=-nA_
    print('=== %s  kindB=%s  rmsA=%.2f rmsB=%.2f' % (name,kB,rmsA,rmsB))
    for f in fracs:
        s = s_t + f*(s_n-s_t)
        P = pB + s*d
        uA = -((P-pA)@nA_)/(nA_@nn)
        uu = np.arange(-26,27,2.0)
        # average +-6 px along the edge
        acc={'L':0,'Y':0,'T':0}
        for ds in np.arange(-6,6.5,1.5):
            X=P[0]+ds*d[0]+uu*nn[0]; Yy=P[1]+ds*d[1]+uu*nn[1]
            acc['L']=acc['L']+R.bilinear(L,X,Yy); acc['Y']=acc['Y']+R.bilinear(Y,X,Yy); acc['T']=acc['T']+R.bilinear(TEXs,X,Yy)
        nrep=len(np.arange(-6,6.5,1.5))
        Lp=acc['L']/nrep; Yp=acc['Y']/nrep; Tp=acc['T']/nrep
        print(' f=%.2f  A at u=%+.1f' % (f,uA))
        print('   u :'+''.join('%6.0f'%v for v in uu))
        print('   L :'+''.join('%6.2f'%v for v in Lp))
        print('   Y :'+''.join('%6.3f'%v for v in Yp))
        print('   T :'+''.join('%6.3f'%v for v in Tp))
for nm in ['T2-N1','T1-N1','T0-N0','T3-N2','T4-N4']:
    prof(nm)
