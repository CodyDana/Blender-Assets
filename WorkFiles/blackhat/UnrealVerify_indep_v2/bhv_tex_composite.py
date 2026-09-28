"""Texture step 2 (independent copy of the build's bhu_tex_composite.py step, pointed at THIS
verifier's content path): each ORM names its part's N as its Composite Texture, mode
CTM_NormalRoughnessToGreen, power 1.0 (the sidecar's orm_texture_settings), and saves.
Runs in its own fresh process after the props importer; pass B re-reads it in another."""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v2")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import bhv_common as C                                          # noqa: E402

OUT = HERE / "tex_composite.json"


def main():
    side = json.loads(C.SIDECAR.read_text(encoding="utf-8"))
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "maps": {}}
    ok = True
    try:
        for mat, rec in side["materials"].items():
            ots = rec["orm_texture_settings"]
            orm_name = rec["textures"]["ORM"]
            n_name = ots["composite_texture"]
            orm = unreal.load_asset(f"{C.TEXDEST}/{orm_name}")
            nrm = unreal.load_asset(f"{C.TEXDEST}/{n_name}")
            if orm is None or nrm is None:
                report["maps"][orm_name] = {"error": "ORM or N did not load"}
                ok = False
                continue
            mode = getattr(unreal.CompositeTextureMode, ots["composite_texture_mode"])
            orm.set_editor_property("composite_texture", nrm)
            orm.set_editor_property("composite_texture_mode", mode)
            orm.set_editor_property("composite_power", float(ots["composite_power"]))
            saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(orm, only_if_is_dirty=False))
            report["maps"][orm_name] = {
                "sidecar": ots,
                "composite_texture": str(orm.get_editor_property("composite_texture").get_path_name()),
                "composite_texture_mode": str(orm.get_editor_property("composite_texture_mode")),
                "composite_power": float(orm.get_editor_property("composite_power")),
                "saved": saved}
            ok = ok and saved
    except Exception:                                            # noqa: BLE001
        report["error"] = traceback.format_exc()
        ok = False
    report["passed"] = ok
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("BHV_TEX_COMPOSITE_DONE " + str(OUT))


main()
