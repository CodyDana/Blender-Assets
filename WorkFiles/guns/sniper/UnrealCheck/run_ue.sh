#!/bin/sh
# SR01 W5 (Unreal) pass runner. ONE Unreal process on the machine at a time: waits behind sr_guard.ps1 (any
# UnrealEditor*.exe = busy), stops only its own leftover (matched by its script name), never another process.
# usage: run_ue.sh <script.py> <log> [cmd|render|tools]   (SR_DEST from content_path.txt)
#   cmd    = -run=pythonscript -nullrhi (import / read-back)
#   render = -run=pythonscript with D3D12 offscreen rendering
#   tools  = cmd + -EnablePlugins=AllToolsets (the Blueprint graph toolset used to author the U2b ABP)
export MSYS_NO_PATHCONV=1
HERE="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
export SR_DEST="$(cat "$HERE/content_path.txt" | tr -d '\r\n')"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$HERE/sr_guard.ps1" -GuardLog "$HERE/guard.log" -Label "SR01 $1" || { echo "guard: not free; not starting"; exit 3; }
case "$3" in
  render) EXTRA="-AllowCommandletRendering -RenderOffscreen" ;;
  tools)  EXTRA="-nullrhi -nosound -EnablePlugins=AllToolsets" ;;
  *)      EXTRA="-nullrhi -nosound" ;;
esac
echo "start $(date +%T) $1 dest=$SR_DEST mode=${3:-cmd}"
timeout 1800 "$UE" "$PROJ" -run=pythonscript -script="$HERE/$1" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$HERE/$2" 2>&1
rc=$?
SN=$(basename "$1")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | Where-Object { \$_.CommandLine -like '*$SN*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
echo "end $(date +%T) ue rc=$rc; warning/error lines: $(grep -c -E 'Warning:|Error:' "$HERE/$2"); python errors: $(grep -c 'LogPython: Error' "$HERE/$2")"
