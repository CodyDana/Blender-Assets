"""PaperBomb review pass 2: load the SAVED asset in a FRESH process and gate it.

Nothing is imported or written to any asset here.  Every expectation comes from
the study and from the independent Blender re-import of the shipped FBX bytes.
Also re-reads the four textures' flags from the SAVED texture assets - an
in-process read in the writing process cannot tell a persisted flag from a
transient one.
"""
import json
import math
import re
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealReview")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import pbr_common as C  # noqa: E402
import pbr_textures as T  # noqa: E402

OUT = HERE / "pbr_pass2.json"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR),
              "texture_sha256": {s: C.sha256(C.TEXDIR / f"{s}.png") for s in C.TEXTURES}}
    try:
        rel = C.DEST[len("/Game/"):]
        uasset = Path(unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_content_dir())) / rel / f"{C.MESH}.uasset"
        report["uasset_on_disk"] = str(uasset)
        report["uasset_exists"] = uasset.exists()

        mesh = unreal.load_asset(C.ASSET)
        info = C.inspect(mesh)
        report.update(info)

        # which StaticMesh properties this engine even exposes for screen size / auto LOD
        doc = unreal.StaticMesh.__doc__ or ""
        names = sorted(set(re.findall(r"``(\w*(?:screen|auto|lod)\w*)``", doc, re.I)))
        report["staticmesh_props_matching_screen_auto_lod"] = names
        vals = {}
        for name in names:
            try:
                vals[name] = str(mesh.get_editor_property(name))
            except Exception as exc:  # noqa: BLE001
                vals[name] = f"<{type(exc).__name__}: {exc}>"[:120]
        report["prop_values"] = vals

        textures = T.verify(C.TEX_DEST, C.TEXTURES)
        report["textures"] = textures

        g, detail = C.gates(info, textures)
        report["gates"] = g
        report["gate_detail"] = detail

        # ---- legibility at the switch distances, from the asset's own bounds ----
        R_mm = info["bounds_radius_mm"]
        leg = {}
        for i, S in enumerate(info["lod_screen_sizes"][1:], start=1):
            px_per_mm_1080 = S * 1080.0 / (2.0 * R_mm)
            leg[f"LOD{i}_switch"] = {
                "screen_size": round(S, 6),
                "distance_m": round(C.screen_size_distance_m(S, R_mm / 1000.0), 4),
                "px_per_mm_at_1080p": round(px_per_mm_1080, 4),
                "card_on_screen_px": [round(info["size_cm"][1] * 10.0 * px_per_mm_1080, 1),
                                      round(info["size_cm"][0] * 10.0 * px_per_mm_1080, 1)],
            }
        report["legibility_projection"] = leg

        # ---- LOD0 vertex positions against the shipped FBX ----
        try:
            ue_lod0 = C.lod_positions_cm(mesh, 0)
            report["lod0_vertex_count_unreal"] = len(ue_lod0)
            report["lod0_vertex_count_fbx"] = len(C.LOD0_VERTS_FBX)
            report["lod0_two_sided_max_cm_vs_fbx"] = round(
                C.two_sided_max(ue_lod0, [tuple(v) for v in C.LOD0_VERTS_FBX]), 8)
            mirrored = [(x, -y, z) for x, y, z in C.LOD0_VERTS_FBX]
            report["lod0_two_sided_max_cm_if_mirrored"] = round(C.two_sided_max(ue_lod0, mirrored), 6)
        except Exception as exc:  # noqa: BLE001
            report["lod0_positions_error"] = f"{type(exc).__name__}: {exc}"[:300]

        report["all_gates_passed"] = all(g.values())
    except Exception:
        report["error"] = traceback.format_exc()
        report["all_gates_passed"] = False
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PBR_PASS2_DONE " + str(OUT))


main()
