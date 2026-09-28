import unreal, json
out = {}
def names(cls_name, filt=None):
    c = getattr(unreal, cls_name, None)
    if c is None:
        return "MISSING"
    n = [x for x in dir(c) if not x.startswith("_")]
    return [x for x in n if (filt is None or any(f in x.lower() for f in filt))]
out["SkeletalMeshEditorSubsystem"] = names("SkeletalMeshEditorSubsystem")
out["AnimationLibrary"] = names("AnimationLibrary", ["pose", "length", "frame", "key", "rate"])
out["SkeletalMesh"] = names("SkeletalMesh", ["socket", "lod", "physics", "bound", "ref", "skeleton"])
out["PoseableMeshComponent"] = names("PoseableMeshComponent", ["bone"])
out["PhysicsAsset"] = names("PhysicsAsset")
out["BodySetup"] = names("BodySetup")
out["PhysicsAssetFactory"] = names("PhysicsAssetFactory")
out["PhysicsAssetEditorSubsystem"] = names("PhysicsAssetEditorSubsystem")
out["SkeletalMeshSocket"] = names("SkeletalMeshSocket")
out["KAggregateGeom"] = names("KAggregateGeom")
out["KBoxElem"] = names("KBoxElem")
out["physics_classes"] = [x for x in dir(unreal) if "physic" in x.lower() or "bodysetup" in x.lower()][:80]
out["SkeletalMeshLODInfo"] = names("SkeletalMeshLODInfo")
out["Skeleton"] = names("Skeleton", ["socket", "bone", "ref"])
out["FbxAnimSequenceImportData"] = names("FbxAnimSequenceImportData")
out["FbxSkeletalMeshImportData"] = names("FbxSkeletalMeshImportData")
open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/UnrealCheck/probe_api.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE_DONE")
