#!/bin/sh
# Stage 8 (Unreal) runner for AR-01. ONE Unreal commandlet / headless process on the machine at a time:
# waits behind the machine guard (WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1), stops only its own leftover.
# usage: run_ue.sh <script.py> <log> [render|editor]   (AR_DEST from content_path.txt)
export MSYS_NO_PATHCONV=1
HERE="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd -W 2>/dev/null || pwd)"
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UEG="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
export AR_DEST="$(cat "$HERE/content_path.txt")"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1" -GuardLog "$HERE/guard.log" -Label "AR01 $1" || { echo "guard: not free; not starting"; exit 3; }
if [ "$3" = "render" ]; then EXTRA="-AllowCommandletRendering -RenderOffscreen"; else EXTRA="-nullrhi -nosound"; fi
echo "start $(date +%T) $1 dest=$AR_DEST"
if [ "$3" = "game" ]; then
  timeout 900 "$UE" "$PROJ" -game -RenderOffscreen -dx12 -ResX=1280 -ResY=720 -windowed -unattended -nosplash -nop4 -NoSound -NoLiveCoding -NoVSync -ExecutePythonScript=$HERE/$1 -stdout -FullStdOutLogOutput > "$HERE/$2" 2>&1
elif [ "$3" = "editor" ]; then
  timeout 1500 "$UEG" "$PROJ" -ExecutePythonScript="$HERE/$1" -unattended -nop4 -nosplash -nosound -RenderOffscreen -stdout -FullStdOutLogOutput -log > "$HERE/$2" 2>&1
else
  timeout 1800 "$UE" "$PROJ" -run=pythonscript -script="$HERE/$1" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$HERE/$2" 2>&1
fi
rc=$?
SN=$(basename "$1")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | Where-Object { \$_.CommandLine -like '*$SN*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
echo "end $(date +%T) ue rc=$rc; warning/error lines: $(grep -c -E 'Warning:|Error:' "$HERE/$2"); python errors: $(grep -c 'LogPython: Error' "$HERE/$2")"
