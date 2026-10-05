#!/usr/bin/env bash
# AR-01 rifle, stages 1-2 (blockout + form) and their gates, from nothing. One Blender process per step.
# Usage: Scripts/guns/rifle/run_rifle.sh [--skip-b3] [--no-solve]
# Needs: lock AR01 held by claude (py -3 -B Scripts/pipeline/lock.py claim AR01 --agent claude).
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/rifle"
LOG="$W/scratch/logs"
mkdir -p "$LOG"
SKIPB3=0; SOLVE="--solve"
for a in "$@"; do
  [ "$a" = "--skip-b3" ] && SKIPB3=1
  [ "$a" = "--no-solve" ] && SOLVE=""
done
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 Traceback "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
echo "== stage 1: blockout"
run_blender blockout --python "$HERE/build_rifle.py" -- --stage blockout
py -3 -B "$HERE/rifle_silhouette.py" --npz "$W/scratch/blockout_tris.npz" --stage blockout --json "$W/scratch/sil_blockout.json" > /dev/null
py -3 -B "$HERE/rifle_q34.py" --npz "$W/scratch/blockout_tris.npz" --stage blockout $SOLVE > /dev/null
py -3 -B "$HERE/rifle_gates.py" --stage blockout
echo "== stage 2: form"
run_blender form --python "$HERE/build_rifle.py" -- --stage form
grep -E "total tris" "$LOG/form.log"
py -3 -B "$HERE/rifle_silhouette.py" --npz "$W/scratch/form_tris.npz" --stage form --json "$W/scratch/sil.json" > /dev/null
py -3 -B "$HERE/rifle_q34.py" --npz "$W/scratch/form_tris.npz" --stage form $SOLVE > /dev/null
py -3 -B "$HERE/rifle_closeups.py" --npz "$W/scratch/form_tris.npz" > /dev/null
[ $SKIPB3 = 1 ] || run_blender b3 "$ROOT/Assets/Guns/AR01.blend" --python "$HERE/rifle_b3.py"
run_blender b6a "$ROOT/Assets/Guns/AR01.blend" --python "$HERE/rifle_b6a.py"
run_blender measure "$ROOT/Assets/Guns/AR01.blend" --python "$HERE/rifle_measure.py"
run_blender h1 "$ROOT/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend" --python "$HERE/rifle_h1.py"
run_blender render_grey "$ROOT/Assets/Guns/AR01.blend" --python "$HERE/rifle_render.py" -- --set grey --ss 3 --samples 96 --light 0.45 --out "$ROOT/Renders/Guns/AR01"
run_blender render_crops "$ROOT/Assets/Guns/AR01.blend" --python "$HERE/rifle_render.py" -- --set crops --ss 3 --light 0.55 --out "$W/review/early"
py -3 -B "$HERE/rifle_gates.py" --stage form
echo ALL_DONE
