"""Probe: animation compression API (UE 5.8.3) and its effect on the component's evaluated pose."""
import json
import math
import sys
import traceback

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck")
import unreal  # noqa: E402

DEST = "/Game/FanCheck/Dev1a"
out = {}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AT = unreal.AssetToolsHelpers.get_asset_tools()
try:
    out["classes"] = [n for n in dir(unreal) if "Compress" in n and ("Codec" in n or "Settings" in n or n.startswith("AnimCompress"))]
    seq = unreal.load_asset(DEST + "/A_Fan_Openness")
    mesh = unreal.load_asset(DEST + "/SK_Fan")
    cur = seq.get_editor_property("bone_compression_settings")
    out["current"] = cur.get_path_name() if cur else None
    if cur:
        out["current_codecs"] = [c.get_class().get_name() for c in cur.get_editor_property("codecs")]
        c0 = cur.get_editor_property("codecs")[0]
        out["codec_props"] = {n: str(safe_v) for n, safe_v in []}
        out["codec_dir"] = [n for n in dir(c0) if not n.startswith("_") and "_" in n][:80]
    out["al_compress"] = [n for n in dir(unreal.AnimationLibrary) if "ompress" in n]
    out["seq_compress"] = [n for n in dir(seq) if "ompress" in n]

    def yaw_at(t):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(mesh)
        c.override_animation_data(seq, False, False, t, 0.0)
        r = {}
        for b in ("stick_00", "stick_25", "leaf_49", "stick_12"):
            tt = c.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT)
            x = unreal.MathLibrary.transform_direction(tt, unreal.Vector(1, 0, 0))
            r[b] = math.degrees(math.atan2(x.y, x.x))
        EAS.destroy_actor(a)
        return r
    out["before"] = yaw_at(0.0)
    # try a near-lossless setting
    st = AT.create_asset("ACS_FanProbe", DEST, unreal.AnimBoneCompressionSettings, None)
    out["settings_created"] = st.get_path_name() if st else None
    made = None
    for cls_name in ("AnimCompress_BitwiseCompressOnly",):
        cls = getattr(unreal, cls_name, None)
        if cls is None:
            continue
        codec = unreal.new_object(cls, outer=st)
        props = {}
        for k in ("rotation_compression_format", "translation_compression_format", "scale_compression_format"):
            try:
                props[k] = str(codec.get_editor_property(k))
            except Exception as e:                                # noqa: BLE001
                props[k] = "ERR " + str(e)[:100]
        out["bitwise_props"] = props
        try:
            codec.set_editor_property("rotation_compression_format", unreal.AnimationCompressionFormat.ACF_FLOAT96_NO_W)
            codec.set_editor_property("translation_compression_format", unreal.AnimationCompressionFormat.ACF_NONE)
        except Exception as e:                                    # noqa: BLE001
            out["bitwise_set_err"] = str(e)[:200]
        made = codec
    st.set_editor_property("codecs", [made])
    seq.set_editor_property("bone_compression_settings", st)
    for fn in ("request_anim_compression", "wait_on_compression", "compress"):
        if hasattr(unreal.AnimationLibrary, fn):
            out["called_" + fn] = True
    try:
        unreal.AnimationLibrary.request_anim_compression(seq, unreal.AnimationLibrary.RequestAnimCompressionParams if False else None)
    except Exception as e:                                        # noqa: BLE001
        out["req_err"] = str(e)[:300]
    out["after"] = yaw_at(0.0)
except Exception:                                                  # noqa: BLE001
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe6.json", "w").write(json.dumps(out, indent=1, default=str))
unreal.log("PROBE6_DONE")
