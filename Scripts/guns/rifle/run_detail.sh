#!/usr/bin/env bash
# AR-01 detail pass: (re)build the form model, then per-part close-up cameras, traces and ROUGH LOOK crops.
# Usage: Scripts/guns/rifle/run_detail.sh [--parts selector,grip] [--tag before] [--no-build] [--force] [--force-panels]
#   --parts         detail-part modules (Scripts/guns/rifle/parts/); default all
#   --tag           prefix for ours/pair/edges/crops files (default: none = current)
#   --no-build      reuse Assets/Guns/AR01.blend + scratch/form_tris.npz
#   --force         re-solve the part cameras; --force-panels re-solves the panel cameras too (landmarks + silhouette)
# Needs: lock AR01 held by claude. Writes WorkFiles/guns/rifle/review/detail/<part>/ and scratch/detail/.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W="$ROOT/WorkFiles/guns/rifle"
mkdir -p "$W/scratch/logs"
BUILD=1; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --parts|--tag) ARGS+=("$1" "$2"); shift ;;
    --force|--force-panels) ARGS+=("$1") ;;
  esac
  shift
done
cd "$ROOT"
if [ $BUILD = 1 ]; then
  "$B" -b --factory-startup --python "$HERE/build_rifle.py" -- --stage form > "$W/scratch/logs/form.log" 2>&1 || true
  if grep -q "Traceback" "$W/scratch/logs/form.log"; then echo "FAILED form"; grep -A15 Traceback "$W/scratch/logs/form.log" | head -30; exit 1; fi
  grep -E "total tris" "$W/scratch/logs/form.log"
fi
py -3 -B "$HERE/rifle_detail.py" all "${ARGS[@]}" --json "$W/scratch/detail/last_run.json"
echo DETAIL_DONE
