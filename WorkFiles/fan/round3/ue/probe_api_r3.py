import json, unreal
out = {}
out["sub"] = [n for n in dir(unreal.SkeletalMeshEditorSubsystem) if not n.startswith("_")]
out["skm"] = [n for n in dir(unreal.SkeletalMesh) if not n.startswith("_")]
out["seq"] = [n for n in dir(unreal.AnimSequence) if not n.startswith("_") and ("loop" in n.lower() or "compress" in n.lower())]
out["al"] = [n for n in dir(unreal.AnimationLibrary) if not n.startswith("_") and ("loop" in n.lower() or "compress" in n.lower())]
out["mat"] = [n for n in dir(unreal.Material) if "used_with" in n]
out["smc"] = [n for n in dir(unreal.SkeletalMeshComponent) if "socket" in n.lower() or "material" in n.lower()]
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\round3\ue\probe_api_r3.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE_DONE")
extra = {}
cdo = unreal.get_default_object(unreal.AnimSequence)
for k in ("loop", "b_loop", "bone_compression_settings", "compression_error_threshold_scale"):
    try:
        extra[k] = str(cdo.get_editor_property(k))
    except Exception as e:
        extra[k] = "ERR " + str(e)[:120]
sk = unreal.get_default_object(unreal.SkeletalMesh)
for k in ("positive_bounds_extension", "negative_bounds_extension", "lod_info", "materials"):
    try:
        extra["skm." + k] = str(sk.get_editor_property(k))[:200]
    except Exception as e:
        extra["skm." + k] = "ERR " + str(e)[:120]
m = unreal.get_default_object(unreal.Material)
for k in ("used_with_skeletal_mesh", "used_with_instanced_static_meshes"):
    try:
        extra["mat." + k] = str(m.get_editor_property(k))
    except Exception as e:
        extra["mat." + k] = "ERR " + str(e)[:120]
out["extra"] = extra
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\round3\ue\probe_api_r3.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE2_DONE")
