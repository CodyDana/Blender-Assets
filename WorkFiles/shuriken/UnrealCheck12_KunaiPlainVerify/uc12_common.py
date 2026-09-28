"""UnrealCheck12 shared helpers (runs inside the UE 5.8 pythonscript commandlet).

Independent Unreal verifier for SM_Kunai_Plain (library 3.10), written fresh for this verification.  It does NOT
import the build's UnrealCheck6 checker (uc6_common / pass*.py); the only project code it runs inside Unreal is the
two post-import tools the task names: Scripts/pipeline/ue_import_sockets.py (the sidecar) and
Scripts/shuriken/ue_import_textures.py (the maps).  Expectations come from b1_truth.json (Blender's own reading of the
shipped FBX and of Assets/Shuriken.blend) and from the study (References/Kunai/KUNAI_STUDY.md), evaluated in
summarize.py; nothing here decides pass or fail.

Fresh content path: /Game/KunaiPlainVerify12/Run1 (mesh) and /Game/KunaiPlainVerify12/Run1/Textures (maps); override
with SHURIKEN_UC12_DEST.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck12_KunaiPlainVerify"
EXPORTS = PROJ / "Exports" / "Shuriken"
MESH = "SM_Kunai_Plain"
FBX = EXPORTS / f"{MESH}.fbx"
SIDECAR = EXPORTS / f"{MESH}.sockets.json"
TEX_DIR = EXPORTS / "Textures"
KUNAI_MAPS = ["T_Kunai_Plain_BC", "T_Kunai_Plain_ORM", "T_Kunai_Plain_N", "T_Kunai_Wrap_BC", "T_Kunai_Wrap_ORM",
              "T_Kunai_Wrap_N", "T_Kunai_Wrap_Natural_BC", "T_Kunai_Lettering"]
DEST = os.environ.get("SHURIKEN_UC12_DEST", "/Game/KunaiPlainVerify12/Run1")
TEX_DEST = DEST + "/Textures"
ASSET = f"{DEST}/{MESH}"
SOCKETS = ("Grip", "Trail", "Tip", "Ring")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def v3(v, nd=7):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:240]}


def plain(val):
    if isinstance(val, (bool, int, float, str)) or val is None or isinstance(val, dict):
        return val
    if hasattr(val, "x") and hasattr(val, "y") and hasattr(val, "z"):
        return [val.x, val.y, val.z]
    if hasattr(val, "roll") and hasattr(val, "pitch"):
        return {"roll": val.roll, "pitch": val.pitch, "yaw": val.yaw}
    return str(val)


def subsystem():
    sub = None
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    return sub if sub is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


def registry_import_tag(obj):
    """The asset registry's AssetImportData tag: JSON with the source file and the MD5 Unreal hashed at import."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    data = safe(lambda: reg.get_asset_by_object_path(obj.get_path_name()))
    if isinstance(data, dict):
        return data
    out = {}
    val = safe(lambda: data.get_tag_value("AssetImportData"))
    if isinstance(val, (list, tuple)) and len(val) == 2:
        ok, val = val
        out["found"] = bool(ok)
    out["AssetImportData"] = str(val)
    try:
        out["parsed"] = json.loads(str(val))
    except Exception:  # noqa: BLE001
        pass
    return out


IMPORT_KEYS = ("import_mesh_lods", "auto_generate_collision", "one_convex_hull_per_ucx", "combine_meshes",
               "generate_lightmap_u_vs", "normal_import_method", "normal_generation_method", "convert_scene",
               "convert_scene_unit", "force_front_x_axis", "import_uniform_scale", "import_rotation",
               "import_translation", "bake_pivot_in_vertex", "transform_vertex_to_absolute",
               "reorder_material_to_fbx_order", "remove_degenerates", "build_reversed_index_buffer",
               "compute_weighted_normals", "build_nanite")


def import_settings(mesh):
    aid = mesh.get_editor_property("asset_import_data")
    out = {"class": aid.get_class().get_name() if aid else None}
    for k in IMPORT_KEYS:
        out[k] = plain(safe(lambda k=k: aid.get_editor_property(k)))
    return out


def lod_build(sub, mesh, i):
    bs = sub.get_lod_build_settings(mesh, i)
    out = {}
    for k in ("generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "min_lightmap_resolution",
              "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates",
              "use_full_precision_u_vs", "use_high_precision_tangent_basis", "build_reversed_index_buffer",
              "build_scale3d", "compute_weighted_normals"):
        out[k] = plain(safe(lambda k=k: bs.get_editor_property(k)))
    return out


def inspect_mesh(mesh):
    sub = subsystem()
    info = {"asset": mesh.get_path_name(), "class": mesh.get_class().get_name()}
    n = int(mesh.get_num_lods())
    info["num_lods"] = n
    info["lod_count_subsystem"] = safe(lambda: int(sub.get_lod_count(mesh)))
    info["lod_triangles"] = [int(mesh.get_num_triangles(i)) for i in range(n)]
    info["lod_vertices"] = [int(mesh.get_num_vertices(i)) for i in range(n)]
    info["lod_sections"] = [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)]
    info["lod_section_material_slot"] = [
        [safe(lambda i=i, s=s: int(sub.get_lod_material_slot(mesh, i, s))) for s in range(int(mesh.get_num_sections(i)))]
        for i in range(n)]
    info["lod_screen_sizes"] = safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)])
    info["auto_compute_lod_screen_size"] = plain(safe(lambda: mesh.get_editor_property("auto_compute_lod_screen_size")))
    info["source_uv_channels_per_lod"] = [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]
    info["lod_build_settings"] = [safe(lambda i=i: lod_build(sub, mesh, i)) for i in range(n)]
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["allow_cpu_access_saved"] = plain(safe(lambda: mesh.get_editor_property("allow_cpu_access")))
    info["nanite_enabled"] = plain(safe(lambda: mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    info["min_lod"] = plain(safe(lambda: mesh.get_editor_property("min_lod")))
    info["positive_bounds_extension"] = plain(safe(lambda: mesh.get_editor_property("positive_bounds_extension")))
    info["negative_bounds_extension"] = plain(safe(lambda: mesh.get_editor_property("negative_bounds_extension")))
    body = mesh.get_editor_property("body_setup")
    info["has_body_setup"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        convex = agg.get_editor_property("convex_elems")
        info["convex_hulls"] = len(convex)
        hulls = []
        for c in convex:
            hv = safe(lambda c=c: [v3(p, 6) for p in c.get_editor_property("vertex_data")])
            hulls.append({"vertex_data_count": len(hv) if isinstance(hv, list) else hv,
                          "vertex_data_cm": hv if isinstance(hv, list) else None,
                          "elem_box": plain(safe(lambda c=c: str(c.get_editor_property("elem_box"))))})
        info["convex_hull_vertex_data"] = hulls
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)))
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems",
                                                   "level_set_elems", "skinned_level_set_elems")}
        info["collision_trace_flag"] = str(safe(lambda: body.get_editor_property("collision_trace_flag")))
        bi = safe(lambda: body.get_editor_property("default_instance"))
        if not isinstance(bi, dict):
            info["body_instance"] = {k: plain(safe(lambda k=k: bi.get_editor_property(k)))
                                     for k in ("override_mass", "mass_in_kg_override", "com_nudge", "simulate_physics")}
    bb = mesh.get_bounding_box()
    info["bounds_min_cm"] = v3(bb.min)
    info["bounds_max_cm"] = v3(bb.max)
    info["size_cm"] = [round(bb.max.x - bb.min.x, 7), round(bb.max.y - bb.min.y, 7), round(bb.max.z - bb.min.z, 7)]
    bs_ = mesh.get_bounds()
    info["bounds_origin_cm"] = v3(bs_.origin)
    info["bounds_box_extent_cm"] = v3(bs_.box_extent)
    info["bounds_sphere_radius_cm"] = round(float(bs_.sphere_radius), 7)
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "imported_slot": str(safe(lambda s=s: s.get_editor_property("imported_material_slot_name"))),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    info["all_socket_names_on_asset"] = safe(lambda: [str(s.get_editor_property("socket_name"))
                                                      for s in mesh.get_editor_property("sockets")])
    info["socket_objects"] = []
    for name in SOCKETS:
        s = mesh.find_socket(name)
        if s is None:
            info["socket_objects"].append({"name": name, "found": False})
            continue
        r = s.get_editor_property("relative_rotation")
        info["socket_objects"].append({
            "name": str(s.get_editor_property("socket_name")), "found": True,
            "outer": s.get_outer().get_path_name() if s.get_outer() else None,
            "relative_location_cm": v3(s.get_editor_property("relative_location")),
            "relative_rotation": {"roll": round(r.roll, 6), "pitch": round(r.pitch, 6), "yaw": round(r.yaw, 6)},
            "relative_scale": v3(s.get_editor_property("relative_scale")),
        })
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    info["component_socket_names"] = sorted(str(x) for x in comp.get_all_socket_names())
    info["component_sockets"] = {}
    for name in info["component_socket_names"]:
        t = comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
        rot = t.rotation.rotator()
        info["component_sockets"][name] = {
            "location_cm": v3(t.translation), "scale": v3(t.scale3d),
            "rotator": {"roll": round(rot.roll, 6), "pitch": round(rot.pitch, 6), "yaw": round(rot.yaw, 6)},
            "forward_x_axis": safe(lambda rot=rot: v3(unreal.MathLibrary.get_forward_vector(rot), 6)),
            "up_z_axis": safe(lambda rot=rot: v3(unreal.MathLibrary.get_up_vector(rot), 6))}
    aid = safe(lambda: mesh.get_editor_property("asset_import_data"))
    info["import_filenames"] = safe(lambda: [str(f) for f in aid.extract_filenames()]) if not isinstance(aid, dict) else aid
    info["import_settings"] = safe(lambda: import_settings(mesh))
    info["registry_import_tag"] = registry_import_tag(mesh)
    return info


TEX_KEYS = ("srgb", "compression_settings", "flip_green_channel", "lod_group", "compression_no_alpha",
            "mip_gen_settings", "address_x", "address_y", "power_of_two_mode", "virtual_texture_streaming",
            "never_stream", "filter")


def inspect_texture(tex):
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for k in TEX_KEYS:
        info[k] = str(safe(lambda k=k: tex.get_editor_property(k)))
    info["size"] = safe(lambda: [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())])
    aid = safe(lambda: tex.get_editor_property("asset_import_data"))
    info["import_filenames"] = safe(lambda: [str(f) for f in aid.extract_filenames()]) if not isinstance(aid, dict) else aid
    info["registry_import_tag"] = registry_import_tag(tex)
    info["registry_tags"] = registry_tags(tex)
    return info


TEX_TAG_CANDIDATES = ("Dimensions", "Format", "NumMips", "MipCount", "ResourceSize", "HasAlphaChannel",
                      "CompressionSettings", "SRGB", "LODGroup", "MipGenSettings", "PowerOfTwoMode", "SourceFormat",
                      "NeverStream", "VirtualTextureStreaming", "IsStreamable")


def registry_tags(obj, names=TEX_TAG_CANDIDATES):
    """Whatever of these asset-registry tags the engine writes for the object (informational)."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    data = safe(lambda: reg.get_asset_by_object_path(obj.get_path_name()))
    if isinstance(data, dict):
        return data
    out = {}
    for n in names:
        val = safe(lambda n=n: data.get_tag_value(n))
        if isinstance(val, (list, tuple)) and len(val) == 2:
            if val[0]:
                out[n] = str(val[1])
        elif val not in (None, "", "None") and not isinstance(val, dict):
            out[n] = str(val)
    return out


def dirty_packages():
    try:
        return sorted(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    except Exception as exc:  # noqa: BLE001
        return f"n/a: {exc}"[:120]


def write(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
