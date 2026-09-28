#!/bin/sh
# Runs ONE UE 5.8 pythonscript commandlet for the fan checks (one process at a time; never left running).
# usage: run_ue.sh <script.py> <log> [render]   env: FAN_EXPORTS FAN_REPORT FAN_DEST FAN_OUT
# Round 2: it only ever stops ITS OWN process (found by this run's script path on the command line), never
# another session's editor.
export MSYS_NO_PATHCONV=1
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "another UnrealEditor-Cmd is running; not starting"; exit 3; fi
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
if [ "$3" = "render" ]; then EXTRA="-AllowCommandletRendering -RenderOffscreen"; else EXTRA="-nullrhi -nosound"; fi
timeout 460 "$UE" "$PROJ" -run=pythonscript -script="$1" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$2" 2>&1
rc=$?
SCRIPT_NAME=$(basename "$1")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor-Cmd.exe'\" | Where-Object { \$_.CommandLine -like '*$SCRIPT_NAME*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
echo "ue rc=$rc; python errors: $(grep -c 'LogPython: Error' "$2")"
