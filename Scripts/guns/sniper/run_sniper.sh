#!/usr/bin/env bash
# SR01 (Sniper Rifle SR-01), W1a: blockout + form and their gates, from nothing (the SMG run_smg.sh chain).
# One headless Blender process per step. Usage: Scripts/guns/sniper/run_sniper.sh [--fast] [--skip-b3] [--skip-renders]
# Needs: lock SR01 held by claude (py -3 -B Scripts/pipeline/lock.py claim SR01 --agent claude
#        --blend Assets/Guns/SR01.blend). The L8 judge passes are run by the session (two fresh judges on the
#        review/l8 sheets) and recorded in scratch/w1/l8_judges.json, which sr_gates.py folds into gates/form.json.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/sniper"
S="$W/scratch/w1"
LOG="$S/logs"
mkdir -p "$LOG"
FAST=""; SKIPB3=0; RENDERS=1
for a in "$@"; do
  [ "$a" = "--fast" ] && FAST="--fast"
  [ "$a" = "--skip-b3" ] && SKIPB3=1
  [ "$a" = "--skip-renders" ] && RENDERS=0
done
run_blender() {  # name, args...
  local name="$1"; shift
  "$B" -b --factory-startup "$@" > "$LOG/$name.log" 2>&1 || true
  if grep -q "Traceback" "$LOG/$name.log"; then echo "FAILED $name"; grep -A15 Traceback "$LOG/$name.log" | head -30; exit 1; fi
}
cd "$ROOT"
echo "== blockout"
run_blender blockout --python "$HERE/build_sniper.py" -- --stage blockout
py -3 -B "$HERE/sr_silhouette.py" --npz "$S/blockout_tris.npz" --stage blockout > /dev/null
py -3 -B "$HERE/sr_gates.py" --stage blockout
echo "== form"
run_blender form --python "$HERE/build_sniper.py" -- --stage form
grep -E "total tris" "$LOG/form.log"
py -3 -B "$HERE/sr_silhouette.py" --npz "$S/form_tris.npz" --stage form --with-npz "$S/blockout_tris.npz" > /dev/null
ONLY="g5,b6a,f,magfit,h1"; [ $SKIPB3 = 1 ] || ONLY="$ONLY,b3"
rm -f "$S/fgates.json"
run_blender fgates "$ROOT/Assets/Guns/SR01.blend" --python "$HERE/sr_fgates.py" -- --only "$ONLY" $FAST
if [ $RENDERS = 1 ]; then
  run_blender render "$ROOT/Assets/Guns/SR01.blend" --python "$HERE/sr_render.py" -- --set all --samples 48
fi
py -3 -B "$HERE/sr_gates.py" --stage form
echo ALL_DONE
