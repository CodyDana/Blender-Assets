#!/usr/bin/env bash
# AR-01 stages 3 (UV + bake + paint) and 4 (game: LODs, hulls, sockets, twin) and their gates, from the form-stage
# Assets/Guns/AR01.blend (run_rifle.sh first). One Blender process per step; Python steps in plain py -3.
# Usage: [SKIP="bake paint"] Scripts/guns/rifle/run_game.sh [--from lod|uv|bake|paint|game|gates|renders]
# Needs: lock AR01 held by claude.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/rifle"
LOG="$W/scratch/logs"
BL="$ROOT/Assets/Guns/AR01.blend"
mkdir -p "$LOG"
FROM="lod"
[ "$1" = "--from" ] && FROM="$2"
order="lod uv bake paint game gates renders"
go=0
# SKIP="bake paint" leaves those steps out (e.g. a LOD-only change: the LOD0 islands, bakes and maps are unchanged)
want() { case " $SKIP " in *" $1 "*) return 1;; esac
         for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 Traceback "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
if want lod; then
  echo "== LOD1-3 (same generators at gunlib.lod levels 1-2; LOD3 = the blockout generator)"
  for lv in 1 2 3; do run_blender lod$lv --python "$HERE/build_rifle.py" -- --stage lod --level $lv; grep -h "LOD$lv parts" "$LOG/lod$lv.log"; done
fi
if want uv; then
  echo "== stage 3a: UVs (from the gated form-stage blend)"
  [ -f "$W/scratch/AR01_form_stage.blend" ] || { echo "no scratch/AR01_form_stage.blend: run run_rifle.sh first"; exit 1; }
  cp "$W/scratch/AR01_form_stage.blend" "$BL"
  run_blender uv "$BL" --python "$HERE/rifle_uv.py"
  grep -E "AR01-uv\] (sets|UV_DONE)" "$LOG/uv.log"
fi
if want bake; then
  echo "== stage 3b: bakes"
  run_blender bake "$BL" --python "$HERE/rifle_bake.py"
  grep -E "BAKE_DONE" "$LOG/bake.log"
fi
if want paint; then
  echo "== stage 3c: painted maps"
  py -3 -B "$HERE/rifle_paint.py" > "$LOG/paint.log" 2>&1 || { echo "FAILED paint"; tail -20 "$LOG/paint.log"; exit 1; }
  grep PAINT_DONE "$LOG/paint.log"
  # furniture recolour maps (Detail16 + recolour_maps.json) and the pre-check through the pack's derive step
  py -3 -B "$HERE/rifle_recolour.py" > "$LOG/recolour.log" 2>&1 || { echo "FAILED recolour"; tail -20 "$LOG/recolour.log"; exit 1; }
  grep -o "AR01-recolour\] [A-Z]*" "$LOG/recolour.log"
fi
if want game; then
  echo "== stage 4: static twin, hulls, sockets"
  run_blender game "$BL" --python "$HERE/rifle_game.py"
  grep -E "AR01-game\] (LOD|GAME_DONE)" "$LOG/game.log"
fi
if want gates; then
  echo "== stage 4 gates"
  py -3 -B "$HERE/rifle_viewgates.py" > "$LOG/viewgates.log" 2>&1 || { echo "FAILED viewgates"; tail -20 "$LOG/viewgates.log"; exit 1; }
  grep -E "lodpop|S2" "$LOG/viewgates.log"
  # G5 at LOD2-3 (study R5: intersections only below 1 px at the LOD's switch-in distance; needs the sizes above)
  run_blender g5_lods "$BL" --python "$HERE/rifle_g5_lods.py"
  grep -E "G5-lods\] LOD" "$LOG/g5_lods.log"
  py -3 -B "$HERE/rifle_g5_visible.py" > "$LOG/g5_visible.log" 2>&1 || { echo "FAILED g5_visible"; tail -20 "$LOG/g5_visible.log"; exit 1; }
  grep -E "G5-visible" "$LOG/g5_visible.log"
  run_blender game_gates "$BL" --python "$HERE/rifle_game_gates.py"
  grep -E "AR01-gates" "$LOG/game_gates.log" | cut -c1-300
  run_blender b3_lod1 "$BL" --python "$HERE/rifle_b3.py" -- --suffix _LOD1 --out "$W/scratch/b3_lod1.json"
  # G5 on the shipped LOD0 triangles (the UV stage triangulates: the form gates measured Blender's own loop triangles)
  run_blender b3_lod0_tri "$BL" --python "$HERE/rifle_b3.py" -- --collection AR01_Parts --quick --out "$W/scratch/b3_lod0_tri.json"
fi
if want renders; then
  echo "== renders from the baked maps + L5 (physical rig)"
  py -3 -B "$HERE/rifle_l5_fit.py" > "$LOG/l5fit.log" 2>&1 || { echo "FAILED l5fit"; tail -20 "$LOG/l5fit.log"; exit 1; }
  grep "l5fit" "$LOG/l5fit.log"
  py -3 -B -c "import json; d=json.load(open('WorkFiles/guns/rifle/scratch/game/l5.json')); [print('[L5]', k, v['delta'], v['pass']) for k, v in d['regions'].items()]"
  for s in realism closeups lods; do run_blender tex_$s "$BL" --python "$HERE/rifle_texrender.py" -- --set $s --samples 128 --out "$W/review/tex"; done
  # the realism judges' four views from the final maps (look-polish round): review/realism_tex
  run_blender tex_realism2 "$BL" --python "$HERE/rifle_texrender.py" -- --set realism --samples 256 --out "$W/review/realism_tex"
fi
py -3 -B "$HERE/rifle_texcontact.py" || true
py -3 -B "$HERE/rifle_stage34_gates.py"
echo ALL_DONE
