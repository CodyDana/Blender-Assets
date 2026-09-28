"""Probe: how many UV channels did the imported mesh end up with, and did
Generate Lightmap UVs actually run? Fresh process, reads the saved asset only.

StaticMesh has no get_num_uv_channels on 5.8.2, so this tries every route and
records which ones work (ASSET_GUIDELINES 6.5: subsystems fail silently under
-run=pythonscript, so record the failure rather than assuming a number).
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\uv_probe.json")
ASSET = "/Game/ShurikenCheck/SM_Shuriken_FourPoint"


def try_(label, fn, out):
    try:
        out[label] = fn()
    except Exception as exc:  # noqa: BLE001
        out[label] = f"UNAVAILABLE {type(exc).__name__}: {exc}"[:300]


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": ASSET}
    try:
        mesh = unreal.load_asset(ASSET)
        n = mesh.get_num_lods()
        out["num_lods"] = n

        sub = None
        try_("subsystem", lambda: str(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)), out)
        try:
            sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        except Exception:  # noqa: BLE001
            sub = None
        out["subsystem_is_none"] = sub is None

        if sub is not None:
            try_("subsystem_uv_channels",
                 lambda: [sub.get_num_uv_channels(mesh, i) for i in range(n)], out)
            def build_settings():
                rows = []
                for i in range(n):
                    b = sub.get_lod_build_settings(mesh, i)
                    rows.append({
                        "lod": i,
                        "generate_lightmap_uvs": bool(b.get_editor_property("generate_lightmap_u_vs")),
                        "src_lightmap_index": b.get_editor_property("src_lightmap_index"),
                        "dst_lightmap_index": b.get_editor_property("dst_lightmap_index"),
                        "min_lightmap_resolution": b.get_editor_property("min_lightmap_resolution"),
                        "recompute_normals": bool(b.get_editor_property("recompute_normals")),
                        "recompute_tangents": bool(b.get_editor_property("recompute_tangents")),
                        "use_mikk_t_space": bool(b.get_editor_property("use_mikk_t_space")),
                        "remove_degenerates": bool(b.get_editor_property("remove_degenerates")),
                        "build_scale3d": [b.get_editor_property("build_scale3d").x,
                                          b.get_editor_property("build_scale3d").y,
                                          b.get_editor_property("build_scale3d").z],
                    })
                return rows
            try_("lod_build_settings", build_settings, out)
            try_("subsystem_lod_count", lambda: sub.get_lod_count(mesh), out)
            try_("subsystem_convex_count", lambda: sub.get_convex_collision_count(mesh), out)
            try_("subsystem_simple_collision_count", lambda: sub.get_simple_collision_count(mesh), out)

        try_("EditorStaticMeshLibrary_uv_channels",
             lambda: [unreal.EditorStaticMeshLibrary.get_num_uv_channels(mesh, i) for i in range(n)], out)
        try_("source_models",
             lambda: len(mesh.get_editor_property("source_models")), out)

        # Actual UV0 data via ProceduralMeshLibrary (single channel only, but it proves
        # the mesh section is readable and the UVs are real numbers).
        def uv0_stats():
            verts, tris, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
            us = [v.x for v in uvs]
            vs = [v.y for v in uvs]
            return {"section_verts": len(verts), "section_tris": len(tris) // 3,
                    "uv0_count": len(uvs),
                    "uv0_u_range": [round(min(us), 4), round(max(us), 4)],
                    "uv0_v_range": [round(min(vs), 4), round(max(vs), 4)]}
        try_("uv0_stats", uv0_stats, out)

        out["light_map_coordinate_index"] = mesh.get_editor_property("light_map_coordinate_index")
        out["light_map_resolution"] = mesh.get_editor_property("light_map_resolution")
        try_("lod_screen_sizes",
             lambda: [float(sub.get_lod_screen_sizes(mesh)[i]) for i in range(n)] if sub else "no subsystem", out)
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_UVPROBE " + json.dumps(out, default=str)[:4000])


if __name__ == "__main__":
    main()
