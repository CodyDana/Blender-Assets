#!/usr/bin/env bash
# SMG01 W2 surface (SMG_BUILD_PLAN 15 row W2; the AR-01 run_game.sh stages 3a-3c + renders): UV0 -> UV1 -> bakes ->
# paint -> recolour pre-check -> Blender-side gates -> L5 -> renders from the baked maps -> gates/uv_bake_paint.json.
# Starts from the gated form-stage blend (run_smg.sh first). One Blender process per step; Python steps in plain py -3.
# Usage: Scripts/guns/smg/run_surface.sh [--from uv|uv1|bake|paint|recolour|blender|l5|renders|gates]
# Needs: lock SMG01 held by claude.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/smg"
S="$W/scratch"
LOG="$S/logs"
BL="$ROOT/Assets/Guns/SMG01.blend"
mkdir -p "$LOG"
FROM="uv"
[ "$1" = "--from" ] && FROM="$2"
order="uv uv1 bake paint recolour blender l5 renders gates"
go=0
want() { for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
if want uv; then
  echo "== W2a UV0 (from the gated form-stage blend)"
  [ -f "$S/SMG01_form_stage.blend" ] || { echo "no scratch/SMG01_form_stage.blend: run run_smg.sh first"; exit 1; }
  cp "$S/SMG01_form_stage.blend" "$BL"
  run_blender uv "$BL" --python "$HERE/smg_uv.py"
  grep -E "SMG01-uv\] (sets|UV_DONE)" "$LOG/uv.log"
fi
if want uv1; then
  echo "== W2a' UV1 (authored lightmap) + UD4"
  run_blender uv1 "$BL" --python "$HERE/smg_uv1.py"
  py -3 -B "$HERE/smg_ud4.py" | tail -1
fi
if want bake; then
  echo "== W2b bakes (margin 0; the magazine's AO alone; the gun's AO with the magazine out)"
  run_blender bake "$BL" --python "$HERE/smg_bake.py"
  grep -E "BAKE_DONE" "$LOG/bake.log"
fi
if want paint; then
  echo "== W2c painted maps"
  py -3 -B "$HERE/smg_paint.py" > "$LOG/paint.log" 2>&1 || { echo "FAILED paint"; tail -20 "$LOG/paint.log"; exit 1; }
  grep -E "audit|PAINT_DONE" "$LOG/paint.log" | cut -c1-300
fi
if want recolour; then
  echo "== Detail16 + recolour pre-check (the pack's derive step)"
  py -3 -B "$HERE/smg_recolour.py" > "$LOG/recolour.log" 2>&1 || { echo "FAILED recolour"; tail -20 "$LOG/recolour.log"; exit 1; }
  grep -o "SMG01-recolour\] [A-Za-z]* [A-Z]*" "$LOG/recolour.log"
fi
if want blender; then
  echo "== Blender-side gates (UD1-UD3, layers, the twin through qa_check)"
  run_blender w2_blender "$BL" --python "$HERE/smg_w2_blender.py"
  grep -E "twin qa|twin UD1" "$LOG/w2_blender.log" | cut -c1-300
fi
if want l5; then
  echo "== L5 (physical rig, light scale fitted on the upper receiver)"
  py -3 -B "$HERE/smg_l5_fit.py" > "$LOG/l5fit.log" 2>&1 || { echo "FAILED l5fit"; tail -20 "$LOG/l5fit.log"; exit 1; }
  grep "l5fit" "$LOG/l5fit.log"
fi
if want renders; then
  echo "== renders from the baked maps (review/realism_tex)"
  for s in realism closeups; do run_blender tex_$s "$BL" --python "$HERE/smg_texrender.py" -- --set $s --samples 160; done
  py -3 -B "$HERE/smg_contact.py" > /dev/null
fi
py -3 -B "$HERE/smg_w2_gates.py"
echo ALL_DONE
