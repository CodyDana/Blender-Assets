"""Heels Unreal check: data verification in a FRESH commandlet (reads the saved /Game/HeelsCheck assets; saves nothing).

Checks: mesh skeleton / LOD count / vertex counts / bounds vs the Blender export (skin_data.json) / ref skeleton vs her body /
material slots + materials; every texture's sRGB, compression, LOD group, mip-gen, size (power of two), mip count;
CR_HeelPose and the three test ABPs load and are up to date. Writes WorkFiles/SnowFlowerHeels/ue/verify_data_<RUN>.json.
"""
import json
import math
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/" + RUN
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
SMS = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
rep = {"status": "failed", "errors": []}


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return "ERR " + str(exc)[:200]


def cs_pose(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    local, parent = {}, {}
    for i in range(comp.get_num_bones()):
        n = str(comp.get_bone_name(i))
        local[n] = comp.get_ref_pose_transform(i)
        p = str(comp.get_parent_bone(n))
        parent[n] = None if p in ("None", "") else p
    cache = {}

    def cs(n):
        if n not in cache:
            cache[n] = local[n] if parent[n] is None else local[n].multiply(cs(parent[n]))
        return cache[n]
    return {n: cs(n) for n in local}, parent


try:
    mesh = unreal.load_asset(DEST + "/SK_SnowFlowerHeels")
    blender = json.load(open(UE + "/skin_data.json", encoding="utf-8"))["meshes"]
    m = {"skeleton": mesh.get_editor_property("skeleton").get_path_name(), "lods": SMS.get_lod_count(mesh),
         "verts": [SMS.get_num_verts(mesh, i) for i in range(SMS.get_lod_count(mesh))],
         "materials": [(str(x.get_editor_property("material_slot_name")), safe(lambda x=x: x.get_editor_property("material_interface").get_path_name()))
                       for x in mesh.get_editor_property("materials")],
         "lod_settings": safe(lambda: mesh.get_editor_property("lod_settings").get_path_name()),
         "physics_asset": safe(lambda: str(mesh.get_editor_property("physics_asset"))),
         "post_process_abp": safe(lambda: str(mesh.get_editor_property("post_process_anim_blueprint")))}
    b = mesh.get_bounds()
    m["bounds_ue_cm"] = [[b.origin.x - b.box_extent.x, b.origin.y - b.box_extent.y, b.origin.z - b.box_extent.z],
                         [b.origin.x + b.box_extent.x, b.origin.y + b.box_extent.y, b.origin.z + b.box_extent.z]]
    ib = safe(lambda: mesh.get_imported_bounds())
    if not isinstance(ib, str):
        m["imported_bounds_ue_cm"] = [[ib.origin.x - ib.box_extent.x, ib.origin.y - ib.box_extent.y, ib.origin.z - ib.box_extent.z],
                                      [ib.origin.x + ib.box_extent.x, ib.origin.y + ib.box_extent.y, ib.origin.z + ib.box_extent.z]]
    m["blender_bbox_ue_cm"] = blender["SK_SnowFlowerHeels"]["bbox_ue_cm"]
    heels_cs, hp = cs_pose(mesh)
    body_cs, bp = cs_pose(unreal.load_asset(BODY))
    worst = 0.0
    for n in body_cs:
        if n in heels_cs:
            worst = max(worst, (heels_cs[n].translation - body_cs[n].translation).length())
    m["ref_skeleton_vs_body_max_cm"] = worst
    m["bones"] = len(heels_cs)
    rep["mesh"] = m
    tex = {}
    for slot in ("Leather", "Metal", "Insole"):
        for kind in ("BC", "ORM", "N"):
            name = "T_SnowFlowerHeels_%s_%s" % (slot, kind)
            t = unreal.load_asset(DEST + "/Textures/" + name)
            sx, sy = t.blueprint_get_size_x(), t.blueprint_get_size_y()
            tex[name] = {"srgb": t.get_editor_property("srgb"), "compression": str(t.get_editor_property("compression_settings")),
                         "lod_group": str(t.get_editor_property("lod_group")), "mip_gen": str(t.get_editor_property("mip_gen_settings")),
                         "size": [sx, sy], "pow2": (sx & (sx - 1)) == 0 and (sy & (sy - 1)) == 0,
                         "full_mips_expected": int(math.log2(max(sx, sy))) + 1,
                         "never_stream": t.get_editor_property("never_stream"),
                         "flip_green": t.get_editor_property("flip_green_channel"),
                         "num_mips": safe(lambda t=t: t.get_editor_property("num_mips") if False else unreal.ToolsetLibrary.get_object_properties(t, ["NumMips"]) if hasattr(unreal, "ToolsetLibrary") else "n/a")}
    rep["textures"] = tex
    cr = unreal.load_asset("/Game/HeelsCheck/CR_HeelPose")
    rep["cr"] = {"loaded": cr is not None, "status": safe(lambda: str(cr.get_editor_property("status"))),
                 "variables": safe(lambda: [str(v.get_editor_property("name")) for v in cr.get_member_variables()]),
                 "nodes": safe(lambda: len(cr.get_controller_by_name("RigVMModel").get_graph().get_nodes()))}
    rep["abps"] = {}
    for c in ("Idle", "Walk", "Run"):
        a = unreal.load_asset("%s/ABP_HeelsTest_%s" % (DEST, c))
        rep["abps"][c] = {"status": safe(lambda a=a: str(a.get_editor_property("status"))),
                          "skeleton": safe(lambda a=a: a.get_editor_property("target_skeleton").get_path_name())}
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/verify_data_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
