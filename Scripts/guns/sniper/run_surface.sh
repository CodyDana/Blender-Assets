#!/usr/bin/env bash
# SR01 W2 surface (SR01_BUILD_PLAN 7 / 9 "W2 surface"; the SMG's run_surface.sh chain): gun UV0 -> UV1 + UD4 -> bakes
# -> paint -> Detail16 / recolour pre-check -> Blender-side gates; the same for the scope attachment
# (SR01_SURFACE_TARGET=scope); renders from the baked maps (studio-HDRI rig); L5; gates/uv_bake_paint.json.
# Starts from the gated form-stage blends (run_sniper.sh first; this keeps copies in scratch/w2*/).
# Usage: Scripts/guns/sniper/run_surface.sh [--from uv|uv1|bake|paint|recolour|blender|scope|renders|l5|gates]
# Needs: lock SR01 held by claude.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/sniper"
S="$W/scratch/w2"
SS="$W/scratch/w2_scope"
LOG="$S/logs"
BL="$ROOT/Assets/Guns/SR01.blend"
SBL="$ROOT/Assets/Guns/Att_Scope_LongRange.blend"
mkdir -p "$LOG" "$SS"
FROM="uv"
[ "$1" = "--from" ] && FROM="$2"
SAMPLES="${SR01_RENDER_SAMPLES:-512}"
order="uv uv1 bake paint recolour blender scope renders l5 gates"
go=0
want() { for s in $order; do [ "$s" = "$FROM" ] && go=1; [ "$s" = "$1" ] && { [ $go = 1 ] && return 0 || return 1; }; done; return 1; }
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback\|SystemExit" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 "Traceback\|SystemExit" "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
py -3 -B Scripts/pipeline/lock.py status 2>/dev/null | grep -q "SR01" || true
if want uv; then
  echo "== W2a UV0 (from the gated form-stage blend)"
  [ -f "$S/SR01_form_stage.blend" ] || cp "$BL" "$S/SR01_form_stage.blend"
  cp "$S/SR01_form_stage.blend" "$BL"
  run_blender uv "$BL" --python "$HERE/sr_uv.py"
  grep -E "SR01-uv\] (sets|UV_DONE)" "$LOG/uv.log"
fi
if want uv1; then
  echo "== W2a' UV1 (authored lightmap) + UD4"
  run_blender uv1 "$BL" --python "$HERE/sr_uv1.py"
  py -3 -B "$HERE/sr_ud4.py" | tail -1
fi
if want bake; then
  echo "== W2b bakes (margin 0; the magazine's AO alone; the gun's AO with the magazine out)"
  run_blender bake "$BL" --python "$HERE/sr_bake.py"
  grep -E "BAKE_DONE" "$LOG/bake.log"
fi
if want paint; then
  echo "== W2c painted maps"
  py -3 -B "$HERE/sr_paint.py" > "$LOG/paint.log" 2>&1 || { echo "FAILED paint"; tail -20 "$LOG/paint.log"; exit 1; }
  grep -E "DONE" "$LOG/paint.log" | cut -c1-300
fi
if want recolour; then
  echo "== Detail16 + recolour pre-check"
  py -3 -B "$HERE/sr_recolour.py" > "$LOG/recolour.log" 2>&1 || { echo "FAILED recolour"; tail -20 "$LOG/recolour.log"; exit 1; }
  tail -1 "$LOG/recolour.log" | cut -c1-300
fi
if want blender; then
  echo "== Blender-side gates (UD1-UD3, layers, the twin through qa_check)"
  run_blender w2_blender "$BL" --python "$HERE/sr_w2_blender.py"
  grep -E "twin qa|twin UD1" "$LOG/w2_blender.log" | cut -c1-300
fi
if want scope; then
  echo "== scope attachment: UV0, UV1 + UD4, bakes, paint, Blender-side gates"
  export SR01_SURFACE_TARGET=scope
  [ -f "$SS/Att_Scope_form_stage.blend" ] || cp "$SBL" "$SS/Att_Scope_form_stage.blend"
  cp "$SS/Att_Scope_form_stage.blend" "$SBL"
  run_blender scope_uv "$SBL" --python "$HERE/sr_uv.py"
  run_blender scope_uv1 "$SBL" --python "$HERE/sr_uv1.py"
  py -3 -B "$HERE/sr_ud4.py" | tail -1
  run_blender scope_bake "$SBL" --python "$HERE/sr_bake.py"
  py -3 -B "$HERE/sr_paint.py" > "$LOG/scope_paint.log" 2>&1 || { echo "FAILED scope paint"; tail -20 "$LOG/scope_paint.log"; exit 1; }
  run_blender scope_w2_blender "$SBL" --python "$HERE/sr_w2_blender.py"
  grep -E "twin qa" "$LOG/scope_w2_blender.log" | cut -c1-300
  unset SR01_SURFACE_TARGET
fi
if want renders; then
  echo "== renders from the baked maps (studio-HDRI rig) -> Renders/Guns/SR01/tex_*.png"
  run_blender tex_renders "$BL" --python "$HERE/sr_render.py" -- --set tex --looks tex --rig studio --with-scope --samples "$SAMPLES"
fi
if want l5; then
  echo "== L5 (GR crop-matched, physical rig, one light scale on the forend OD)"
  py -3 -B "$HERE/sr_l5.py" > "$LOG/l5.log" 2>&1 || { echo "FAILED l5"; tail -20 "$LOG/l5.log"; exit 1; }
  grep "SR01-l5" "$LOG/l5.log"
fi
py -3 -B "$HERE/sr_w2_gates.py"
echo ALL_DONE
