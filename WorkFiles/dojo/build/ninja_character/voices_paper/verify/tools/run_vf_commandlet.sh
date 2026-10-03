#!/usr/bin/env bash
# INDEPENDENT VERIFIER: one pythonscript commandlet on DojoLab (-nullrhi), guarded like run_ninja_port.sh:
# STOP if an UnrealEditor*.exe has DojoLab open; wait while ANY UnrealEditor-Cmd runs (never ours to touch).
#   run_vf_commandlet.sh <script.py> <logname> <done-marker>
set -u
export MSYS_NO_PATHCONV=1
SCRIPT="$1"; NAME="$2"; MARK="$3"
V="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/voices_paper/verify"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
mkdir -p "$V/logs"
stamp() { echo "$(date '+%F %T') $*" | tee -a "$V/logs/timings.txt"; }
guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'UnrealEditor*' -and \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then stamp "STOP DojoLab open in pid $hit"; exit 3; fi
}
guard
n=0
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
  [ $((n % 8)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours)"
  n=$((n + 1)); sleep 15
done
guard
stamp "start $NAME"
t0=$(date +%s)
timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" -unattended -nop4 -nosplash -nullrhi -nosound -stdout \
  -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0" \
  > "$V/logs/$NAME.log" 2>&1
code=$?
stamp "$NAME exit $code in $(( $(date +%s) - t0 )) s | $(grep -o "$MARK.*" "$V/logs/$NAME.log" | head -1)"
echo "    errors: $(grep -c 'Error:' "$V/logs/$NAME.log")  ensures: $(grep -ci 'ensure' "$V/logs/$NAME.log")"
