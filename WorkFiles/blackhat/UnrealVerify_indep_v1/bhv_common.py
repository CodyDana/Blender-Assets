"""Independent Unreal verification of SM_BlackHat - shared reader (runs inside Unreal).

Written by the independent verifier (not the build's bhu_common.py).  Expectations come only
from the shipped bytes in Exports/BlackHat and this verifier's own Blender truth_fbx.json.
inspect_mesh / inspect_texture are copied from the smoke bomb's independent verifier.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "blackhat" / "UnrealVerify_indep_v1"
EXPORTS = PROJ / "Exports" / "BlackHat"
MESH_NAME = "SM_BlackHat"
FBX = EXPORTS / f"{MESH_NAME}.fbx"
SIDECAR = EXPORTS / f"{MESH_NAME}.sockets.json"
TEXDIR = EXPORTS / "Textures"
DEST = os.environ.get("BHV_DEST", "/Game/PropsCheck/BlackHat_IndepV1_0926a")
ASSET = f"{DEST}/{MESH_NAME}"
TEXDEST = f"{DEST}/Textures"
TEX_NAMES = [p.stem for p in sorted(TEXDIR.glob("*.png"))]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def all_hashes():
    h = {"fbx": sha256(FBX), "sidecar": sha256(SIDECAR)}
    for p in sorted(TEXDIR.glob("*.png")):
        h[p.name] = sha256(p)
    return h


def vec(v, nd=6):
    return [round(float(v.x), nd), round(float(v.y), nd), round(float(v.z), nd)]


def safe(fn, default="<ERR>"):
    try:
        return fn()
    except Exception as exc:                                     # noqa: BLE001
        return f"{default}:{type(exc).__name__}: {exc}"[:240]


def sme():
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:                                            # noqa: BLE001
        s = None
    return s if s is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


def inspect_mesh(mesh, with_points=False):
    sub = sme()
    n = mesh.get_num_lods()
    info = {
        "asset": mesh.get_path_name(),
        "num_lods": n,
        "lod_triangles": [int(mesh.get_num_triangles(i)) for i in range(n)],
        "lod_vertices": [int(mesh.get_num_vertices(i)) for i in range(n)],
        "lod_sections": [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)],
        "lod_count_subsystem": safe(lambda: int(sub.get_lod_count(mesh))),
        "lod_screen_sizes": safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)]),
        "auto_compute_lod_screen_size": safe(
            lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size"))),
        "is_lod_screen_size_auto_computed": safe(lambda: bool(mesh.is_lod_screen_size_auto_computed())),
        "num_uv_channels": [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)],
        "light_map_coordinate_index": safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index"))),
        "light_map_resolution": safe(lambda: int(mesh.get_editor_property("light_map_resolution"))),
        "lod_for_collision": safe(lambda: int(mesh.get_editor_property("lod_for_collision"))),
        "positive_bounds_extension": safe(lambda: vec(mesh.get_editor_property("positive_bounds_extension"))),
        "negative_bounds_extension": safe(lambda: vec(mesh.get_editor_property("negative_bounds_extension"))),
        "nanite_enabled": safe(
            lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))),
    }
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: safe(lambda k=k: bs.get_editor_property(k)) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                "min_lightmap_resolution", "recompute_normals", "recompute_tangents",
                "use_mikk_t_space", "remove_degenerates", "use_full_precision_u_vs")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds

    # materials
    mats = []
    for m in mesh.get_editor_property("static_materials"):
        mats.append({"slot": str(m.material_slot_name),
                     "imported_slot": safe(lambda m=m: str(m.imported_material_slot_name)),
                     "material": safe(lambda m=m: m.material_interface.get_path_name()
                                      if m.material_interface else None)})
    info["static_materials"] = mats
    info["section_material_slot"] = [
        [safe(lambda i=i, s=s: int(sub.get_lod_material_slot(mesh, i, s)))
         for s in range(int(mesh.get_num_sections(i)))] for i in range(n)]

    # collision
    body = mesh.get_editor_property("body_setup")
    info["body_setup_present"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        convex = agg.get_editor_property("convex_elems")
        info["convex_hulls"] = len(convex)
        info["other_collision_elems"] = {
            k: safe(lambda k=k: len(agg.get_editor_property(k)), default="-1")
            for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems",
                      "level_set_elems", "skinned_level_set_elems")}
        info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
        hulls = []
        for e in convex:
            rec = {}
            pts = safe(lambda e=e: [[float(p.x), float(p.y), float(p.z)]
                                    for p in e.get_editor_property("vertex_data")], default="ERR")
            rec["vertex_count"] = len(pts) if isinstance(pts, list) else pts
            if with_points and isinstance(pts, list):
                rec["points_cm"] = pts
            rec["elem_box"] = safe(lambda e=e: [vec(e.get_editor_property("elem_box").min),
                                                vec(e.get_editor_property("elem_box").max)])
            rec["transform"] = safe(lambda e=e: {
                "t": vec(e.get_editor_property("transform").translation),
                "s": vec(e.get_editor_property("transform").scale3d)})
            rec["name"] = safe(lambda e=e: str(e.get_editor_property("name")))
            hulls.append(rec)
        info["convex_elems"] = hulls

    box = mesh.get_bounding_box()
    info["bounding_box_cm"] = {"min": vec(box.min), "max": vec(box.max),
                               "size": [round(box.max.x - box.min.x, 6), round(box.max.y - box.min.y, 6),
                                        round(box.max.z - box.min.z, 6)]}
    b = mesh.get_bounds()
    info["bounds"] = {"origin_cm": vec(b.origin), "box_extent_cm": vec(b.box_extent),
                      "sphere_radius_cm": float(b.sphere_radius)}

    # sockets: the array on the mesh AND the component's view
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    raws = []
    for nm in comp.get_all_socket_names():
        s = mesh.find_socket(nm)
        if s is None:
            raws.append({"name": str(nm), "found": False})
            continue
        raws.append({"name": str(s.get_editor_property("socket_name")), "found": True,
                     "outer": s.get_outer().get_path_name() if s.get_outer() else None,
                     "relative_location": vec(s.get_editor_property("relative_location")),
                     "relative_rotation_rpy": [float(s.get_editor_property("relative_rotation").roll),
                                               float(s.get_editor_property("relative_rotation").pitch),
                                               float(s.get_editor_property("relative_rotation").yaw)],
                     "relative_scale": vec(s.get_editor_property("relative_scale"))})
    info["socket_array"] = sorted(raws, key=lambda d: d["name"])
    info["socket_tag_query_all"] = safe(lambda: len(mesh.get_sockets_by_tag("")))
    socks = []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        socks.append({"name": str(name), "location_cm": vec(t.translation),
                      "rpy_deg": [round(e.x, 5), round(e.y, 5), round(e.z, 5)],
                      "scale": vec(t.scale3d)})
    info["component_sockets"] = sorted(socks, key=lambda d: d["name"])

    aid = safe(lambda: mesh.get_editor_property("asset_import_data"), default=None)
    if aid is not None and not isinstance(aid, str):
        info["import_data"] = {
            "class": aid.get_class().get_name(),
            "files": safe(lambda: [str(p) for p in aid.extract_filenames()]),
        }
        for k in ("import_mesh_lods", "generate_lightmap_u_vs", "one_convex_hull_per_ucx",
                  "auto_generate_collision", "combine_meshes", "normal_import_method",
                  "convert_scene", "convert_scene_unit", "force_front_x_axis", "import_uniform_scale",
                  "remove_degenerates"):
            info["import_data"][k] = safe(lambda k=k: str(aid.get_editor_property(k)))
    return info


def inspect_texture(tex):
    def prop(k):
        return safe(lambda: tex.get_editor_property(k))
    d = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for k in ("srgb", "compression_settings", "mip_gen_settings", "lod_group", "flip_green_channel",
              "compression_no_alpha", "never_stream", "virtual_texture_streaming", "power_of_two_mode",
              "max_texture_size", "lod_bias", "compression_quality", "mip_load_options",
              "num_cinematic_mip_levels", "downscale"):
        d[k] = str(prop(k))
    d["size"] = safe(lambda: [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())])
    d["built_size"] = safe(lambda: [int(tex.blueprint_get_built_texture_size().x),
                                    int(tex.blueprint_get_built_texture_size().y)])
    d["memory_size_bytes"] = safe(lambda: int(tex.blueprint_get_memory_size()))
    d["source_disk_and_memory"] = safe(lambda: str(tex.blueprint_get_texture_source_disk_and_memory_size()))
    d["import_files"] = safe(lambda: [str(p) for p in tex.get_editor_property("asset_import_data").extract_filenames()])
    d["mip_members"] = [m for m in dir(tex) if "mip" in m.lower()]
    return d
