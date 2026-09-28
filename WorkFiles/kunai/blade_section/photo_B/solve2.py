import numpy as np, json, math
exec(open('solve.py').read().split("best=sol")[0])
hw_w=float(np.mean([r['halfw'] for r in rows if abs(r['s'])<=3.1])); offs=[r['off'] for r in rows if abs(r['s'])<=6.1]; off_w=float(np.mean(offs))
keep=[]
for a,rl,k,wu,wl in alphas:
    pred=hw_w*math.tan(math.radians(a))*math.tan(math.radians(rl))
    ok=abs(pred-off_w)<=1.0
    keep.append((a,rl,k,wu,wl,pred,ok))
K=[c for c in keep if c[6]]
A=np.array([c[0] for c in K]); Rr=np.array([c[1] for c in K])
print('kept %d/%d combos; alpha min %.1f p25 %.1f med %.1f p75 %.1f max %.1f; roll %.1f..%.1f med %.1f'%(len(K),len(keep),A.min(),*np.percentile(A,[25,50,75]),A.max(),Rr.min(),Rr.max(),np.median(Rr)))
for c in keep: print(' a=%5.1f roll=%5.1f k=%.2f %s/%s pred=%5.2f %s'%c)
json.dump(dict(widest_halfw=hw_w,widest_off=off_w,combos=[dict(alpha=c[0],roll=c[1],k=c[2],curve_up=c[3],curve_lo=c[4],pred_off=c[5],geom_ok=c[6]) for c in keep],
  kept_alpha=[float(A.min()),*map(float,np.percentile(A,[25,50,75])),float(A.max())],kept_roll=[float(Rr.min()),float(np.median(Rr)),float(Rr.max())]),open('joint.json','w'),indent=1)
