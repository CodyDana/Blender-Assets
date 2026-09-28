"""Probe: how to pose SK_Fan from an AnimSequence in a commandlet world (for pass2 renders and bounds)."""
import json
import traceback

import unreal

DEST = "/Game/FanCheck/Dev1a"
out = {}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
try:
    mesh = unreal.load_asset(DEST + "/SK_Fan")
    anim = unreal.load_asset(DEST + "/A_Fan_Openness")
    a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
    smc = a.get_editor_property("skeletal_mesh_component")
    smc.set_skinned_asset_and_update(mesh)
    out["actor"] = a.get_class().get_name()
    out["smc_methods"] = [n for n in dir(smc) if any(k in n for k in ("tick", "refresh", "pose", "update", "anim", "position", "bound"))]

    def rs(tag):
        t = smc.get_socket_transform("stick_25", unreal.RelativeTransformSpace.RTS_COMPONENT)
        r = t.rotation.rotator()
        b = smc.get_editor_property("bounds") if False else None
        out[tag] = {"yaw": r.yaw, "loc": [t.translation.x, t.translation.y, t.translation.z]}
    rs("ref")
    smc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    smc.set_animation(anim)
    smc.set_position(0.0, False)
    rs("A_t0")
    smc.set_position(0.5, False)
    rs("A_t05")
    for fn in ("tick_animation", "refresh_bone_transforms", "tick_pose", "update_pose", "finalize_bone_transform",
               "set_update_animation_in_editor", "tick_component"):
        out["has_" + fn] = hasattr(smc, fn)
    try:
        smc.set_update_animation_in_editor(True)
        smc.set_position(0.25, False)
        rs("C_t025_update_in_editor")
    except Exception as e:                                       # noqa: BLE001
        out["C_err"] = str(e)[:200]
    try:
        smc.override_animation_data(anim, False, False, 0.75, 0.0)
        rs("B_override_075")
    except Exception as e:                                       # noqa: BLE001
        out["B_err"] = str(e)[:200]
    # poseable mesh component attempts
    try:
        pm = unreal.new_object(unreal.PoseableMeshComponent, outer=a)
        out["poseable_methods"] = [n for n in dir(pm) if "bone" in n or "register" in n or "attach" in n]
    except Exception as e:                                       # noqa: BLE001
        out["poseable_err"] = str(e)[:300]
    out["actor_methods"] = [n for n in dir(a) if "component" in n]
    out["libs"] = [n for n in dir(unreal) if n.endswith("Library") and ("Anim" in n or "Skel" in n or "Component" in n)]
except Exception:                                                # noqa: BLE001
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe5.json", "w").write(json.dumps(out, indent=1, default=str))
unreal.log("PROBE5_DONE")
