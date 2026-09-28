import importlib.util,json
from pathlib import Path
import unreal
root=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
spec=importlib.util.spec_from_file_location('cloak_setup',root/'Scripts/BlackCloak/unreal_recolor_setup.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
p=root/'WorkFiles/BlackCloak/UnrealRecolor/Validation/recolor_setup_report.json'
r=json.loads(p.read_text())
materials={'cloth':unreal.load_asset('/Game/BlackCloak/Materials/MI_Cloak_Black'),'steel':unreal.load_asset('/Game/BlackCloak/Materials/M_Cloak_BlackenedSteel'),'leather':unreal.load_asset('/Game/BlackCloak/Materials/M_Cloak_CharcoalLeather')}
new=module.import_mesh(root/'Exports/BlackCloak/BlackCloak_Skeletal.fbx',True,materials)
r['meshes']=[entry if not entry['skeletal'] else new for entry in r['meshes']]
p.write_text(json.dumps(r,indent=2))
unreal.log('CLOAK_SKELETON_SAVED '+new['skeleton'])
