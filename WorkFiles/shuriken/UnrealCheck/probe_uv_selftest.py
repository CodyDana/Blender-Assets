"""Probe 3: is get_num_uv_channels telling the truth, and did the lightmap
generator actually run?

Probe 2 got 1 UV channel from a *constructed* StaticMeshEditorSubsystem while
light_map_coordinate_index says 1 (which would need 2 channels). Guidelines 6.5
says a constructed/duplicated helper result is not trustworthy until it is
re-run with a matched control, so this script self-tests the reader: add a UV
channel to a throwaway duplicate and confirm the count moves 1 -> 2. If it does,
the reader is live and "1 channel" on the shipped mesh is a real answer.

Also reads the per-LOD MeshBuildSettings, which record whether Generate Lightmap
UVs was on for the build and where it was told to write.
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\uv_selftest.json")
SHIPPED = "/Game/ShurikenCheck/SM_Shuriken_FourPoint"
SCRATCH = "/Game/ShurikenCheck/Scratch/SM_UVSelfTest"


def try_(out, label, fn):
    try:
        out[label] = fn()
    except Exception as exc:  # noqa: BLE001
        out[label] = f"UNAVAILABLE {type(exc).__name__}: {exc}"[:300]


def build_settings(sub, mesh, n):
    rows = []
    for i in range(n):
        b = sub.get_lod_build_settings(mesh, i)
        rows.append({
            "lod": i,
            "generate_lightmap_uvs": bool(b.get_editor_property("generate_lightmap_u_vs")),
            "src_lightmap_index": b.get_editor_property("src_lightmap_index"),
            "dst_lightmap_index": b.get_editor_property("dst_lightmap_index"),
            "min_lightmap_resolution": b.get_editor_property("min_lightmap_resolution"),
            "remove_degenerates": bool(b.get_editor_property("remove_degenerates")),
            "recompute_normals": bool(b.get_editor_property("recompute_normals")),
            "recompute_tangents": bool(b.get_editor_property("recompute_tangents")),
            "use_mikk_t_space": bool(b.get_editor_property("use_mikk_t_space")),
            "use_full_precision_uvs": bool(b.get_editor_property("use_full_precision_u_vs")),
        })
    return rows


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
        shipped = unreal.load_asset(SHIPPED)
        n = shipped.get_num_lods()
        out["shipped_uv_channels"] = [sub.get_num_uv_channels(shipped, i) for i in range(n)]
        out["shipped_light_map_coordinate_index"] = shipped.get_editor_property("light_map_coordinate_index")
        try_(out, "shipped_build_settings", lambda: build_settings(sub, shipped, n))

        control = unreal.load_asset("/Game/ShurikenCheck/Control/SM_Shuriken_FourPoint_NoLightmapUV")
        if isinstance(control, unreal.StaticMesh):
            out["control_uv_channels"] = [sub.get_num_uv_channels(control, i) for i in range(control.get_num_lods())]
            out["control_light_map_coordinate_index"] = control.get_editor_property("light_map_coordinate_index")
            try_(out, "control_build_settings", lambda: build_settings(sub, control, control.get_num_lods()))
        else:
            out["control_uv_channels"] = "control asset not present (it was imported unsaved in probe 2)"

        # SELF-TEST of the reader: duplicate, add a UV channel, re-read.
        dup = unreal.EditorAssetLibrary.duplicate_asset(SHIPPED, SCRATCH)
        if isinstance(dup, unreal.StaticMesh):
            before = sub.get_num_uv_channels(dup, 0)
            added = sub.add_uv_channel(dup, 0)
            after = sub.get_num_uv_channels(dup, 0)
            out["selftest"] = {"before": before, "add_uv_channel_returned": bool(added), "after": after,
                               "reader_is_live": bool(added) and after == before + 1}
            unreal.EditorAssetLibrary.delete_asset(SCRATCH)
        else:
            out["selftest"] = "duplicate failed"

        # Deprecated library, for the record
        try_(out, "EditorStaticMeshLibrary_uv_channels",
             lambda: [unreal.EditorStaticMeshLibrary.get_num_uv_channels(shipped, i) for i in range(n)])
        try_(out, "get_editor_subsystem_is_none",
             lambda: unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) is None)
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_UVSELFTEST " + json.dumps(out, default=str)[:4000])


if __name__ == "__main__":
    main()
