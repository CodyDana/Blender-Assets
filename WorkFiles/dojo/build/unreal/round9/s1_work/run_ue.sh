#!/usr/bin/env bash
# Round 8: run ONE pythonscript commandlet (-nullrhi) on DojoLab with the house guards (stop if a DojoLab editor is
# open; wait while any UnrealEditor-Cmd runs). usage: run_ue.sh <abs script.py> <log path>
set -u
export MSYS_NO_PATHCONV=1
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then echo "STOP: DojoLab editor open (pid $hit). Nothing run."; exit 3; fi
}
guard
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting for another UnrealEditor-Cmd"; sleep 20; done
guard
t0=$(date +%s)
timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$1" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput \
  "-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0" > "$2" 2>&1
code=$?
echo "exit $code in $(( $(date +%s) - t0 )) s; errors $(grep -c 'Error:' "$2")"
