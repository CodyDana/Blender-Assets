"""PASS B (a SECOND fresh process, -nullrhi): read everything back off disk WITHOUT importing anything.

Meshes: LOD count / triangles / vertices / sections / slots, screen sizes, lightmap, Nanite, import data, hull
elements with their points, every LOD's vertex positions (for the offline convexity / containment analysis), sockets.
Textures: flags + registry tags.  Editor data validation on every asset.  Nothing is saved.
"""
import json
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import sv_common as C  # noqa: E402

OUT = HERE / "passB.json"
TAGS = ("Dimensions", "Format", "HasAlphaChannel", "NumMips", "SRGB", "CompressionSettings", "LODGroup",
        "MipGenSettings", "NeverStream", "SourceFormat", "PowerOfTwoMode", "MaxTextureSize")
rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "hashes": C.all_hashes(),
       "meshes": {}, "textures": {}}
points = {}
try:
    rep["dest_assets"] = [str(p) for p in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
    for name in C.MESHES:
        mesh = unreal.load_asset(f"{C.DEST}/{name}")
        if not isinstance(mesh, unreal.StaticMesh):
            rep["meshes"][name] = {"error": "did not load"}
            continue
        info = C.inspect_mesh(mesh, with_points=True)
        points[name] = {"hulls": [{"points_cm": h.get("points_cm"), "indices": h.get("indices"),
                                   "transform": h.get("transform")} for h in info.get("convex_elems", [])],
                        "lods": [C.lod_positions(mesh, i) for i in range(info["num_lods"])]}
        for h in info.get("convex_elems", []):
            h.pop("points_cm", None)
            h.pop("indices", None)
        sub = C.sme()
        info["collision_subsystem"] = {
            "convex_collision_count": C.safe(lambda: int(sub.get_convex_collision_count(mesh))),
            "simple_collision_count": C.safe(lambda: int(sub.get_simple_collision_count(mesh))),
            "collision_complexity": C.safe(lambda: str(sub.get_collision_complexity(mesh)))}
        ad = unreal.EditorAssetLibrary.find_asset_data(f"{C.DEST}/{name}")
        info["registry_tags"] = {t: C.safe(lambda t=t: str(ad.get_tag_value(t))) for t in
                                 ("Triangles", "Vertices", "LODs", "UVChannels", "Materials", "CollisionPrims",
                                  "NaniteEnabled", "DefaultCollision", "ApproxSize")}
        # Tip socket vs the max-X vertex of LOD0 (engine frame)
        L0 = points[name]["lods"][0]
        mx = max(L0, key=lambda p: p[0])
        mn = min(L0, key=lambda p: p[0])
        info["lod0_max_x_vertex_cm"] = [round(v, 6) for v in mx]
        info["lod0_min_x_vertex_cm"] = [round(v, 6) for v in mn]
        rep["meshes"][name] = info
    for tname in C.TEXTURES:
        p = f"{C.TEXDEST}/{tname}"
        t = unreal.load_asset(p)
        if not isinstance(t, unreal.Texture2D):
            rep["textures"][tname] = {"error": f"missing {p}"}
            continue
        d = C.inspect_texture(t)
        ad = unreal.EditorAssetLibrary.find_asset_data(p)
        d["tags"] = {k: C.safe(lambda k=k: str(ad.get_tag_value(k))) for k in TAGS}
        d["matches_readme"] = C.flags_match(d, C.TEXTURES[tname][1])
        rep["textures"][tname] = d
    try:
        v = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
        settings = unreal.ValidateAssetsSettings()
        settings.set_editor_property("validation_usecase", unreal.DataValidationUsecase.MANUAL)
        settings.set_editor_property("show_if_no_failures", True)
        data = [unreal.EditorAssetLibrary.find_asset_data(f"{C.DEST}/{n}") for n in C.MESHES] + \
               [unreal.EditorAssetLibrary.find_asset_data(f"{C.TEXDEST}/{n}") for n in C.TEXTURES]
        unreal.log("SV_VALIDATE_BEGIN")
        res = v.validate_assets_with_settings(data, settings)
        unreal.log("SV_VALIDATE_END")
        if isinstance(res, tuple):
            res = next((r for r in res if hasattr(r, "get_editor_property")), res[-1])
        rep["validation"] = {k: C.safe(lambda k=k: int(res.get_editor_property(k))) for k in
                             ("num_checked", "num_valid", "num_invalid", "num_warnings", "num_unable_to_validate")}
    except Exception:  # noqa: BLE001
        rep["validation_error"] = traceback.format_exc()[-800:]
except Exception:  # noqa: BLE001
    rep["error"] = traceback.format_exc()
OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
(HERE / "passB_points.json").write_text(json.dumps(points), encoding="utf-8")
unreal.log("SV_PASSB_DONE")
