#!/usr/bin/env bash
# NINJA PORT INDEPENDENT VERIFIER: ONE Unreal process at a time on DojoLab (waits while any UnrealEditor-Cmd runs; STOP
# if any UnrealEditor* has DojoLab open). Writes only under ninja_character/verify/.
#   run_verify.sh sc | boundary | alley | game_ninja | game_gasp   (several allowed, run in order)
set -u
export MSYS_NO_PATHCONV=1
VD="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/verify"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
mkdir -p "$VD/logs"
note() { echo "$(date '+%F %T') $*" | tee -a "$VD/logs/runs.txt"; }
guard() {
  local free=0
  while [ $free -lt 3 ]; do
    if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 15; else free=$((free + 1)); sleep 3; fi
  done
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'UnrealEditor*' -and \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
  if [ -n "$hit" ]; then note "STOP: DojoLab open in pid $hit"; exit 3; fi
}
NULLF="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
game() {   # $1 tag, $2 mode, $3 url suffix
  printf '{"mode": "%s", "tag": "%s", "warm_s": 90}' "$2" "$1" > "$VD/logs/cfg_$1.json"
  guard
  note "start game $1 mode=$2 url=$3"
  V_CFG="$(cygpath -w "$VD/logs/cfg_$1.json")" timeout 1800 "$UE" "$PROJ" "/Game/Dojo/Maps/L_Dojo$3" -game -RenderOffscreen -dx12 \
    -ResX=1920 -ResY=1080 -windowed -unattended -nosplash -nop4 -NoLiveCoding -NoVSync -NoSound \
    "-ExecCmds=py $VD/ue/v_game_probe.py" "-abslog=$(cygpath -w "$VD/logs/game_$1.log")" > /dev/null 2>&1
  note "exit $? game $1 | $(grep -o 'VPROBE_DONE.*' "$VD/logs/game_$1.log" | head -1)"
}
for s in "$@"; do
  case "$s" in
    sc)
      guard; note "start sc_verify"
      timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$VD/ue/v_sc_verify_wrap.py" $NULLF $DPC > "$VD/logs/sc_verify.log" 2>&1
      note "exit $? sc | $(grep -o 'DJ_STEP_DONE.*' "$VD/logs/sc_verify.log" | head -1 | cut -c1-400)" ;;
    boundary)
      guard; note "start boundary"
      DJ_PARTS=height,routes,interior,flood1v1 DJ_OUT=ue_boundary.json timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$VD/ue/v_ue_boundary.py" $NULLF $DPC > "$VD/logs/boundary.log" 2>&1
      note "exit $? boundary | $(grep -oE 'VHA[A-Z_]*_DONE.*' "$VD/logs/boundary.log" | head -1 | cut -c1-300)" ;;
    alley)
      guard; note "start alley"
      DJ_ZB0=0.13 DJ_PARTS=mantle,flood DJ_OUT=ue_alley.json timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$VD/ue/v_ue_alley.py" $NULLF $DPC > "$VD/logs/alley.log" 2>&1
      note "exit $? alley | $(grep -oE 'VHA[A-Z_]*_DONE.*' "$VD/logs/alley.log" | head -1 | cut -c1-300)" ;;
    game_ninja) game ninja ninja "" ;;
    game_gasp) game gasp gasp "?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C" ;;
    *) echo "unknown $s"; exit 2 ;;
  esac
done
note "ALL DONE $*"
