# Reconciled geometry: B's 16 silhouette lines (verified on strips + step detector), except
# T3-N2 which B took from the face crease: shifted outward by +3.2 px (step detector, +-2 px).
# Uncertainty by Monte-Carlo perturbation of the weak lines.
import json, math, numpy as np
BASE="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo"
A=json.load(open(BASE+"/radial/geom.json")); B=json.load(open(BASE+"/contour/b7_results.json"))
C0=np.array(B['centre']['tip_circle_centre'])
names=list(B['edges'].keys())
def frame(p,d,C):
    d=np.array(d,float); d/=np.linalg.norm(d); n=np.array([-d[1],d[0]])
    if n@(np.array(p)-C)<0: n=-n
    return np.array(p,float),d,n
base={k:frame(e['sil_line'][0],e['sil_line'][1],C0) for k,e in B['edges'].items()}
def inter(L1,L2):
    p1,d1,_=L1; p2,d2,_=L2
    t=np.linalg.solve(np.array([[d1[0],-d2[0]],[d1[1],-d2[1]]]),p2-p1); return p1+t[0]*d1
def circfit(P):
    P=np.asarray(P); A_=np.c_[2*P,np.ones(len(P))]; b=(P**2).sum(1)
    cx,cy,c=np.linalg.lstsq(A_,b,rcond=None)[0]; return np.array([cx,cy]), math.sqrt(c+cx*cx+cy*cy)
def angle_at(V,La,Lb,C,tip=True):
    ws=[]
    for (p,d,n) in (La,Lb):
        w=d if d@(C-V)>0 else -d; ws.append(w)
    a=math.degrees(math.acos(np.clip(ws[0]@ws[1],-1,1)))
    return a   # tip: included angle; notch: V opening (angle between the inward extensions = opening)
def solve(lines):
    tips={};notch={}
    for t in range(8):
        es=[k for k in lines if k.startswith('T%d-'%t)]; V=inter(lines[es[0]],lines[es[1]])
        tips[t]=[V,angle_at(V,lines[es[0]],lines[es[1]],C0,True)]
    for n in range(8):
        es=[k for k in lines if k.endswith('-N%d'%n)]; V=inter(lines[es[0]],lines[es[1]])
        notch[n]=[V,angle_at(V,lines[es[0]],lines[es[1]],C0,False)]
    use=[0,1,2,3,4,6,7]
    Ct,Rt=circfit([tips[t][0] for t in use]); Cn,Rn=circfit([notch[n][0] for n in range(8)])
    C=(Ct+Cn)/2
    return dict(tips=tips,notch=notch,Ct=Ct,Rt=Rt,Cn=Cn,Rn=Rn,C=C)
def shifted(lines,name,du,rot_notch=0.0):
    p,d,n=lines[name]; out=dict(lines); out[name]=(p+du*n,d,n); return out
def rotated(lines,name,du_notch):
    # move the notch end outward by du_notch with the tip end fixed (tilt about tip vertex)
    p,d,n=lines[name]; t=int(name[1]); nn=int(name.split('-N')[1])
    tips=solve(lines)['tips']; nch=solve(lines)['notch']
    Vt=tips[t][0]; Vn=nch[nn][0]; Vn2=Vn+du_notch*n
    d2=(Vn2-Vt)/np.linalg.norm(Vn2-Vt); out=dict(lines); out[name]=frame(Vt,d2,C0); return out
REC=shifted(base,'T3-N2',3.2)
G=solve(REC)
span=2*G['Rt']; rho=G['Rn']/G['Rt']
ta=np.array([G['tips'][t][1] for t in range(8)]); na=np.array([G['notch'][n][1] for n in range(8)])
C=G['Ct']
rt=np.array([np.linalg.norm(G['tips'][t][0]-C) for t in range(8)])
rn=np.array([np.linalg.norm(G['notch'][n][0]-C) for n in range(8)])
pol=np.array([math.degrees(math.atan2(-(G['tips'][t][0][1]-C[1]), G['tips'][t][0][0]-C[0]))%360 for t in range(8)])
print('RECONCILED (B lines, T3-N2 +3.2px)')
print(' tip circle centre %s R %.2f  notch circle centre %s R %.2f'%(np.round(G['Ct'],2),G['Rt'],np.round(G['Cn'],2),G['Rn']))
print(' span %.1f px   rho %.4f   notch R/span %.4f'%(span,rho,G['Rn']/span))
print(' tip angles  ', np.round(ta,2), ' mean(all8) %.2f sd %.2f | excl T5 %.2f sd %.2f'%(ta.mean(),ta.std(ddof=1),np.delete(ta,5).mean(),np.delete(ta,5).std(ddof=1)))
print(' notch opens ', np.round(na,2), ' mean %.2f sd %.2f'%(na.mean(),na.std(ddof=1)), ' notch-tip %.2f'%(na.mean()-ta.mean()))
print(' tip r      ', np.round(rt,1), ' sd(excl T5) %.2f'%np.delete(rt,5).std(ddof=1))
print(' notch r    ', np.round(rn,1), ' sd %.2f'%rn.std(ddof=1))
sp=np.diff(np.r_[pol,pol[0]+360]); print(' tip polar  ', np.round(pol,2), ' spacing', np.round(sp,2), 'sd %.2f'%sp.std(ddof=1))
print(' T5 vertex (clipped tip) ', np.round(G['tips'][5][0],1), ' T3 vertex', np.round(G['tips'][3][0],1))
def reg_tip(rho,n=8):
    a=math.pi/n; return 2*math.degrees(math.atan(rho*math.sin(a)/(1-rho*math.cos(a))))
def reg_rho(tipdeg,n=8):
    a=math.pi/n; t=math.tan(math.radians(tipdeg/2)); return t/(math.sin(a)+t*math.cos(a))
print(' regular-star check: tip from rho %.2f ; rho from mean tip(excl T5) %.4f'%(reg_tip(rho), reg_rho(np.delete(ta,5).mean())))
opp=[np.linalg.norm(G['tips'][i][0]-G['tips'][i+4][0]) for i in range(4)]
print(' opposite tip distances', np.round(opp,1))
# Monte-Carlo on weak lines
rng=np.random.default_rng(1); S=[]
for i in range(400):
    L=shifted(base,'T3-N2',3.2+rng.normal(0,2.0))
    L=shifted(L,'T5-N4',rng.normal(0,2.0))
    L=rotated(L,'T0-N0',rng.normal(0,2.0))
    for k in L:  # generic per-line jitter: 0.5 px offset, 0.1 deg
        p,d,n=L[k]; th=math.radians(rng.normal(0,0.1)); R2=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]])
        L[k]=(p+rng.normal(0,0.5)*n,R2@d,R2@n)
    g=solve(L); t_=np.array([g['tips'][t][1] for t in range(8)]); n_=np.array([g['notch'][n][1] for n in range(8)])
    S.append([2*g['Rt'],g['Rn']/g['Rt'],g['Rn']/(2*g['Rt']),np.delete(t_,5).mean(),n_.mean(),g['Ct'][0],g['Ct'][1]])
S=np.array(S)
print(' MC sd: span %.2f rho %.4f notchR/span %.4f tip %.3f notch %.3f cx %.2f cy %.2f'%tuple(S.std(0)))
out=dict(lines={k:[v[0].tolist(),v[1].tolist()] for k,v in REC.items()},
         tips={t:dict(vertex=G['tips'][t][0].tolist(),angle=G['tips'][t][1],r=float(rt[t]),polar=float(pol[t])) for t in range(8)},
         notches={n:dict(vertex=G['notch'][n][0].tolist(),opening=G['notch'][n][1],r=float(rn[n])) for n in range(8)},
         centre=G['Ct'].tolist(),notch_centre=G['Cn'].tolist(),R_tip=G['Rt'],R_notch=G['Rn'],span=span,rho=rho,
         mc_sd=dict(zip(['span','rho','notchR_span','tip','notch','cx','cy'],S.std(0).tolist())))
json.dump(out,open(BASE+"/reconcile/reconciled_geom.json","w"),indent=1)
