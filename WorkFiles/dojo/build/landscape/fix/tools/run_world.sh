#!/usr/bin/env bash
# LANDSCAPE FIX ROUND world step (world/tools/run_world.sh with the fix round's logs): DojoLandscapeTools is installed in
# DojoLab ONLY for this run (dj_ls_world.py), then removed; the previous world build is cleared first in a null-RHI
# process (dj_ls_clear.py). Guards: no DojoLab editor open; wait for any UnrealEditor-Cmd; Plugins must be empty.
set -u
export MSYS_NO_PATHCONV=1
F="/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fix"
WB="/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/world/plugin_build"
PL="/c/Users/Cody/Documents/Unreal Projects/DojoLab/Plugins"
P="$PL/DojoLandscapeTools"
hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
[ -n "$hit" ] && { echo "STOP: DojoLab editor open ($hit)"; exit 3; }
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do sleep 15; done
[ -d "$PL" ] && [ "$(ls -A "$PL")" != "" ] && { echo "STOP: DojoLab/Plugins is not empty"; ls "$PL"; exit 3; }
bash "$F/tools/run_ue.sh" "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_clear.py" "${1:-ls_world}_clear" || exit $?
mkdir -p "$P"
cp -r "$WB/DojoLandscapeTools/DojoLandscapeTools.uplugin" "$WB/DojoLandscapeTools/Binaries" "$P/"
bash "$F/tools/run_ue.sh" "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_world.py" "${1:-ls_world}" render; code=$?
rm -rf "$P"; rmdir "$PL" 2>/dev/null
echo "plugin removed: $([ -d "$P" ] && echo NO || echo yes) exit $code"
exit $code
