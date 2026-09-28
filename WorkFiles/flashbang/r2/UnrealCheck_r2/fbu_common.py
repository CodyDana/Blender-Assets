"""Shared helpers for SM_Flashbang's Unreal verification (UE 5.8 pythonscript commandlet), adapted from the smoke
bomb's WorkFiles/smokebomb/UnrealCheck_fp/sbu_common.py.  Everything expected is read from the build's outputs."""
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "flashbang" / "r2" / "UnrealCheck_r2"
DEST = os.environ.get("FLASHBANG_DEST", "/Game/PropsCheck/Flashbang")
REPORT = json.loads((PROJ / "WorkFiles" / "flashbang" / "flashbang_report.json").read_text(encoding="utf-8"))
EXP = PROJ / "Exports" / "Flashbang"
MESHES = {"assembled": "SM_Flashbang", "body": "SM_Flashbang_Body", "pullring": "SM_Flashbang_PullRing",
          "lever": "SM_Flashbang_Lever"}
HULLS = {"assembled": 4, "body": 2, "pullring": 1, "lever": 1}
SLOTS = {"assembled": 2, "body": 2, "pullring": 1, "lever": 1}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:200]} if default is None else default


def vec(v, nd=4):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def subsystem():
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    return sub or unreal.new_object(unreal.StaticMeshEditorSubsystem)


def lod_positions_cm(mesh, lod=0):
    desc = mesh.get_static_mesh_description(lod)
    out = []
    for i in range(desc.get_vertex_count()):
        vid = unreal.VertexID()
        try:
            vid.set_editor_property("id_value", i)
        except Exception:  # noqa: BLE001
            vid.set_editor_property("value", i)
        p = desc.get_vertex_position(vid)
        out.append((p.x, p.y, p.z))
    return out


def inspect(mesh):
    sub = subsystem()
    n = mesh.get_num_lods()
    info = {"asset": mesh.get_path_name(), "num_lods": n,
            "lod_triangles": [mesh.get_num_triangles(i) for i in range(n)],
            "lod_sections": [safe(lambda i=i: mesh.get_num_sections(i)) for i in range(n)],
            "lod_screen_sizes": safe(lambda: [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)]),
            "light_map_coordinate_index": safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index"))),
            "nanite_enabled": safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))),
            "material_slots": [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")]}
    builds = []
    for i in range(n):
        def rd(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: bs.get_editor_property(k) for k in ("generate_lightmap_u_vs", "src_lightmap_index",
                                                          "dst_lightmap_index", "recompute_normals")}
        builds.append(safe(rd))
    info["lod_build_settings"] = builds
    agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
    elems = agg.get_editor_property("convex_elems")
    info["convex_hulls"] = len(elems)
    info["convex_hull_vertex_counts"] = safe(lambda: [len(e.get_editor_property("vertex_data")) for e in elems])
    box = mesh.get_bounding_box()
    info["bounds_min_cm"], info["bounds_max_cm"] = vec(box.min), vec(box.max)
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    socks = []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        s = mesh.find_socket(name)
        r = t.rotation.rotator()
        socks.append({"name": str(name), "location_cm": vec(t.translation),
                      "rotation": [round(r.roll, 3), round(r.pitch, 3), round(r.yaw, 3)],
                      "scale": vec(t.scale3d),
                      "relative_scale": vec(s.get_editor_property("relative_scale")) if s else None,
                      "outer": s.get_outer().get_path_name() if s and s.get_outer() else None})
    info["sockets"] = sorted(socks, key=lambda d: d["name"])
    return info
