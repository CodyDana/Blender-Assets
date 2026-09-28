"""Rig, download source textures, and assemble a MetaHuman (env PD_ASSET, default MH_PlayerDefault; PD_OUT report folder) (needs Cody's interactive Epic sign-in).

Run inside a normal (windowed) UnrealEditor on CharacterLab, WITHOUT -Unattended or
-NoMetaHumanAccountPortalLoginFallback, so the Epic login can open the browser.
Each stage saves the asset and writes a checkpoint to WorkFiles/MetaHuman/player_default/rig/rig_report.json.
Never enters credentials: Cody signs in in the browser.
"""
from pathlib import Path
import datetime
import json
import os
import traceback
import unreal as ue

ROOT = Path(r'C:\Users\Cody\Desktop\Blender_Projects')
OUT = ROOT / os.environ.get('PD_OUT', 'WorkFiles/MetaHuman/player_default/rig')
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / 'rig_report.json'
ASSET = os.environ.get('PD_ASSET', '/Game/Characters/MetaHumans/MH_PlayerDefault')
BUILD_ROOT = '/Game/MetaHumans'
QUALITY = os.environ.get('PD_QUALITY', 'HIGH')

report = {'asset': ASSET, 'engine': ue.SystemLibrary.get_engine_version(), 'quality': QUALITY,
          'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'steps': []}


def checkpoint(status, **extra):
    report['status'] = status
    report['steps'].append({'t_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': status, **extra})
    REPORT.write_text(json.dumps(report, indent=2))
    ue.log('PD_RIG ' + status)


def save(asset):
    ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)


def dump_bones():
    """Record the bone list of every built skeletal mesh (feeds the planned pipeline gates)."""
    registry = ue.AssetRegistryHelpers.get_asset_registry()
    out = {}
    world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    for a in registry.get_assets_by_path(BUILD_ROOT, recursive=True):
        if str(a.asset_class_path.asset_name) != 'SkeletalMesh':
            continue
        path = str(a.package_name)
        try:
            skm = ue.load_asset(path)
            actor = ue.get_editor_subsystem(ue.EditorActorSubsystem).spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, 0, -10000))
            comp = actor.skeletal_mesh_component
            comp.set_skeletal_mesh_asset(skm)
            names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
            skel = skm.get_editor_property('skeleton')
            out[path] = {'skeleton': skel.get_path_name() if skel else None, 'bone_count': len(names), 'bones': names}
            ue.get_editor_subsystem(ue.EditorActorSubsystem).destroy_actor(actor)
        except Exception as exc:  # best effort, never blocks the build result
            out[path] = {'error': repr(exc)}
    (OUT / 'bones.json').write_text(json.dumps(out, indent=2))
    return {k: v.get('bone_count') for k, v in out.items()}


sub = None
character = None
try:
    character = ue.load_asset(ASSET)
    assert character, 'MH_PlayerDefault not found'
    sub = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    if not sub.is_object_added_for_editing(character):
        assert sub.try_add_object_to_edit(character), 'cannot edit asset (open elsewhere?)'
    checkpoint('loaded', can_build=sub.can_build_meta_human(character, False))

    if not sub.can_build_meta_human(character, False):
        checkpoint('requesting_rig_SIGN_IN_IN_BROWSER')
        rig = ue.MetaHumanCharacterAutoRiggingRequestParams()
        rig.blocking = True
        rig.report_progress = True
        rig.rig_type = ue.MetaHumanRigType.JOINTS_ONLY
        sub.request_auto_rigging(character, rig)
        save(character)
        checkpoint('rig_returned', can_build=sub.can_build_meta_human(character, False))

    if not character.get_editor_property('has_high_resolution_textures'):
        checkpoint('requesting_texture_sources')
        tex = ue.MetaHumanCharacterTextureRequestParams()
        tex.blocking = True
        tex.report_progress = True
        sub.request_texture_sources(character, tex)
        save(character)
    report['has_high_resolution_textures'] = character.get_editor_property('has_high_resolution_textures')
    report['can_build'] = sub.can_build_meta_human(character, False)
    checkpoint('textures_returned', hi_res=report['has_high_resolution_textures'], can_build=report['can_build'])

    if report['can_build']:
        checkpoint('building_optimized_' + QUALITY)
        b = ue.MetaHumanCharacterEditorBuildParameters()
        b.pipeline_type = ue.MetaHumanDefaultPipelineType.OPTIMIZED
        b.pipeline_quality = getattr(ue.MetaHumanQualityLevel, QUALITY)
        b.absolute_build_path = BUILD_ROOT
        b.common_folder_path = BUILD_ROOT + '/Common'
        b.enable_wardrobe_item_validation = False
        try:
            sub.build_meta_human(character=character, params=b)
        except RuntimeError as exc:
            # UE 5.8.3 raises on logged errors during the call. Copying Epic's face Control Rigs into
            # /Game/MetaHumans/Common logs "Cannot break link ... RerouteNode" even though the log then says
            # "MetaHuman Character assembly succeeded". Tolerate exactly that; re-raise anything else.
            lines = [l.strip() for l in str(exc).splitlines() if l.strip()]
            if not lines or not all('Cannot break link' in l for l in lines):
                raise
            report['build_tolerated_warnings'] = lines
        save(character)
        ue.EditorAssetLibrary.save_directory(BUILD_ROOT, only_if_is_dirty=True, recursive=True)
        reg = ue.AssetRegistryHelpers.get_asset_registry()
        entries = reg.get_assets_by_path(BUILD_ROOT, recursive=True)
        report['built_asset_count'] = len(entries)
        report['blueprints'] = [str(a.package_name) for a in entries if str(a.asset_class_path.asset_name) == 'Blueprint']
        report['bone_counts'] = dump_bones()
        checkpoint('assembled' if report['blueprints'] else 'built_no_blueprint')
    else:
        checkpoint('rig_or_textures_incomplete')
except Exception:
    report['error'] = traceback.format_exc()
    checkpoint('failed')
    ue.log_error(report['error'])
finally:
    if sub and character and sub.is_object_added_for_editing(character):
        sub.remove_object_to_edit(character)
    report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, indent=2))
    ue.SystemLibrary.quit_editor()
