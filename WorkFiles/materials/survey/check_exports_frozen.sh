#!/usr/bin/env bash
# Prove every EXISTING export file of the four in-scope items is byte-identical to its baseline, and list
# any NEW files (allowed) under the four export folders.  Read-only.  Exit 0 = frozen, 1 = a baseline file
# differs or is missing.
#   baselines: shuriken  WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt (export/, textures/)
#              smoke     WorkFiles/smokebomb/regression/post_smoke_bomb/SHA256SUMS.txt (Exports/SmokeBomb/...)
#              hat       WorkFiles/blackhat/regression/post_black_hat/SHA256SUMS.txt   (Exports/BlackHat/...)
#              paper     WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt  (Exports/PaperBomb/...)
#              survey    WorkFiles/materials/survey/exports_sha256_at_survey_2026-09-26.txt (all 63 files incl.
#                        Exports/PaperBomb/README.txt, which no older baseline lists)
# SUMS files are CRLF: strip \r before parsing.
set -u
cd "C:/Users/Cody/Desktop/Blender_Projects" || exit 2
W=WorkFiles
ok=0; bad=0
declare -A KNOWN
check() {
  local exp=$1 f=$2
  KNOWN["$f"]=1
  if [ -f "$f" ]; then
    local got; got=$(sha256sum "$f" | cut -d' ' -f1)
    if [ "$got" = "$exp" ]; then ok=$((ok+1)); else bad=$((bad+1)); echo "DIFF    $f"; fi
  else bad=$((bad+1)); echo "MISSING $f"; fi
}
while read -r h p; do p=${p#\*}; case $p in
  export/*) check "$h" "Exports/Shuriken/${p#export/}";;
  textures/*) check "$h" "Exports/Shuriken/Textures/${p#textures/}";; esac
done < <(tr -d '\r' < $W/shuriken/regression/post_kunai_plain/SHA256SUMS.txt)
while read -r h p; do p=${p#\*}; case $p in Exports/*) check "$h" "$p";; esac
done < <(cat $W/smokebomb/regression/post_smoke_bomb/SHA256SUMS.txt $W/blackhat/regression/post_black_hat/SHA256SUMS.txt \
             $W/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt | tr -d '\r' | grep -E "Exports/(SmokeBomb|BlackHat|PaperBomb)/")
while read -r h p; do p=${p#\*}; [ -n "${KNOWN[$p]+x}" ] || check "$h" "$p"
done < <(tr -d '\r' < $W/materials/survey/exports_sha256_at_survey_2026-09-26.txt)
echo "baseline files identical=$ok differing_or_missing=$bad"
echo "NEW files (allowed):"
find Exports/Shuriken Exports/SmokeBomb Exports/BlackHat Exports/PaperBomb -type f | sort | while read -r f; do
  [ -n "${KNOWN[$f]+x}" ] || echo "  NEW $f  $(sha256sum "$f" | cut -c1-16)"
done
[ "$bad" -eq 0 ]
