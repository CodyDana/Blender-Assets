#!/usr/bin/env bash
# SMG01 W3 rig + mag (SMG_BUILD_PLAN 15 row W3; the AR-01's run_game.sh stage 4 + run_rig_mag.sh stages 5-6):
#   lod       LOD1-3 from the same generators (build_smg --stage lod 1..3; LOD3 = the blockout generator)
#   lods      the LODs into the asset blend: triangulation, UV0 transfer from the W2 islands, UV1 per LOD, UD1-UD4
#   game      the static twin SM_SMG01 (8 hulls, 21 sockets, CoM, LOD group) + per-LOD triangle dumps (both stock states)
#   view      LOD-pop on both stock states -> screen sizes (gates/game_lod_sizes.json), S2 at LOD0-3
#   g5        G5 at LOD2-3 (penetration depth in px at the switch distance) + the visible measure
#   ggates    qa_check / C1 / S1 test export / twin UD / B10 on the saved twin
#   b3        B3 + G5 at LOD1 (all moving groups incl. the stock fold) and G5 on the shipped LOD0 triangles (quick)
#   rig       armature, SK_SMG01 LOD0-3, 8 clips, bounds extension (B11), sockets, physics, export SK set + SM_SMG01
#   verify    B1-B5, clips read back, sha256, S1, B10 in a FRESH process on the exported bytes
#   mag       SM_SMG01_Mag from the shipped twin bytes (sha guard): LODs, UV1, hull, sockets, derived sizes, export
#   fit       M1-M10 + F5 on the shipped bytes of both (fresh process)
#   h1        H1 full: the posed hand fit on MH_PlayerDefault
#   look      posed SK + magazine renders from the exported bytes
#   gates     gates/game.json (+ rig_export.json, mag.json written by verify / fit)
# One Blender process per step; Python steps in plain py -3.
# Usage: Scripts/guns/smg/run_rig_mag.sh [--from <step>] [--only <step>]
# Needs: lock SMG01 held by claude; the W2 blend (scratch/SMG01_w2_final.blend = the committed W2 asset blend).
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/smg"
S="$W/scratch"
LOG="$S/logs"
BL="$ROOT/Assets/Guns/SMG01.blend"
RUN="$ROOT/Scripts/guns/gunlib/drivers/run.py"
GUN="$HERE/smg_gun.py"
FIT="$ROOT/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend"
mkdir -p "$LOG"
FROM="lod"; ONLY=""
[ "$1" = "--from" ] && FROM="$2"
[ "$1" = "--only" ] && ONLY="$2"
order="lod lods game view g5 ggates b3 rig verify mag fit h1 look gates"
go=0
want() { if [ -n "$ONLY" ]; then [ "$ONLY" = "$1" ]; return; fi
         for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
if want lod; then
  echo "== W3a LOD1-3 (the same generators; LOD3 = the blockout generator)"
  for lv in 1 2 3; do run_blender lod$lv --python "$HERE/build_smg.py" -- --stage lod --level $lv; grep -h "LOD$lv parts" "$LOG/lod$lv.log"; done
fi
if want lods; then
  echo "== W3a LODs into the asset blend (from the W2 blend): triangulation, UV0, UV1, UD"
  [ -f "$S/SMG01_w2_final.blend" ] || { echo "no scratch/SMG01_w2_final.blend (copy the committed W2 Assets/Guns/SMG01.blend)"; exit 1; }
  cp "$S/SMG01_w2_final.blend" "$BL"
  run_blender lods "$BL" --python "$HERE/smg_lods.py"
  grep -E "UD LOD|LODS_DONE" "$LOG/lods.log" | cut -c1-200
  cp "$BL" "$S/SMG01_w3_lods.blend"
fi
if want game; then
  echo "== W3b static twin, hulls, sockets"
  run_blender game "$BL" --python "$HERE/smg_game.py"
  grep -E "SMG01-game\] (LOD|mass|GAME_DONE)" "$LOG/game.log"
fi
if want view; then
  echo "== LOD-pop (both stock states) -> screen sizes; S2 at LOD0-3"
  py -3 -B "$RUN" --gun "$GUN" --driver viewgates > "$LOG/viewgates.log" 2>&1 || { echo "FAILED viewgates"; tail -20 "$LOG/viewgates.log"; exit 1; }
  grep -E "lodpop|viewgates\] (S2|DONE)" "$LOG/viewgates.log"
fi
if want g5; then
  echo "== G5 at LOD2-3"
  run_blender g5_lods "$BL" --python "$RUN" -- --gun "$GUN" --driver g5_lods
  grep -E "G5-lods\] LOD" "$LOG/g5_lods.log"
  py -3 -B "$HERE/smg_g5_visible.py" > "$LOG/g5_visible.log" 2>&1 || { echo "FAILED g5_visible"; tail -20 "$LOG/g5_visible.log"; exit 1; }
  grep -E "G5-visible" "$LOG/g5_visible.log"
fi
if want ggates; then
  echo "== twin gates (qa_check, C1, S1, UD, B10)"
  run_blender game_gates "$BL" --python "$HERE/smg_game_gates.py"
  grep -E "SMG01-gates\] (qa|C1|S1|GATES)" "$LOG/game_gates.log" | cut -c1-300
fi
if want b3; then
  echo "== B3 + G5 at LOD1 (long: the stock fold), G5 on the shipped LOD0 triangles"
  run_blender b3_lod1 "$S/SMG01_w3_lods.blend" --python "$RUN" -- --gun "$GUN" --driver b3 --collection SMG01_LOD1 \
    --suffix _LOD1 --out "$S/b3_lod1.json"
  run_blender b3_lod0_tri "$S/SMG01_w3_lods.blend" --python "$RUN" -- --gun "$GUN" --driver b3 --collection SMG01_Parts \
    --quick --out "$S/b3_lod0_tri.json"
fi
if want rig; then
  echo "== rig, clips, SK_SMG01 set + SM_SMG01 export"
  run_blender rig "$BL" --python "$HERE/smg_rig.py"
  grep -E "SMG01-rig\] (SK_|qa_|bounds|RIG_DONE)" "$LOG/rig.log" | cut -c1-300
fi
if want verify; then
  echo "== rig gates on the exported bytes (fresh process)"
  run_blender rig_verify --python "$RUN" -- --gun "$GUN" --driver rig_verify
  grep "SMG01-rigv" "$LOG/rig_verify.log"
fi
if want mag; then
  echo "== SM_SMG01_Mag from the shipped twin (sha guard)"
  run_blender mag "$BL" --python "$HERE/smg_mag.py"
  grep -E "SMG01-mag\] (SM_|C1|qa_check|twin|MAG_DONE)" "$LOG/mag.log" | cut -c1-300
fi
if want fit; then
  echo "== M1-M10 + F5 on the shipped bytes of both (fresh process)"
  run_blender mag_fit --python "$RUN" -- --gun "$GUN" --driver mag_fit
  grep "SMG01-fit" "$LOG/mag_fit.log"
fi
if want h1; then
  echo "== H1 full (posed hand fit on MH_PlayerDefault)"
  run_blender h1_full "$FIT" --python "$HERE/smg_h1_full.py"
  grep -E "H1F\]" "$LOG/h1_full.log" | cut -c1-300
fi
if want look; then
  echo "== look check: posed SK + magazine from the exported bytes"
  run_blender rig_render --python "$HERE/smg_rig_render.py"
  grep "SMG01-rr" "$LOG/rig_render.log"
fi
if want gates; then
  py -3 -B "$HERE/smg_w3_gates.py"
fi
echo ALL_DONE
