"""UnrealCheck8 shared helpers (runs inside the UE 5.8 pythonscript commandlet).

Independent import verifier for shuriken style pass 2 (knife grind, library 3.6.0). Written fresh, not a
copy of UnrealCheck6/7: its expectations come from the FORM SPECS (build_*.py spec values), from the
.blend (b1_blend_truth.py) and from the sidecar bytes, never from the build report alone.
Fresh content path: /Game/ShurikenCheck8/Verify (meshes) and /Game/ShurikenCheck8/Verify/Textures.
"""
import hashlib
import json
import math
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck8"
EXPORTS = PROJ / "Exports" / "Shuriken"
# A fresh content path per verification run (SHURIKEN_UC8_DEST; the style-pass-2 run used /Game/ShurikenCheck8/Verify).
DEST = os.environ.get("SHURIKEN_UC8_DEST", "/Game/ShurikenCheck8/Verify")
TEX_DEST = DEST + "/Textures"

# Spec figures (build_four_point.py / build_eight_point.py / build_square_plate.py spec values):
#   four-point tip circle 97.0 mm, 3.0 mm; eight-point 100.0 mm, 2.5 mm; senban side 76.2 mm (corner to corner
#   76.2 * sqrt 2 on the axes), 1.9 mm. Screen sizes: pack 1.0 / 0.10 / 0.035, the senban's scaled by
#   corner radius / 50 mm and rounded to 4 digits (spec.scaled_lod_screen_sizes).
_SENBAN_DIAG_CM = 7.62 * math.sqrt(2.0)
_SENBAN_R_MM = 76.2 / math.sqrt(2.0)
FORMS = {
    "four_point": {"mesh": "SM_Shuriken_FourPoint", "size_cm": [9.7, 9.7, 0.3],
                   "screen_sizes": [1.0, 0.1, 0.035]},
    "eight_point": {"mesh": "SM_Shuriken_EightPoint", "size_cm": [10.0, 10.0, 0.25],
                    "screen_sizes": [1.0, 0.1, 0.035]},
    "square_plate": {"mesh": "SM_Shuriken_SquarePlate", "size_cm": [_SENBAN_DIAG_CM, _SENBAN_DIAG_CM, 0.19],
                     "screen_sizes": [1.0, round(0.1 * _SENBAN_R_MM / 50.0, 4), round(0.035 * _SENBAN_R_MM / 50.0, 4)]},
    # build_six_point.py spec: tip circle 98.0 mm with +X down one tip (X span 98 mm, Y span 2 x 49 sin 60 =
    # 84.87 mm), 2.0 mm; screen sizes scaled by tip radius 49 / 50 mm.
    # build_spike.py spec: a 150 mm bar, 6 mm square, lying on a face along +X; screen sizes scaled by Unreal's bounds
    # sphere radius sqrt(75^2 + 2 x 1.5^2) = 75.03 mm (the butt corners from the box centre) / 50 mm.
    "spike": {"mesh": "SM_Shuriken_Spike", "size_cm": [15.0, 0.6, 0.6],
              "screen_sizes": [1.0, round(0.1 * math.sqrt(75.0 ** 2 + 4.5) / 50.0, 4),
                               round(0.035 * math.sqrt(75.0 ** 2 + 4.5) / 50.0, 4)]},
    "six_point": {"mesh": "SM_Shuriken_SixPoint", "size_cm": [9.8, 2.0 * 4.9 * math.sin(math.radians(60.0)), 0.2],
                  "screen_sizes": [1.0, round(0.1 * 49.0 / 50.0, 4), round(0.035 * 49.0 / 50.0, 4)]},
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def fbx(form):
    return EXPORTS / f"{FORMS[form]['mesh']}.fbx"


def sidecar(form):
    return EXPORTS / f"{FORMS[form]['mesh']}.sockets.json"


def asset(form):
    return f"{DEST}/{FORMS[form]['mesh']}"


def v3(v, nd=6):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:240]}


def sm_subsystem():
    sub = None
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    if sub is None:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
    return sub


def import_data(obj):
    """Source file and stored hash the importer recorded (ties the asset to the bytes it came from)."""
    out = {}
    aid = safe(lambda: obj.get_editor_property("asset_import_data"))
    if isinstance(aid, dict) or aid is None:
        return {"asset_import_data": aid}
    out["filenames"] = safe(lambda: [str(f) for f in aid.extract_filenames()])
    out["first_filename"] = safe(lambda: str(aid.get_first_filename()))
    try:
        src = aid.get_editor_property("source_data")
        files = src.get_editor_property("source_files")
        out["source_files"] = []
        for f in files:
            rec = {}
            for k in ("relative_filename", "file_hash", "timestamp", "display_label_name"):
                rec[k] = str(safe(lambda k=k: f.get_editor_property(k)))
            out["source_files"].append(rec)
    except Exception as exc:  # noqa: BLE001
        out["source_files"] = f"{type(exc).__name__}: {exc}"[:200]
    return out


def inspect_mesh(mesh):
    sub = sm_subsystem()
    info = {"asset": mesh.get_path_name(), "class": mesh.get_class().get_name()}
    n = mesh.get_num_lods()
    info["num_lods"] = n
    info["lod_triangles"] = [int(mesh.get_num_triangles(i)) for i in range(n)]
    info["lod_vertices"] = [int(mesh.get_num_vertices(i)) for i in range(n)]
    info["lod_sections"] = [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)]
    info["lod_screen_sizes"] = safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)])
    info["auto_compute_lod_screen_size"] = safe(lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
    info["lod_uv_channels"] = [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]
    builds = []
    for i in range(n):
        def rd(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: (bool(v) if isinstance(v, bool) else (int(v) if isinstance(v, int) else str(v)))
                    for k, v in ((k, bs.get_editor_property(k)) for k in (
                        "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                        "min_lightmap_resolution", "recompute_normals", "recompute_tangents",
                        "use_mikk_t_space", "remove_degenerates", "use_full_precision_u_vs",
                        "use_high_precision_tangent_basis", "build_scale3d"))}
        builds.append(safe(rd))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    info["has_body_setup"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        convex = agg.get_editor_property("convex_elems")
        info["convex_hulls"] = len(convex)
        info["convex_elem_fields"] = []
        for c in convex:
            fields = {}
            for k in ("vertex_data", "index_data", "elem_box", "transform", "name"):
                val = safe(lambda k=k: c.get_editor_property(k))
                if isinstance(val, dict):
                    fields[k] = val
                elif k == "vertex_data":
                    fields[k] = [v3(p, 6) for p in val]
                elif k == "index_data":
                    fields[k] = [int(x) for x in val]
                else:
                    fields[k] = str(val)[:200]
            info["convex_elem_fields"].append(fields)
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)))
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
        info["collision_trace_flag"] = str(safe(lambda: body.get_editor_property("collision_trace_flag")))
    bb = mesh.get_bounding_box()
    info["bounds_min_cm"] = v3(bb.min)
    info["bounds_max_cm"] = v3(bb.max)
    info["size_cm"] = [round(bb.max.x - bb.min.x, 6), round(bb.max.y - bb.min.y, 6), round(bb.max.z - bb.min.z, 6)]
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    # sockets, read two ways: the asset's own socket objects, and a component's socket transforms
    info["socket_objects"] = []
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
    info["component_socket_names"] = sorted(str(n) for n in comp.get_all_socket_names())
    info["component_sockets"] = {}
    for name in info["component_socket_names"]:
        t = comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
        info["component_sockets"][name] = {"location_cm": v3(t.translation), "scale": v3(t.scale3d),
                                           "rotator": {"roll": round(t.rotation.rotator().roll, 6),
                                                       "pitch": round(t.rotation.rotator().pitch, 6),
                                                       "yaw": round(t.rotation.rotator().yaw, 6)}}
    info["import_data"] = import_data(mesh)
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
    info["import_data"] = import_data(tex)
    return info


def write(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
