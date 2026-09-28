"""PASS B - a SECOND fresh editor process.  Nothing is in memory from pass A.

Loads the saved packages off disk and re-reads everything, then re-exports the mesh to
FBX so the collision hull and the generated lightmap UV can be measured outside Unreal.
This is the only pass whose numbers are allowed to be gates.
"""
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealVerify2")
sys.path.insert(0, str(HERE))

import unreal                                                    # noqa: E402
import v2_common as C                                            # noqa: E402

OUT = HERE / "passB.json"
ROUNDTRIP = HERE / "roundtrip.fbx"


def probe(obj, label):
    """Record which editor properties actually exist on this engine build."""
    names = set()
    try:
        for n in dir(obj):
            if not n.startswith("_"):
                names.add(n)
    except Exception:                                            # noqa: BLE001
        pass
    return {"label": label, "type": type(obj).__name__, "members": sorted(names)}


def hull_points(mesh):
    """Every convex element's points, whatever the accessor is called on this build."""
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    elems = agg.get_editor_property("convex_elems")
    out = []
    for e in elems:
        rec = {"tried": {}}
        for attr in ("vertex_data", "vertexdata", "VertexData"):
            try:
                pts = e.get_editor_property(attr)
                rec["tried"][attr] = len(pts)
                rec["points"] = [[round(float(p.x), 6), round(float(p.y), 6), round(float(p.z), 6)]
                                 for p in pts]
                break
            except Exception as exc:                             # noqa: BLE001
                rec["tried"][attr] = f"{type(exc).__name__}"
        for meth in ("get_convex_vertices",):
            try:
                pts = getattr(e, meth)()
                rec["points"] = [[round(float(p.x), 6), round(float(p.y), 6), round(float(p.z), 6)]
                                 for p in pts]
                rec["tried"][meth] = len(pts)
            except Exception as exc:                             # noqa: BLE001
                rec["tried"][meth] = f"{type(exc).__name__}"
        try:
            b = e.get_editor_property("elem_box")
            rec["elem_box"] = [round(float(b.min.x), 5), round(float(b.min.y), 5),
                               round(float(b.min.z), 5), round(float(b.max.x), 5),
                               round(float(b.max.y), 5), round(float(b.max.z), 5)]
        except Exception:                                        # noqa: BLE001
            pass
        rec["members"] = probe(e, "KConvexElem")["members"]
        out.append(rec)
    return out


def texture_detail(tex):
    d = C.inspect_texture(tex)
    d["blueprint_size"] = C.safe(lambda: [int(tex.blueprint_get_size_x()),
                                          int(tex.blueprint_get_size_y())])
    for attr in ("num_mips", "get_num_mips"):
        try:
            v = getattr(tex, attr)
            d["num_mips_via_" + attr] = int(v() if callable(v) else v)
        except Exception:                                        # noqa: BLE001
            pass
    for prop in ("mip_load_options", "max_texture_size", "power_of_two_mode",
                 "downscale", "virtual_texture_streaming", "srgb", "never_stream",
                 "compression_quality", "deferred_pass_compression"):
        d[prop] = C.safe(lambda p=prop: tex.get_editor_property(p))
    try:
        d["mip_count_runtime"] = int(unreal.SystemLibrary.get_object_name(tex) and
                                     tex.get_editor_property("num_mips"))
    except Exception:                                            # noqa: BLE001
        pass
    d["members_sample"] = [m for m in probe(tex, "Texture2D")["members"]
                           if "mip" in m.lower() or "size" in m.lower()]
    return d


def screen_size_math(radius_cm):
    """Unreal's own ComputeBoundsScreenSize, inverted, for a 90 and a 60 degree FOV.

        ScreenSize = 2 * (0.5 * P00) * R / D          (P00 = 1 / tan(halfFOV))

    so D = P00 * R / ScreenSize.  Also reports the projected pixel size of the bounding
    sphere at 1080 lines, which is what 'ScreenSize' means physically.
    """
    out = {}
    for fov in (90.0, 60.0):
        p00 = 1.0 / math.tan(math.radians(fov) * 0.5)
        out[f"fov{int(fov)}"] = {
            "p00": round(p00, 6),
            "switch_distance_m": [round(p00 * (radius_cm / 100.0) / ss, 5) if ss > 0 else None
                                  for ss in C.EXP_SCREEN],
        }
    out["sphere_pixel_diameter_at_1080"] = [round(ss * 1080.0, 3) for ss in C.EXP_SCREEN]
    out["radius_cm_used"] = radius_cm
    return out


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET}
    try:
        rep["asset_exists"] = bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))
        mesh = unreal.load_asset(C.ASSET)
        rep["is_static_mesh"] = isinstance(mesh, unreal.StaticMesh)
        info = C.inspect_mesh(mesh)
        rep["mesh"] = info

        # ---- accessors this engine build actually has --------------------------------
        sm_members = probe(mesh, "StaticMesh")["members"]
        rep["staticmesh_lod_screensize_members"] = [
            m for m in sm_members if "screen" in m.lower() or "auto" in m.lower()]
        sub = C.sme()
        rep["subsystem_members"] = [m for m in probe(sub, "StaticMeshEditorSubsystem")["members"]
                                    if "lod" in m.lower() or "uv" in m.lower()]
        rep["hull_elements"] = hull_points(mesh)

        # ---- source (MeshDescription) UV channel count, per LOD ----------------------
        uvinfo = []
        for i in range(mesh.get_num_lods()):
            rec = {"lod": i,
                   "num_uv_channels_subsystem": C.safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i)))}
            try:
                desc = mesh.get_static_mesh_description(i)
                rec["description_uv_count"] = C.safe(lambda d=desc: int(d.get_num_uv_elements()))
                rec["description_vertices"] = C.safe(lambda d=desc: int(d.get_vertex_count()))
                rec["description_triangles"] = C.safe(lambda d=desc: int(d.get_triangle_count()))
            except Exception as exc:                             # noqa: BLE001
                rec["description_error"] = f"{type(exc).__name__}: {exc}"[:160]
            uvinfo.append(rec)
        rep["uv_channels"] = uvinfo

        # ---- physics -----------------------------------------------------------------
        body = mesh.get_editor_property("body_setup")
        rep["physics"] = {
            "collision_trace_flag": str(body.get_editor_property("collision_trace_flag")),
            "mass_in_kg_override": C.safe(
                lambda: float(body.get_editor_property("default_instance").get_editor_property("mass_in_kg_override"))),
            "override_mass": C.safe(
                lambda: bool(body.get_editor_property("default_instance").get_editor_property("override_mass"))),
        }

        # ---- LOD policy arithmetic ---------------------------------------------------
        r_engine = info.get("bounds_sphere_radius_cm")
        rep["lod_policy"] = {
            "sidecar_screen_sizes": C.EXP_SCREEN,
            "engine_screen_sizes": info.get("lod_screen_sizes"),
            "engine_sphere_radius_cm": r_engine,
            "blender_box_corner_radius_cm": C.truth_sphere_radius_cm(),
            "blender_lod0_sphere_radius_cm": (C.TRUTH["bounds"]["lod0_sphere_radius_about_lod0_centre_mm"] / 10.0)
                                             if C.TRUTH else None,
            "with_engine_radius": screen_size_math(r_engine) if isinstance(r_engine, float) else None,
            "with_build_radius": screen_size_math(C.truth_sphere_radius_cm())
                                 if C.truth_sphere_radius_cm() else None,
        }

        # ---- textures ----------------------------------------------------------------
        tex = {}
        for suffix in C.TEX_INTENT:
            p = f"{C.TEXDEST}/T_PaperBomb_{suffix}"
            t = unreal.load_asset(p)
            tex[suffix] = texture_detail(t) if isinstance(t, unreal.Texture2D) else {
                "error": f"not a Texture2D at {p}"}
        rep["textures"] = tex

        # ---- round-trip export --------------------------------------------------------
        try:
            opt = unreal.FbxExportOption()
            opt.set_editor_property("collision", True)
            opt.set_editor_property("level_of_detail", True)
            opt.set_editor_property("vertex_color", False)
            opt.set_editor_property("ascii", False)
            opt.set_editor_property("fbx_export_compatibility",
                                    unreal.FbxExportCompatibility.FBX_2013)
            task = unreal.AssetExportTask()
            task.set_editor_property("object", mesh)
            task.set_editor_property("filename", str(ROUNDTRIP))
            task.set_editor_property("automated", True)
            task.set_editor_property("prompt", False)
            task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
            task.set_editor_property("options", opt)
            rep["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
            rep["export_path"] = str(ROUNDTRIP)
            rep["export_bytes"] = ROUNDTRIP.stat().st_size if ROUNDTRIP.is_file() else 0
        except Exception:
            rep["export_error"] = traceback.format_exc()[-1500:]
    except Exception:
        rep["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("PBV2_PASSB_DONE " + str(OUT))


main()
