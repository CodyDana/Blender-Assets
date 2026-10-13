#!/usr/bin/env bash
# SR01 W3 rig + magazine + bipod + exports (SR01_BUILD_PLAN 9 "W3"; the SMG's run_rig_mag.sh chain, adapted):
#   game     LOD1-3 (collapse decimation of the surfaced LOD0 parts), the static twin SM_SR01 (10 hulls, 20 sockets, CoM,
#            LOD group), per-LOD triangle dumps on both bipod poses
#   view     LOD-pop on both bipod poses -> screen sizes (gates/game_lod_sizes.json)
#   rig      armature (13 bones, P1 sniper-side), SK_SR01 LOD0-3, 8 clips, B11 bounds (clips + extreme poses), sockets,
#            physics; qa_check; export SK set + SM_SR01
#   verify   B1-B5, clips read back, sha256, S1, B10 in a FRESH process on the exported bytes (gates/rig_export.json)
#   mag      SM_SR01_Mag (the twin's magazine LOD objects): hull, sockets, qa_check, export
#   scope    SM_Att_Scope_LongRange (3 LODs, 3 hulls, 5 sockets): qa_check, export
#   scopev   the scope on the exported bytes, fresh process (gates/scope_export.json)
#   fit      M1-M10 on the shipped bytes, fresh process (gates/mag.json)
#   look     contact sheets from the exported bytes (every clip's key frames; LOD switch sheet)
#   gates    gates/game.json (+ a W3 summary)
# One Blender process per step; Python steps in plain py -3.
# Usage: Scripts/guns/sniper/run_rig_mag.sh [--from <step>] [--only <step>]
# Needs: lock SR01 held by claude; Assets/Guns/SR01.blend = the W2 surfaced blend (scratch/w3/SR01_w2_final.blend kept).
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/sniper"
S="$W/scratch/w3"
LOG="$S/logs"
BL="$ROOT/Assets/Guns/SR01.blend"
SBL="$ROOT/Assets/Guns/Att_Scope_LongRange.blend"
mkdir -p "$LOG"
FROM="game"; ONLY=""
[ "$1" = "--from" ] && FROM="$2"
[ "$1" = "--only" ] && ONLY="$2"
order="game view rig verify mag scope scopev fit look gates"
go=0
want() { if [ -n "$ONLY" ]; then [ "$ONLY" = "$1" ]; return; fi
         for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
if want game; then
  echo "== W3a/b LODs + static twin (from the W2 blend)"
  [ -f "$S/SR01_w2_final.blend" ] || { echo "no scratch/w3/SR01_w2_final.blend (copy the W2 Assets/Guns/SR01.blend)"; exit 1; }
  cp "$S/SR01_w2_final.blend" "$BL"
  run_blender game "$BL" --python "$HERE/sr_game.py"
  grep -E "SR01-game\] (LOD|mass|hull|GAME_DONE)" "$LOG/game.log" | cut -c1-240
fi
if want view; then
  echo "== LOD-pop (both bipod poses) -> screen sizes"
  py -3 -B "$HERE/sr_viewgates.py" > "$LOG/viewgates.log" 2>&1 || { echo "FAILED viewgates"; tail -20 "$LOG/viewgates.log"; exit 1; }
  grep -E "lodpop|DONE" "$LOG/viewgates.log"
fi
if want rig; then
  echo "== rig, clips, SK_SR01 set + SM_SR01 export"
  run_blender rig "$BL" --python "$HERE/sr_rig.py"
  grep -E "SR01-rig\] (SK_|qa_|standard|bounds|RIG_DONE)" "$LOG/rig.log" | cut -c1-400
fi
if want verify; then
  echo "== rig gates on the exported bytes (fresh process)"
  run_blender rig_verify --python "$HERE/sr_rig_verify.py"
  grep "SR01-rigv" "$LOG/rig_verify.log"
fi
if want mag; then
  echo "== SM_SR01_Mag"
  SR01_ATTACH=mag run_blender mag "$BL" --python "$HERE/sr_attach.py"
  grep -E "SR01-mag\] (LOD|qa_check|ATTACH_DONE)" "$LOG/mag.log" | cut -c1-300
fi
if want scope; then
  echo "== SM_Att_Scope_LongRange"
  SR01_ATTACH=scope run_blender scope "$SBL" --python "$HERE/sr_attach.py"
  grep -E "SR01-scope\] (LOD|qa_check|ATTACH_DONE)" "$LOG/scope.log" | cut -c1-300
fi
if want scopev; then
  echo "== the scope on the exported bytes (fresh process)"
  run_blender scope_verify --python "$HERE/sr_verify_static.py"
  grep "SR01-scopev" "$LOG/scope_verify.log"
fi
if want fit; then
  echo "== M1-M10 on the shipped bytes (fresh process)"
  run_blender mag_fit --python "$HERE/sr_magfit.py"
  grep "SR01-fit" "$LOG/mag_fit.log"
fi
if want look; then
  echo "== contact sheets from the exported bytes"
  run_blender rig_render --python "$HERE/sr_rig_render.py"
  grep "SR01-rr" "$LOG/rig_render.log"
  py -3 -B "$HERE/sr_rig_render.py" --sheets
fi
if want gates; then
  py -3 -B "$HERE/sr_w3_gates.py"
fi
echo ALL_DONE
