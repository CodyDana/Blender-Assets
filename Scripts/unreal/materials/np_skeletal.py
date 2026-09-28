"""Skeletal-mesh import for the pack (inside Unreal): the folding fan SK_Fan and its optional tassel SK_Fan_Tassel.

ADDED for the fan (2026-09-26, the fan's Integrate phase). Nothing here runs for a static item: np_meshes dispatches
to this module only for a spec item with ``"kind": "skeletal"``, so every existing item's import, assignment and
verification is byte-for-byte the code path it was.

Everything comes from the item's sidecar (Exports/Fan/SK_Fan.skeletal.json, SK_Fan_Tassel.skeletal.json), written by
Scripts/props/build_fan.py - nothing is typed twice. The steps, measured in the fan's own Unreal checks
(WorkFiles/fan/UnrealCheck, UE 5.8.3):
    mesh         legacy FBX, skeletal, normals imported, no morph targets, no auto physics asset, T0 not the ref pose
    LODs         SkeletalMeshEditorSubsystem.import_lod for LOD1 / LOD2 (same skeleton; NO bones removed: every fold
                 is kept at every LOD); the screen sizes through a SkeletalMeshLODSettings asset (LODInfo is not
                 exposed to Python)
    bounds       the mesh's Positive / Negative Bounds Extension from the sidecar (the folding leaf swings up to
                 16 mm behind the rivet plane; the bounds must not depend on the physics asset)
    sockets      from the sidecar's component transforms, made relative to each bone's reference pose
    physics      PHYS_Fan / PHYS_Fan_Tassel built from the shipped proxy FBX (Exports/Fan/Physics: Unreal's builder
                 makes exactly one body per proxy cube), every body rewritten from the sidecar (shapes, collision,
                 mass, type), renamed, assigned; the proxy mesh is deleted
    animations   each at its own rate; BONE COMPRESSION = the sidecar's import.bone_compression (the project default
                 ACL cracks the leaf's folds by up to 1.1 mm: MEASURED); the Loop flag from the sidecar
One save of the item's folder at the end. Re-running replaces the item's own assets (they are deleted first; the
buyer-facing instances are re-assigned by the later 'assign' step).
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import unreal

import np_spec

EAL = unreal.EditorAssetLibrary


def _tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def _sub():
    return unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:300]} if default is None else default


def _task(path: Path, folder: str, name: str, ui):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", ui)
    _tools().import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def mesh_ui(skeleton=None, physics=False):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", True)
    if skeleton is not None:
        ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("create_physics_asset", physics)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    d = ui.get_editor_property("skeletal_mesh_import_data")
    for k, v in (("import_morph_targets", False), ("convert_scene", True), ("force_front_x_axis", False),
                 ("convert_scene_unit", True), ("use_t0_as_ref_pose", False), ("update_skeleton_reference_pose", False),
                 ("import_mesh_lods", False),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)):
        d.set_editor_property(k, v)
    return ui


def anim_ui(skeleton, fps):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", False)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    d = ui.get_editor_property("anim_sequence_import_data")
    for k, v in (("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME),
                 ("use_default_sample_rate", False), ("custom_sample_rate", int(fps)), ("convert_scene", True),
                 ("force_front_x_axis", False), ("convert_scene_unit", True), ("import_meshes_in_bone_hierarchy", False),
                 ("remove_redundant_keys", False)):
        d.set_editor_property(k, v)
    return ui


def _tf(loc_cm, q_xyzw=(0.0, 0.0, 0.0, 1.0)):
    t = unreal.Transform()
    t.translation = unreal.Vector(*[float(v) for v in loc_cm])
    t.rotation = unreal.Quat(*[float(v) for v in q_xyzw])
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def component_space_ref(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    local, parent = {}, {}
    for i in range(comp.get_num_bones()):
        name = str(comp.get_bone_name(i))
        local[name] = comp.get_ref_pose_transform(i)
        p = str(comp.get_parent_bone(name))
        parent[name] = None if p in ("None", "") else p
    world = {}

    def resolve(n):
        if n not in world:
            t = local[n]
            world[n] = t if parent[n] is None else unreal.MathLibrary.compose_transforms(t, resolve(parent[n]))
        return world[n]
    for n in local:
        resolve(n)
    return world


def find_bodies(pa, limit=64):
    """{bone: SkeletalBodySetup}: the body list is not exposed to Python (UE 5.8.3); bodies are subobjects
    SkeletalBodySetup_<n>."""
    out, miss = {}, 0
    for i in range(limit):
        o = unreal.find_object(pa, f"SkeletalBodySetup_{i}")
        if o is None:
            miss += 1
            if miss > 8:
                break
            continue
        out[str(o.get_editor_property("bone_name"))] = o
    return out


def own_assets(m: dict, sidecar: dict) -> list:
    """The item's own assets, in delete order (dependants first)."""
    folder = m["folder"]
    names = [Path(a["file"]).stem for a in sidecar.get("animations", [])]
    names += [f"PHYS_{m['short']}", m["mesh"] + "_PhysicsProxy", m["mesh"], f"LODS_{m['mesh']}", sidecar["skeleton"]]
    return [f"{folder}/{n}" for n in names]


def _set_lod_sizes(mesh, folder, name, sizes):
    ls_path = f"{folder}/{name}"
    ls = _tools().create_asset(name, folder, unreal.SkeletalMeshLODSettings, None)
    groups = []
    for v in sizes:
        g = unreal.SkeletalMeshLODGroupSettings()
        pp = unreal.PerPlatformFloat()
        pp.set_editor_property("default", float(v))
        g.set_editor_property("screen_size", pp)
        groups.append(g)
    ls.set_editor_property("lod_groups", groups)
    mesh.set_editor_property("lod_settings", ls)
    return {"asset": ls_path, "sizes": sizes}


def _add_sockets(mesh, sidecar):
    ref = component_space_ref(mesh)
    out = []
    for s in sidecar.get("sockets", []):
        uc = s["unreal_component"]
        rel = unreal.MathLibrary.make_relative_transform(_tf(uc["location_cm"], uc["quaternion_xyzw"]), ref[s["bone"]])
        sock = unreal.new_object(unreal.SkeletalMeshSocket, outer=mesh)
        try:
            sock.set_socket_parent(mesh, s["bone"])
        except TypeError:
            sock.set_socket_parent(s["bone"], mesh)
        sock.set_editor_property("relative_location", rel.translation)
        sock.set_editor_property("relative_rotation", rel.rotation.rotator())
        sock.set_editor_property("relative_scale", unreal.Vector(1.0, 1.0, 1.0))
        mesh.add_socket(sock, False)
        _sub().rename_socket(mesh, sock.get_editor_property("socket_name"), s["name"])
        out.append({"name": s["name"], "bone": s["bone"]})
    return out


def _build_physics(mesh, skel, proxy_fbx: Path, bodies, folder, phys_name):
    """PHYS_<item> from the shipped proxy (one body per proxy cube), each body rewritten from the sidecar."""
    out = {"proxy": str(proxy_fbx), "proxy_sha256": np_spec.sha256(proxy_fbx)}
    pname = mesh.get_name() + "_PhysicsProxy"
    _task(proxy_fbx, folder, pname, mesh_ui(skeleton=skel, physics=True))
    pmesh = unreal.load_asset(f"{folder}/{pname}")
    pa = pmesh.get_editor_property("physics_asset")
    setups = find_bodies(pa)
    out["auto_bodies"] = sorted(setups)
    ref = component_space_ref(mesh)
    applied = {}
    for body in bodies:
        names = body.get("unreal_bone_any_of") or [body["bone"]]
        bone = next((n for n in names if n in setups), None)
        if bone is None:
            raise RuntimeError(f"no auto body on {names} (got {sorted(setups)})")
        bs = setups[bone]
        g = unreal.KAggregateGeom()
        boxes, sphyls, spheres = [], [], []
        for e in body["elements"]:
            uc = e["unreal_component"]
            rel = unreal.MathLibrary.make_relative_transform(_tf(uc["location_cm"], uc["quaternion_xyzw"]), ref[bone])
            if e["shape"] == "box":
                el = unreal.KBoxElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("rotation", rel.rotation.rotator())
                for k, v in zip(("x", "y", "z"), e["size_cm"]):
                    el.set_editor_property(k, float(v))
                boxes.append(el)
            elif e["shape"] == "capsule":
                el = unreal.KSphylElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("rotation", rel.rotation.rotator())
                el.set_editor_property("radius", float(e["radius_mm"]) * 0.1)
                el.set_editor_property("length", float(e["length_mm"]) * 0.1)
                sphyls.append(el)
            else:
                el = unreal.KSphereElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("radius", float(e["radius_mm"]) * 0.1)
                spheres.append(el)
            el.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS if e["collision"]
                                   else unreal.CollisionEnabled.NO_COLLISION)
            el.set_editor_property("contribute_to_mass", bool(e["contribute_to_mass"]))
        g.set_editor_property("box_elems", boxes)
        g.set_editor_property("sphyl_elems", sphyls)
        g.set_editor_property("sphere_elems", spheres)
        g.set_editor_property("convex_elems", [])
        bs.set_editor_property("agg_geom", g)
        bs.set_editor_property("physics_type", unreal.PhysicsType.PHYS_TYPE_KINEMATIC if body["physics_type"] == "Kinematic"
                               else unreal.PhysicsType.PHYS_TYPE_DEFAULT)
        bs.set_editor_property("consider_for_bounds", bool(body["consider_for_bounds"]))
        bi = bs.get_editor_property("default_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS
                               if any(e["collision"] for e in body["elements"]) else unreal.CollisionEnabled.NO_COLLISION)
        bi.set_editor_property("override_mass", True)
        bi.set_editor_property("mass_in_kg_override", float(body["mass_kg"]))
        bs.set_editor_property("default_instance", bi)
        applied[body["bone"]] = {"unreal_bone": bone, "boxes": len(boxes), "capsules": len(sphyls), "spheres": len(spheres)}
    out["applied"] = applied
    extra = sorted(set(setups) - {a["unreal_bone"] for a in applied.values()})
    if extra:
        raise RuntimeError(f"the proxy made extra bodies {extra}")
    _safe(lambda: pa.set_editor_property("preview_skeletal_mesh", mesh))
    pmesh.set_editor_property("physics_asset", None)
    EAL.delete_loaded_asset(pmesh)
    old = pa.get_path_name().split(".")[0]
    phys_path = f"{folder}/{phys_name}"
    out["renamed"] = bool(EAL.rename_asset(old, phys_path))
    pa = unreal.load_asset(phys_path)
    mesh.set_editor_property("physics_asset", pa)
    out["asset"] = phys_path
    return out


def import_one(m: dict) -> dict:
    """One skeletal item: mesh + LODs + LOD sizes + bounds + sockets + physics + animations; one save."""
    fbx = np_spec.PROJECT / m["fbx"]
    sc_path = np_spec.PROJECT / m["sidecar"]
    sidecar = json.loads(sc_path.read_text(encoding="utf-8"))
    exp = fbx.parent
    folder = m["folder"]
    rep = {"asset": m["asset"], "kind": "skeletal", "fbx": m["fbx"], "fbx_sha256": np_spec.sha256(fbx),
           "sidecar_sha256": np_spec.sha256(sc_path), "existed_before": bool(EAL.does_asset_exist(m["asset"]))}
    deleted = []
    for a in own_assets(m, sidecar):
        if EAL.does_asset_exist(a):
            deleted.append(a if EAL.delete_asset(a) else f"FAILED {a}")
    rep["deleted_before_import"] = deleted
    paths = _task(fbx, folder, m["mesh"], mesh_ui())
    rep["imported_object_paths"] = paths
    mesh = unreal.load_asset(m["asset"])
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"{m['asset']} did not import as a SkeletalMesh ({paths})")
    skel = mesh.get_editor_property("skeleton")
    rep["skeleton"] = skel.get_path_name().split(".")[0]
    rep["lods_imported"] = [{"lod": i, "file": f, "ok": bool(_sub().import_lod(mesh, i, str(exp / f)))}
                            for i, f in enumerate(sidecar["lod_files"][1:], 1)]
    rep["lod_count"] = int(_sub().get_lod_count(mesh))
    if sidecar.get("lod_screen_sizes"):
        rep["lod_settings"] = _set_lod_sizes(mesh, folder, f"LODS_{m['mesh']}", sidecar["lod_screen_sizes"])
    be = (sidecar.get("import") or {}).get("bounds_extension_cm")
    if be:
        mesh.set_editor_property("positive_bounds_extension", unreal.Vector(*[float(v) for v in be["positive_cm"]]))
        mesh.set_editor_property("negative_bounds_extension", unreal.Vector(*[float(v) for v in be["negative_cm"]]))
        rep["bounds_extension_cm"] = {"positive": be["positive_cm"], "negative": be["negative_cm"]}
    rep["sockets"] = _add_sockets(mesh, sidecar)
    proxy = sidecar.get("physics_proxy") or (sidecar.get("physics_proxies") or {}).get(m["mesh"])
    if proxy and sidecar.get("physics_bodies"):
        rep["physics"] = _build_physics(mesh, skel, exp / proxy, sidecar["physics_bodies"], folder, f"PHYS_{m['short']}")
    anims = {}
    comp_path = (sidecar.get("import") or {}).get("bone_compression")
    for a in sidecar.get("animations", []):
        name = Path(a["file"]).stem
        p = _task(exp / a["file"], folder, name, anim_ui(skel, a["fps"]))
        seq = unreal.load_asset(f"{folder}/{name}")
        if seq is None:
            raise RuntimeError(f"{a['file']} imported nothing ({p})")
        if comp_path:
            unreal.AnimationLibrary.set_bone_compression_settings(seq, unreal.load_asset(comp_path))
        if "loop" in a:
            seq.set_editor_property("loop", bool(a["loop"]))
        anims[name] = {"fps": a["fps"], "loop": bool(seq.get_editor_property("loop")),
                       "bone_compression": unreal.AnimationLibrary.get_bone_compression_settings(seq).get_path_name().split(".")[0],
                       "play_length_s": seq.get_play_length()}
    rep["animations"] = anims
    rep["saved"] = bool(EAL.save_directory(folder, only_if_is_dirty=False, recursive=True))
    rep["slots"] = slot_table(mesh)
    rep["lods"] = int(_sub().get_lod_count(mesh))
    return rep


def slot_table(mesh) -> list:
    out = []
    for i, sm in enumerate(mesh.get_editor_property("materials")):
        mi = sm.get_editor_property("material_interface")
        out.append({"index": i, "slot_name": str(sm.get_editor_property("material_slot_name")),
                    "material": mi.get_path_name().split(".")[0] if mi else None})
    return out


def lod_sections(mesh) -> list:
    sub = _sub()
    mats = mesh.get_editor_property("materials")
    out = []
    for lod in range(int(sub.get_lod_count(mesh))):
        secs = []
        for s in range(int(sub.get_num_sections(mesh, lod))):
            slot = int(sub.get_lod_material_slot(mesh, lod, s))
            mi = mats[slot].get_editor_property("material_interface") if 0 <= slot < len(mats) else None
            secs.append({"section": s, "slot": slot, "material": mi.get_path_name().split(".")[0] if mi else None})
        out.append({"lod": lod, "sections": secs})
    return out


def assign(mesh, m: dict) -> dict:
    """Each spec slot gets its instance BY SLOT NAME (a skeletal mesh's slot order follows the FBX); the index must
    match the spec's too."""
    before = slot_table(mesh)
    by_name = {s["slot_name"]: s for s in before}
    if len(before) != len(m["slots"]):
        raise RuntimeError(f"{m['mesh']}: {len(before)} slots in Unreal, {len(m['slots'])} in the spec")
    mats = list(mesh.get_editor_property("materials"))
    for s in m["slots"]:
        got = by_name.get(s["slot_name"])
        if got is None or got["index"] != s["index"]:
            raise RuntimeError(f"{m['mesh']}: slot {s['slot_name']!r} is {got}, spec says index {s['index']}")
        mi = unreal.load_asset(s["instance_path"])
        if mi is None:
            raise RuntimeError(f"{s['instance_path']} missing")
        mats[s["index"]].set_editor_property("material_interface", mi)
    mesh.set_editor_property("materials", mats)
    return {"before": before}


def sockets(mesh) -> list:
    """the mesh's own sockets (a skeletal component also lists every bone as a socket name: those are left out)"""
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    bones = {str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())}
    return sorted(str(n) for n in comp.get_all_socket_names() if str(n) not in bones)


def run_import_item(m: dict) -> dict:
    try:
        return import_one(m)
    except Exception:  # noqa: BLE001
        return {"asset": m["asset"], "kind": "skeletal", "error": traceback.format_exc()}
