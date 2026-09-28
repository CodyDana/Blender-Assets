import bpy, sys, json, collections
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts')
from pipeline.qa_check import qa_check
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/BlackCloak_Skeletal.fbx')
objs = [o for o in bpy.context.scene.objects]
res = qa_check(objs, budget_tris=30000, texel_density=10.24)
checks = res['checks'] if isinstance(res, dict) and 'checks' in res else res
fails = [c for c in checks if not c.get('passed', c.get('ok', True))]
cnt = collections.Counter(c['name'] if 'name' in c else c.get('check') for c in fails)
json.dump({'total': len(checks), 'failed': len(fails), 'by_name': cnt, 'sample': fails[:5]}, open('ve_qa_SK_LOD0.json', 'w'), indent=1, default=str)
print('VE_QA_DONE', len(checks), len(fails))
