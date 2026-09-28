import bpy
o=bpy.data.objects['SM_Kunai_Plain_LOD0']
print('UV', [u.name for u in o.data.uv_layers], 'active_render', [u.name for u in o.data.uv_layers if u.active_render])
import numpy as np
v=np.array([vv.co[:] for vv in o.data.vertices]); print('BBOX', v.min(0), v.max(0))
print('ATTR', [a.name for a in o.data.attributes])
print('MODS', [m.type for m in o.modifiers])
for k in o.keys(): print('PROP', k, str(o[k])[:200])
