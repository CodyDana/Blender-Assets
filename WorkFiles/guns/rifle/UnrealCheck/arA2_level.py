"""AR-01 stage 8, pass A2 (a fresh UnrealEditor-Cmd, -nullrhi, after pass A): build and save the check level
<dest>/L_AR01_Check that pass E plays in -game (Python cannot spawn actors in a game world, so everything is placed
here). Imports nothing; the shipped assets are only referenced.

  physics area (U7): a 40 x 40 m ground slab (top at z = 0); SM_AR01 dropped from 1 m level and a second copy rolled 70
      deg; SM_AR01_Mag dropped from 1 m; SK_AR01 with PHYS_AR01, all with Simulate Physics on (PhysicsActor profile);
  texture area (U12) at x = 5000 cm: SK_AR01 with SM_AR01_Mag on its Mag socket, no physics; camera actors CAM_Hip (the
      receiver about 35 cm away, 90 deg) and CAM_ADS (the eye 25 cm behind the Sight socket on its line, 55 deg);
  a directional light and a sky light.
Actors carry tags AR_* so pass E finds them.
"""
import json, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ar_common as C  # noqa: E402

DEST = C.dest()
MAP = f"{DEST}/L_AR01_Check"
OUT = C.HERE / "arA2_level.json"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ML = unreal.MathLibrary
res = {"map": MAP, "t0": time.time(), "hashes_before": C.all_hashes()}
safe = C.safe


def spawn(cls, loc, rot=None, tag=None):
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), rot or unreal.Rotator())
    if tag:
        a.set_editor_property("tags", [unreal.Name(tag)])
        safe(lambda: a.set_actor_label(tag))
    return a


try:
    res["new_level"] = bool(LES.new_level(MAP))
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    cube.get_bounding_box(); cube.get_num_triangles(0)
    sm = unreal.load_asset(f"{DEST}/SM_AR01")
    mag = unreal.load_asset(f"{DEST}/SM_AR01_Mag")
    sk = unreal.load_asset(f"{DEST}/SK_AR01")
    mats = [unreal.load_asset(f"{DEST}/Materials/M_GC_AR01_{s}") for s in ("Metal", "Furniture", "Mag")]
    sun = spawn(unreal.DirectionalLight, (0, 0, 500), ML.make_rot_from_x(unreal.Vector(0.3, 0.4, -0.86)), "AR_Sun")
    sun.get_editor_property("directional_light_component").set_editor_property("intensity", 6.0)
    sun.get_editor_property("directional_light_component").set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky = spawn(unreal.SkyLight, (0, 0, 600), None, "AR_Sky")
    sc = sky.get_editor_property("light_component")
    safe(lambda: sc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE))
    safe(lambda: sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP))
    safe(lambda: sc.set_editor_property("cubemap", unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")))
    g = spawn(unreal.StaticMeshActor, (0, 0, -50), None, "AR_Ground")
    gc = g.get_editor_property("static_mesh_component")
    gc.set_static_mesh(cube)
    g.set_actor_scale3d(unreal.Vector(40, 40, 1))
    gc.set_collision_profile_name("BlockAll")
    gc.set_material(0, mats[1])

    def dropped(mesh, loc, rot, tag, matl):
        a = spawn(unreal.StaticMeshActor, loc, rot, tag)
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        for i, m in enumerate(matl):
            c.set_material(i, m)
        c.set_collision_profile_name("PhysicsActor")
        c.set_simulate_physics(True)
        return a
    dropped(sm, (0, -150, 100), unreal.Rotator(), "AR_PHYS_SM_AR01", mats)
    r70 = unreal.Rotator()
    r70.roll = 70.0
    dropped(sm, (0, -300, 100), r70, "AR_PHYS_SM_AR01_rolled", mats)
    dropped(mag, (0, 150, 100), unreal.Rotator(), "AR_PHYS_SM_AR01_Mag", [mats[2]])
    ka = spawn(unreal.SkeletalMeshActor, (0, 0, 100), unreal.Rotator(), "AR_PHYS_SK_AR01")
    kc = ka.get_editor_property("skeletal_mesh_component")
    kc.set_skinned_asset_and_update(sk)
    kc.set_material(0, mats[0])
    kc.set_material(1, mats[1])
    kc.set_collision_profile_name("PhysicsActor")
    kc.set_simulate_physics(True)
    res["sk_physics_asset"] = safe(lambda: kc.get_editor_property("physics_asset").get_path_name() if kc.get_editor_property("physics_asset") else sk.get_editor_property("physics_asset").get_path_name())
    # texture area
    base = (5000.0, 0.0, 150.0)
    ta = spawn(unreal.SkeletalMeshActor, base, unreal.Rotator(), "AR_TEX_SK_AR01")
    tc = ta.get_editor_property("skeletal_mesh_component")
    tc.set_skinned_asset_and_update(sk)
    tc.set_material(0, mats[0])
    tc.set_material(1, mats[1])
    # the magazine at the Mag socket (bind pose: identity rotation; a skinned component cannot be queried under -nullrhi)
    mloc = next(x for x in C.sidecar_sk()["sockets"] if x["name"] == "Mag")["unreal_component"]["location_cm"]
    tm = spawn(unreal.StaticMeshActor, (base[0] + mloc[0], base[1] + mloc[1], base[2] + mloc[2]), unreal.Rotator(),
               "AR_TEX_SM_AR01_Mag")
    tmc = tm.get_editor_property("static_mesh_component")
    tmc.set_mobility(unreal.ComponentMobility.MOVABLE)
    tmc.set_static_mesh(mag)
    tmc.set_material(0, mats[2])
    # the Sight socket from the sidecar (a skinned component has no render state under -nullrhi to ask)
    srec = next(x for x in C.sidecar_sk()["sockets"] if x["name"] == "Sight")["unreal_component"]
    q = unreal.Quat(*srec["quaternion_xyzw"])
    fx = q.rotate_vector(unreal.Vector(1, 0, 0))
    eye = unreal.Vector(*srec["location_cm"]) - fx * 25.0
    cams = {"CAM_ADS": ([base[0] + eye.x, base[1] + eye.y, base[2] + eye.z], [fx.x, fx.y, fx.z], 55.0),
            "CAM_Hip": ([base[0] - 14.0, base[1] - 12.0, base[2] + 17.0], [1.0, 0.28, -0.32], 90.0)}
    res["cameras"] = {}
    for nm, (loc, fwd, fov) in cams.items():
        ca = spawn(unreal.CameraActor, loc, ML.make_rot_from_x(unreal.Vector(*fwd)), nm)
        cc = ca.get_editor_property("camera_component")
        cc.set_editor_property("field_of_view", fov)
        safe(lambda: cc.set_editor_property("constrain_aspect_ratio", False))
        res["cameras"][nm] = {"loc": loc, "fwd": fwd, "fov": fov}
    res["saved"] = bool(LES.save_current_level())
    res["listing"] = sorted(str(x) for x in unreal.EditorAssetLibrary.list_assets(DEST, recursive=False, include_folder=False))
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
res["seconds"] = round(time.time() - res["t0"], 1)
C.write(OUT, res)
unreal.log("AR_PASS_A2_DONE status=" + res["status"])
