"""Resume the saved male, obtain Epic rig/textures, then build optimized assets."""
from pathlib import Path
import unreal as ue,json,traceback,datetime,os
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
OUT=ROOT/'Exports/CharacterLab/Unreal/Validation/male_assembly.json'
DEST='/Game/Characters/MetaHumans/MH_MaleBase'
INTERACTIVE=os.environ.get('MH_INTERACTIVE')=='1'
report={'asset':DEST,'engine':ue.SystemLibrary.get_engine_version(),'status':'starting','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
subsystem=None;character=None
def checkpoint(status):
    report['status']=status;OUT.write_text(json.dumps(report,indent=2));ue.log('MH_ASSEMBLY '+status)
try:
    character=ue.load_asset(DEST);assert character
    subsystem=ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    if INTERACTIVE:
        ue.EditorPythonScripting.set_keep_python_script_alive(True)
        ue.get_editor_subsystem(ue.AssetEditorSubsystem).open_editor_for_assets([character])
    if not subsystem.is_object_added_for_editing(character):assert subsystem.try_add_object_to_edit(character)
    checkpoint('saved_character_reopened')
    if not subsystem.can_build_meta_human(character,False):
        checkpoint('requesting_rig')
        rig=ue.MetaHumanCharacterAutoRiggingRequestParams();rig.blocking=True;rig.report_progress=False
        rig.rig_type=ue.MetaHumanRigType.JOINTS_ONLY
        subsystem.request_auto_rigging(character,rig)
        ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
        checkpoint('rig_request_returned')
        if not character.get_editor_property('has_high_resolution_textures'):
            checkpoint('requesting_texture_sources')
            textures=ue.MetaHumanCharacterTextureRequestParams();textures.blocking=True;textures.report_progress=False
            subsystem.request_texture_sources(character,textures)
            ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
    report['has_high_resolution_textures']=character.get_editor_property('has_high_resolution_textures')
    report['can_build']=subsystem.can_build_meta_human(character,False)
    if report['can_build']:
        checkpoint('building_optimized_high')
        build=ue.MetaHumanCharacterEditorBuildParameters();build.pipeline_type=ue.MetaHumanDefaultPipelineType.OPTIMIZED
        build.pipeline_quality=ue.MetaHumanQualityLevel.HIGH
        build.absolute_build_path='/Game/MetaHumans';build.common_folder_path='/Game/MetaHumans/Common'
        build.enable_wardrobe_item_validation=False
        subsystem.build_meta_human(character,build)
        ue.EditorAssetLibrary.save_loaded_asset(character,only_if_is_dirty=False)
        registry=ue.AssetRegistryHelpers.get_asset_registry()
        entries=registry.get_assets_by_path('/Game/MetaHumans',recursive=True)
        report['built_asset_count']=len(entries)
        report['blueprints']=[str(a.package_name) for a in entries if str(a.asset_class_path.asset_name)=='Blueprint']
        assert report['blueprints'],'Assembly did not produce a Blueprint'
        checkpoint('assembled')
    else:checkpoint('rig_or_texture_service_incomplete')
except Exception:
    report['error']=traceback.format_exc();checkpoint('failed');ue.log_error(report['error'])
finally:
    if not INTERACTIVE:
        if subsystem and character and subsystem.is_object_added_for_editing(character):subsystem.remove_object_to_edit(character)
        ue.SystemLibrary.quit_editor()
