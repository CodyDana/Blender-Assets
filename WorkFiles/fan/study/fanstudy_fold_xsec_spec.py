"""FAN_STUDY 5.4: cross-section test of pleat sense schemes (uniform vs converging) with stacked sticks.
At radius r, rib crease i = (r cos phi_i, r sin phi_i, z_i). Free crease = isometric point: equidistant
(developed chord) from both ribs, on the side given by the scheme. Tests: segment crossings between
non-adjacent leaf segments, leaf segments entering the guard rectangles, max |z| excursion, closed width."""
import numpy as np, math, json
N=26; G=N-1; TH_OPEN=math.radians(163.2); PSI=math.radians(173.6); beta=PSI/(2*G)   # REFERENCE_SPEC rows 2, 7
t_in=0.85; t_g=1.9; W_G=8.9   # REFERENCE_SPEC 4, 5 (designed thickness), guard tip width 0.047 L
# z of rib creases (stick mid-planes): guard0 front (negative z = toward viewer)
z=[-(24*t_in)/2 - t_in/2] + [-(24*t_in)/2 + t_in*(k+0.5) for k in range(24)] + [(24*t_in)/2 + t_in/2]   # equal Z pitch for every gap; guard creases on guard inner faces
def seg_x(p,q,a,b):
    def cr(o,a_,b_): return (a_[0]-o[0])*(b_[1]-o[1])-(a_[1]-o[1])*(b_[0]-o[0])
    d1,d2,d3,d4=cr(a,b,p),cr(a,b,q),cr(p,q,a),cr(p,q,b)
    return (d1*d2<0) and (d3*d4<0)
def run(scheme, r, th):
    a=th/G; phis=[-th/2+i*a for i in range(N)]
    P=[np.array([r*math.cos(p), r*math.sin(p), z[i]]) for i,p in enumerate(phis)]
    chord=2*r*math.sin(beta/2); pts=[]; worst_iso=0
    for i in range(G):
        A,B=P[i],P[i+1]; M=(A+B)/2; s=B-A; d=np.linalg.norm(s)
        h2=chord**2-(d/2)**2
        if h2<0: return None   # over-opened
        h=math.sqrt(h2)
        radial=M/np.linalg.norm(M); radial[2]=0; radial/=np.linalg.norm(radial)
        n=np.cross(s/d, radial); n/=np.linalg.norm(n)   # perpendicular to rib-rib segment, in the tangential-z plane
        sense = +1 if scheme=="uniform" else (+1 if i < G/2 else -1)
        if n[2]*sense<0: n=-n          # sense +1: pleat pops to +z (back)
        C=M+h*n; pts.append((A,C))
        worst_iso=max(worst_iso,abs(np.linalg.norm(C-A)-chord),abs(np.linalg.norm(C-B)-chord))
    pts.append((P[-1],None))
    # 2D cross-section coords: tangential arc position y = r*atan2, z
    def to2(p): return (r*math.atan2(p[1],p[0]), p[2])
    segs=[]
    for i in range(G):
        A,C=pts[i]; B=pts[i+1][0]; segs.append((i,0,to2(A),to2(C))); segs.append((i,1,to2(C),to2(B)))
    cross=0
    for x in range(len(segs)):
        for y in range(x+2,len(segs)):
            if abs(segs[x][0]-segs[y][0])<=0 and False: pass
            if seg_x(segs[x][2],segs[x][3],segs[y][2],segs[y][3]): cross+=1
    # guard rectangles: centred on guard rib crease, width W_G tangential, thickness t_g
    gpen=0
    for gi in (0,N-1):
        gy,gz=to2(P[gi]); gz = gz - t_g/2 if gi==0 else gz + t_g/2  # guard body lies outside its crease
        for (i,k,p,q) in segs:
            if (gi==0 and i==0 and k==0) or (gi==N-1 and i==G-1 and k==1): continue
            for f in np.linspace(0.02,0.98,25):
                yy=p[0]+(q[0]-p[0])*f; zz=p[1]+(q[1]-p[1])*f
                if abs(yy-gy)<W_G/2 and abs(zz-gz)<t_g/2: gpen+=1; break
    zs=[s[3][1] for s in segs]+[s[2][1] for s in segs]; ys=[s[2][0] for s in segs]+[s[3][0] for s in segs]
    stack_front=z[0]-t_g; stack_back=z[-1]+t_g
    return dict(cross=cross, guard_hits=gpen, iso_err_mm=worst_iso,
                z_min=round(min(zs),2), z_max=round(max(zs),2),
                beyond_stack_mm=round(max(0,stack_front-min(zs), max(zs)-stack_back),2),
                y_span=round(max(ys)-min(ys),2))
res={}
for scheme in ("uniform","converging"):
    rows=[]
    for thd in [163.2,150,120,100,80,60,50,40,30,25,20,15,12,10,8,6,5,4,3,2,1.5,1,0.7,0.5,0.3,0.2,0.1,0.05,0.02]:
        for r in (81.9,110.0,150.0,190.0):
            o=run(scheme,r,math.radians(thd))
            if o is None: rows.append(dict(theta=thd,r=r,note="over-open")); continue
            o.update(theta=thd,r=r); rows.append(o)
    res[scheme]=rows
json.dump(res,open("fanstudy_fold_xsec_spec.json","w"),indent=1)
for s,rows in res.items():
    print("==",s)
    for o in rows: print({k:(round(v,4) if isinstance(v,float) else v) for k,v in o.items()})
