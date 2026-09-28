"""Verifier pass 2 (a SECOND, fresh process): load the saved asset and gate it. Writes nothing to the asset.

Runs the verifier's gates 1-6 (study-derived expectations, vsp_unreal.verifier_gates) and, for comparison,
UnrealCheck6's own gate function parameterized to this content path (uc6_common.gates).
"""
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\VerifySquarePlate")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import vsp_unreal as U  # noqa: E402

V, C, S = U.V, U.C, U.S
_TAG = os.environ.get("VSP_TAG", "")
OUT = HERE / (f"{V.FORM}_vpass2_{_TAG}.json" if _TAG else f"{V.FORM}_vpass2.json")


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": V.FORM, "asset": S["asset"],
              "sha256_now": {"fbx": V.sha256(S["fbx"]), "sidecar": V.sha256(S["sidecar"])}}
    try:
        rel = V.DEST[len("/Game/"):]
        uasset = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())) / rel / f"{S['mesh']}.uasset"
        report["uasset_on_disk"] = str(uasset)
        report["uasset_exists"] = uasset.exists()
        report["uasset_sha256_at_load"] = V.sha256(uasset) if uasset.exists() else None
        mesh = unreal.load_asset(S["asset"])
        info = C.inspect(mesh)
        extra = U.extra_inspect(mesh)
        report["inspect"] = info
        report["extra"] = extra
        sidecar = json.loads(Path(S["sidecar"]).read_text(encoding="utf-8"))
        gates, detail = U.verifier_gates(info, extra, sidecar)
        report["gates"] = gates
        report["gate_detail"] = detail
        report["passed_1_to_6"] = all(gates.values())
        uc6_gates, uc6_detail = C.gates(info)
        report["uc6_parameterized_gates"] = uc6_gates
        report["uc6_parameterized_detail"] = uc6_detail
    except Exception:
        report["error"] = traceback.format_exc()
        report["passed_1_to_6"] = False
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("VPASS2_DONE " + str(OUT))


main()
