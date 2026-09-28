# independent: blade volume = integral h(x) * (R(x) + E) dx  (unground diamond, area = h(R+E)), plus tang+ring fixed
import numpy as np, math
STOCK=5.0
def h(x):
    x=np.asarray(x,float); u=(x-35)/105
    return np.where(x<=35, 8+10*x/35, 18*(1-u)*(1+0.25*u))
def ridge(x,RB,RT,RTA,ramp,knots):
    out=[]
    for xi in x:
        if xi<=35:
            if ramp and xi<=ramp[0]: out.append(STOCK); continue
            if ramp and xi<ramp[1]: out.append(STOCK+(RB-STOCK)*(xi-ramp[0])/(ramp[1]-ramp[0])); continue
            out.append(RB); continue
        ks=[(35,RB)]+knots+[(RTA,RT)]
        v=None
        for (xa,ta),(xb,tb) in zip(ks,ks[1:]):
            if xi<=xb: v=max(RT,ta+(tb-ta)*(xi-xa)/(xb-xa)); break
        if v is None:
            (xa,ta),(xb,tb)=ks[-2],ks[-1]; v=max(RT,tb+(tb-ta)*(xi-xb)/(xb-xa))
        out.append(v)
    return np.array(out)
x=np.linspace(0,140,140001)
fixed=16*5*110 + math.pi/4*(32**2-20**2)*5 - 104.6
opts={'current':(5,1.6,135,None,[],1.5),'A':(5,1.6,135,None,[(63.6,5.0)],0.6),
      'B':(9,2.7,135,(5,24.42),[],1.5),'C':(7,1.6,135,(5,24.42),[],0.3)}
mesh={'current':151.89,'A':146.17,'B':185.61,'C':153.34}; tgt={'current':153.02,'A':146.98,'B':186.17,'C':154.06}
base=None
for k,(RB,RT,RTA,ramp,kn,E) in opts.items():
    R=ridge(x,RB,RT,RTA,ramp,kn); vb=np.trapezoid(h(x)*(R+E),x)
    g=(vb+fixed)*7.85e-3
    if base is None: base=g
    print(f"{k}: blade {vb:.1f} mm3  steel_unground {g:.2f} g  target {tgt[k]} (d {g-tgt[k]:+.2f})  mesh {mesh[k]} (d {g-mesh[k]:+.2f})  delta vs current: mine {g-base:+.2f} mesh {mesh[k]-mesh['current']:+.2f}")
    for xs in (13.4,26.7,39.4,56.7,74.1,91.4,108.7):
        Rx=ridge([xs],RB,RT,RTA,ramp,kn)[0]; hh=float(h(xs))
        print(f"   x{xs}: face_slope {(Rx-E)/2/hh:.3f} ridge_ratio {Rx/2/hh:.3f}", end='')
    print()
