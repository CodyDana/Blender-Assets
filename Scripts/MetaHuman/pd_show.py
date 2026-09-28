"""Open the assembled player character for Cody to look at (no saves)."""
import unreal as ue

BP = '/Game/MetaHumans/MH_PlayerDefault/BP_MH_PlayerDefault'
bp = ue.load_asset(BP)
if bp:
    ue.get_editor_subsystem(ue.AssetEditorSubsystem).open_editor_for_assets([bp])
    ue.EditorAssetLibrary.sync_browser_to_objects([BP])
    ue.log('PD_SHOW opened ' + BP)
else:
    ue.log_error('PD_SHOW could not load ' + BP)
