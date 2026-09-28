"""Texture step 2 (final pass, 2026-09-26): each ORM names its part's N as its Composite Texture,
mode CTM_NormalRoughnessToGreen, so Unreal widens ORM.G (roughness) per mip by the normal map's
variance (Toksvig).  This is the weave's anti-shimmer at distance; the sidecar records it for
buyers ("orm_texture_settings").  Runs after the props importer, in its own fresh process, and
saves; pass 2 re-reads it from the saved packages in another fresh process.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealCheck")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import bhu_common as C                                          # noqa: E402

OUT = C.HERE / "tex_composite.json"
STEMS = ("T_BlackHat_Straw", "T_BlackHat_Cloth")


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "maps": {}}
    ok = True
    try:
        mode = unreal.CompositeTextureMode.CTM_NORMAL_ROUGHNESS_TO_GREEN
        for stem in STEMS:
            orm = unreal.load_asset(f"{C.TEXTURE_DEST}/{stem}_ORM")
            nrm = unreal.load_asset(f"{C.TEXTURE_DEST}/{stem}_N")
            if orm is None or nrm is None:
                report["maps"][stem] = {"error": "ORM or N did not load"}
                ok = False
                continue
            orm.set_editor_property("composite_texture", nrm)
            orm.set_editor_property("composite_texture_mode", mode)
            orm.set_editor_property("composite_power", 1.0)
            saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(orm, only_if_is_dirty=False))
            report["maps"][stem] = {
                "composite_texture": str(orm.get_editor_property("composite_texture").get_path_name()),
                "composite_texture_mode": str(orm.get_editor_property("composite_texture_mode")),
                "composite_power": float(orm.get_editor_property("composite_power")),
                "saved": saved}
            ok = ok and saved
    except Exception:
        report["error"] = traceback.format_exc()
        ok = False
    report["passed"] = ok
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("BHU_TEX_COMPOSITE_DONE " + str(OUT))


main()
