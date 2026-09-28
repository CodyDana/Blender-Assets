"""UnrealCheck10 shared helpers (runs inside the UE 5.8 pythonscript commandlet).

Independent Unreal verifier for SM_Shuriken_Spike only. Written fresh for this verification; expectations come
from b1_truth.json (spec numbers, the .blend and a re-import of the shipped FBX), never from the build report.
Fresh content path: /Game/SpikeVerify10/Run1 (mesh) and /Game/SpikeVerify10/Run1/Textures (maps); override with
SHURIKEN_UC10_DEST.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck10_SpikeVerify"
EXPORTS = PROJ / "Exports" / "Shuriken"
MESH = "SM_Shuriken_Spike"
FBX = EXPORTS / f"{MESH}.fbx"
SIDECAR = EXPORTS / f"{MESH}.sockets.json"
TEXTURES = {k: EXPORTS / "Textures" / f"T_Shuriken_Spike_{k}.png" for k in ("BC", "ORM", "N")}
DEST = os.environ.get("SHURIKEN_UC10_DEST", "/Game/SpikeVerify10/Run1")
TEX_DEST = DEST + "/Textures"
ASSET = f"{DEST}/{MESH}"


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
    for tag in ("AssetImportData",):
        val = safe(lambda tag=tag: data.get_tag_value(tag))
        if isinstance(val, (list, tuple)) and len(val) == 2:
            ok, val = val
            out["found"] = bool(ok)
        out[tag] = str(val)
        try:
            out["parsed"] = json.loads(str(val))
        except Exception:  # noqa: BLE001
            pass
    return out


def inspect_mesh(mesh):
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
                      "use_full_precision_u_vs", "build_scale3d"):
                v = bs.get_editor_property(k)
                out[k] = v if isinstance(v, (bool, int, float)) else str(v)
            return out
        builds.append(safe(rd))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    info["has_body_setup"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)))
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
        info["collision_trace_flag"] = str(safe(lambda: body.get_editor_property("collision_trace_flag")))
        info["body_mass_override"] = {
            "override_mass": safe(lambda: bool(body.get_editor_property("default_instance").get_editor_property("override_mass"))),
        }
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
    info["socket_objects"] = []
    all_sockets = safe(lambda: [str(s.get_editor_property("socket_name")) for s in mesh.get_editor_property("sockets")])
    info["all_socket_names_on_asset"] = all_sockets
    for name in ("Grip", "Trail"):
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
        fwd = safe(lambda rot=rot: v3(unreal.MathLibrary.get_forward_vector(rot), 6))
        info["component_sockets"][name] = {"location_cm": v3(t.translation), "scale": v3(t.scale3d),
                                           "rotator": {"roll": round(rot.roll, 6), "pitch": round(rot.pitch, 6),
                                                       "yaw": round(rot.yaw, 6)},
                                           "forward_x_axis": fwd}
    aid = safe(lambda: mesh.get_editor_property("asset_import_data"))
    info["import_filenames"] = safe(lambda: [str(f) for f in aid.extract_filenames()]) if not isinstance(aid, dict) else aid
    info["registry_import_tag"] = registry_import_tag(mesh)
    return info


TEX_INTENT = {
    "BC": {"srgb": "True", "compression_settings": str(unreal.TextureCompressionSettings.TC_DEFAULT)},
    "ORM": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_MASKS)},
    "N": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_NORMALMAP),
          "flip_green_channel": "False"},
}


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
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
