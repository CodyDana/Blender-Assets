#!/usr/bin/env bash
# SMG01 (Compact SMG SM-01), W1b: blockout + form and their gates, from nothing (the AR-01 run_rifle.sh chain).
# One Blender process per step. Usage: Scripts/guns/smg/run_smg.sh [--skip-b3] [--no-solve] [--skip-renders]
# Needs: lock SMG01 held by claude (py -3 -B Scripts/pipeline/lock.py claim SMG01 --agent claude
#        --blend Assets/Guns/SMG01.blend).
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/smg"
S="$W/scratch"
LOG="$S/logs"
RUN="$ROOT/Scripts/guns/gunlib/drivers/run.py"
GUN="$HERE/smg_gun.py"
mkdir -p "$LOG" "$W/review/b4"
SKIPB3=0; SOLVE="--solve"; RENDERS=1
for a in "$@"; do
  [ "$a" = "--skip-b3" ] && SKIPB3=1
  [ "$a" = "--no-solve" ] && SOLVE=""
  [ "$a" = "--skip-renders" ] && RENDERS=0
done
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 Traceback "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
echo "== blockout"
run_blender blockout --python "$HERE/build_smg.py" -- --stage blockout
py -3 -B "$HERE/smg_silhouette.py" --npz "$S/blockout_tris.npz" --stage blockout --json "$S/sil_blockout.json" > /dev/null
py -3 -B "$HERE/smg_q34.py" --npz "$S/blockout_tris.npz" --stage blockout $SOLVE > /dev/null
py -3 -B "$RUN" --gun "$GUN" --driver b4 --npz "$S/blockout_tris.npz" --out "$S/b4_blockout.json" \
  --img "$W/review/blockout/b4_sight_picture.png" > "$LOG/b4_blockout.log" 2>&1
py -3 -B "$HERE/smg_gates.py" --stage blockout
echo "== form"
run_blender form --python "$HERE/build_smg.py" -- --stage form
grep -E "total tris" "$LOG/form.log"
py -3 -B "$HERE/smg_facet_check.py" --npz "$S/form_tris.npz" | tail -1
# the gated form-stage blend, kept for the later stages
cp "$ROOT/Assets/Guns/SMG01.blend" "$S/SMG01_form_stage.blend"
py -3 -B "$HERE/smg_silhouette.py" --npz "$S/form_tris.npz" --stage form --json "$S/sil_form.json" > /dev/null
py -3 -B "$HERE/smg_q34.py" --npz "$S/form_tris.npz" --stage form $SOLVE > /dev/null
[ $SKIPB3 = 1 ] || run_blender b3 "$ROOT/Assets/Guns/SMG01.blend" --python "$RUN" -- --gun "$GUN" --driver b3 \
  --out "$S/b3_result.json"
run_blender b6a "$ROOT/Assets/Guns/SMG01.blend" --python "$RUN" -- --gun "$GUN" --driver b6a --out "$S/b6a_result.json"
run_blender measure "$ROOT/Assets/Guns/SMG01.blend" --python "$RUN" -- --gun "$GUN" --driver measure \
  --out "$S/measure_result.json"
run_blender fgates "$ROOT/Assets/Guns/SMG01.blend" --python "$HERE/smg_fgates.py"
# magazine fit at the form stage: the M-gate geometry on the LOD0 parts -> gates/form_magfit.json
run_blender magfit "$ROOT/Assets/Guns/SMG01.blend" --python "$RUN" -- --gun "$GUN" --driver magfit_check \
  --out "$W/gates/form_magfit.json"
py -3 -B "$RUN" --gun "$GUN" --driver b4 --npz "$S/form_tris.npz" --out "$S/b4_result.json" \
  --img "$W/review/b4/b4_sight_picture.png" > "$LOG/b4.log" 2>&1 || { echo "FAILED b4"; tail -20 "$LOG/b4.log"; exit 1; }
py -3 -B "$HERE/smg_b4b.py" > "$LOG/b4b.log" 2>&1 || { echo "FAILED b4b"; tail -20 "$LOG/b4b.log"; exit 1; }
run_blender h1 "$ROOT/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend" --python "$HERE/smg_h1.py"
if [ $RENDERS = 1 ]; then
  run_blender render_grey "$ROOT/Assets/Guns/SMG01.blend" --python "$HERE/smg_render.py" -- --ss 2 --samples 48
  py -3 -B "$HERE/smg_realism.py" --samples 64 > "$LOG/realism_run.log" 2>&1 || { echo "FAILED realism"; tail -20 "$LOG/realism_run.log"; exit 1; }
fi
py -3 -B "$HERE/smg_gates.py" --stage form
echo ALL_DONE
