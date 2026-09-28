"""UnrealCheck7 pass 4: import the nine baked maps through unreal.AssetImportTask and record their flags.

Two copies of every map are imported so the verdict separates "what the importer does by itself"
from "what the asset looks like after the flags are set":

  <DEST>/TexturesRaw/    plain AssetImportTask (factory auto-detected -> TextureFactory), nothing touched
  <DEST>/TexturesFixed/  the same import, then srgb / compression set to the pack's intent and saved:
                         BC  -> srgb True,  TC_DEFAULT
                         ORM -> srgb False, TC_MASKS
                         N   -> srgb False, TC_NORMALMAP, flip_green_channel False (DirectX on disk)

In-process reads are recorded but are NOT the gate: pass 5 re-reads both folders in a fresh process.
Records the SHA-256 of each PNG it imported. Writes textures_pass4.json next to this file.
"""
import hashlib
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck7")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc7_textures as T  # noqa: E402

OUT = HERE / "textures_pass4.json"


def import_one(png, dest, name):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    factory = task.get_editor_property("factory")
    return paths, (factory.get_class().get_name() if factory else None)


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": T.DEST, "maps": {}}
    try:
        for stem, png in T.PNGS.items():
            rec = {"png": str(png), "sha256": hashlib.sha256(png.read_bytes()).hexdigest(), "kind": T.kind_of(stem)}
            for variant in ("Raw", "Fixed"):
                dest = f"{T.DEST}/Textures{variant}"
                paths, factory = import_one(png, dest, stem)
                entry = {"imported_object_paths": paths, "factory": factory}
                tex = unreal.load_asset(f"{dest}/{stem}") if paths else None
                if tex is None:
                    entry["error"] = "no texture imported"
                else:
                    entry["as_imported"] = T.inspect(tex)
                    if variant == "Fixed":
                        entry["applied"] = T.apply_intent(tex)
                        entry["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
                        entry["after_fix_in_process_not_authoritative"] = T.inspect(tex)
                rec[variant] = entry
            report["maps"][stem] = rec
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS4_DONE " + str(OUT))


main()
