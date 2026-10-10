#!/usr/bin/env bash
# AR-01 regression for gunlib 0.2.0 (SMG_BUILD_PLAN 15, W1a): re-run the AR-01's stage-2 / 4 / 5 (+ 6) gate drivers
# through the promoted code (the rifle_* shims -> gunlib.drivers with rifle_gun.CFG) on COPIES of the gated blends and
# on the shipped exports (read only), every output into WorkFiles/guns/smg/scratch/regression/, then compare them with
# the committed values (ar01_regression_compare.py -> WorkFiles/guns/smg/gates/gunlib_regression.json).
# Nothing under WorkFiles/guns/rifle/, Assets/ or Exports/ is written. One Blender process per step.
# Then the new modules' own test (test_parts.py) and the UD1-UD2 driver on the AR-01's form-stage parts (information:
# the AR-01 predates the UD rule; its U5 / U10 findings are why the rule exists).
# Usage: Scripts/guns/gunlib/tests/ar01_regression.sh [--from form|game|rig|mag|parts|compare]
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
RIF="$ROOT/Scripts/guns/rifle"
W="$ROOT/WorkFiles/guns/rifle"
R="$ROOT/WorkFiles/guns/smg/scratch/regression"
LOG="$R/logs"
mkdir -p "$LOG" "$R/game" "$R/review"
FROM="form"
[ "$1" = "--from" ] && FROM="$2"
order="form game rig mag parts compare"
go=0
want() { for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
sha256sum Assets/Guns/AR01.blend Assets/Guns/AR01_Mag.blend "$W/scratch/AR01_form_stage.blend" > "$R/inputs_sha256_before.txt"
find Exports/Guns/AR01 -type f | sort | xargs sha256sum > "$R/exports_sha256_before.txt"
if want form; then
  echo "== stage 2 (form) gates on a copy of scratch/AR01_form_stage.blend"
  cp "$W/scratch/AR01_form_stage.blend" "$R/AR01_form_stage.blend"
  run_blender b3 "$R/AR01_form_stage.blend" --python "$RIF/rifle_b3.py" -- --out "$R/b3_result.json"
  run_blender b6a "$R/AR01_form_stage.blend" --python "$RIF/rifle_b6a.py" -- --out "$R/b6a_result.json"
  run_blender measure "$R/AR01_form_stage.blend" --python "$RIF/rifle_measure.py" -- --out "$R/measure_result.json"
  run_blender magfit "$R/AR01_form_stage.blend" --python "$RIF/rifle_magfit_check.py" -- --out "$R/form_magfit.json"
  py -3 -B "$RIF/rifle_b4.py" --npz "$W/scratch/form_tris.npz" --out "$R/b4_result.json" --img "$R/review/b4_sight_picture.png" > "$LOG/b4.log" 2>&1 || { echo "FAILED b4"; tail -20 "$LOG/b4.log"; exit 1; }
fi
if want game; then
  echo "== stage 4 gates (view gates on the committed LOD dumps; G5 / B3 on a copy of Assets/Guns/AR01.blend)"
  cp "$ROOT/Assets/Guns/AR01.blend" "$R/AR01.blend"
  py -3 -B "$RIF/rifle_viewgates.py" --outdir "$R/game" --outr "$R/review/game" --sizes-out "$R/game_lod_sizes.json" > "$LOG/viewgates.log" 2>&1 || { echo "FAILED viewgates"; tail -20 "$LOG/viewgates.log"; exit 1; }
  run_blender g5_lods "$R/AR01.blend" --python "$RIF/rifle_g5_lods.py" -- --out "$R/game/g5_lods.json"
  run_blender b3_lod1 "$R/AR01.blend" --python "$RIF/rifle_b3.py" -- --collection AR01_LOD1 --suffix _LOD1 --out "$R/b3_lod1.json"
  run_blender b3_lod0_tri "$R/AR01.blend" --python "$RIF/rifle_b3.py" -- --collection AR01_Parts --quick --out "$R/b3_lod0_tri.json"
fi
if want rig; then
  echo "== stage 5 gates on the shipped bytes (fresh process)"
  run_blender rig_verify --python "$RIF/rifle_rig_verify.py" -- --out "$R/rig_export.json"
fi
if want mag; then
  echo "== stage 6 fit gates on the shipped bytes (fresh process)"
  run_blender mag_fit --python "$RIF/rifle_mag_fit.py" -- --out "$R/mag.json" --geom "$R/fit_geom.npz"
fi
if want parts; then
  echo "== gunlib 0.2.0 new modules (test_parts.py) + UD1-UD2 on the AR-01 form-stage parts (info)"
  run_blender test_parts --python "$HERE/test_parts.py" -- --out "$R/parts_test.json"
  grep -E "gunlib-test\] (PASS|FAIL|DONE)" "$LOG/test_parts.log" | cut -c1-140
  [ -f "$R/AR01_form_stage.blend" ] || cp "$W/scratch/AR01_form_stage.blend" "$R/AR01_form_stage.blend"
  run_blender ud_ar01 "$R/AR01_form_stage.blend" --python "$ROOT/Scripts/guns/gunlib/drivers/run.py" -- --gun Scripts/guns/rifle/rifle_gun.py --driver ud --collection AR01_Parts --label "AR-01 form-stage LOD0 parts, info" --out "$R/ud_ar01_form.json"
fi
sha256sum Assets/Guns/AR01.blend Assets/Guns/AR01_Mag.blend "$W/scratch/AR01_form_stage.blend" > "$R/inputs_sha256_after.txt"
find Exports/Guns/AR01 -type f | sort | xargs sha256sum > "$R/exports_sha256_after.txt"
py -3 -B "$HERE/ar01_regression_compare.py"
echo ALL_DONE
