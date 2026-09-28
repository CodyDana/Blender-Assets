"""PASS B (a fresh process after the imports) - read everything back off disk, probe mips, re-export.

Nothing is in memory from the import processes.  These are the gate numbers.  The re-export
(collision + LODs + UV1) is measured outside Unreal by bhv_roundtrip.py.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v1")
sys.path.insert(0, str(HERE))

import unreal                                                    # noqa: E402
import bhv_common as C                                           # noqa: E402

OUT = HERE / "passB.json"
ROUNDTRIP = HERE / "bhv_unreal_roundtrip.fbx"


def lod_positions(mesh, lod):
    desc = mesh.get_static_mesh_description(lod)
    out = []
    n = int(desc.get_vertex_count())
    for i in range(n):
        vid = unreal.VertexID()
        try:
            vid.set_editor_property("id_value", i)
        except Exception:                                        # noqa: BLE001
            vid.set_editor_property("value", i)
        p = desc.get_vertex_position(vid)
        out.append([float(p.x), float(p.y), float(p.z)])
    return out


def tag(ad, name):
    try:
        return str(ad.get_tag_value(name))
    except Exception as exc:                                     # noqa: BLE001
        return f"<{type(exc).__name__}: {exc}>"[:120]


def mip_probe(tex):
    """Every zero-arg mip/size accessor on the texture, plus a few named attempts."""
    rec = {}
    for m in dir(tex):
        lm = m.lower()
        if m.startswith("_") or m.startswith("set_") or "force" in lm:
            continue
        if not any(w in lm for w in ("mip", "size", "resident", "platform")):
            continue
        attr = getattr(tex, m, None)
        if callable(attr):
            try:
                rec[m] = str(attr())[:200]
            except Exception as exc:                             # noqa: BLE001
                rec[m] = f"<{type(exc).__name__}: {exc}>"[:140]
        else:
            rec[m] = str(attr)[:200]
    return rec


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET, "hashes": C.all_hashes()}
    try:
        rep["asset_exists"] = bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))
        rep["dest_assets"] = [str(p) for p in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
        mesh = unreal.load_asset(C.ASSET)
        rep["is_static_mesh"] = isinstance(mesh, unreal.StaticMesh)
        rep["mesh"] = C.inspect_mesh(mesh, with_points=True)
        sub = C.sme()
        rep["collision_subsystem"] = {
            "convex_collision_count": C.safe(lambda: int(sub.get_convex_collision_count(mesh))),
            "simple_collision_count": C.safe(lambda: int(sub.get_simple_collision_count(mesh))),
            "collision_complexity": C.safe(lambda: str(sub.get_collision_complexity(mesh)))}
        rep["lod0_description_positions_cm"] = C.safe(lambda: lod_positions(mesh, 0))
        ad = unreal.EditorAssetLibrary.find_asset_data(C.ASSET)
        rep["mesh_tags"] = {t: tag(ad, t) for t in ("Triangles", "Vertices", "LODs", "UVChannels", "Materials",
                                                   "CollisionPrims", "ApproxSize", "NaniteEnabled", "DefaultCollision")}
        tex = {}
        for name in C.TEX_NAMES:
            p = f"{C.TEXDEST}/{name}"
            t = unreal.load_asset(p)
            if not isinstance(t, unreal.Texture2D):
                tex[name] = {"error": f"missing {p}"}
                continue
            d = C.inspect_texture(t)
            tad = unreal.EditorAssetLibrary.find_asset_data(p)
            d["tags"] = {k: tag(tad, k) for k in ("Dimensions", "Format", "NumMips", "SRGB", "CompressionSettings",
                                                  "LODGroup", "MipGenSettings", "AddressX", "AddressY")}
            d["mip_probe"] = mip_probe(t)
            tex[name] = d
        rep["textures"] = tex
        rep["unreal_mip_names"] = [n for n in dir(unreal) if "mip" in n.lower() or n.startswith("TextureExporter")
                                   or "TextureLibrary" in n]
        # the streaming manager's texture listing goes to the log; parsed afterwards
        unreal.log("BHV_LISTTEXTURES_BEGIN")
        unreal.SystemLibrary.execute_console_command(None, "ListTextures")
        unreal.log("BHV_LISTTEXTURES_END")

        try:
            v = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
            settings = unreal.ValidateAssetsSettings()
            settings.set_editor_property("validation_usecase", unreal.DataValidationUsecase.MANUAL)
            settings.set_editor_property("show_if_no_failures", True)
            data = [unreal.EditorAssetLibrary.find_asset_data(p) for p in
                    [C.ASSET] + [f"{C.TEXDEST}/{n}" for n in C.TEX_NAMES]]
            res = v.validate_assets_with_settings(data, settings)
            if isinstance(res, tuple):
                res = next((r for r in res if hasattr(r, "get_editor_property")), res[-1])

            def _n(name):
                try:
                    return int(res.get_editor_property(name))
                except Exception:                                # noqa: BLE001
                    return -1
            rep["validation"] = {k: _n(k) for k in ("num_checked", "num_valid", "num_invalid",
                                                    "num_warnings", "num_unable_to_validate")}
        except Exception:                                        # noqa: BLE001
            rep["validation_error"] = traceback.format_exc()[-800:]

        try:
            if ROUNDTRIP.exists():
                ROUNDTRIP.unlink()
            opt = unreal.FbxExportOption()
            opt.set_editor_property("collision", True)
            opt.set_editor_property("level_of_detail", True)
            opt.set_editor_property("vertex_color", False)
            opt.set_editor_property("ascii", False)
            task = unreal.AssetExportTask()
            task.set_editor_property("object", mesh)
            task.set_editor_property("filename", str(ROUNDTRIP))
            task.set_editor_property("automated", True)
            task.set_editor_property("prompt", False)
            task.set_editor_property("replace_identical", True)
            task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
            task.set_editor_property("options", opt)
            rep["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
            rep["export_bytes"] = ROUNDTRIP.stat().st_size if ROUNDTRIP.is_file() else 0
            rep["export_sha256"] = C.sha256(ROUNDTRIP) if ROUNDTRIP.is_file() else None
        except Exception:                                        # noqa: BLE001
            rep["export_error"] = traceback.format_exc()[-1500:]
    except Exception:                                            # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["hashes_after"] = C.all_hashes()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("BHV_PASSB_DONE " + str(OUT))


main()
