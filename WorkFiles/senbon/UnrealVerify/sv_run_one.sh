#!/usr/bin/env bash
# Run ONE Unreal pythonscript commandlet (fresh process) on the validation project.
# Refuses if any UnrealEditor-Cmd is already running (the user's own UnrealEditor.exe on another project is left alone).
# Usage: sv_run_one.sh <label> <script.py> [render]
set -u
export MSYS_NO_PATHCONV=1
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
HERE="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/senbon/UnrealVerify"
if [ "${3:-}" = "render" ]; then EXTRA="-AllowCommandletRendering -RenderOffscreen -nosound -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"; else EXTRA="-nullrhi -nosound"; fi
if tasklist | grep -i -q "UnrealEditor-Cmd"; then
  echo "REFUSED: an UnrealEditor-Cmd is already running"; tasklist | grep -i unreal; exit 3
fi
echo "=== $1 start $(date +%T)"
timeout 460 "$UE" "$PROJ" -run=pythonscript -script="$2" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$HERE/$1.log" 2> "$HERE/$1.log.stderr"
code=$?
echo "    exit $code end $(date +%T)"
echo "    LogPython Error lines: $(grep -c 'LogPython: Error' "$HERE/$1.log")   Warning:/Error: lines: $(grep -c -E 'Warning:|Error:' "$HERE/$1.log")"
SN=$(basename "$2")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor-Cmd.exe'\" | Where-Object { \$_.CommandLine -like '*$SN*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
if tasklist | grep -i -q "UnrealEditor-Cmd"; then echo "WARNING: an UnrealEditor-Cmd is still running"; tasklist | grep -i unreal; else echo "    no UnrealEditor-Cmd left running"; fi
