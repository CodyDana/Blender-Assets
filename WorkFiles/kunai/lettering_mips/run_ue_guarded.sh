#!/usr/bin/env bash
# One Unreal commandlet at a time on this machine: wait (never touch) while any UnrealEditor-Cmd runs or any
# UnrealEditor.exe was started headless (-run= / -nullrhi / -ExecutePythonScript), then run ONE script on the
# validation project with a real RHI.   usage: run_ue_guarded.sh <script.py> <log>
set -u
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="$ROOT/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
busy() {
  powershell -NoProfile -Command "\$p = Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | Where-Object { \$_.Name -eq 'UnrealEditor-Cmd.exe' -or \$_.CommandLine -match '-run=|-nullrhi|-ExecutePythonScript' }; if (\$p) { 'BUSY ' + ((\$p | ForEach-Object ProcessId) -join ',') }"
}
for i in $(seq 1 360); do
  b="$(busy)"
  if [ -z "$b" ]; then break; fi
  echo "$(date +%T) waiting: $b" | tee -a "$2.guard"
  sleep 15
done
b="$(busy)"; if [ -n "$b" ]; then echo "STOP: Unreal still busy after 90 min: $b"; exit 3; fi
echo "$(date +%T) free, launching $1" | tee -a "$2.guard"
timeout 1800 "$UE" "$PROJ" -run=pythonscript -script="$1" -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput \
  -AllowCommandletRendering -RenderOffscreen -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0 > "$2" 2>&1
echo "exit $?"
