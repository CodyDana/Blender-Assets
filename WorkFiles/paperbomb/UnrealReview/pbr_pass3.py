"""PaperBomb review pass 3, in a third fresh process.

Three things, none of which touches the reviewed asset:

1. NAIVE TEXTURE IMPORT.  The four PNGs are imported into a brand-new content
   path with NOTHING applied afterwards, to measure what the UE 5.8.2
   TextureFactory does to the shipped bytes on its own - i.e. what a buyer gets
   when they drag the PNGs in.  (A re-import over an existing asset inherits the
   saved settings, so this must be a path that has never been written.)
2. SOCKET AXES from Unreal's own rotator maths, not from hand-rolled trig.
3. RE-EXPORT the saved asset to FBX with LODs and Collision ON, so the convex
   hull's real geometry - unreadable from Python - can be compared in Blender.
"""
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealReview")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import pbr_common as C  # noqa: E402
import pbr_textures as T  # noqa: E402

OUT = HERE / "pbr_pass3.json"
FBX_OUT = HERE / "roundtrip" / f"{C.MESH}_from_unreal.fbx"
NAIVE_DEST = os.environ.get("PB_NAIVE_DEST", "/Game/PropsCheck/PaperBombNaive01/Textures")


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "naive_dest": NAIVE_DEST, "fbx_out": str(FBX_OUT)}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")

    # ---- 1. what the TextureFactory does on its own ----
    report["naive_texture_import"] = {}
    for stem in C.TEXTURES:
        entry = {"kind": T.kind_of(stem)}
        try:
            existed = unreal.EditorAssetLibrary.does_asset_exist(f"{NAIVE_DEST}/{stem}")
            entry["asset_existed_before"] = bool(existed)
            _paths, texs = T.import_one(C.TEXDIR / f"{stem}.png", stem, NAIVE_DEST)
            if texs:
                entry["flags"] = T.inspect(texs[0])
                entry["matches_intent"] = T.matches(entry["flags"], entry["kind"])
            else:
                entry["error"] = "no Texture2D produced"
        except Exception:
            entry["error"] = traceback.format_exc()
        report["naive_texture_import"][stem] = entry
    report["naive_all_correct_without_fixups"] = all(
        (e.get("matches_intent") or {}).get("all") and e.get("asset_existed_before") is False
        for e in report["naive_texture_import"].values())

    # ---- 2 and 3. the reviewed asset ----
    try:
        mesh = unreal.load_asset(C.ASSET)

        axes = {}
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        for name in comp.get_all_socket_names():
            s = mesh.find_socket(str(name))
            rot = s.get_editor_property("relative_rotation")
            axes[str(name)] = {
                "rotator_roll_pitch_yaw": [round(rot.roll, 4), round(rot.pitch, 4), round(rot.yaw, 4)],
                "forward_plus_X": C.vec(unreal.MathLibrary.get_forward_vector(rot), 4),
                "right_plus_Y": C.vec(unreal.MathLibrary.get_right_vector(rot), 4),
                "up_plus_Z": C.vec(unreal.MathLibrary.get_up_vector(rot), 4),
            }
        report["socket_axes_from_unreal_math"] = axes

        FBX_OUT.parent.mkdir(parents=True, exist_ok=True)
        opts = unreal.FbxExportOption()
        for key, val in (("ascii", False), ("force_front_x_axis", False), ("level_of_detail", True),
                         ("collision", True), ("vertex_color", False)):
            try:
                opts.set_editor_property(key, val)
            except Exception as exc:  # noqa: BLE001
                report.setdefault("option_errors", {})[key] = str(exc)[:160]
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(FBX_OUT))
        task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        task.set_editor_property("options", opts)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        report["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
        report["fbx_exists"] = FBX_OUT.exists()
        report["fbx_bytes"] = FBX_OUT.stat().st_size if FBX_OUT.exists() else 0
    except Exception:
        report["error"] = traceback.format_exc()

    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PBR_PASS3_DONE " + str(OUT))


main()
