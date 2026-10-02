#!/usr/bin/env bash
# ROUND 6: fresh read-only commandlets on DojoLab, one at a time (waits while ANY UnrealEditor-Cmd runs; stops if a
# DojoLab editor is open). Usage: run_r6_ue.sh <script.py> [<script.py> ...]; logs next to the scripts.
set -u
export MSYS_NO_PATHCONV=1
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fix/checks/ue"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
for s in "$@"; do
  free=0
  while [ $free -lt 2 ]; do
    if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 20; else free=$((free + 1)); sleep 5; fi
  done
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
  if [ -n "$hit" ]; then echo "STOP: DojoLab editor open (pid $hit)"; exit 3; fi
  echo "start $s $(date '+%T')"
  timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$D/$s" -unattended -nop4 -nosplash -nullrhi -nosound \
    -stdout -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncStaticMeshCompilation=0" > "$D/${s%.py}.log" 2>&1
  echo "exit $? $(date '+%T') $(grep -oE '(V5_[A-Z0-9]+_DONE|R6_REPLAY_DONE).*' "$D/${s%.py}.log" | head -1)"
done
