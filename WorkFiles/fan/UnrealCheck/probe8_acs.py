"""Probe: which shipped bone-compression settings keep the fan's pose (component vs raw)."""
import json
import math
import traceback

import unreal

DEST = "/Game/FanCheck/Dev1a"
out = {}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AL = unreal.AnimationLibrary
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    found = []
    for root in ("/Engine", "/ACLPlugin"):
        ar.scan_paths_synchronous([root], True)
        for ad in ar.get_assets_by_path(root, recursive=True):
            cls = str(ad.asset_class_path.asset_name) if hasattr(ad, "asset_class_path") else str(ad.asset_class)
            if cls == "AnimBoneCompressionSettings":
                found.append(str(ad.package_name))
    out["settings_assets"] = found
    seq = unreal.load_asset(DEST + "/A_Fan_Openness")
    mesh = unreal.load_asset(DEST + "/SK_Fan")
    names = ["root"] + [str(n) for n in AL.get_animation_track_names(seq)] if hasattr(AL, "get_animation_track_names") else None
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    bn = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
    par = {n: str(comp.get_parent_bone(n)) for n in bn}

    def cs_raw(t):
        poses = AL.get_bone_poses_for_time(seq, bn, t, False)
        loc = dict(zip(bn, poses))
        world = {}

        def res(n):
            if n not in world:
                p = par[n]
                world[n] = loc[n] if p in ("None", "") else unreal.MathLibrary.compose_transforms(loc[n], res(p))
            return world[n]
        for n in bn:
            res(n)
        return world

    def err(t):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(mesh)
        c.override_animation_data(seq, False, False, t, 0.0)
        raw = cs_raw(t)
        worst = 0.0
        for b in bn:
            tt = c.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT)
            # a point 19 cm out along the bone's x and y axes
            for ax in (unreal.Vector(19, 0, 0), unreal.Vector(0, 19, 0)):
                p1 = unreal.MathLibrary.transform_location(tt, ax)
                p2 = unreal.MathLibrary.transform_location(raw[b], ax)
                worst = max(worst, math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2))
        EAS.destroy_actor(a)
        return worst
    times = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    out["default"] = {"settings": AL.get_bone_compression_settings(seq).get_path_name(),
                      "worst_cm_at_19cm": max(err(t) for t in times)}
    trials = {}
    for pth in found:
        try:
            st = unreal.load_asset(pth)
            AL.set_bone_compression_settings(seq, st)
            trials[pth] = {"codecs": [c.get_class().get_name() for c in st.get_editor_property("codecs")],
                           "worst_cm_at_19cm": max(err(t) for t in times)}
        except Exception as e:                                    # noqa: BLE001
            trials[pth] = "ERR " + str(e)[:200]
    out["trials"] = trials
except Exception:                                                  # noqa: BLE001
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe8.json", "w").write(json.dumps(out, indent=1, default=str))
unreal.log("PROBE8_DONE")
