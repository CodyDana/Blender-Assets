#!/usr/bin/env bash
# HALL + ARMORY round copy of the fix round copy of fxlight/tools/run_fx.sh (logs in fix/logs). FX stage: install our DojoFXTools editor plugin into DojoLab ONLY for this run, run <script> through run_ue.sh (guards:
# no DojoLab editor open, wait for any UnrealEditor-Cmd), then remove the plugin again (no asset references it).
#   run_fx.sh <script.py> <logname> [render]
set -u
export MSYS_NO_PATHCONV=1
O="/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight"
F="/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/ue"
PL="/c/Users/Cody/Documents/Unreal Projects/DojoLab/Plugins"
P="$PL/DojoFXTools"
hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
[ -n "$hit" ] && { echo "STOP: DojoLab editor open ($hit)"; exit 3; }
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do sleep 15; done
[ -d "$PL" ] && [ "$(ls -A "$PL")" != "" ] && { echo "STOP: DojoLab/Plugins is not empty (another step's plugin?)"; ls "$PL"; exit 3; }
mkdir -p "$P"
cp -r "$O/plugin_build/DojoFXTools/DojoFXTools.uplugin" "$O/plugin_build/DojoFXTools/Binaries" "$P/"
bash "$F/tools/run_ue.sh" "$1" "$2" "${3:-null}"; code=$?
rm -rf "$P"; rmdir "$PL" 2>/dev/null
echo "plugin removed: $([ -d "$P" ] && echo NO || echo yes) exit $code"
exit $code
