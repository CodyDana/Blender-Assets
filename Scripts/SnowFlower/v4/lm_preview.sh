#!/usr/bin/env bash
# look-match preview: lm_preview.sh <outdir> <parts|all> <views> [what] [tag] [samples]
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
PY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
V4="C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4"
OUT=$(cd "$(dirname "$1")" 2>/dev/null && pwd -W)/$(basename "$1"); [ -d "$(dirname "$1")" ] || { echo "parent of $1 missing"; exit 1; }; PARTS=$2; VIEWS=$3; WHAT=${4:-high}; TAG=${5:-}; SAMP=${6:-48}
[ "$PARTS" = all ] && PARTS=""
mkdir -p "$OUT"
"$B" -b --factory-startup --python "$V4/sfv4_lm_preview.py" -- --out "$OUT" --parts "$PARTS" --views "$VIEWS" --what $WHAT --tag "$TAG" --samples $SAMP > "$OUT/${TAG}preview.log" 2>&1
grep -E "LMP|Error|Traceback" "$OUT/${TAG}preview.log" | tail -12
grep -A12 Traceback "$OUT/${TAG}preview.log" | head -30
"$PY" "$V4/sfv4_lm_compose.py" "$OUT" "$OUT/cmp_${TAG}" "$VIEWS" "$TAG"
