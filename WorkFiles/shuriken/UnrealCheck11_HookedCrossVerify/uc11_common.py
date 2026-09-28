"""UnrealCheck11 shared helpers (runs inside the UE 5.8 pythonscript commandlet).

Independent Unreal verifier for SM_Shuriken_HookedCross, including HANDEDNESS.  Written fresh for this verification
(adapted from the UnrealCheck10 verifier's helpers, not from the build's UnrealCheck6).  The six-point is imported
alongside ONLY as the coordinate-mapping control.  Expectations come from b1_truth.json, never from the build report.
Fresh content path: /Game/HookedCrossVerify11/Run1 (meshes) and /Game/HookedCrossVerify11/Run1/Textures (maps);
override with SHURIKEN_UC11_DEST.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck11_HookedCrossVerify"
EXPORTS = PROJ / "Exports" / "Shuriken"
MESH = "SM_Shuriken_HookedCross"
CTRL = "SM_Shuriken_SixPoint"
FBX = {m: EXPORTS / f"{m}.fbx" for m in (MESH, CTRL)}
SIDECAR = {m: EXPORTS / f"{m}.sockets.json" for m in (MESH, CTRL)}
TEXTURES = {k: EXPORTS / "Textures" / f"T_Shuriken_HookedCross_{k}.png" for k in ("BC", "ORM", "N")}
DEST = os.environ.get("SHURIKEN_UC11_DEST", "/Game/HookedCrossVerify11/Run1")
TEX_DEST = DEST + "/Textures"
ASSET = {m: f"{DEST}/{m}" for m in (MESH, CTRL)}


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
    path = obj.get_path_name()
    data = safe(lambda: reg.get_asset_by_object_path(path))
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
               "import_translation", "bake_pivot_in_vertex", "transform_vertex_to_absolute", "reorder_material_to_fbx_order",
               "remove_degenerates", "build_reversed_index_buffer")


def import_settings(mesh):
    """The saved asset's own record of how it was imported (AssetImportData = FbxStaticMeshImportData)."""
    aid = mesh.get_editor_property("asset_import_data")
    out = {"class": aid.get_class().get_name() if aid else None}
    for k in IMPORT_KEYS:
        val = safe(lambda k=k: aid.get_editor_property(k))
        if isinstance(val, (bool, int, float, str)) or isinstance(val, dict):
            out[k] = val
        elif hasattr(val, "x") and hasattr(val, "y") and hasattr(val, "z"):
            out[k] = [val.x, val.y, val.z]
        elif hasattr(val, "roll"):
            out[k] = {"roll": val.roll, "pitch": val.pitch, "yaw": val.yaw}
        else:
            out[k] = str(val)
    return out


def inspect_mesh(mesh, socket_names=("Grip", "Trail")):
    sub = subsystem()
    info = {"asset": mesh.get_path_name(), "class": mesh.get_class().get_name()}
    n = mesh.get_num_lods()
    info["num_lods"] = n
    info["lod_triangles"] = [int(mesh.get_num_triangles(i)) for i in range(n)]
    info["lod_vertices"] = [int(mesh.get_num_vertices(i)) for i in range(n)]
    info["lod_sections"] = [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)]
    info["lod_screen_sizes"] = safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)])
    info["lod_count_subsystem"] = safe(lambda: int(sub.get_lod_count(mesh)))
    info["source_uv_channels_per_lod"] = [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]
    builds = []
    for i in range(n):
        def rd(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            out = {}
            for k in ("generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "min_lightmap_resolution",
                      "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates",
                      "use_full_precision_u_vs", "use_high_precision_tangent_basis", "build_reversed_index_buffer",
                      "build_scale3d"):
                v = safe(lambda k=k: bs.get_editor_property(k))
                if hasattr(v, "x") and hasattr(v, "z"):
                    v = [v.x, v.y, v.z]
                out[k] = v if isinstance(v, (bool, int, float, list, dict)) else str(v)
            return out
        builds.append(safe(rd))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["allow_cpu_access_saved"] = safe(lambda: bool(mesh.get_editor_property("allow_cpu_access")))
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
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
                          "vertex_data_cm": hv if isinstance(hv, list) else None})
        info["convex_hull_vertex_data"] = hulls
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)))
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
        info["collision_trace_flag"] = str(safe(lambda: body.get_editor_property("collision_trace_flag")))
    bb = mesh.get_bounding_box()
    info["bounds_min_cm"] = v3(bb.min)
    info["bounds_max_cm"] = v3(bb.max)
    info["size_cm"] = [round(bb.max.x - bb.min.x, 7), round(bb.max.y - bb.min.y, 7), round(bb.max.z - bb.min.z, 7)]
    bs_ = mesh.get_bounds()
    info["bounds_origin_cm"] = v3(bs_.origin)
    info["bounds_box_extent_cm"] = v3(bs_.box_extent)
    info["bounds_sphere_radius_cm"] = round(float(bs_.sphere_radius), 7)
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    info["all_socket_names_on_asset"] = safe(lambda: [str(s.get_editor_property("socket_name"))
                                                      for s in mesh.get_editor_property("sockets")])
    info["socket_objects"] = []
    for name in socket_names:
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


def inspect_texture(tex):
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "compression_no_alpha",
              "mip_gen_settings", "virtual_texture_streaming"):
        info[k] = str(safe(lambda k=k: tex.get_editor_property(k)))
    info["size"] = safe(lambda: [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())])
    aid = safe(lambda: tex.get_editor_property("asset_import_data"))
    info["import_filenames"] = safe(lambda: [str(f) for f in aid.extract_filenames()]) if not isinstance(aid, dict) else aid
    info["registry_import_tag"] = registry_import_tag(tex)
    return info


def write(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
