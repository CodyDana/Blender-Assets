import unreal,json
from pathlib import Path
p=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
m=unreal.load_asset('/Game/BlackCloak/Meshes/SK_BlackCloak')
s=m.get_editor_property('skeleton')
r={'skeleton':s.get_path_name() if s else None}
(p/'Validation/dependency_probe.json').write_text(json.dumps(r,indent=2))
unreal.log('CLOAK_DEPENDENCY '+json.dumps(r))
