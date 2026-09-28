"""UnrealCheck7 pass 5: re-read the SAVED textures of pass 4 in a FRESH process and gate their flags.

Nothing is imported or written to any asset here. For each of the nine maps and both folders
(TexturesRaw = importer defaults, TexturesFixed = intent applied) it records srgb, compression,
flip_green_channel, size and source format, and whether they equal the pack's intent
(BC sRGB / TC_Default; ORM linear / TC_Masks; N linear / TC_Normalmap, green not flipped).
Writes textures_pass5.json next to this file.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck7")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc7_textures as T  # noqa: E402

OUT = HERE / "textures_pass5.json"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": T.DEST, "maps": {}}
    try:
        content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
        rel = T.DEST[len("/Game/"):]
        for stem in T.PNGS:
            kind = T.kind_of(stem)
            rec = {"kind": kind}
            for variant in ("Raw", "Fixed"):
                path = f"{T.DEST}/Textures{variant}/{stem}"
                entry = {"asset": path, "uasset_exists": (content / rel / f"Textures{variant}" / f"{stem}.uasset").exists()}
                tex = unreal.load_asset(path)
                if tex is None:
                    entry["error"] = "load_asset returned None"
                    entry["matches_intent"] = {"all": False}
                else:
                    info = T.inspect(tex)
                    entry.update(info)
                    entry["matches_intent"] = T.flags_match_intent(info, kind)
                    entry["size_2048_pot"] = info.get("size") == [2048, 2048]
                rec[variant] = entry
            report["maps"][stem] = rec
        report["raw_import_all_match_intent"] = all(m["Raw"]["matches_intent"]["all"] for m in report["maps"].values())
        report["fixed_all_match_intent"] = all(m["Fixed"]["matches_intent"]["all"] for m in report["maps"].values())
        report["all_2048"] = all(m[v].get("size_2048_pot") for m in report["maps"].values() for v in ("Raw", "Fixed"))
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS5_DONE " + str(OUT))


main()
