"""Probe 6: LOD screen sizes and a cross-check of the collision count.

The constructed StaticMeshEditorSubsystem proved live in probe 3 (the UV reader
self-test moved 1 -> 2), so use it for the numbers get_editor_subsystem cannot
supply under -run=pythonscript.
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\lod_screensizes.json")
ASSET = "/Game/ShurikenCheck/SM_Shuriken_FourPoint"


def try_(out, label, fn):
    try:
        out[label] = fn()
    except Exception as exc:  # noqa: BLE001
        out[label] = f"UNAVAILABLE {type(exc).__name__}: {exc}"[:240]


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": ASSET}
    try:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
        mesh = unreal.load_asset(ASSET)
        n = mesh.get_num_lods()
        out["num_lods"] = n
        try_(out, "lod_screen_sizes", lambda: [round(float(v), 5) for v in sub.get_lod_screen_sizes(mesh)])
        try_(out, "subsystem_lod_count", lambda: sub.get_lod_count(mesh))
        try_(out, "subsystem_convex_collision_count", lambda: sub.get_convex_collision_count(mesh))
        try_(out, "subsystem_simple_collision_count", lambda: sub.get_simple_collision_count(mesh))
        try_(out, "subsystem_collision_complexity", lambda: str(sub.get_collision_complexity(mesh)))
        try_(out, "lod_group_setting", lambda: str(mesh.get_editor_property("lod_group")))
        try_(out, "min_lod", lambda: str(mesh.get_editor_property("min_lod")))
        try_(out, "auto_lod_screen_sizes",
             lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
        try_(out, "num_sections", lambda: [mesh.get_num_sections(i) for i in range(n)])
        try_(out, "body_setup_convex",
             lambda: len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
                         .get_editor_property("convex_elems")))
        try_(out, "distance_field_replace_mesh",
             lambda: str(mesh.get_editor_property("distance_field_replacement_mesh")))
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_LODSS " + json.dumps(out, default=str)[:3000])


if __name__ == "__main__":
    main()
