"""Probe: a tight ACL bone-compression setting on the fan's animations; component pose vs raw pose."""
import json
import math
import time
import traceback

import unreal

DEST = "/Game/FanCheck/Dev1a"
out = {}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AL = unreal.AnimationLibrary
try:
    seq = unreal.load_asset(DEST + "/A_Fan_Openness")
    mesh = unreal.load_asset(DEST + "/SK_Fan")
    cur = AL.get_bone_compression_settings(seq)
    c0 = cur.get_editor_property("codecs")[0]
    props = {}
    for k in ("error_threshold", "default_virtual_vertex_distance", "safe_virtual_vertex_distance", "compression_level",
              "rotation_format", "translation_format", "scale_format", "keyframe_stripping_proportion",
              "keyframe_stripping_threshold"):
        try:
            props[k] = str(c0.get_editor_property(k))
        except Exception as e:                                    # noqa: BLE001
            props[k] = "ERR " + str(e)[:80]
    out["acl_default_props"] = props
    names = ["stick_00", "stick_25", "leaf_49", "stick_12", "leaf_24"]

    def comp_yaws(t):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(mesh)
        c.override_animation_data(seq, False, False, t, 0.0)
        r = {}
        for b in names:
            tt = c.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT)
            x = unreal.MathLibrary.transform_direction(tt, unreal.Vector(1, 0, 0))
            r[b] = math.degrees(math.atan2(x.y, x.x))
        EAS.destroy_actor(a)
        return r

    def raw_yaws(t):
        allnames = [str(n) for n in AL.get_bone_names(seq)] if hasattr(AL, "get_bone_names") else None
        return None
    out["before"] = {t: comp_yaws(t) for t in (0.0, 0.5, 1.0)}
    st = unreal.EditorAssetLibrary.duplicate_asset("/ACLPlugin/ACLAnimBoneCompressionSettings", DEST + "/ACS_Fan")
    codec = st.get_editor_property("codecs")[0]
    sets = {}
    for k, v in (("error_threshold", 0.0001), ("default_virtual_vertex_distance", 20.0), ("safe_virtual_vertex_distance", 100.0)):
        try:
            codec.set_editor_property(k, v)
            sets[k] = str(codec.get_editor_property(k))
        except Exception as e:                                    # noqa: BLE001
            sets[k] = "ERR " + str(e)[:120]
    try:
        lv = unreal.load_object(None, "/Script/ACLPlugin.ACLCompressionLevel") if False else None
        codec.set_editor_property("compression_level", getattr(unreal, "ACLCompressionLevel").ACL_CL_HIGHEST)
        sets["compression_level"] = str(codec.get_editor_property("compression_level"))
    except Exception as e:                                        # noqa: BLE001
        sets["compression_level"] = "ERR " + str(e)[:160]
    out["sets"] = sets
    t0 = time.time()
    AL.set_bone_compression_settings(seq, st)
    out["set_seconds"] = time.time() - t0
    out["after"] = {t: comp_yaws(t) for t in (0.0, 0.5, 1.0)}
except Exception:                                                  # noqa: BLE001
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe7.json", "w").write(json.dumps(out, indent=1, default=str))
unreal.log("PROBE7_DONE")
