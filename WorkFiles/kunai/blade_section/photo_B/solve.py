import numpy as np, json, math
from PIL import Image
probe=json.load(open('ring_probe.json'))['curve']  # up, med, q25, q75, n
fac=json.load(open('facets.json')); rows=fac['rows']
UP=np.array([r[0] for r in probe]); CUR={'med':np.array([r[1] for r in probe]),'q25':np.array([r[2] for r in probe]),'q75':np.array([r[3] for r in probe])}
def inv(Lval,which='med'):
    c=np.maximum.accumulate(CUR[which]); m=(UP>=-30)&(UP<=46)
    u=UP[m]; c=c[m]+np.arange(m.sum())*1e-3
    if Lval<=c[0]: return float(u[0])
    if Lval>=c[-1]: return float(u[-1])
    return float(np.interp(Lval,c,u))
SY=0.9221  # image-up component of the in-plane width direction (perp to axis at -22.76 deg)
def beta(up): return math.degrees(math.asin(max(-1,min(1,math.sin(math.radians(up))/SY))))
s_sh,s_tip,s_vis=fac['s_shoulder'],fac['s_tip'],fac['s_visible_end']
def ours_mm(s):
    return (s-s_sh)/(0-s_sh)*35.0 if s<0 else 35.0+s/s_tip*105.0
def ours(x):
    h=8+10*x/35 if x<=35 else 18*(1-(x-35)/105)*(1+0.25*(x-35)/105)
    t=5.0 if x<=35 else max(1.6,5+(1.6-5)*(x-35)/100)
    return h,t/2
def at(s,key):
    rr=min(rows,key=lambda r:abs(r['s']-s)); 
    near=[r for r in rows if abs(r['s']-s)<=4.6]
    return float(np.mean([r[key] for r in near]))
stations=[0.10,0.245,0.40,0.60,0.80,0.93]
out=[]
# global roll from the front facets (planar: brightness constant) for each albedo assumption
front=[r for r in rows if 0.30<=r['frac_vis']<=0.85]
Lu_f=float(np.median([r['Lup'] for r in front])); Ll_f=float(np.median([r['Llo'] for r in front]))
print('front facet L median up %.1f lo %.1f'%(Lu_f,Ll_f))
sol={}
for k in (1.0,1.1,1.25):
    for which in ('med','q25','q75'):
        bu=beta(inv(Lu_f/k,which)); bl=beta(inv(Ll_f/k,which))
        # q25 curve is darker => larger tilt needed for the same L; for the lower facet use the paired opposite curve for a bound
        sol[(k,which)]=dict(beta_up=bu,beta_lo=bl,alpha=(bu-bl)/2,roll=(bu+bl)/2)
for key,v in sol.items(): print(key,{a:round(b,2) for a,b in v.items()})
# bounds: widest alpha range = lower facet from q25 (darker curve->less negative?) combos
alphas=[]
for k in (1.0,1.1,1.25):
    for wu in ('med','q25','q75'):
        for wl in ('med','q25','q75'):
            bu=beta(inv(Lu_f/k,wu)); bl=beta(inv(Ll_f/k,wl)); alphas.append(((bu-bl)/2,(bu+bl)/2,k,wu,wl))
A=np.array([a[0] for a in alphas]); Rl=np.array([a[1] for a in alphas])
print('alpha over all combos: min %.1f p25 %.1f med %.1f p75 %.1f max %.1f'%(A.min(),*np.percentile(A,[25,50,75]),A.max()))
print('roll over all combos: min %.1f med %.1f max %.1f'%(Rl.min(),np.median(Rl),Rl.max()))
best=sol[(1.1,'med')]
alpha_c=best['alpha']; roll_c=best['roll']
aP25,aP75=np.percentile(A,[25,75]); aMin,aMax=A.min(),A.max()
# geometric check at the widest station: predicted ridge offset (px) vs measured
hw_w=at(0.0,'halfw'); off_w=at(-3,'off')*0.5+at(3,'off')*0.5
pred=hw_w*math.tan(math.radians(alpha_c))*math.tan(math.radians(roll_c))
print('widest halfw %.2f measured ridge off %.2f px, predicted %.2f px (alpha %.1f roll %.1f)'%(hw_w,off_w,pred,alpha_c,roll_c))
# coplanar-ring hypothesis H1
rf=json.load(open('ring_fit.json'))['45']; cth=(rf['inner']['semi_minor']+rf['outer']['semi_minor'])/(rf['inner']['semi_major']+rf['outer']['semi_major'])
th=math.degrees(math.acos(cth)); print('ring centreline cos %.3f -> roll %.1f deg'%(cth,th))
for fv in stations:
    s=s_sh+fv*(s_vis-s_sh); x=ours_mm(s); w_o,hr_o=ours(x)
    hw=at(s,'halfw'); off=at(s,'off'); Lu=at(s,'Lup'); Ll=at(s,'Llo')
    q=off/hw
    if s>=0:
        a_c=alpha_c; a_lo=aP25; a_hi=aP75; a_min=aMin; a_max=aMax
        note='front facet: planar (brightness constant %.0f-%.0f), slope shared with the widest-station crease section'%(min(r['Lup'] for r in front),max(r['Lup'] for r in front))
    else:
        # rear: per-station brightness inversion with fixed roll; correct for the backward lean of the rear facet
        a_list=[]
        for k in (1.0,1.1,1.25):
            for wu in ('med','q25','q75'):
                bu=beta(inv(Lu/k,wu)); bl=beta(inv(Ll/k,wu))
                al=(bu-bl)/2
                # backward lean of the facet normal ~0.24*slope rad along -x (image dir has up comp -0.394): adds ~0.39*lean to needed tilt
                lean=math.degrees(0.24*math.tan(math.radians(al))); al+=0.5*0.394*lean
                a_list.append(al)
        a_list=np.array(a_list); a_c=float(np.median(a_list)); a_lo,a_hi=np.percentile(a_list,[25,75]); a_min,a_max=a_list.min(),a_list.max()
        note='rear facet: brightness inversion per station (roll taken from the front), small backward-lean correction'
    fs=math.tan(math.radians(a_c)); e_w=0.75/w_o
    q_H1=q/math.tan(math.radians(th))
    out.append(dict(frac_from_shoulder_visible=round(fv,3),frac_from_shoulder_to_extrapolated_tip=round((s-s_sh)/(s_tip-s_sh),3),
        ours_mm_from_shoulder=round(x,1),photo_halfwidth_px=round(hw,2),photo_halfwidth_over_max=round(hw/hw_w,3),
        ridge_offset_px=round(off,2),ridge_offset_frac_q=round(q,4),facet_L_upper=round(Lu,1),facet_L_lower=round(Ll,1),
        face_angle_deg=round(a_c,1),face_angle_IQR=[round(float(a_lo),1),round(float(a_hi),1)],face_angle_full_range=[round(float(a_min),1),round(float(a_max),1)],
        face_slope=round(fs,3),face_slope_IQR=[round(math.tan(math.radians(a_lo)),3),round(math.tan(math.radians(a_hi)),3)],face_slope_full_range=[round(math.tan(math.radians(a_min)),3),round(math.tan(math.radians(a_max)),3)],
        edge_half_over_halfwidth_used=round(e_w,4),ridge_ratio=round(fs+e_w,3),ridge_ratio_if_sharp_edge=round(fs,3),
        ours_face_slope=round((hr_o-0.75)/w_o,3),ours_ridge_ratio=round(hr_o/w_o,3),
        H1_coplanar_ring_ridge_ratio=round(q_H1,3),note=note))
for o in out: print(o['frac_from_shoulder_visible'],o['ours_mm_from_shoulder'],'q',o['ridge_offset_frac_q'],'alpha',o['face_angle_deg'],o['face_angle_IQR'],'slope',o['face_slope'],o['face_slope_IQR'],'ridge',o['ridge_ratio'],'ours',o['ours_face_slope'],o['ours_ridge_ratio'],'H1',o['H1_coplanar_ring_ridge_ratio'])
json.dump(dict(alpha_front=alpha_c,roll=roll_c,alpha_IQR=[float(aP25),float(aP75)],alpha_range=[float(aMin),float(aMax)],roll_range=[float(Rl.min()),float(Rl.max())],
  widest_off_meas=off_w,widest_off_pred=pred,ring_roll_if_circle=th,ring_cos=cth,front_L=[Lu_f,Ll_f],stations=out),open('solve.json','w'),indent=1)
