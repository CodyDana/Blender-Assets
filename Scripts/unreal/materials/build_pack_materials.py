"""Build the ninja pack's Unreal materials from nothing: the entry point (runs inside Unreal's pythonscript commandlet).

ONE MODE PER PROCESS (a verify must prove what a previous process saved; a new package saved several times in one
process races the changelist scan). ``run_build.sh`` runs the modes in order, one Unreal process at a time:

    import_meshes    legacy FBX import of every item + the sidecar (sockets, LOD screen sizes); the only save
    import_textures  every texture the spec names, with its kind's flags, + the black hat's ORM composite
    clean            delete the authored materials and instances only (refuses if anything else is there;
                     graphs are never rebuilt in place: np_build docstring)
    build            5 material functions, 3 masters, 25 instances (12 _Base + 12 buyer MIs + 1 preset), from
                     nothing (refuses if any exist)
    assign           every mesh slot -> its instance
    verify           fresh-process read-back of all of the above + the canonical dump (np_dump)
    render           offscreen renders and base-colour captures (needs a real RHI: see np_render.py)

Mode and output tag come from the environment (NP_MODE, NP_TAG) or from the command line after the script path.
Results: WorkFiles/materials/build/<mode>[_<tag>].json (+ dump_<tag>.json for verify).

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" <ShurikenValidation.uproject>
        -run=pythonscript -script="<this file>" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True        # never drop __pycache__ into the line's script folders (the importers are loaded)
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import unreal  # noqa: E402

import np_spec  # noqa: E402

OUT_DIR = Path(os.environ["NP_OUT_DIR"]) if os.environ.get("NP_OUT_DIR") else np_spec.WORK / "build"   # trial builds
MODES = ("import_meshes", "import_textures", "build", "assign", "verify", "render", "clean")


def _args():
    mode = os.environ.get("NP_MODE", "").strip().lower()
    tag = os.environ.get("NP_TAG", "").strip()
    argv = [a for a in sys.argv[1:] if not a.endswith(".py")]
    if not mode and argv:
        mode = argv[0].lower()
    if not tag and len(argv) > 1:
        tag = argv[1]
    if mode not in MODES:
        raise SystemExit(f"NP_MODE must be one of {MODES}, got {mode!r}")
    return mode, tag


def main():
    mode, tag = _args()
    suffix = f"_{tag}" if tag else ""
    out_path = OUT_DIR / f"{mode}{suffix}.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    report = {"mode": mode, "tag": tag, "engine": unreal.SystemLibrary.get_engine_version(),
              "spec_sha256": np_spec.sha256(np_spec.SPEC_PATH), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        plan = np_spec.resolve()
        report["recolour_sources"] = {k: {kk: vv for kk, vv in v.items() if kk != "params"}
                                      for k, v in plan["recolour"].items()}
        if mode == "import_meshes":
            import np_meshes
            report.update(np_meshes.run_import(plan))
        elif mode == "import_textures":
            import np_textures
            report.update(np_textures.run_import(plan))
        elif mode == "build":
            import np_build
            report.update(np_build.run_build(plan))
        elif mode == "assign":
            import np_meshes
            report.update(np_meshes.run_assign(plan))
        elif mode == "verify":
            import np_dump
            import np_verify
            rep, dump = np_verify.run_verify(plan)
            report.update(rep)
            dump_path = OUT_DIR / f"dump{suffix}.json"
            dump_path.write_text(json.dumps(np_dump.strip_layout(dump), indent=1, sort_keys=True), encoding="utf-8")
            (OUT_DIR / f"dump_layout{suffix}.json").write_text(json.dumps(
                {s: {k: (v or {}).get("layout") for k, v in dump[s].items()} for s in ("functions", "masters")},
                sort_keys=True), encoding="utf-8")
            report["dump"] = str(dump_path)
        elif mode == "render":
            import np_render
            report.update(np_render.run_render(plan, tag))
        elif mode == "clean":
            import np_build
            report.update(np_build.run_clean(plan))
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
        report["passed"] = False
    report["sec"] = round(time.time() - t0, 1)
    out_path.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    unreal.log(f"NP_BUILD_DONE mode={mode} passed={report.get('passed')} sec={report['sec']} out={out_path}")


main()
