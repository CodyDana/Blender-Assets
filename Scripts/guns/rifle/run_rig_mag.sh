#!/usr/bin/env bash
# AR-01 stages 5 (rig + export: SK_AR01 set, clips, SM_AR01) and 6 (SM_AR01_Mag build, fit on the shipped bytes) and
# their gates, from the stage-4 Assets/Guns/AR01.blend (run_game.sh first). One Blender process per step.
# Usage: Scripts/guns/rifle/run_rig_mag.sh [--from rig|verify|mag|fit|look]
# Needs: lock AR01 held by claude. Writes gates/rig_export.json and gates/mag.json.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/rifle"
LOG="$W/scratch/logs"
BL="$ROOT/Assets/Guns/AR01.blend"
mkdir -p "$LOG"
FROM="rig"
[ "$1" = "--from" ] && FROM="$2"
order="rig verify mag fit look"
go=0
want() { for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
if want rig; then
  echo "== stage 5: rig, clips, SK_AR01 set + SM_AR01 export"
  # the rig stage re-runs on the stage-4 blend (it removes and rebuilds its own objects)
  run_blender rig "$BL" --python "$HERE/rifle_rig.py"
  grep -E "AR01-rig\] (SK_|qa_|RIG_DONE)" "$LOG/rig.log"
fi
if want verify; then
  echo "== stage 5 gates on the exported bytes (fresh process)"
  run_blender rig_verify --python "$HERE/rifle_rig_verify.py"
  grep "AR01-rigv" "$LOG/rig_verify.log"
fi
if want mag; then
  echo "== stage 6: SM_AR01_Mag from the shipped rifle (sha guard)"
  run_blender mag "$BL" --python "$HERE/rifle_mag.py"
  grep -E "AR01-mag\] (SM_|C1|qa_check|MAG_DONE)" "$LOG/mag.log"
fi
if want fit; then
  echo "== stage 6 fit gates M1-M8 on the shipped bytes of both (fresh process)"
  run_blender mag_fit --python "$HERE/rifle_mag_fit.py"
  grep "AR01-fit" "$LOG/mag_fit.log"
  py -3 -B "$HERE/rifle_mag_sheets.py"
fi
if want look; then
  echo "== look check: posed SK + magazine from the exported bytes"
  run_blender rig_render --python "$HERE/rifle_rig_render.py"
  grep "AR01-rr" "$LOG/rig_render.log"
fi
echo ALL_DONE
