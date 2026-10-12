#!/usr/bin/env bash
# SMG01 full chain from nothing (SMG_BUILD_PLAN 15 row W4: "every fix in the generators, then the full chain from
# nothing"): run_smg.sh (blockout + form, W1) -> run_surface.sh (W2) -> the W2 blend kept for W3 -> the AR-01 regression
# (gunlib changed) -> the W2 gate record again (it reads the regression) -> run_rig_mag.sh (W3) -> the W4 review renders
# from the exported bytes (smg_review_export.py) -> the W4 fix record (smg_w4_fix_gates.py).
# One Blender process per step (inside each runner). Usage: Scripts/guns/smg/run_all.sh [--from smg|surface|reg|rig|review|fix]
# Needs: locks SMG01 and GunLib held by claude.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
S="$ROOT/WorkFiles/guns/smg/scratch"
LOG="$S/logs"
mkdir -p "$LOG"
FROM="smg"
[ "$1" = "--from" ] && FROM="$2"
order="smg surface reg rig review fix"
go=0
want() { for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
stamp() { echo "[run_all] $(date +%H:%M:%S) $*"; }
need_pass() {  # gate files ...: stop the chain on a failing stage (fix the generator, then --from that stage)
  for f in "$@"; do
    py -3 -c "import json,sys; j=json.load(open(sys.argv[1])); sys.exit(0 if j.get('status')=='pass' else 1)"       "$ROOT/WorkFiles/guns/smg/gates/$f.json" || { echo "[run_all] STOP: gates/$f.json does not pass"; exit 1; }
  done
}
cd "$ROOT"
if want smg; then
  stamp "W1 run_smg.sh"
  bash "$HERE/run_smg.sh"
  need_pass form
fi
if want surface; then
  stamp "W2 run_surface.sh"
  bash "$HERE/run_surface.sh"
  cp "$ROOT/Assets/Guns/SMG01.blend" "$S/SMG01_w2_final.blend"
fi
if want reg; then
  stamp "AR-01 regression (gunlib changed)"
  bash "$ROOT/Scripts/guns/gunlib/tests/ar01_regression.sh" > "$LOG/ar01_regression_w4.log" 2>&1 || true
  tail -3 "$LOG/ar01_regression_w4.log"
  py -3 -B "$HERE/smg_w2_gates.py"
  need_pass uv_bake_paint
fi
if want rig; then
  stamp "W3 run_rig_mag.sh"
  bash "$HERE/run_rig_mag.sh"
  need_pass game rig_export mag
fi
if want review; then
  stamp "W4 review renders from the exported bytes"
  py -3 -B "$HERE/smg_review_export.py" > "$LOG/review_export.log" 2>&1 || { echo "FAILED review"; tail -20 "$LOG/review_export.log"; exit 1; }
  tail -3 "$LOG/review_export.log"
  need_pass review_export
fi
if want fix; then
  stamp "W4 fix record"
  py -3 -B "$HERE/smg_w4_fix_gates.py"
fi
stamp ALL_DONE
