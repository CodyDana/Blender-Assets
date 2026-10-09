import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal, ar_common as C
out = {k: sorted(x for x in dir(getattr(unreal, k)) if "spawn" in x.lower()) for k in ("GameplayStatics", "World", "EditorLevelLibrary", "EditorActorSubsystem", "Actor", "SystemLibrary")}
out["unreal_spawn"] = sorted(x for x in dir(unreal) if "spawn" in x.lower())[:50]
out["Pawn_add"] = sorted(x for x in dir(unreal.Actor) if "add_component" in x.lower())
C.write(C.HERE / "ar_probe2.json", out)
