"""Build the locked fitting body for garment work (headless Blender, writes References/Characters/<Base>/).

    blender -b --factory-startup --python Scripts/garments/build_fitbody.py -- [--base MH_PlayerDefault] [--force]

Inputs (all under ``References/Characters/<Base>/source/``):

* ``SKM_<Base>_BodyMesh.fbx`` / ``SKM_<Base>_FaceMesh.fbx`` - LOD0 body and face as Unreal exported them
  (MH_PlayerDefault: DemoGame_1 ``Tools/Claude/Cloak/export_mh_body_fbx.py``, 2026-09-26, copied here from
  DemoGame_1/Saved on the first run; MH_PlayerFemale: ``ue_export_fitbody.py`` with ``FITBODY_BASE=MH_PlayerFemale``,
  2026-09-27), SHA-256 checked against ``BASES[base]["known_sources"]``,
* the groom's helmet FBX and its LOD0 card FBX (``BASES[base]["hair_helmet"]`` / ``["hair_cards"]``; one or more card
  groups, joined) and ``ue_reference.json`` - written by ``ue_export_fitbody.py`` in a CharacterLab commandlet,
* ``bones.json`` - the rig step's bone list (342 bones, metahuman_base_skel).

Output: ``<Base>_FitBody.blend`` with one locked collection ``FITBODY_<Base>``:

* ``root`` - the metahuman_base_skel armature. Unreal's ``root`` bone becomes the Blender armature OBJECT on import
  (its bones start at ``pelvis``), so the object must stay named exactly ``root`` or Unreal grows an extra root bone.
  Imported with ``automatic_bone_orientation=False`` (Outfit_Pipeline trap 1), the importer's 0.01 unit Empty baked
  into the bones: identity object transform, metres, Z up, facing -Y (the house convention),
* ``FIT_<Base>_Body`` - LOD0 body, its own weights (up to 8 influences), Armature modifier,
* ``FIT_<Base>_Head`` - the face mesh's SKIN section only (the collider), re-weighted onto the body skeleton
  (facial bones fold into ``head``); ``FIT_<Base>_HeadParts`` - eyes, teeth, lashes (reference only, never a
  collider: their inward normals spike a clearance pass, Outfit_Pipeline trap 15),
* ``FIT_<Base>_HairProxy`` - the groom's own helmet shell, rim filled into a closed volume, rigid on ``head``;
  ``FIT_<Base>_HairCards`` - the LOD0 cards (reference and triangle count only).

Everything is hide_select and lives in its collection; ``base_lock.json`` records the file SHA-256, the skeleton hash,
per-mesh geometry hashes, the triangle counts the whole-character budget uses, the body's influence histogram and the
cross-check against Unreal's own reference skeleton.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

from pipeline import garment_qa as gq  # noqa: E402

DEMOGAME_SAVED = Path("C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Saved/Claude/Blender")
# The exact bytes the BlackCloak one-off fit used (DemoGame_1 commit 43fd6ce); re-checked on copy.
KNOWN_SOURCES = {
    "SKM_MH_PlayerDefault_BodyMesh.fbx": ("SKM_MH_Body.fbx", "717db8e38c09b531252b401fbfa614a4ee86e812194e5d23bbf61d259c5f03c5"),
    "SKM_MH_PlayerDefault_FaceMesh.fbx": ("SKM_MH_Face.fbx", "65addb81a899b4bb390036dcf481fa6a9ffe6edfc14bea4cf034ebaea561d0c7"),
}
BONES_JSON = ROOT / "WorkFiles/MetaHuman/player_default/rig/bones.json"
UE_BODY_ASSET = "/Game/MetaHumans/MH_PlayerDefault/Body/SKM_MH_PlayerDefault_BodyMesh"
# Per base: where the body/face FBX come from (copy_from None = ue_export_fitbody.py wrote them into source/), the rig
# step's bone list, the body asset, the groom files. The female's body/face are the CharacterLab export of 2026-09-27
# (ue_export_fitbody.py, FITBODY_BASE=MH_PlayerFemale, needs the wrapper's -Render); a None hash is not checked.
BASES = {
    "MH_PlayerDefault": {"known_sources": KNOWN_SOURCES, "copy_from": DEMOGAME_SAVED, "bones_json": BONES_JSON,
                         "body_asset": UE_BODY_ASSET, "hair_helmet": "Hair_S_BrushCut_Helmet_LOD5.fbx",
                         "hair_cards": ("Hair_S_BrushCut_CardsMesh_Group0_LOD0.fbx",)},
    "MH_PlayerFemale": {
        "known_sources": {  # pinned from the first build (base_lock.json 2026-09-27)
            "SKM_MH_PlayerFemale_BodyMesh.fbx": (None, "503d78f030d371207a7abffe23a51a25a0ec585058e682bc86817e5943c43359"),
            "SKM_MH_PlayerFemale_FaceMesh.fbx": (None, "12224a50a920e73835e72afa92cdf99e6e04b3938d8f0e9307bca89dd9a58087")},
        "copy_from": None, "bones_json": ROOT / "WorkFiles/MetaHuman/player_female/rig/bones.json",
        "body_asset": "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh",
        "hair_helmet": "Hair_L_Straight_Helmet_LOD5.fbx",
        "hair_cards": ("Hair_L_Straight_CardsMesh_Group0_LOD0.fbx", "Hair_L_Straight_CardsMesh_Group1_LOD0.fbx")},
}
MAX_FACE_INFLUENCES = 8
HAIR_ENCLOSE_PERCENTILE = 99.5
SKIN_COLOR = (0.80, 0.62, 0.52, 1.0)
HAIR_COLOR = (0.12, 0.09, 0.07, 1.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fresh_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0
    units.length_unit = "METERS"


def import_fbx(path: Path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), global_scale=1.0, automatic_bone_orientation=False)
    return [obj for obj in bpy.data.objects if obj not in before]


def bake_mesh(obj, parent=None) -> None:
    """Move ``obj``'s world transform into its vertices and leave it at identity (optionally parented)."""
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.data.transform(world)
    obj.matrix_world = Matrix.Identity(4)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
    obj.data.update()


def bake_armature(arm) -> None:
    """Bake the importer's unit Empty (scale 0.01) into the bones: identity object transform, metres."""
    world = arm.matrix_world.copy()
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in arm.data.edit_bones:
        bone.transform(world, scale=True, roll=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)
    arm.parent = None
    arm.matrix_world = Matrix.Identity(4)


def bone_world_heads(arm):
    return {bone.name: np.array(arm.matrix_world @ bone.head_local) for bone in arm.data.bones}


def split_by_material(obj, keep_index: int):
    """Split ``obj`` into (faces with material ``keep_index``, the rest) and return both objects."""
    other = obj.copy()
    other.data = obj.data.copy()
    for collection in obj.users_collection:
        collection.objects.link(other)
    for target, keep in ((obj, True), (other, False)):
        bm = bmesh.new()
        bm.from_mesh(target.data)
        doomed = [face for face in bm.faces if (face.material_index == keep_index) != keep]
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        loose = [vert for vert in bm.verts if not vert.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(target.data)
        bm.free()
        target.data.update()
    return obj, other


def body_ancestor(face_arm, name: str, body_bones: set) -> str:
    """The bone itself when the body skeleton has it, else its nearest ancestor that the body has (else head)."""
    bone = face_arm.data.bones.get(name)
    while bone is not None and bone.name not in body_bones:
        bone = bone.parent
    return bone.name if bone is not None else "head"


def reweight_face(obj, face_arm, body_bones: set) -> dict:
    """Move the face mesh onto the body skeleton: body bones keep their weights, each facial-only bone folds into
    its nearest body ancestor (the FACIAL_*Neck* bones into neck_01/neck_02, the rest into head)."""
    names = {group.index: group.name for group in obj.vertex_groups}
    per_vertex = []
    folded = 0
    for vertex in obj.data.vertices:
        weights = {}
        for element in vertex.groups:
            name = names[element.group]
            target = body_ancestor(face_arm, name, body_bones)
            if target != name:
                folded += 1
            weights[target] = weights.get(target, 0.0) + element.weight
        per_vertex.append(weights)
    obj.vertex_groups.clear()
    groups = {}
    histogram = {}
    for index, weights in enumerate(per_vertex):
        top = sorted(weights.items(), key=lambda kv: -kv[1])[:MAX_FACE_INFLUENCES]
        total = sum(weight for _name, weight in top) or 1.0
        histogram[len(top)] = histogram.get(len(top), 0) + 1
        for name, weight in top:
            group = groups.get(name) or obj.vertex_groups.new(name=name)
            groups[name] = group
            group.add([index], weight / total, "REPLACE")
    return {"folded_facial_weights": folded, "bones": sorted(groups), "influence_histogram": histogram}


def fill_rim(obj) -> dict:
    """Close the helmet's open rim so it is a volume, and make the normals point out."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary_before = sum(1 for edge in bm.edges if edge.is_boundary)
    result = bmesh.ops.holes_fill(bm, edges=[edge for edge in bm.edges if edge.is_boundary], sides=0)
    new_faces = result.get("faces", [])
    if new_faces:
        bmesh.ops.triangulate(bm, faces=new_faces)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    boundary_after = sum(1 for edge in bm.edges if edge.is_boundary)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {"boundary_edges_before": boundary_before, "boundary_edges_after": boundary_after,
            "fill_faces": len(new_faces), "non_manifold_after": non_manifold}


def inflate_to_enclose(proxy, cards, percentile: float = HAIR_ENCLOSE_PERCENTILE) -> dict:
    """Push the helmet out along its vertex normals until it holds ``percentile`` % of the card vertices.

    The groom's helmet is Epic's low-LOD stand-in for the hair; at LOD0 about a tenth of the card vertices (the tips)
    stand up to 8.5 mm proud of it, and a hat must clear those, not the stand-in.
    """
    before = gq.fraction_inside(cards, proxy)
    collider = gq.Collider([proxy])
    coords, _ = gq.evaluated_world(cards)
    distance, found, _ = collider.signed(coords, max_distance=1.0)
    outside = np.where(found, np.maximum(distance, 0.0), 0.0)
    offset = float(np.percentile(outside, percentile))
    mesh = proxy.data
    for vertex in mesh.vertices:
        vertex.co += vertex.normal * offset
    mesh.update()
    after = gq.fraction_inside(cards, proxy)
    return {"percentile": percentile, "offset_cm": round(offset * 100.0, 3), "before": before, "after": after}


def rigid_on(obj, arm, bone: str) -> None:
    obj.vertex_groups.clear()
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm


def viewport_material(name: str, color) -> "bpy.types.Material":
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = color
    if material.node_tree is None:
        material.use_nodes = True
    principled = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
    return material


def ue_cross_check(arm, reference: dict) -> dict:
    """Compare the Blender armature with Unreal's own reference skeleton (component space, cm, Y mirrored)."""
    bones = {entry["name"]: entry for entry in reference["body_ref_skeleton"]}
    world = {}

    def component(name):
        if name in world:
            return world[name]
        entry = bones[name]
        x, y, z, w = entry["rotation_xyzw"]
        local = Matrix.Translation(Vector(entry["location_cm"])) @ Quaternion((w, x, y, z)).to_matrix().to_4x4()
        result = local if entry["parent"] is None else component(entry["parent"]) @ local
        world[name] = result
        return result

    heads = bone_world_heads(arm)
    worst = 0.0
    worst_bone = None
    for name, head in heads.items():
        ue = component(name).translation
        blender_from_ue = np.array([ue.x, -ue.y, ue.z]) / 100.0
        delta = float(np.linalg.norm(blender_from_ue - head))
        if delta > worst:
            worst, worst_bone = delta, name
    ue_names = set(bones)
    blender_names = set(heads) | {arm.name}
    parents_ok = all((bones[b.name]["parent"] or None) == (b.parent.name if b.parent else arm.name)
                     for b in arm.data.bones if b.name in bones)
    return {"ue_bones": len(ue_names), "blender_bones_plus_object": len(blender_names),
            "names_equal": ue_names == blender_names, "parents_equal": parents_ok,
            "max_head_delta_mm": round(worst * 1000.0, 5), "worst_bone": worst_bone}


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="build_fitbody.py")
    parser.add_argument("--base", default=gq.DEFAULT_BASE)
    parser.add_argument("--force", action="store_true", help="rebuild even if the .blend exists (never done silently)")
    args = parser.parse_args(argv)
    base = args.base
    if base not in BASES:
        raise RuntimeError(f"unknown base {base}; add it to BASES")
    config = BASES[base]
    body_asset = config["body_asset"]
    base_dir = gq.base_dir(base)
    source = base_dir / "source"
    blend_path = base_dir / f"{base}_FitBody.blend"
    lock_path = base_dir / "base_lock.json"
    log_dir = ROOT / "WorkFiles" / "garment_pipeline"
    log_dir.mkdir(parents=True, exist_ok=True)
    report = {"base": base, "status": "failed"}
    if blend_path.exists() and not args.force:
        print(f"FITBODY_EXISTS {blend_path} (pass --force to rebuild; the lock would change)")
        return 1
    source.mkdir(parents=True, exist_ok=True)
    for name, (demo_name, expected) in config["known_sources"].items():
        target = source / name
        if not target.exists():
            if config["copy_from"] is None:
                raise RuntimeError(f"{target} missing; run ue_export_fitbody.py with FITBODY_BASE={base} first")
            shutil.copy2(config["copy_from"] / demo_name, target)
        got = sha256(target)
        if expected is not None and got != expected:
            raise RuntimeError(f"{target} sha256 {got} != expected {expected}")
    if not (source / "bones.json").exists():
        shutil.copy2(config["bones_json"], source / "bones.json")
    ue_reference = json.loads((source / "ue_reference.json").read_text(encoding="utf-8"))
    if ue_reference.get("status") != "ok":
        raise RuntimeError("ue_reference.json is not ok; run ue_export_fitbody.py first")

    fresh_scene()
    # ---- body + skeleton
    new = import_fbx(source / f"SKM_{base}_BodyMesh.fbx")
    arm = next(o for o in new if o.type == "ARMATURE")
    body = next(o for o in new if o.type == "MESH")
    empties = [o for o in new if o.type == "EMPTY"]
    heads_before = bone_world_heads(arm)
    bake_armature(arm)
    bake_mesh(body, parent=arm)
    for empty in empties:
        bpy.data.objects.remove(empty, do_unlink=True)
    heads_after = bone_world_heads(arm)
    bake_error = max(float(np.linalg.norm(heads_before[n] - heads_after[n])) for n in heads_before)
    if bake_error > 1e-6:
        raise RuntimeError(f"baking the unit scale moved a bone by {bake_error} m")
    arm.name = gq.ROOT_BONE
    arm.data.name = "metahuman_base_skel"
    arm.data.display_type = "STICK"
    arm.show_in_front = True
    body.name = body.data.name = f"FIT_{base}_Body"
    body.modifiers[0].object = arm
    body.data.materials.clear()
    body.data.materials.append(viewport_material(f"FIT_{base}_Skin", SKIN_COLOR))
    report["bake_max_bone_shift_m"] = bake_error

    # ---- face: skin section as the head collider, the rest as reference parts
    new = import_fbx(source / f"SKM_{base}_FaceMesh.fbx")
    face_arm = next(o for o in new if o.type == "ARMATURE")
    face = next(o for o in new if o.type == "MESH")
    face_empties = [o for o in new if o.type == "EMPTY"]
    body_bones = {bone.name for bone in arm.data.bones}
    shared = []
    allowed = set()
    for bone in face_arm.data.bones:
        if bone.name not in body_bones:
            continue
        a = face_arm.matrix_world @ bone.matrix_local
        b = arm.matrix_world @ arm.data.bones[bone.name].matrix_local
        delta_mm = (a.translation - b.translation).length * 1000.0
        angle = math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)
        entry = {"bone": bone.name, "delta_mm": round(delta_mm, 4), "delta_deg": round(angle, 4)}
        shared.append(entry)
        if delta_mm < 0.1 and angle < 0.05:
            allowed.add(bone.name)
    report["face_shared_bones"] = shared
    report["face_bones_kept"] = sorted(allowed)
    counts = {}
    for poly in face.data.polygons:
        counts[poly.material_index] = counts.get(poly.material_index, 0) + 1
    skin_index = max(counts, key=counts.get)
    report["face_sections"] = {str(k): v for k, v in sorted(counts.items())}
    report["face_triangles_all_sections"] = sum(len(p.vertices) - 2 for p in face.data.polygons)
    bake_mesh(face)
    head, parts = split_by_material(face, skin_index)
    for obj in (head, parts):
        obj.parent = arm
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        obj.modifiers.clear()
        obj.modifiers.new("Armature", "ARMATURE").object = arm
    report["head_weights"] = reweight_face(head, face_arm, body_bones)
    report["head_parts_weights"] = reweight_face(parts, face_arm, body_bones)
    # The face archetype skeleton places pelvis..spine_03 16 cm away from the body's; that only matters if the head
    # skin is weighted to a bone whose rest differs, so report exactly those.
    report["head_bones_with_rest_delta"] = [s for s in shared if s["bone"] in report["head_weights"]["bones"]
                                            and s["bone"] not in allowed]
    head.name = head.data.name = f"FIT_{base}_Head"
    parts.name = parts.data.name = f"FIT_{base}_HeadParts"
    head.data.materials.clear()
    head.data.materials.append(bpy.data.materials[f"FIT_{base}_Skin"])
    bpy.data.objects.remove(face_arm, do_unlink=True)
    for empty in face_empties:
        bpy.data.objects.remove(empty, do_unlink=True)

    # ---- hair: the groom's helmet (closed) as the proxy, the LOD0 cards as reference
    hair = {}
    for label, filenames in (("HairProxy", (config["hair_helmet"],)), ("HairCards", tuple(config["hair_cards"]))):
        pieces = []
        for filename in filenames:
            new = import_fbx(source / filename)
            meshes = [o for o in new if o.type == "MESH"]
            if len(meshes) != 1:
                raise RuntimeError(f"{filename}: expected one mesh, got {[o.name for o in meshes]}")
            piece = meshes[0]
            bake_mesh(piece)
            for other in new:
                if other is not piece:
                    bpy.data.objects.remove(other, do_unlink=True)
            pieces.append(piece)
        obj = pieces[0]
        if len(pieces) > 1:  # several card groups: one reference object
            with bpy.context.temp_override(active_object=obj, selected_editable_objects=pieces):
                bpy.ops.object.join()
        obj.name = obj.data.name = f"FIT_{base}_{label}"
        obj.parent = arm
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        obj.data.materials.clear()
        obj.data.materials.append(viewport_material(f"FIT_{base}_Hair", HAIR_COLOR))
        hair[label] = obj
    report["hair_proxy_rim"] = fill_rim(hair["HairProxy"])
    report["hair_proxy_inflation"] = inflate_to_enclose(hair["HairProxy"], hair["HairCards"])
    for obj in hair.values():
        rigid_on(obj, arm, "head")

    # ---- the collection, locked
    collection = bpy.data.collections.new(gq.fitbody_collection(base))
    bpy.context.scene.collection.children.link(collection)
    members = [arm, body, head, parts, hair["HairProxy"], hair["HairCards"]]
    for obj in members:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.hide_select = True
        obj["fitbody_base"] = base
    parts.hide_set(True)
    hair["HairCards"].hide_set(True)
    hair["HairProxy"].display_type = "WIRE"
    collection.hide_select = True
    for extra in [o for o in bpy.data.objects if o not in members]:
        bpy.data.objects.remove(extra, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
        for data in list(block):
            if data.users == 0:
                block.remove(data)

    # The importer leaves float noise in the pose (<= 0.03 mm, 0 deg). Clear it: the garment is exported in this
    # pose, and Unreal may rebind to the time-zero pose when Blender's bind poses are partial, so pose == rest.
    for pose_bone in arm.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)

    # ---- measurements for the lock
    bpy.context.view_layer.update()
    tri = {obj.name: gq.triangle_count(obj) for obj in (body, head, parts, hair["HairProxy"], hair["HairCards"])}
    face_tris = tri[head.name] + tri[parts.name]
    ue_cards_tris = sum(entry["triangles_lod0"] for entry in ue_reference["static"] if entry["asset"].endswith("LOD0"))
    base_tris = tri[body.name] + face_tris + tri[hair["HairCards"].name]
    influence_histogram = {}
    for vertex in body.data.vertices:
        count = sum(1 for element in vertex.groups if element.weight > 0.0)
        influence_histogram[count] = influence_histogram.get(count, 0) + 1
    cards_inside = gq.fraction_inside(hair["HairCards"], hair["HairProxy"])
    ue_check = ue_cross_check(arm, ue_reference)
    bones_json = json.loads((source / "bones.json").read_text(encoding="utf-8"))
    rig_bones = [b if isinstance(b, str) else b.get("name") for b in bones_json[body_asset]["bones"]]
    blender_bones = [arm.name] + [bone.name for bone in arm.data.bones]
    if set(rig_bones) != set(blender_bones):
        raise RuntimeError("the armature does not carry the rig's bone list")
    if not (ue_check["names_equal"] and ue_check["parents_equal"] and ue_check["max_head_delta_mm"] < 0.05):
        raise RuntimeError(f"the Blender skeleton does not match Unreal's reference skeleton: {ue_check}")

    report["measurements"] = {"triangles": tri, "ue_cards_triangles_lod0": ue_cards_tris,
                              "body_influence_histogram": {str(k): v for k, v in sorted(influence_histogram.items())},
                              "hair_cards_inside_proxy": cards_inside, "ue_cross_check": ue_check}
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=False)

    lock = {
        "base": base,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "locked",
        "blend": str(blend_path.relative_to(ROOT)).replace("\\", "/"),
        "blend_sha256": sha256(blend_path),
        "collection": collection.name,
        "armature_object": arm.name,
        "unreal": {"skeleton": ue_reference["skeleton_asset"], "physics_asset": ue_reference["physics_asset"],
                   "body_mesh": body_asset, "face_mesh": ue_reference["face"]["asset"],
                   "bone_count_including_root": len(blender_bones), "ik_bones": [n for n in blender_bones if n.startswith("ik_")],
                   "ref_skeleton_cross_check": ue_check},
        "sources": {path.name: sha256(path) for path in sorted(source.iterdir()) if path.is_file()},
        "skeleton": gq.skeleton_record(arm),
        "meshes": {obj.name: gq.mesh_record(obj) for obj in (body, head, hair["HairProxy"])},
        "objects": {"body": body.name, "head": head.name, "head_parts": parts.name, "hair_proxy": hair["HairProxy"].name,
                    "hair_cards": hair["HairCards"].name},
        "triangles": {"body_lod0": tri[body.name], "face_lod0_all_sections": face_tris,
                      "hair_cards_lod0": tri[hair["HairCards"].name], "base_lod0_total": base_tris,
                      "not_counted": "eyebrow cards, eyelash groom (small; not exported)"},
        "body_max_influences": max(influence_histogram),
        "hair_proxy": {"source": f"/Game/MetaHumans/{base}/Grooms/{Path(config['hair_helmet']).stem}, rim filled, "
                                 "pushed out along its normals to hold the LOD0 cards",
                       "cards": [Path(name).stem for name in config["hair_cards"]],
                       "inflation": report["hair_proxy_inflation"], "cards_inside_fraction": cards_inside},
        "pose_set_version": gq.POSE_SET_VERSION,
    }
    lock["skeleton_hash"] = lock["skeleton"]["hash"]
    lock_path.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    report["status"] = "ok"
    report["lock"] = str(lock_path)
    (log_dir / f"fitbody_build_{base}.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"FITBODY_OK {blend_path} base_tris={base_tris} skeleton_hash={lock['skeleton_hash'][:16]} "
          f"ue_max_delta_mm={ue_check['max_head_delta_mm']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("FITBODY_FAILED")
        sys.exit(1)
