"""Probe 5: read the render-data UV channel count the only way 5.8.2 exposes it.

Probe 4's .uasset size test was INVALID: an uncooked StaticMesh package stores
the source MeshDescription, while the built render data lives in the DDC, so the
two packages were always going to be the same size. Discard that verdict.

UStaticMesh::GetAssetRegistryTags publishes "UVChannels" (and Triangles,
Vertices, CollisionPrims, LODs) from RenderData->LODResources[0], so the asset
registry is a genuine render-data readout. Read it both for the loaded object
(tags recomputed in memory) and for the on-disk record, on the shipped asset and
on the matched lightmap-on / lightmap-off pair from probe 4.
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\uv_registry.json")
TARGETS = {
    "shipped": "/Game/ShurikenCheck/SM_Shuriken_FourPoint",
    "lm_on": "/Game/ShurikenCheck/LMProbe/SM_LM_On",
    "lm_off": "/Game/ShurikenCheck/LMProbe/SM_LM_Off",
}
TAGS = ["UVChannels", "Triangles", "Vertices", "Materials", "LODs", "CollisionPrims",
        "ApproxSize", "MinLOD", "NaniteEnabled", "SectionsWithCollision"]


def tags_for(ar, path, on_disk):
    try:
        data = ar.get_asset_by_object_path(unreal.SoftObjectPath(f"{path}.{path.rsplit('/', 1)[-1]}"),
                                           include_only_on_disk_assets=on_disk)
    except TypeError:
        data = ar.get_asset_by_object_path(f"{path}.{path.rsplit('/', 1)[-1]}",
                                           include_only_on_disk_assets=on_disk)
    if not data or not data.is_valid():
        return {"error": "no asset data"}
    out = {}
    for t in TAGS:
        try:
            v = data.get_tag_value(t)
        except Exception as exc:  # noqa: BLE001
            v = f"UNAVAILABLE {type(exc).__name__}"
        out[t] = str(v) if v is not None else None
    return out


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version(), "assets": {}}
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        ar.wait_for_completion()
        for key, path in TARGETS.items():
            mesh = unreal.load_asset(path)
            entry = {"path": path, "loaded": isinstance(mesh, unreal.StaticMesh)}
            if entry["loaded"]:
                entry["light_map_coordinate_index"] = mesh.get_editor_property("light_map_coordinate_index")
                entry["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(mesh.get_num_lods())]
                entry["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]
            entry["tags_in_memory"] = tags_for(ar, path, False)
            entry["tags_on_disk"] = tags_for(ar, path, True)
            out["assets"][key] = entry
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_UVREG " + json.dumps(out, default=str)[:4000])


if __name__ == "__main__":
    main()
