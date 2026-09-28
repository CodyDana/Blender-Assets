"""Rev-3 blade envelope per z slice (master SF_Blade + relief), read-only. blender -b Master.blend --factory-startup --python blade_envelope.py -- out.json"""
import bpy, sys, json
import numpy as np
out=sys.argv[sys.argv.index('--')+1]
res={}
def pts(names):
    P=[]
    for o in bpy.data.objects:
        if o.type=='MESH' and any(o.name.startswith(n) for n in names):
            m=o.matrix_world; P+= [tuple(m@v.co) for v in o.data.vertices]
    return np.array(P)
B=pts(['SF_Blade']); R=pts(['SF_BladeRelief'])
rows=[]
for z in np.arange(0.14,1.09,0.05):
    s=B[(B[:,2]>=z)&(B[:,2]<z+0.05)]; r=R[(R[:,2]>=z)&(R[:,2]<z+0.05)] if len(R) else np.zeros((0,3))
    if len(s): rows.append({'z':round(float(z),3),'blade_x':[round(float(s[:,0].min()),4),round(float(s[:,0].max()),4)],'blade_y':[round(float(s[:,1].min()),4),round(float(s[:,1].max()),4)],
        'relief_y':[round(float(r[:,1].min()),4),round(float(r[:,1].max()),4)] if len(r) else None})
res['slices']=rows
G=pts(['SF_Guard']); res['guard']={'min':G.min(0).round(4).tolist(),'max':G.max(0).round(4).tolist()}
json.dump(res,open(out,'w'),indent=1);print('DONE')
