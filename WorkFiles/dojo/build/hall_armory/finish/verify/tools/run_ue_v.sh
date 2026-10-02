#!/usr/bin/env bash
# VERIFIER (finish stage): ONE fresh read-only pythonscript commandlet on DojoLab; logs in finish/verify/logs.
# Waits while ANY UnrealEditor-Cmd runs; STOP if any process has DojoLab.uproject open.
set -u
export MSYS_NO_PATHCONV=1
VD="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/finish/verify"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
S="$1"; LOG="$2"
free=0
while [ $free -lt 2 ]; do
  if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 20; else free=$((free + 1)); sleep 5; fi
done
hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'UnrealEditor*' -and \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
if [ -n "$hit" ]; then echo "STOP: a process has DojoLab open (pid $hit)"; exit 3; fi
echo "start $S $(date '+%F %T') parts=${DJ_PARTS:-} out=${DJ_OUT:-}" | tee -a "$VD/logs/ue_runs.txt"
timeout 7200 "$UE" "$PROJ" -run=pythonscript -script="$S" -unattended -nop4 -nosplash -nullrhi -nosound \
  -stdout -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0" > "$VD/logs/$LOG" 2>&1
code=$?
echo "exit $code $(date '+%F %T')" | tee -a "$VD/logs/ue_runs.txt"
grep -oE "(VHA[A-Z0-9_]*_DONE|DJ_STEP_DONE).*" "$VD/logs/$LOG" | head -3 | cut -c1-400 | tee -a "$VD/logs/ue_runs.txt"
