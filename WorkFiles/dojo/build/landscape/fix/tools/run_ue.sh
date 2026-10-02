#!/usr/bin/env bash
# LANDSCAPE FIX ROUND runner (a copy of world/tools/run_ue.sh, logs in fix/logs): ONE UnrealEditor-Cmd pythonscript commandlet on DojoLab, guarded like
# Scripts/dojo/unreal/run_showcase_unreal.sh: STOP (exit 3) if an UnrealEditor.exe has DojoLab open; wait while ANY
# UnrealEditor-Cmd runs (never ours to touch); never kills anything but its own process on its own timeout.
#   run_ue.sh <script.py> <logname> [render]      render = -AllowCommandletRendering (a real RHI, D3D12) instead of -nullrhi
set -u
export MSYS_NO_PATHCONV=1
SCRIPT="$1"; NAME="$2"; MODE="${3:-null}"
W="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fix"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
LOG="$W/logs/$NAME.log"
mkdir -p "$W/logs"
stamp() { echo "$(date '+%F %T') $*" | tee -a "$W/logs/timings.txt"; }
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then stamp "STOP editor open pid $hit ($NAME)"; exit 3; fi
}
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 8)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours)"
    n=$((n + 1)); sleep 15
  done
}
editor_guard; wait_free; editor_guard
if [ "$MODE" = "render" ]; then
  FLAGS="-unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput -AllowCommandletRendering -dx12"
else
  FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
fi
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
stamp "start $NAME ($MODE) $SCRIPT"
t0=$(date +%s)
timeout 7200 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" $FLAGS $DPC > "$LOG" 2>&1; code=$?
t1=$(date +%s)
stamp "$NAME exit $code in $((t1 - t0)) s | $(grep -o 'DJ_STEP_DONE.*' "$LOG" | head -1)"
echo "    errors: $(grep -c 'Error:' "$LOG")  warnings: $(grep -c 'Warning:' "$LOG")"
exit $code
