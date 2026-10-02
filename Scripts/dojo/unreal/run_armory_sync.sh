#!/usr/bin/env bash
# DojoLab side of the ARMORY HALL sync (WorkFiles/shared/armory_hall/SYNC.md section 3):
#   1. the file stage (plain Python): the armory's materials / textures / pack items copied from ArmoryLab by sha256;
#   2. the Unreal stage (ONE pythonscript commandlet on DojoLab): SM_AK_* re-imported by FBX sha256, the interior,
#      items and design + backer lights rebuilt in L_Dojo from the shared jsons, gates; WorkFiles/dojo/build/unreal/
#      armory_sync/sync.json.
# Guards (house rules): STOP (exit 3) if an UnrealEditor.exe has DojoLab open; wait while ANY UnrealEditor-Cmd runs
# (one commandlet machine-wide; never ours to touch). Never opens ArmoryLab (its files are only read).
set -u
export MSYS_NO_PATHCONV=1
HERE="C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/unreal/armory_sync"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
mkdir -p "$OUT/logs"
stamp() { echo "$(date '+%F %T') $*" | tee -a "$OUT/logs/timings.txt"; }
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then stamp "STOP editor open pid $hit"; exit 3; fi
}
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 8)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours)"
    n=$((n + 1)); sleep 15
  done
}
editor_guard; wait_free; editor_guard
stamp "start armory_sync files"
py -3 -B "$HERE/dj_armory_sync.py" files || { stamp "armory_sync files FAILED"; exit 1; }
FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
editor_guard; wait_free
stamp "start armory_sync unreal"
t0=$(date +%s)
timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$HERE/dj_armory_sync.py" $FLAGS $DPC > "$OUT/logs/sync.log" 2>&1; code=$?
t1=$(date +%s)
grep -q "DJ_STEP_DONE armory_sync passed=True" "$OUT/logs/sync.log" || { [ $code -eq 0 ] && code=8; }
stamp "armory_sync exit $code in $((t1 - t0)) s | $(grep -o 'DJ_STEP_DONE.*' "$OUT/logs/sync.log" | head -1)"
echo "    errors: $(grep -c 'Error:' "$OUT/logs/sync.log")  warnings: $(grep -c 'Warning:' "$OUT/logs/sync.log")"
exit $code
