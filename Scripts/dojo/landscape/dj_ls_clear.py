"""LANDSCAPE ROUND (world stage): remove every actor tagged DJ_Landscape from L_Dojo and save (pythonscript commandlet,
-nullrhi). Run before dj_ls_world.py: a RENDERING commandlet that LOADS a level already holding the Megaplants cypress
(PVE skinned Nanite assemblies) asserts on a background worker (ShowFlags IsInGameThread, measured twice), while the
null-RHI load and the -game load are fine, and spawning them fresh in the rendering build is fine."""
import json
from pathlib import Path
import unreal
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ok = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
n = 0
for a in EAS.get_all_level_actors():
    if unreal.Name("DJ_Landscape") in list(a.tags):
        EAS.destroy_actor(a)
        n += 1
saved = bool(les.save_current_level())
rest = len(EAS.get_all_level_actors())
Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\world\json\ls_clear.json").write_text(
    json.dumps({"loaded": ok, "removed": n, "saved": saved, "actors_left": rest}), encoding="utf-8")
unreal.log(f"DJ_STEP_DONE ls_clear passed={ok and saved} removed={n} left={rest}")
