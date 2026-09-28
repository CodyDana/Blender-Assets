"""Unreal side of the locked fitting body (runs in a CharacterLab commandlet, saves nothing).

Run through ``Scripts/garments/run_ue_characterlab.ps1 -Script Scripts/garments/ue_export_fitbody.py``.
It reads ``/Game/MetaHumans/MH_PlayerDefault`` (byte-identical to DemoGame_1's copy; the runner hashes both) and writes
into ``References/Characters/MH_PlayerDefault/source/``:

* ``Hair_S_BrushCut_Helmet_LOD5.fbx`` - the groom's own "helmet" shell (the hair-volume proxy source),
* ``Hair_S_BrushCut_CardsMesh_Group0_LOD0.fbx`` - the LOD0 hair cards (their extent and triangle count),
* ``ue_reference.json`` - the body mesh's reference skeleton as Unreal stores it (bone names, parents, local
  reference transforms in cm), the skeleton asset path, and triangle / vertex counts of the meshes that make up
  the dressed character, so the Blender side can be cross-checked against the engine.

The body and face FBX are NOT re-exported here: the copies in ``source/`` are the ones
``DemoGame_1/Tools/Claude/Cloak/export_mh_body_fbx.py`` wrote on 2026-09-26 from these same bytes, which is what the
BlackCloak one-off fit used (keeping them keeps the regression exact).

Other bases (2026-09-27): set the environment variable ``FITBODY_BASE`` (e.g. ``MH_PlayerFemale``) before running the
wrapper. A base listed in ``BASES`` with ``export_meshes`` also gets its LOD0 body and face FBX written here
(``SKM_<Base>_BodyMesh.fbx`` / ``SKM_<Base>_FaceMesh.fbx``, the options DemoGame_1's ``export_mh_body_fbx.py`` used:
binary, no collision, no LODs, no morph targets), since no other exporter exists for it. Unset = MH_PlayerDefault,
byte-for-byte the old behaviour.
"""
import json
import os
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
BASES = {
    "MH_PlayerDefault": {"grooms": ("Hair_S_BrushCut_Helmet_LOD5", "Hair_S_BrushCut_CardsMesh_Group0_LOD0"),
                         "export_meshes": False},
    # the female player (CharacterLab, assembled UE Optimized HIGH 2026-09-26): long straight hair has two card groups
    "MH_PlayerFemale": {"grooms": ("Hair_L_Straight_Helmet_LOD5", "Hair_L_Straight_CardsMesh_Group0_LOD0",
                                   "Hair_L_Straight_CardsMesh_Group1_LOD0"),
                        "export_meshes": True},
}
BASE = os.environ.get("FITBODY_BASE", "MH_PlayerDefault")
if BASE not in BASES:
    raise RuntimeError("unknown FITBODY_BASE " + BASE)
OUT = ROOT + "/References/Characters/" + BASE + "/source"
MH = "/Game/MetaHumans/" + BASE
BODY = MH + "/Body/SKM_" + BASE + "_BodyMesh"
FACE = MH + "/Face/SKM_" + BASE + "_FaceMesh"
STATIC = tuple(MH + "/Grooms/" + name for name in BASES[BASE]["grooms"])
report = {"status": "failed", "errors": []}


def note(message):
    unreal.log("[fitbody] " + message)


def export_static(path):
    mesh = unreal.load_asset(path)
    if mesh is None:
        raise RuntimeError("missing " + path)
    name = path.rsplit("/", 1)[1]
    out = os.path.join(OUT, name + ".fbx")
    task = unreal.AssetExportTask()
    task.set_editor_property("object", mesh)
    task.set_editor_property("filename", out)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    options = unreal.FbxExportOption()
    options.set_editor_property("ascii", False)
    options.set_editor_property("collision", False)
    options.set_editor_property("level_of_detail", False)
    task.set_editor_property("options", options)
    ok = unreal.Exporter.run_asset_export_task(task)
    bounds = mesh.get_bounds()
    entry = {"asset": path, "fbx": out, "exported": bool(ok) and os.path.exists(out),
             "bounds_cm": {"origin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                           "extent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z]}}
    try:
        entry["triangles_lod0"] = mesh.get_num_triangles(0)
    except Exception as exc:  # noqa: BLE001
        entry["triangles_lod0"] = "unavailable: %s" % exc
    return entry


def export_skeletal(mesh, name):
    """LOD0 skeletal mesh FBX with the options DemoGame_1's export_mh_body_fbx.py used for the male base."""
    out = os.path.join(OUT, name)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", mesh)
    task.set_editor_property("filename", out)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    options = unreal.FbxExportOption()
    options.set_editor_property("ascii", False)
    options.set_editor_property("collision", False)
    options.set_editor_property("level_of_detail", False)
    options.set_editor_property("export_morph_targets", False)
    task.set_editor_property("options", options)
    ok = unreal.Exporter.run_asset_export_task(task)
    return {"asset": mesh.get_path_name(), "fbx": out, "exported": bool(ok) and os.path.exists(out),
            "bytes": os.path.getsize(out) if os.path.exists(out) else 0}


def ref_skeleton(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh) if hasattr(comp, "set_skinned_asset_and_update") else comp.set_skeletal_mesh_asset(mesh)
    bones = []
    for index in range(comp.get_num_bones()):
        name = str(comp.get_bone_name(index))
        parent = str(comp.get_parent_bone(name))
        t = comp.get_ref_pose_transform(index)
        q = t.rotation
        bones.append({"name": name, "parent": None if parent in ("None", "") else parent,
                      "location_cm": [t.translation.x, t.translation.y, t.translation.z],
                      "rotation_xyzw": [q.x, q.y, q.z, q.w],
                      "scale": [t.scale3d.x, t.scale3d.y, t.scale3d.z]})
    return bones


def mesh_counts(mesh):
    counts = {}
    try:
        subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        counts["verts_lod0"] = subsystem.get_num_verts(mesh, 0)
        counts["lods"] = subsystem.get_lod_count(mesh)
    except Exception as exc:  # noqa: BLE001
        counts["error"] = str(exc)
    return counts


try:
    os.makedirs(OUT, exist_ok=True)
    body = unreal.load_asset(BODY)
    face = unreal.load_asset(FACE)
    skeleton = body.get_editor_property("skeleton")
    physics = body.get_editor_property("physics_asset")
    report["skeleton_asset"] = skeleton.get_path_name()
    report["physics_asset"] = physics.get_path_name() if physics else None
    report["body"] = {"asset": BODY, **mesh_counts(body)}
    report["face"] = {"asset": FACE, "skeleton": face.get_editor_property("skeleton").get_path_name(), **mesh_counts(face)}
    report["body_ref_skeleton"] = ref_skeleton(body)
    face_bones = ref_skeleton(face)
    body_names = {b["name"] for b in report["body_ref_skeleton"]}
    report["face"]["bone_count"] = len(face_bones)
    report["face"]["shared_bones"] = [b for b in face_bones if b["name"] in body_names]
    report["static"] = [export_static(path) for path in STATIC]
    report["base"] = BASE
    if BASES[BASE]["export_meshes"]:
        report["skeletal_exports"] = [export_skeletal(body, "SKM_%s_BodyMesh.fbx" % BASE),
                                      export_skeletal(face, "SKM_%s_FaceMesh.fbx" % BASE)]
        if not all(entry["exported"] for entry in report["skeletal_exports"]):
            raise RuntimeError("skeletal export failed: %s" % report["skeletal_exports"])
    report["status"] = "ok"
except Exception:  # noqa: BLE001
    report["errors"].append(traceback.format_exc())
finally:
    with open(os.path.join(OUT, "ue_reference.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    note("status " + report["status"])
