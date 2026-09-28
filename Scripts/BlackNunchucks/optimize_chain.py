import sys,json,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('PIPELINE_LOCK_DIR',str(ROOT/'WorkFiles/locks'))
sys.path.insert(0,str(ROOT/'Scripts/pipeline'))
from lock import assert_owner
assert_owner('BlackNunchucks','codex')

optional_deps=ROOT/'WorkFiles/BlackNunchucks/qa_deps'
if optional_deps.is_dir():sys.path.insert(0,str(optional_deps))
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.distance import cdist
base=json.loads((ROOT/'WorkFiles/BlackNunchucks/chain_centers.json').read_text())
names=[f'chain_{i:02d}' for i in range(1,8)]+['eye_L','eye_R']
pairs=[(i,i+1) for i in range(6)]+[(7,0),(8,6)]
radii=np.array([7.6,8.7,8.7,8.7,8.7,8.7,7.6,7.,7.])
degrees=[-73,-47,-22,0,22,47,73]; rolls=[18,75,0,-65,0,-75,-18]
models=[]
for i,n in enumerate(names):
 p=np.array(base[n]['points']); c=p.mean(0)
 if i<7:
  phi=np.deg2rad(degrees[i]);psi=np.deg2rad(rolls[i]);axis=np.array([np.cos(phi),0,-np.sin(phi)]);across=np.array([np.sin(phi),0,np.cos(phi)])*np.cos(psi)+np.array([0,1,0])*np.sin(psi)
 else:
  mat=np.array(base[n]['matrix']);axis=mat[:3,2];across=p[0]-p[-1];across/=np.linalg.norm(across);c=(p[0]+p[-1])/2
 q=p-c;major=q@axis;minor=q@across;normal=np.cross(axis,across);normal/=np.linalg.norm(normal);perp=q@normal
 models.append((c,axis,across,normal,major,minor,perp))

def pose(x):
 pts=[];transforms=[]
 for i,m in enumerate(models):
  c,axis,across,normal,major,minor,perp=m
  if i<7:
   dx,dy,dz,roll,widen=x[i*5:i*5+5];shift=np.array([dx,dy,dz])
  else:
   roll,widen=x[35+(i-7)*2:37+(i-7)*2];shift=np.zeros(3)
  width=max(abs(minor));sc=1+widen/width
  aa=across*np.cos(roll)+normal*np.sin(roll);nn=normal*np.cos(roll)-across*np.sin(roll)
  pp=c+shift+major[:,None]*axis+minor[:,None]*sc*aa+perp[:,None]*nn
  pts.append(pp)
  transforms.append({'center':c.tolist(),'shift':shift.tolist(),'axis':axis.tolist(),'across':across.tolist(),'normal':normal.tolist(),'new_across':aa.tolist(),'new_normal':nn.tolist(),'width_scale':float(sc),'wire_radius_px':float(radii[i]),'roll_delta_deg':float(np.rad2deg(roll))})
 return pts,transforms

calls=0;start=time.time()
def residual(x):
 global calls
 calls+=1
 pts,_=pose(x);res=[]
 for a,b in pairs:
  d=cdist(pts[a],pts[b]);target=radii[a]+radii[b]+.9
  res.extend(np.maximum(0,target-d.min(0))*8);res.extend(np.maximum(0,target-d.min(1))*8)
 for i in range(7):
  v=x[i*5:i*5+5];res.extend(v*np.array([.25,.018,.25,5.,.25]))
 res.extend(x[35:]*np.array([5.,.2,5.,.2]))
 if calls%2000==0:print('progress',calls,round(time.time()-start,1),float(np.linalg.norm(res)),flush=True)
 return np.array(res)

x=np.zeros(39);x[4:35:5]=1.5;x[36::2]=2.
lb=[];ub=[]
for i in range(7):lb.extend([-8,-45,-8,-.65,0]);ub.extend([8,45,8,.65,6])
lb.extend([-.6,0,-.6,0]);ub.extend([.6,8,.6,8])
result=least_squares(residual,x,bounds=(lb,ub),max_nfev=500,ftol=1e-9,xtol=1e-8,gtol=1e-8,diff_step=1e-4)
pts,trans=pose(result.x)
clearances=[]
for a,b in pairs:
 clearance=float(cdist(pts[a],pts[b]).min()-radii[a]-radii[b]);clearances.append({'pair':[names[a],names[b]],'sample_clearance_px':clearance});print('clearance',names[a],names[b],clearance,flush=True)
report={'time_seconds':time.time()-start,'success':bool(result.success),'message':result.message,'cost':float(result.cost),'parameters':result.x.tolist(),'parts':dict(zip(names,trans)),'clearances':clearances}
(ROOT/'WorkFiles/BlackNunchucks/chain_solution.json').write_text(json.dumps(report,indent=2))
print('SOLUTION_WRITTEN',report['time_seconds'],flush=True)
