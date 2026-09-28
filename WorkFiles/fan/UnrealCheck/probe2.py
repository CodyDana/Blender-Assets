import unreal, json
out = {}
mesh = unreal.load_asset("/Game/FanCheck/Dev1_a/SK_Fan")
for n in ["lod_info", "lod_infos", "LODInfo", "lod_settings", "minimum_lod", "positive_bounds_extension", "enable_per_poly_collision"]:
    try:
        v = mesh.get_editor_property(n); out[n] = str(type(v))
    except Exception as e:
        out[n] = "ERR " + str(e)[:120]
sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
sock = unreal.new_object(unreal.SkeletalMeshSocket, outer=mesh)
for n in ["bone_name", "relative_location", "relative_rotation"]:
    try:
        sock.set_editor_property(n, sock.get_editor_property(n)); out["sock_"+n] = "writable"
    except Exception as e:
        out["sock_"+n] = "ERR " + str(e)[:100]
try:
    sock.set_editor_property("bone_name", "stick_00")
    mesh.add_socket(sock, False)
    out["added_name"] = str(sock.get_editor_property("socket_name"))
    out["num_sockets"] = mesh.num_sockets()
    r = sub.rename_socket(mesh, sock.get_editor_property("socket_name"), "Grip")
    out["rename"] = str(r)
    out["after"] = str(mesh.get_socket_by_index(0).get_editor_property("socket_name"))
except Exception as e:
    out["socket_err"] = str(e)[:300]
out["lib"] = [x for x in dir(unreal) if "SkeletalMeshLibrary" in x or "LODSettings" in x or "SkeletalMeshLOD" in x]
el = getattr(unreal, "EditorSkeletalMeshLibrary", None)
out["EditorSkeletalMeshLibrary"] = [x for x in dir(el) if not x.startswith("_")] if el else None
open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/UnrealCheck/probe2.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE_DONE")
