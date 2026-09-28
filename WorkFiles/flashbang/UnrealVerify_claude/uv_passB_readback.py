"""PASS B (a SECOND fresh process, -nullrhi): read everything back off disk WITHOUT importing.

Meshes (LODs, triangles, screen sizes, hull points, sockets, lightmap, slots), texture flags + registry tags, the
editor validator, engine-side assembly identity of the part meshes at their sockets, and the lever's +pitch opening.
Hull points and LOD0 positions are written out for the offline convexity / containment analysis.
"""
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealVerify_claude")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import uv_common as C  # noqa: E402

OUT = HERE / "passB.json"
TAGS = ("Dimensions", "Format", "HasAlphaChannel", "NumMips", "SRGB", "CompressionSettings", "LODGroup",
        "MipGenSettings", "NeverStream", "SourceFormat", "PowerOfTwoMode", "MaxTextureSize")
rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "hashes": C.all_hashes(),
       "meshes": {}, "textures": {}}
points = {}
try:
    rep["dest_assets"] = [str(p) for p in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
    loaded = {}
    for name in C.MESHES:
        mesh = unreal.load_asset(f"{C.DEST}/{name}")
        if not isinstance(mesh, unreal.StaticMesh):
            rep["meshes"][name] = {"error": "did not load"}
            continue
        loaded[name] = mesh
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
    # editor data validation on every asset
    try:
        v = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
        settings = unreal.ValidateAssetsSettings()
        settings.set_editor_property("validation_usecase", unreal.DataValidationUsecase.MANUAL)
        settings.set_editor_property("show_if_no_failures", True)
        data = [unreal.EditorAssetLibrary.find_asset_data(f"{C.DEST}/{n}") for n in C.MESHES] + \
               [unreal.EditorAssetLibrary.find_asset_data(f"{C.TEXDEST}/{n}") for n in C.TEXTURES]
        res = v.validate_assets_with_settings(data, settings)
        if isinstance(res, tuple):
            res = next((r for r in res if hasattr(r, "get_editor_property")), res[-1])
        rep["validation"] = {k: C.safe(lambda k=k: int(res.get_editor_property(k))) for k in
                             ("num_checked", "num_valid", "num_invalid", "num_warnings", "num_unable_to_validate")}
    except Exception:  # noqa: BLE001
        rep["validation_error"] = traceback.format_exc()[-800:]
    # engine-side assembly identity: Body + parts at their sockets vs the assembled mesh, every LOD
    if len(loaded) == 4:
        asm = {}
        for host in ("SM_Flashbang", "SM_Flashbang_Body"):
            comp = unreal.new_object(unreal.StaticMeshComponent)
            comp.set_static_mesh(loaded[host])
            per = {}
            for part, sock in (("SM_Flashbang_PullRing", "Pin"), ("SM_Flashbang_Lever", "LeverHinge")):
                T = comp.get_socket_transform(sock, unreal.RelativeTransformSpace.RTS_COMPONENT)
                lods = []
                for lod in range(3):
                    A = points["SM_Flashbang"]["lods"][lod]
                    worst = 0.0
                    for p in points[part]["lods"][lod]:
                        w = T.transform_location(unreal.Vector(*p))
                        d = min((w.x - a[0]) ** 2 + (w.y - a[1]) ** 2 + (w.z - a[2]) ** 2 for a in A)
                        worst = max(worst, d)
                    lods.append(round(math.sqrt(worst), 7))
                per[part] = {"socket": sock, "worst_cm_per_lod": lods,
                             "socket_T": {"t": C.vec(T.translation), "rpy": [T.rotation.rotator().roll,
                                                                              T.rotation.rotator().pitch,
                                                                              T.rotation.rotator().yaw]}}
            asm[host] = per
        rep["assembly_identity"] = asm
        # body verts must all appear in the assembled mesh (LOD0)
        A = points["SM_Flashbang"]["lods"][0]
        Aset = {(round(a[0], 3), round(a[1], 3), round(a[2], 3)) for a in A}
        B = points["SM_Flashbang_Body"]["lods"][0]
        rep["body_in_assembled_lod0"] = {"body_verts": len(B), "exact_matches_1e-3cm": sum(
            (round(b[0], 3), round(b[1], 3), round(b[2], 3)) in Aset for b in B)}
        # lever opening: +100 pitch about the LeverHinge frame; the tip (lowest lever vertex) must move outward (+X)
        L = points["SM_Flashbang_Lever"]["lods"][0]
        tip = min(L, key=lambda p: p[2])
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(loaded["SM_Flashbang_Body"])
        T = comp.get_socket_transform("LeverHinge", unreal.RelativeTransformSpace.RTS_COMPONENT)
        closed = T.transform_location(unreal.Vector(*tip))
        opened_local = unreal.Rotator(roll=0.0, pitch=100.0, yaw=0.0).quaternion().rotate_vector(unreal.Vector(*tip))
        opened = T.transform_location(opened_local)
        rep["lever_open"] = {"tip_local_cm": tip, "closed_component_cm": C.vec(closed),
                             "open_component_cm": C.vec(opened), "outward": bool(opened.x > closed.x + 5.0)}
        # pin pull: move the ring along socket +X by pin_travel; it must leave the body's bounds sideways (away)
        side = C.sidecar("SM_Flashbang")
        trav = side["parts"]["PullRing"]["pin_travel_mm"] / 10.0
        Tp = comp.get_socket_transform("Pin", unreal.RelativeTransformSpace.RTS_COMPONENT)
        ax = Tp.rotation.rotate_vector(unreal.Vector(1, 0, 0))
        rep["pin_pull_axis_component"] = C.vec(ax)
        rep["pin_travel_cm"] = trav
except Exception:  # noqa: BLE001
    rep["error"] = traceback.format_exc()
OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
(HERE / "passB_points.json").write_text(json.dumps(points), encoding="utf-8")
unreal.log("UV_PASSB_DONE")
