"""Independent Unreal verification of SM_PaperBomb - shared reader.

This is NOT the build's uc_common.py.  Every expectation is re-derived here from

    Exports/PaperBomb/SM_PaperBomb.fbx           the bytes that ship (hashed)
    Exports/PaperBomb/SM_PaperBomb.sockets.json  the sidecar the customer applies
    Exports/PaperBomb/README.txt                 what the customer is promised
    WorkFiles/paperbomb/UnrealVerify2/blender_truth.json
                                                 a fresh Blender's re-import of those
                                                 exact bytes, measured by this reviewer

The build's paperbomb_report.json is read only to CONTRAST with, never to gate on.
"""
import hashlib
import json
import math
import os
import re
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "exact" / "pbuv0926"
EXPORTS = PROJ / "Exports" / "PaperBomb"
MESH_NAME = "SM_PaperBomb"
FBX = EXPORTS / f"{MESH_NAME}.fbx"
SIDECAR = EXPORTS / f"{MESH_NAME}.sockets.json"
README = EXPORTS / "README.txt"
TEXDIR = EXPORTS / "Textures"

DEST = os.environ.get("PBUV_DEST", "/Game/PBExact_0926")
ASSET = f"{DEST}/{MESH_NAME}"
TEXDEST = f"{DEST}/Textures"

SIDECAR_JSON = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXP_SCREEN = SIDECAR_JSON["lod_screen_sizes"]
EXP_SOCKETS = {s["socket"]: s for s in SIDECAR_JSON["sockets"]}

TRUTH = {}
_tp = HERE / "pbuv_blender_truth.json"
if _tp.is_file():
    TRUTH = json.loads(_tp.read_text(encoding="utf-8"))

# ---- what the README promises the buyer, parsed out of the shipped text --------------
README_TEXT = README.read_text(encoding="utf-8")


def readme_hashes():
    out = {}
    for m in re.finditer(r"(\S+\.(?:fbx|png))\s+sha256\s+([0-9a-f]{64})", README_TEXT):
        out[m.group(1)] = m.group(2)
    return out


def readme_screen_sizes():
    m = re.search(r"LOD screen sizes\s+([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)", README_TEXT)
    return [float(g) for g in m.groups()] if m else None


def readme_triangles():
    m = re.search(r"LOD triangles\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", README_TEXT)
    return [int(g) for g in m.groups()] if m else None


def readme_bounds_cm():
    m = re.search(r"bounds\s+([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)\s*cm", README_TEXT)
    return [float(g) for g in m.groups()] if m else None


def truth_lod_triangles():
    if not TRUTH:
        return None
    return [TRUTH["nodes"][f"{MESH_NAME}_LOD{i}"]["triangles"] for i in range(3)]


def truth_size_cm():
    return TRUTH["bounds"]["size_cm"] if TRUTH else None


def truth_sphere_radius_cm():
    return TRUTH["bounds"]["box_corner_radius_mm"] / 10.0 if TRUTH else None


# ---- texture intent, taken from README section 3, not from the build's code -----------
TEX_INTENT = {
    "BC":  {"srgb": True,  "compression": "TC_DEFAULT"},
    "N":   {"srgb": False, "compression": "TC_NORMALMAP", "flip_green": False},
    "ORM": {"srgb": False, "compression": "TC_MASKS"},
    "M":   {"srgb": False, "compression": "TC_MASKS"},
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v, nd=5):
    return [round(float(v.x), nd), round(float(v.y), nd), round(float(v.z), nd)]


def safe(fn, default="<ERR>"):
    try:
        return fn()
    except Exception as exc:                                     # noqa: BLE001
        return f"{default}:{type(exc).__name__}: {exc}"[:220]


def ang_close(a, b, tol=1e-2):
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0) < tol


def sme():
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:                                            # noqa: BLE001
        s = None
    return s if s is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


def inspect_mesh(mesh):
    sub = sme()
    n = mesh.get_num_lods()
    info = {
        "asset": mesh.get_path_name(),
        "package": mesh.get_outermost().get_path_name(),
        "num_lods": n,
        "lod_triangles": [mesh.get_num_triangles(i) for i in range(n)],
        "lod_vertices": [mesh.get_num_vertices(i) for i in range(n)],
        "lod_sections": [safe(lambda i=i: mesh.get_num_sections(i)) for i in range(n)],
        "lod_screen_sizes": safe(lambda: [round(float(v), 7) for v in sub.get_lod_screen_sizes(mesh)]),
        "auto_compute_lod_screen_size": safe(
            lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size"))),
        "num_uv_channels": [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)],
        "light_map_coordinate_index": safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index"))),
        "light_map_resolution": safe(lambda: int(mesh.get_editor_property("light_map_resolution"))),
        "material_slots": [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")],
        "nanite_enabled": safe(
            lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))),
    }
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: bs.get_editor_property(k) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                "recompute_normals", "recompute_tangents", "use_mikk_t_space",
                "remove_degenerates", "use_high_precision_tangent_basis",
                "min_lightmap_resolution")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds

    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    convex = agg.get_editor_property("convex_elems")
    info["convex_hulls"] = len(convex)
    info["convex_hull_vertex_counts"] = [
        safe(lambda e=e: len(e.get_editor_property("vertex_data")), default="-1") for e in convex]
    info["other_collision_elems"] = {
        k: safe(lambda k=k: len(agg.get_editor_property(k)), default="-1")
        for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
    info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
    info["collision_complexity_ok"] = "SimpleAndComplex" in info["collision_trace_flag"] or \
                                      "Default" in info["collision_trace_flag"]
    # convex hull extents, straight off the stored points
    hull_pts = []
    for e in convex:
        try:
            for p in e.get_editor_property("vertex_data"):
                hull_pts.append((p.x, p.y, p.z))
        except Exception:                                        # noqa: BLE001
            pass
    if hull_pts:
        xs = [p[0] for p in hull_pts]; ys = [p[1] for p in hull_pts]; zs = [p[2] for p in hull_pts]
        info["hull_min_cm"] = [round(min(xs), 5), round(min(ys), 5), round(min(zs), 5)]
        info["hull_max_cm"] = [round(max(xs), 5), round(max(ys), 5), round(max(zs), 5)]
        info["hull_size_cm"] = [round(max(xs) - min(xs), 5), round(max(ys) - min(ys), 5),
                                round(max(zs) - min(zs), 5)]
        info["hull_point_count"] = len(hull_pts)

    box = mesh.get_bounding_box()
    info["bounds_min_cm"] = vec(box.min)
    info["bounds_max_cm"] = vec(box.max)
    info["size_cm"] = [round(box.max.x - box.min.x, 5), round(box.max.y - box.min.y, 5),
                       round(box.max.z - box.min.z, 5)]
    b = mesh.get_bounds()
    info["bounds_origin_cm"] = safe(lambda: vec(b.origin))
    info["bounds_box_extent_cm"] = safe(lambda: vec(b.box_extent))
    info["bounds_sphere_radius_cm"] = safe(lambda: round(float(b.sphere_radius), 5))

    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    socks, raws = [], []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        socks.append({"name": str(name), "location_cm": vec(t.translation),
                      "rpy_deg": [round(e.x, 4), round(e.y, 4), round(e.z, 4)],
                      "scale": vec(t.scale3d)})
        s = mesh.find_socket(name)
        raws.append({"name": str(name), "found": s is not None,
                     "outer": (s.get_outer().get_path_name() if (s and s.get_outer()) else None),
                     "relative_location": vec(s.get_editor_property("relative_location")) if s else None,
                     "relative_rotation": (
                         [round(float(s.get_editor_property("relative_rotation").roll), 4),
                          round(float(s.get_editor_property("relative_rotation").pitch), 4),
                          round(float(s.get_editor_property("relative_rotation").yaw), 4)] if s else None),
                     "relative_scale": vec(s.get_editor_property("relative_scale")) if s else None})
    info["sockets"] = sorted(socks, key=lambda d: d["name"])
    info["socket_raw"] = sorted(raws, key=lambda d: d["name"])
    return info


def inspect_texture(tex):
    def prop(k):
        return safe(lambda: tex.get_editor_property(k))
    d = {
        "asset": tex.get_path_name(),
        "srgb": prop("srgb"),
        "compression_settings": str(prop("compression_settings")),
        "mip_gen_settings": str(prop("mip_gen_settings")),
        "lod_group": str(prop("lod_group")),
        "never_stream": prop("never_stream"),
        "compression_no_alpha": prop("compression_no_alpha"),
        "flip_green_channel": prop("flip_green_channel"),
        "source_x": safe(lambda: int(tex.blueprint_get_size_x())),
        "source_y": safe(lambda: int(tex.blueprint_get_size_y())),
        "num_mips": safe(lambda: int(len(tex.get_editor_property("platform_data").mips))
                         if tex.get_editor_property("platform_data") else -1),
    }
    d["source_size"] = safe(lambda: [int(tex.get_editor_property("source").get_size_x()),
                                     int(tex.get_editor_property("source").get_size_y())])
    d["source_format"] = safe(lambda: str(tex.get_editor_property("source").get_format()))
    d["imported_size"] = safe(lambda: [int(tex.get_editor_property("imported_size").x),
                                       int(tex.get_editor_property("imported_size").y)])
    d["asset_import_file"] = safe(
        lambda: [str(p) for p in tex.get_editor_property("asset_import_data").extract_filenames()])
    return d


# ---- recolour maps: intent from recolour_maps.json / material_spec.json texture_import ----
RECOLOUR_DIR = TEXDIR / "Recolour"
RECOLOUR_INTENT = {
    "T_PaperBomb_PaperDetail": {"srgb": True, "compression": "TC_EDITOR_ICON"},
    "T_PaperBomb_InkWeights": {"srgb": False, "compression": "TC_VECTOR_DISPLACEMENTMAP"},
}
EXPECTED_SHA = {
    "SM_PaperBomb.fbx": "5f7e584c477c8449a9c9566bb25bde3b2d44cbf1498090dcd256af530c851cf2",
    "SM_PaperBomb.sockets.json": "7cb7ab4f38c954278cbbc932fea949af526dd4fa72d2fb096e86e03f31177d7b",
    "T_PaperBomb_BC.png": "812f2cb4a3649d2e6bd47f81cbaaa83f8bc585e81b725989c20f649846aa824b",
    "T_PaperBomb_M.png": "a111adc8462778309321570f70f0ce0cdce2009fecdd05624547ff89b0ff3710",
    "T_PaperBomb_N.png": "6f854e56d3f604c7b5a79c09c0689b149f26cd6bd94b055575daf585ad080bc5",
    "T_PaperBomb_ORM.png": "4873d2e0fda8bd76128299a83e8ca3bfdbeb93ad93bec1b6cad1fbe58e5b14b9",
    "T_PaperBomb_InkWeights.png": "bd8cc07db9b9ddfe86b2ca07cccd57a79bf6524001ab37ee458eaf11d4cac7fd",
    "T_PaperBomb_PaperDetail.png": "08bf5c918ff177995847618b4b021e55c30ebf35c035ff0f4d3c01610cbf0def",
}
