#!/usr/bin/env bash
# LANDSCAPE ROUND world step: install our editor helper plugin into DojoLab ONLY for this run, run dj_ls_world.py in a
# rendering commandlet (guards in run_ue.sh), then remove the plugin again (nothing in the level references it).
set -u
export MSYS_NO_PATHCONV=1
W="/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/world"
P="/c/Users/Cody/Documents/Unreal Projects/DojoLab/Plugins/DojoLandscapeTools"
SCRIPT="${1:-C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_world.py}"
NAME="${2:-ls_world}"
hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
[ -n "$hit" ] && { echo "STOP: DojoLab editor open ($hit)"; exit 3; }
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do sleep 15; done
# clear the previous world build first in a null-RHI process (see dj_ls_clear.py)
bash "$W/tools/run_ue.sh" "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_clear.py" ls_clear || exit $?
mkdir -p "$P"
cp -r "$W/plugin_build/DojoLandscapeTools/DojoLandscapeTools.uplugin" "$W/plugin_build/DojoLandscapeTools/Binaries" "$P/"
bash "$W/tools/run_ue.sh" "$SCRIPT" "$NAME" render; code=$?
rm -rf "$P"; rmdir "/c/Users/Cody/Documents/Unreal Projects/DojoLab/Plugins" 2>/dev/null
echo "plugin removed: $([ -d "$P" ] && echo NO || echo yes) exit $code"
exit $code
