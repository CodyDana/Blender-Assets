#!/bin/sh
# One UnrealEditor-Cmd at a time. Waits while any other UnrealEditor-Cmd runs; stops only its own leftover.
# usage: run_ue.sh <script.py> <log> [render]
export MSYS_NO_PATHCONV=1
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
n=0
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do n=$((n+1)); [ $n -gt 40 ] && { echo "another UnrealEditor-Cmd still running; giving up"; exit 3; }; sleep 10; done
if [ "$3" = "render" ]; then EXTRA="-AllowCommandletRendering -RenderOffscreen"; else EXTRA="-nullrhi -nosound"; fi
timeout 460 "$UE" "$PROJ" -run=pythonscript -script="$1" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$2" 2>&1
rc=$?
SN=$(basename "$1")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor-Cmd.exe'\" | Where-Object { \$_.CommandLine -like '*$SN*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
echo "ue rc=$rc; warning/error lines: $(grep -c -E 'Warning:|Error:' "$2"); python errors: $(grep -c 'LogPython: Error' "$2")"
