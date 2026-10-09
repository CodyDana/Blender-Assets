"""API probe (fresh commandlet, -nullrhi): names only, nothing imported or saved."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ar_common as C  # noqa: E402

res = {"engine": unreal.SystemLibrary.get_engine_version()}


def names(obj, keys):
    try:
        return sorted(x for x in dir(obj) if any(k in x.lower() for k in keys))
    except Exception as e:  # noqa
        return str(e)


def props(cls, keys):
    out = []
    try:
        o = unreal.new_object(cls)
    except Exception:
        o = None
    for x in dir(cls):
        if any(k in x.lower() for k in keys):
            out.append(x)
    if o is not None:
        for k in keys:
            pass
    return sorted(set(out))


res["AnimationLibrary_notify"] = names(unreal.AnimationLibrary, ("notify", "frame", "time", "pose", "compress", "raw"))
res["AnimNotifyEvent"] = names(unreal.AnimNotifyEvent, ("") ) if hasattr(unreal, "AnimNotifyEvent") else None
res["AnimNotifyEvent_all"] = sorted(x for x in dir(unreal.AnimNotifyEvent) if not x.startswith("_")) if hasattr(unreal, "AnimNotifyEvent") else None
res["AnimSequence"] = names(unreal.AnimSequence, ("notif", "frame", "rate", "length", "compress", "bound"))
res["Skeleton"] = names(unreal.Skeleton, ("notif", "socket", "bone", "ref"))
res["SkeletalMesh"] = names(unreal.SkeletalMesh, ("lod", "tri", "bound", "socket", "phys", "vert", "section", "material", "mesh"))
res["SkeletalMeshEditorSubsystem"] = names(unreal.SkeletalMeshEditorSubsystem, ("",))
res["SkinnedMeshComponent"] = names(unreal.SkinnedMeshComponent, ("lod", "vert", "skin", "bone", "bound", "socket"))
res["SkeletalMeshComponent"] = names(unreal.SkeletalMeshComponent, ("anim", "lod", "vert", "pose", "phys", "simul", "bone"))
res["PrimitiveComponent"] = names(unreal.PrimitiveComponent, ("first", "person", "shadow", "owner", "lod", "world_space", "visible", "hidden"))
res["enums"] = {k: (sorted(x for x in dir(getattr(unreal, k)) if x.isupper()) if hasattr(unreal, k) else None)
                for k in ("FirstPersonPrimitiveType", "EFirstPersonPrimitiveType")}
res["unreal_first"] = sorted(x for x in dir(unreal) if "firstperson" in x.lower() or "first_person" in x.lower())
res["CameraComponent"] = names(unreal.CameraComponent, ("first", "person", "fov", "field"))
res["SceneCaptureComponent2D"] = names(unreal.SceneCaptureComponent2D, ("first", "person", "show", "view", "lod", "stream", "owner", "hidden"))
res["Texture2D"] = names(unreal.Texture2D, ("mip", "resid", "stream", "lod", "size", "memory", "group"))
res["Texture"] = names(unreal.Texture, ("mip", "resid", "stream", "lod", "group", "compress"))
res["RenderingLibrary"] = names(unreal.RenderingLibrary, ("",))
res["SystemLibrary_tick"] = names(unreal.SystemLibrary, ("tick", "delay", "physics", "trace", "sweep", "overlap", "bounds", "console", "cvar"))
res["KismetSystem_cvar"] = names(unreal.SystemLibrary, ("cvar", "console_variable"))
res["EditorLevelLibrary"] = names(unreal.EditorLevelLibrary, ("play", "simul", "pie", "tick", "world"))
res["LevelEditorSubsystem"] = names(unreal.LevelEditorSubsystem, ("play", "simul", "pie", "tick", "world"))
res["UnrealEditorSubsystem"] = names(unreal.UnrealEditorSubsystem, ("world", "game", "pie"))
res["World"] = names(unreal.World, ("tick", "time", "physics", "delta"))
res["unreal_tick"] = sorted(x for x in dir(unreal) if "tick" in x.lower())[:80]
res["AutomationLibrary"] = names(unreal.AutomationLibrary, ("screenshot", "stream", "flush", "wait", "frame")) if hasattr(unreal, "AutomationLibrary") else None
res["PhysicsAsset"] = names(unreal.PhysicsAsset, ("body", "constraint", "bound"))
res["StaticMeshComponent"] = names(unreal.StaticMeshComponent, ("simul", "physics", "lod", "wake", "sleep", "velocity", "mass"))
res["StaticMesh"] = names(unreal.StaticMesh, ("uv", "light", "lod", "tri", "bound", "nanite", "socket", "description"))
res["StaticMeshEditorSubsystem"] = names(unreal.StaticMeshEditorSubsystem, ("uv", "light", "lod", "collision", "convex", "screen"))
res["SkeletalMeshExporterFBX"] = hasattr(unreal, "SkeletalMeshExporterFBX")
res["AnimSequenceExporterFBX"] = hasattr(unreal, "AnimSequenceExporterFBX")
res["FbxExportOption"] = sorted(x for x in dir(unreal.FbxExportOption) if not x.startswith("_") and x.islower())
res["MeshDescription"] = sorted(x for x in dir(unreal) if "meshdescription" in x.lower())
res["SkeletalMeshLODSettings"] = hasattr(unreal, "SkeletalMeshLODSettings")
res["AnimPose"] = names(unreal.AnimPoseExtensions, ("",)) if hasattr(unreal, "AnimPoseExtensions") else None
res["cvars"] = {}
for cv in ("r.Shadow.Virtual.Enable", "r.AllowStaticLighting", "r.TextureStreaming", "r.Streaming.PoolSize", "r.FirstPerson.Enable"):
    res["cvars"][cv] = C.safe(lambda cv=cv: unreal.SystemLibrary.get_console_variable_int_value(cv))
C.write(C.HERE / "ar_probe.json", res)
unreal.log("AR_PROBE_DONE")
