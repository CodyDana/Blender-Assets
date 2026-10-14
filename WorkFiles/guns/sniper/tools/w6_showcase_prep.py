"""W6 showcase prep (headless Blender 5.2): builds the composite scenes studio.py renders, from the SHIPPED bytes only.

    blender.exe -b --factory-startup --python w6_showcase_prep.py -- <export_dir> <out_dir>

Writes into <out_dir> (scratch, never into Exports/):
    sr01_scoped.blend    SM_SR01 LOD0 (bipod folded) + SM_Att_Scope_LongRange LOD0 on Rail_Top + 2 slots
    sr01_deployed.blend  SK_SR01 LOD0 posed at the last frame of A_SR01_BipodDeploy (legs 90 deg, 12 deg splay, ext 38),
                         armature applied, + SM_SR01_Mag on the Mag socket + the scope
    scope.blend          the scope alone (materials renamed so studio.py finds its texture sets)
    prep.json            what was placed where
The scope's Mount goes to Rail_Top + 20.02 mm along X (sidecar gun.scope); the magazine to the Mag socket (zero offset).
Material names are copied to the texture-set key (M_<set key>) so studio.py's matcher wires the shipped maps.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
EXP, OUT = Path(a[0]), Path(a[1])
OUT.mkdir(parents=True, exist_ok=True)
side = json.loads((EXP / "SK_SR01.skeletal.json").read_text())
sm_sock = {s["socket"]: s for s in json.loads((EXP / "SM_SR01.sockets.json").read_text())["sockets"]}
rep = {"sources": [], "placed": {}}

MAT_KEYS = {"M_SR01_Metal": "M_SR01_Metal", "M_SR01_Chassis": "M_SR01_Chassis", "M_SR01_Mag": "M_SR01_Mag",
            "M_Att_Scope_Body": "M_Att_Scope_LongRange_Scope_Body", "M_Att_Scope_Lens": "M_Att_Scope_LongRange_Scope_Lens"}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def imp(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(EXP / name))
    rep["sources"].append(name)
    return [o for o in bpy.data.objects if o not in before]


def lod0_meshes(objs):
    keep = [o for o in objs if o.type == "MESH" and not o.name.startswith("UCX_") and
            "_LOD1" not in o.name and "_LOD2" not in o.name and "_LOD3" not in o.name]
    for o in objs:
        if o.type == "MESH" and o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    return keep


def rename_mats(objs):
    for o in objs:
        for m in o.data.materials:
            if m is None:
                continue
            base = m.name.split(".")[0]
            for k, v in MAT_KEYS.items():
                if base == k:
                    m.name = v


def ue_cm_to_blender_m(loc_cm):
    return Vector((loc_cm[0] / 100.0, -loc_cm[1] / 100.0, loc_cm[2] / 100.0))


def root_of(objs):
    """The top-level imported object (FBX empties / armature carry the unit scale)."""
    tops = [o for o in objs if o.parent is None]
    return tops


def place(objs, loc):
    for t in root_of(objs):
        t.location = t.location + loc


def socket_world(objs, name):
    for o in objs:
        if o.type == "EMPTY" and o.name.endswith("_" + name):
            return o.matrix_world.translation.copy()
    return None


def add_scope(gun_objs, tag):
    sc = imp("SM_Att_Scope_LongRange.fbx")
    bpy.context.view_layer.update()
    rail = socket_world(gun_objs, "Rail_Top")
    if rail is None:
        rail = ue_cm_to_blender_m(sm_sock["Rail_Top"]["location_cm"])
    mount = socket_world(sc, "Mount") or Vector((0, 0, 0))
    off = Vector((side["gun"]["scope"]["mount_offset_slots"] * side["gun"]["scope"]["slot_pitch_mm"] / 1000.0, 0, 0))
    place(sc, rail + off - mount)
    bpy.context.view_layer.update()
    rep["placed"][tag + ":scope_mount_m"] = [round(v, 5) for v in (socket_world(sc, "Mount") or rail + off)]
    rep["placed"][tag + ":rail_top_m"] = [round(v, 5) for v in rail]
    return lod0_meshes(sc)


def save(name):
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o.parent is not None]:
        mw = o.matrix_world.copy()          # keep the FBX root's unit scale + the placement before the root goes
        o.parent = None
        o.matrix_world = mw
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / name))


# 1. scoped static twin (folded bipod)
reset()
g = imp("SM_SR01.fbx")
s = add_scope(g, "scoped")
g = lod0_meshes(g)
rename_mats(g + s)
rep["placed"]["scoped:objects"] = [o.name for o in g + s]
save("sr01_scoped.blend")

# 2. deployed: SK_SR01 at the end of BipodDeploy
reset()
sk = imp("SK_SR01.fbx")
arm = next(o for o in sk if o.type == "ARMATURE")
clip = imp("A_SR01_BipodDeploy.fbx")
carm = next(o for o in clip if o.type == "ARMATURE")
act = carm.animation_data.action
f_end = side["animations"][[x["file"] for x in side["animations"]].index("A_SR01_BipodDeploy.fbx")]["frames"][1]
arm.animation_data_create()
arm.animation_data.action = act
try:
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
except AttributeError:
    pass
for o in clip:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.context.scene.frame_set(int(f_end))
bpy.context.view_layer.update()
pb = arm.pose.bones
rep["placed"]["deployed:frame"] = f_end
rep["placed"]["deployed:pose"] = {n: {"rot_quat": [round(v, 4) for v in pb[n].rotation_quaternion],
                                      "loc": [round(v, 3) for v in pb[n].location]}
                                  for n in ("bipod_leg_l", "bipod_leg_r", "bipod_leg_l_ext", "bipod_leg_r_ext") if n in pb}
foot = socket_world(sk, "BipodFoot_L")
dg = bpy.context.evaluated_depsgraph_get()
meshes = lod0_meshes(sk)
baked = []
for o in meshes:
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    nb = bpy.data.objects.new(o.name + "_posed", me)
    nb.matrix_world = o.matrix_world.copy()
    bpy.context.scene.collection.objects.link(nb)
    baked.append(nb)
zmin = min((nb.matrix_world @ v.co).z for nb in baked for v in nb.data.vertices)
rep["placed"]["deployed:lowest_point_m"] = round(zmin, 5)
mag = imp("SM_SR01_Mag.fbx")
bpy.context.view_layer.update()
mag_sock = socket_world(sk, "Mag")
if mag_sock is None:
    mag_sock = Vector(side["bones_rest"]["magazine"]["head_mm"]) / 1000.0
    mag_sock.y = -mag_sock.y
place(mag, mag_sock - (socket_world(mag, "Mag") or Vector()))
bpy.context.view_layer.update()
rep["placed"]["deployed:mag_socket_m"] = [round(v, 5) for v in mag_sock]
mag = lod0_meshes(mag)
s = add_scope(sk, "deployed")
for o in meshes:
    bpy.data.objects.remove(o, do_unlink=True)
rename_mats(baked + mag + s)
rep["placed"]["deployed:objects"] = [o.name for o in baked + mag + s]
save("sr01_deployed.blend")

# 3. the scope alone
reset()
s = lod0_meshes(imp("SM_Att_Scope_LongRange.fbx"))
rename_mats(s)
save("scope.blend")

(OUT / "prep.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
print("PREP_DONE", json.dumps(rep["placed"]))
