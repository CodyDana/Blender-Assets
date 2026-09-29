"""Set the ArmoryLab copy of the template's BP_ThirdPersonCharacter to Manny (SKM_Manny_Simple; the 5.8 template ships
with Quinn). Same skeleton and ABP_Unarmed, so only the mesh changes. Our own copy in ArmoryLab only; saved once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402

CH = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
bp = unreal.load_asset(CH)
cls = unreal.EditorAssetLibrary.load_blueprint_class(CH)
cdo = unreal.get_default_object(cls)
mesh = cdo.get_editor_property("mesh")
before = mesh.get_editor_property("skeletal_mesh_asset").get_name()
mesh.set_editor_property("skeletal_mesh_asset", unreal.load_asset(MANNY))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
saved = unreal.EditorAssetLibrary.save_asset(CH, only_if_is_dirty=False)
after = mesh.get_editor_property("skeletal_mesh_asset").get_name()
# Unreal rebuild: the runner greps "AK_STEP_DONE manny passed=True" like every other step (this line had no passed=)
unreal.log(f"AK_STEP_DONE manny passed={bool(saved and 'Manny' in after)} before={before} after={after} saved={saved}")
