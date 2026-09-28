"""PASS C (fresh process) - try to read the BUILT mip count of each saved texture (read-only; never saves).

nullrhi leaves platform data uncompiled in pass B (ListTextures: PF_Unknown, NumMips 0).  Here:
synchronous texture compilation, then ListTextures again.  Nothing is saved.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v2")
sys.path.insert(0, str(HERE))

import unreal                                                    # noqa: E402
import bhv_common as C                                           # noqa: E402

OUT = HERE / "passC.json"


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "hashes": C.all_hashes()}
    try:
        rep["compile_names"] = [n for n in dir(unreal) if "ompil" in n]
        unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncTextureCompilation 0")
        texs = {}
        for name in C.TEX_NAMES:
            t = unreal.load_asset(f"{C.TEXDEST}/{name}")
            texs[name] = t
        rep["texture_methods"] = sorted(m for m in dir(texs[C.TEX_NAMES[0]]) if not m.startswith("_"))
        tried = {}
        for name, t in texs.items():
            for fn in ("update_resource", "post_edit_change"):
                f = getattr(t, fn, None)
                if callable(f):
                    try:
                        f()
                        tried[f"{name}.{fn}"] = "ok"
                    except Exception as exc:                     # noqa: BLE001
                        tried[f"{name}.{fn}"] = f"{type(exc).__name__}: {exc}"[:160]
                else:
                    tried[f"{name}.{fn}"] = "absent"
        rep["tried"] = tried
        for m in ("AssetCompilingManager", "TextureCompilingManager"):
            cls = getattr(unreal, m, None)
            rep[f"{m}_members"] = [x for x in dir(cls) if not x.startswith("_")] if cls else None
        unreal.log("BHV_LISTTEXTURES2_BEGIN")
        unreal.SystemLibrary.execute_console_command(None, "ListTextures")
        unreal.log("BHV_LISTTEXTURES2_END")
    except Exception:                                            # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["hashes_after"] = C.all_hashes()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("BHV_PASSC_DONE " + str(OUT))


main()
