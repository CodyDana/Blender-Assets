#!/usr/bin/env bash
# VERIFIER (hall + armory): ONE fresh read-only pythonscript commandlet on DojoLab running verify/<arg1>, log verify/<arg2>.
# Waits while ANY UnrealEditor-Cmd runs (one commandlet machine-wide; never ours to touch); stops if a DojoLab editor or
# any other process has DojoLab.uproject open.
set -u
export MSYS_NO_PATHCONV=1
VD="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/finish/checks/ue"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
S="$1"; LOG="$2"
guard() {
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'UnrealEditor*' -and \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
  if [ -n "$hit" ]; then echo "STOP: a process has DojoLab open (pid $hit)"; exit 3; fi
}
free=0
while [ $free -lt 2 ]; do
  if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 20; else free=$((free + 1)); sleep 5; fi
done
guard
echo "start $S $(date '+%F %T') parts=${DJ_PARTS:-} out=${DJ_OUT:-}" | tee -a "$VD/ue_runs.txt"
timeout 7200 "$UE" "$PROJ" -run=pythonscript -script="$VD/$S" -unattended -nop4 -nosplash -nullrhi -nosound \
  -stdout -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncStaticMeshCompilation=0" > "$VD/$LOG" 2>&1
code=$?
echo "exit $code $(date '+%F %T')" | tee -a "$VD/ue_runs.txt"
grep -oE "VHA[A-Z0-9_]*_DONE.*" "$VD/$LOG" | head -3 | tee -a "$VD/ue_runs.txt"
