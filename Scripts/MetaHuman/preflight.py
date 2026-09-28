"""Read installed MetaHuman capabilities without creating placeholder characters."""
from pathlib import Path
import json,unreal as ue,datetime
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
OUT=ROOT/'Exports/CharacterLab/Unreal/Validation/preflight.json'
optional=Path(r'C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\MetaHuman\MetaHumanCharacter\Content\Optional')
registry=ue.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/MetaHumanCharacter'],force_rescan=True)
presets=[str(a.package_name) for a in registry.get_assets_by_path('/MetaHumanCharacter/Optional/Presets',recursive=True)]
characters=[{'package':str(a.package_name),'class':str(a.asset_class_path)} for a in registry.get_assets_by_path('/MetaHumanCharacter/Optional',recursive=True) if str(a.asset_class_path.asset_name)=='MetaHumanCharacter']
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'engine':ue.SystemLibrary.get_engine_version(),'creator_class_available':hasattr(ue,'MetaHumanCharacter'),
        'creator_subsystem_available':hasattr(ue,'MetaHumanCharacterEditorSubsystem'),
        'core_data_present':optional.is_dir(),'presets':presets,'character_presets':characters,
        'status':'ready' if optional.is_dir() and characters else 'needs_core_data_install'}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2))
ue.log('METAHUMAN_PREFLIGHT '+json.dumps(report))
