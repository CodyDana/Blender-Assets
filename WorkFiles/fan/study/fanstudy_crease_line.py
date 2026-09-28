"""FAN_STUDY 5.4: how far the exact free crease C(r) departs from one straight line (one rigid pleat bone),
constant Z pitch t (stacked sticks) vs cone pitch t*r/r_in. Gap 6 (front half) and gap 0."""
import math, numpy as np, json
N=26; G=25; TH=math.radians(166); beta=1.2*TH/(2*G); t=0.45; r_in=87.0; r_out=184.0
def crease(th, gap, r, cone):
    a=th/G; pitch = t*r/r_in if cone else t
    zi=lambda i: pitch*(i-12.5)
    phis=[-th/2+i*a for i in range(N)]
    A=np.array([r*math.cos(phis[gap]), r*math.sin(phis[gap]), zi(gap)])
    B=np.array([r*math.cos(phis[gap+1]), r*math.sin(phis[gap+1]), zi(gap+1)])
    M=(A+B)/2; s=B-A; d=np.linalg.norm(s); chord=2*r*math.sin(beta/2)
    h=math.sqrt(max(0,chord**2-(d/2)**2))
    radial=M/np.linalg.norm(M); radial[2]=0; radial/=np.linalg.norm(radial)
    n=np.cross(s/d, radial); n/=np.linalg.norm(n)
    sense = 1 if gap < G/2 else -1
    if n[2]*sense<0: n=-n
    return M+h*n
out={}
for cone in (False, True):
    worst=(0,None)
    for thd in [166,120,80,40,20,10,6,4,2,1,0.5,0.2,0.1,0.05]:
        for gap in (0,6,12):
            rs=np.linspace(r_in,r_out,12)
            P=np.array([crease(math.radians(thd),gap,r,cone) for r in rs])
            c=P.mean(0); U,S,Vt=np.linalg.svd(P-c); dirn=Vt[0]
            res=np.linalg.norm((P-c)-np.outer((P-c)@dirn,dirn),axis=1).max()
            # line through the pivot axis? distance of the fitted line from the rivet axis (x=y=0)
            if res>worst[0]: worst=(res,(thd,gap))
    out["cone" if cone else "constant_pitch"]=dict(max_line_residual_mm=round(float(worst[0]),3), at=worst[1],
        rim_stack_mm=round(25*(t*r_out/r_in if cone else t),2))
print(json.dumps(out,indent=1)); json.dump(out,open("fanstudy_crease_line.json","w"),indent=1)
