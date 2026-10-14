"""SR01 W5, pass A2 (a fresh UnrealEditor-Cmd, -nullrhi, after pass A): build and save the check level
<dest>/L_SR01_Check that pass E plays in -game (Python cannot spawn actors in a game world, so everything is placed
here). Imports nothing; the shipped assets are only referenced.

  physics area (U7): a 40 x 40 m ground slab (top at z = 0); SM_SR01 dropped from 1 m level and a second copy rolled 70
      deg; SM_SR01_Mag dropped from 1 m; SK_SR01 with PHYS_SR01 (bipod folded) and a second SK_SR01 holding the
      BipodDeploy clip's last frame (bipod deployed: the component-bounds check; the game drops the gun with the legs
      folded, so its legs may sink into the ground by design), all with Simulate Physics on (PhysicsActor profile);
  texture area (U12) at x = 5000 cm: SK_SR01 with SM_SR01_Mag on its Mag socket, no physics; camera actors CAM_Hip (the
      receiver about 35 cm away, 90 deg) and CAM_ADS (the scope's EyePoint looking down its Sight line, 55 deg), with
      SM_Att_Scope_LongRange at Rail_Top + 2 slots;
  a directional light and a sky light.
Actors carry tags SM_* so pass E finds them.
"""
import json, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import sr_common as C  # noqa: E402

DEST = C.dest()
MAP = f"{DEST}/L_SR01_Check"
OUT = C.HERE / "srA2_level.json"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ML = unreal.MathLibrary
PX = 400.0   # the drops stand 4 m off the origin: -game spawns its DefaultPawn (a 35 cm sphere) at the origin (measured:
             # the first run's SK came to rest on it)
res = {"map": MAP, "t0": time.time(), "hashes_before": C.all_hashes()}
safe = C.safe


def spawn(cls, loc, rot=None, tag=None):
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), rot or unreal.Rotator())
    if tag:
        a.set_editor_property("tags", [unreal.Name(tag)])
        safe(lambda: a.set_actor_label(tag))
    return a


try:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):      # our own check level from an earlier run of this pass: reuse it
        res["loaded_previous_level"] = bool(LES.load_level(MAP))
        old = EAS.get_all_level_actors()
        res["removed_previous_actors"] = len(old)
        for a_ in old:
            EAS.destroy_actor(a_)
    else:
        res["new_level"] = bool(LES.new_level(MAP))
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    cube.get_bounding_box(); cube.get_num_triangles(0)
    sm = unreal.load_asset(f"{DEST}/SM_SR01")
    mag = unreal.load_asset(f"{DEST}/SM_SR01_Mag")
    sk = unreal.load_asset(f"{DEST}/SK_SR01")
    mats = [unreal.load_asset(f"{DEST}/Materials/M_GC_SR01_{s}") for s in ("Metal", "Chassis", "Mag")]
    smats = [unreal.load_asset(f"{DEST}/Materials/M_GC_SR01_{s}") for s in ("Scope_Body", "Scope_Lens")]
    scope = unreal.load_asset(f"{DEST}/{C.SCOPE}")
    sun = spawn(unreal.DirectionalLight, (0, 0, 500), ML.make_rot_from_x(unreal.Vector(0.3, 0.4, -0.86)), "SM_Sun")
    sun.get_editor_property("directional_light_component").set_editor_property("intensity", 6.0)
    sun.get_editor_property("directional_light_component").set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky = spawn(unreal.SkyLight, (0, 0, 600), None, "SM_Sky")
    sc = sky.get_editor_property("light_component")
    safe(lambda: sc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE))
    safe(lambda: sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP))
    safe(lambda: sc.set_editor_property("cubemap", unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")))
    g = spawn(unreal.StaticMeshActor, (0, 0, -50), None, "SM_Ground")
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
    dropped(sm, (PX, -150, 100), unreal.Rotator(), "SM_PHYS_SM_SR01", mats)
    r70 = unreal.Rotator()
    r70.roll = 70.0
    dropped(sm, (PX, -300, 100), r70, "SM_PHYS_SM_SR01_rolled", mats)
    dropped(mag, (PX, 150, 100), unreal.Rotator(), "SM_PHYS_SM_SR01_Mag", [mats[2]])
    ka = spawn(unreal.SkeletalMeshActor, (PX, 0, 100), unreal.Rotator(), "SM_PHYS_SK_SR01")
    kc = ka.get_editor_property("skeletal_mesh_component")
    kc.set_skinned_asset_and_update(sk)
    kc.set_material(0, mats[0])
    kc.set_material(1, mats[1])
    kc.set_collision_profile_name("PhysicsActor")
    kc.set_simulate_physics(True)
    # the deployed-bipod drop (U7 bounds): SK_SR01 holding A_SR01_BipodDeploy's last frame (single node, not playing)
    # while its one body simulates; bones without bodies follow the animation relative to 'body'
    fa = spawn(unreal.SkeletalMeshActor, (PX, 450, 100), unreal.Rotator(), "SM_PHYS_SK_SR01_deployed")
    fc = fa.get_editor_property("skeletal_mesh_component")
    fc.set_skinned_asset_and_update(sk)
    fc.set_material(0, mats[0])
    fc.set_material(1, mats[1])
    fold = unreal.load_asset(f"{DEST}/A_SR01_BipodDeploy")
    fc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    pd = unreal.SingleAnimationPlayData()
    pd.set_editor_property("anim_to_play", fold)
    pd.set_editor_property("saved_looping", False)
    pd.set_editor_property("saved_playing", False)
    pd.set_editor_property("saved_position", float(fold.get_play_length()))
    pd.set_editor_property("saved_play_rate", 0.0)
    fc.set_editor_property("animation_data", pd)
    fc.set_collision_profile_name("PhysicsActor")
    fc.set_simulate_physics(True)
    res["folded_actor"] = {"anim": fold.get_path_name(), "position_s": float(fold.get_play_length()),
                           "mode": str(fc.get_editor_property("animation_mode"))}
    res["sk_physics_asset"] = safe(lambda: kc.get_editor_property("physics_asset").get_path_name() if kc.get_editor_property("physics_asset") else sk.get_editor_property("physics_asset").get_path_name())
    # texture area
    base = (5000.0, 0.0, 150.0)
    ta = spawn(unreal.SkeletalMeshActor, base, unreal.Rotator(), "SM_TEX_SK_SR01")
    tc = ta.get_editor_property("skeletal_mesh_component")
    tc.set_skinned_asset_and_update(sk)
    tc.set_material(0, mats[0])
    tc.set_material(1, mats[1])
    # the magazine at the Mag socket (the sidecar's Mag transform; a skinned component cannot be queried under -nullrhi)
    mloc = next(x for x in C.sidecar_sk()["sockets"] if x["name"] == "Mag")["unreal_component"]["location_cm"]
    mq = next(x for x in C.sidecar_sk()["sockets"] if x["name"] == "Mag")["unreal_component"]["quaternion_xyzw"]
    tm = spawn(unreal.StaticMeshActor, (base[0] + mloc[0], base[1] + mloc[1], base[2] + mloc[2]), unreal.Quat(*mq).rotator(),
               "SM_TEX_SM_SR01_Mag")
    tmc = tm.get_editor_property("static_mesh_component")
    tmc.set_mobility(unreal.ComponentMobility.MOVABLE)
    tmc.set_static_mesh(mag)
    tmc.set_material(0, mats[2])
    # the scope at Rail_Top + 2 slots (sidecar gun.scope) and its EyePoint / Sight from the scope sidecar (a skinned
    # component has no render state under -nullrhi to ask); every rotation here is identity (sidecars)
    rail = next(x for x in C.sidecar_sk()["sockets"] if x["name"] == "Rail_Top")["unreal_component"]["location_cm"]
    mount = [rail[0] + C.scope_offset_cm(), rail[1], rail[2]]
    so = spawn(unreal.StaticMeshActor, (base[0] + mount[0], base[1] + mount[1], base[2] + mount[2]), unreal.Rotator(), "SM_TEX_SCOPE")
    soc = so.get_editor_property("static_mesh_component")
    soc.set_mobility(unreal.ComponentMobility.MOVABLE)
    soc.set_static_mesh(scope)
    for i, m in enumerate(smats):
        soc.set_material(i, m)
    ssc = json.loads((C.EXP / f"{C.SCOPE}.sockets.json").read_text(encoding="utf-8"))
    ep = next(x for x in ssc["sockets"] if x["socket"] == "EyePoint")["location_cm"]
    fx = unreal.Vector(1, 0, 0)
    eye = unreal.Vector(mount[0] + ep[0], mount[1] + ep[1], mount[2] + ep[2])
    res["scope_mount_cm"] = mount
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
unreal.log("SR_PASS_A2_DONE status=" + res["status"])
