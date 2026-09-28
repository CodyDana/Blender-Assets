import bpy,json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('PIPELINE_LOCK_DIR',str(ROOT/'WorkFiles/locks'))
sys.path.insert(0,str(ROOT/'Scripts/pipeline'))
from lock import assert_owner
assert_owner('BlackNunchucks','codex')

data={}
for ob in bpy.data.objects:
 p=ob.get('part_id','')
 if ob.type!='MESH' or ob.get('lod_level')!=0 or not (p.startswith('chain_') or p.startswith('eye_')):continue
 n=14; count=len(ob.data.vertices)//n
 if p.startswith('eye_'):count=(len(ob.data.vertices)-2)//n
 pts=[]
 for j in range(count):
  vs=[ob.matrix_world@v.co for v in ob.data.vertices[j*n:(j+1)*n]]
  pts.append([sum(v[k] for v in vs)/n/.0003 for k in range(3)])
 data[p]={'points':pts,'matrix':[list(row) for row in ob.matrix_world]}
(ROOT/'WorkFiles/BlackNunchucks/chain_centers.json').write_text(json.dumps(data))
