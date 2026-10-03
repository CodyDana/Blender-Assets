"""Senbon UNREAL verifier (2026-10-03) - shared reader for the UE 5.8 pythonscript commandlet.

Modelled on WorkFiles/flashbang/UnrealVerify_claude/uv_common.py and UnrealCheck_fin/fbu_common.py.  Expectations come
only from the shipped files (FBX bytes, sidecars, README) and this verifier's own fresh-Blender truth (truth_fbx.json).
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import unreal  # noqa: E402

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "senbon" / "UnrealVerify"
EXP = PROJ / "Exports" / "Senbon"
TEXDIR = EXP / "Textures"
DEST = os.environ.get("SV_DEST") or (HERE / "content_path.txt").read_text(encoding="utf-8").strip()
TEXDEST = f"{DEST}/Textures"
MATDEST = f"{DEST}/VerifierMaterials"
MESHES = ["SM_Senbon_Needle", "SM_Senbon_Heavy"]
SLOTS = {"SM_Senbon_Needle": 1, "SM_Senbon_Heavy": 2}
TC = unreal.TextureCompressionSettings
TMGS = unreal.TextureMipGenSettings
# README "If you import the textures yourself": BC sRGB ON Default; ORM sRGB OFF Masks; N sRGB OFF Normalmap, flip
# green OFF; Detail16 sRGB OFF Grayscale.  Mips from the texture group on all (full chains).
_BC = {"srgb": True, "compression_settings": TC.TC_DEFAULT, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP}
_ORM = {"srgb": False, "compression_settings": TC.TC_MASKS, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP}
_N = {"srgb": False, "compression_settings": TC.TC_NORMALMAP, "flip_green_channel": False,
      "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP}
_D16 = {"srgb": False, "compression_settings": TC.TC_GRAYSCALE, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP}
TEXTURES = {}
for _set in ("Needle", "Heavy", "Heavy_Wrap"):
    for _k, _w in (("BC", _BC), ("ORM", _ORM), ("N", _N)):
        TEXTURES[f"T_Senbon_{_set}_{_k}"] = (TEXDIR / f"T_Senbon_{_set}_{_k}.png", _w)
TEXTURES["T_Senbon_Heavy_Wrap_Detail16"] = (TEXDIR / "Recolour" / "T_Senbon_Heavy_Wrap_Detail16.png", _D16)
TRUTH = json.loads((HERE / "truth_fbx.json").read_text(encoding="utf-8")) if (HERE / "truth_fbx.json").exists() else {}


def sidecar(name):
    return json.loads((EXP / f"{name}.sockets.json").read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def all_hashes():
    h = {}
    for p in sorted(EXP.rglob("*")):
        if p.is_file():
            h[str(p.relative_to(EXP)).replace("\\", "/")] = sha256(p)
    return h


def vec(v, nd=6):
    return [round(float(v.x), nd), round(float(v.y), nd), round(float(v.z), nd)]


def safe(fn, default="<ERR>"):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return f"{default}:{type(exc).__name__}: {exc}"[:240]


def sme():
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        s = None
    return s if s is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


def lod_positions(mesh, lod):
    desc = mesh.get_static_mesh_description(lod)
    out = []
    for i in range(int(desc.get_vertex_count())):
        vid = unreal.VertexID()
        try:
            vid.set_editor_property("id_value", i)
        except Exception:  # noqa: BLE001
            vid.set_editor_property("value", i)
        p = desc.get_vertex_position(vid)
        out.append([float(p.x), float(p.y), float(p.z)])
    return out


def inspect_mesh(mesh, with_points=False):
    sub = sme()
    n = mesh.get_num_lods()
    info = {
        "asset": mesh.get_path_name(), "num_lods": n,
        "lod_triangles": [int(mesh.get_num_triangles(i)) for i in range(n)],
        "lod_vertices": [int(mesh.get_num_vertices(i)) for i in range(n)],
        "lod_sections": [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)],
        "lod_screen_sizes": safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)]),
        "auto_compute_lod_screen_size": safe(lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size"))),
        "num_uv_channels": [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)],
        "light_map_coordinate_index": safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index"))),
        "light_map_resolution": safe(lambda: int(mesh.get_editor_property("light_map_resolution"))),
        "lod_for_collision": safe(lambda: int(mesh.get_editor_property("lod_for_collision"))),
        "nanite_enabled": safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))),
        "lod_group": safe(lambda: str(mesh.get_editor_property("lod_group"))),
    }
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: safe(lambda k=k: str(bs.get_editor_property(k))) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "recompute_normals",
                "recompute_tangents", "use_mikk_t_space", "remove_degenerates", "use_full_precision_u_vs")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds
    info["static_materials"] = [{"slot": str(m.material_slot_name),
                                 "material": safe(lambda m=m: m.material_interface.get_path_name()
                                                  if m.material_interface else None)}
                                for m in mesh.get_editor_property("static_materials")]
    info["section_material_slot"] = [[safe(lambda i=i, s=s: int(sub.get_lod_material_slot(mesh, i, s)))
                                       for s in range(int(mesh.get_num_sections(i)))] for i in range(n)]
    body = mesh.get_editor_property("body_setup")
    info["body_setup_present"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        convex = agg.get_editor_property("convex_elems")
        info["convex_hulls"] = len(convex)
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)), default="-1")
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems")}
        info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
        hulls = []
        for e in convex:
            rec = {"name": safe(lambda e=e: str(e.get_editor_property("name")))}
            pts = safe(lambda e=e: [[float(p.x), float(p.y), float(p.z)]
                                    for p in e.get_editor_property("vertex_data")], default="ERR")
            rec["vertex_count"] = len(pts) if isinstance(pts, list) else pts
            idx = safe(lambda e=e: [int(i) for i in e.get_editor_property("index_data")], default="ERR")
            rec["index_count"] = len(idx) if isinstance(idx, list) else idx
            if with_points:
                rec["points_cm"] = pts
                rec["indices"] = idx
            rec["transform"] = safe(lambda e=e: {"t": vec(e.get_editor_property("transform").translation),
                                                 "s": vec(e.get_editor_property("transform").scale3d)})
            hulls.append(rec)
        info["convex_elems"] = hulls
    box = mesh.get_bounding_box()
    info["bounding_box_cm"] = {"min": vec(box.min), "max": vec(box.max)}
    b = mesh.get_bounds()
    info["bounds"] = {"origin_cm": vec(b.origin), "box_extent_cm": vec(b.box_extent),
                      "sphere_radius_cm": float(b.sphere_radius)}
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    socks = []
    for nm in comp.get_all_socket_names():
        s = mesh.find_socket(nm)
        t = comp.get_socket_transform(str(nm), unreal.RelativeTransformSpace.RTS_COMPONENT)
        r = t.rotation.rotator()
        rec = {"name": str(nm), "component_location_cm": vec(t.translation),
               "component_rpy": [round(r.roll, 5), round(r.pitch, 5), round(r.yaw, 5)],
               "component_scale": vec(t.scale3d)}
        if s is not None:
            rr = s.get_editor_property("relative_rotation")
            rec.update({"outer": s.get_outer().get_path_name() if s.get_outer() else None,
                        "relative_location": vec(s.get_editor_property("relative_location")),
                        "relative_rpy": [float(rr.roll), float(rr.pitch), float(rr.yaw)],
                        "relative_scale": vec(s.get_editor_property("relative_scale"))})
        socks.append(rec)
    info["sockets"] = sorted(socks, key=lambda d: d["name"])
    aid = safe(lambda: mesh.get_editor_property("asset_import_data"), default=None)
    if aid is not None and not isinstance(aid, str):
        info["import_data"] = {"class": aid.get_class().get_name(),
                               "files": safe(lambda: [str(p) for p in aid.extract_filenames()])}
        for k in ("import_mesh_lods", "generate_lightmap_u_vs", "one_convex_hull_per_ucx", "auto_generate_collision",
                  "combine_meshes", "normal_import_method", "normal_generation_method", "convert_scene",
                  "convert_scene_unit", "force_front_x_axis", "import_uniform_scale"):
            info["import_data"][k] = safe(lambda k=k: str(aid.get_editor_property(k)))
    return info


def inspect_texture(tex):
    d = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for k in ("srgb", "compression_settings", "mip_gen_settings", "lod_group", "flip_green_channel",
              "compression_no_alpha", "never_stream", "virtual_texture_streaming", "power_of_two_mode",
              "max_texture_size", "lod_bias", "address_x", "address_y", "filter"):
        d[k] = str(safe(lambda k=k: tex.get_editor_property(k)))
    d["size"] = safe(lambda: [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())])
    d["import_files"] = safe(lambda: [str(p) for p in tex.get_editor_property("asset_import_data").extract_filenames()])
    return d


def flags_match(info, want):
    out = {}
    for k, v in want.items():
        out[k] = str(info.get(k)) == str(v)
    out["mips_not_disabled"] = "NO_MIPMAPS" not in str(info.get("mip_gen_settings", "")).upper()
    s = info.get("size")
    out["power_of_two"] = isinstance(s, list) and all(x > 0 and (x & (x - 1)) == 0 for x in s)
    out["all"] = all(out.values())
    return out
