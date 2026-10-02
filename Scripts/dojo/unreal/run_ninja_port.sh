#!/usr/bin/env bash
# DojoLab ninja character port (DemoGame_1 -> DojoLab, 2026-10-02): the Unreal-side steps, ONE process at a time.
#   run_ninja_port.sh [steps...]      default: build setup ini check
# steps:
#   build   Build.bat DojoLabEditor Win64 Development (UnrealBuildTool; -NoHotReloadFromIDE because Build.bat refuses with
#           "Live Coding is active" whenever ANY editor of this engine runs, even another project's)
#   setup   commandlet -nullrhi: dj_ninja_setup.py (BP_NinjaGasp components, IMC_NinjaGasp trim, GM_DojoNinja, L_Dojo
#           world game mode)
#   ini     (no Unreal) Config/DefaultEngine.ini GlobalDefaultGameMode GM_Dojo -> GM_DojoNinja
#   check   commandlet -nullrhi, FRESH process: dj_ninja_check.py (load L_Dojo + every ported package; log scan)
#   fixjump commandlet -nullrhi: dj_ninja_fixjump.py (play-test fix T1: BP_NinjaGasp CDO jump_max_count = GASP's
#           SandboxCharacter_CMC value; DemoGame_1's setup wrote 2 for the removed air-jump flip)
# Guards (house rules): STOP (exit 3) if an UnrealEditor.exe has DojoLab open; wait while ANY UnrealEditor-Cmd runs
# (one commandlet machine-wide; never ours to touch); the build also waits, so it never competes with another chat's run.
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-build setup ini check}"
HERE="C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/build"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
BUILD_BAT="C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
INI="C:/Users/Cody/Documents/Unreal Projects/DojoLab/Config/DefaultEngine.ini"
mkdir -p "$OUT/logs"
FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
stamp() { echo "$(date '+%F %T') $*" | tee -a "$OUT/logs/timings.txt"; }
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then stamp "STOP editor open pid $hit"; exit 3; fi
}
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 8)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours)"
    n=$((n + 1)); sleep 15
  done
}
for step in $STEPS; do
  t0=$(date +%s)
  case "$step" in
    build)
      editor_guard; wait_free; editor_guard
      stamp "start build"
      powershell -NoProfile -Command "& '$(cygpath -w "$BUILD_BAT")' DojoLabEditor Win64 Development '-Project=$(cygpath -w "$PROJ")' -WaitMutex -NoHotReloadFromIDE; exit \$LASTEXITCODE" > "$OUT/logs/build.log" 2>&1; code=$?
      [ -f "C:/Users/Cody/Documents/Unreal Projects/DojoLab/Binaries/Win64/UnrealEditor-DojoLab.dll" ] || { [ $code -eq 0 ] && code=8; } ;;
    setup|check|fixjump)
      editor_guard; wait_free; editor_guard
      stamp "start $step"
      timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$HERE/dj_ninja_$step.py" $FLAGS $DPC > "$OUT/logs/$step.log" 2>&1; code=$?
      grep -q "DJ_STEP_DONE ninja_$step passed=True" "$OUT/logs/$step.log" || { [ $code -eq 0 ] && code=8; } ;;
    ini)
      py -3 - "$INI" <<'PYEOF'
import sys
from pathlib import Path
p = Path(sys.argv[1]); b = p.read_bytes().decode("utf-8")
old = "GlobalDefaultGameMode=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C"
new = "GlobalDefaultGameMode=/Game/Dojo/Blueprints/GM_DojoNinja.GM_DojoNinja_C"
if new in b:
    print("ini: already GM_DojoNinja")
elif b.count(old) == 1:
    p.write_bytes(b.replace(old, new).encode("utf-8")); print("ini: GlobalDefaultGameMode -> GM_DojoNinja")
else:
    print("ini: GlobalDefaultGameMode line not found once"); sys.exit(1)
PYEOF
      code=$? ;;
    *) echo "unknown step $step"; exit 2 ;;
  esac
  t1=$(date +%s)
  stamp "$step exit $code in $((t1 - t0)) s"
  if [ "$step" = "setup" ] || [ "$step" = "check" ] || [ "$step" = "fixjump" ]; then
    echo "    errors: $(grep -c 'Error:' "$OUT/logs/$step.log")  warnings: $(grep -c 'Warning:' "$OUT/logs/$step.log")"
  fi
  if [ $code -ne 0 ]; then echo "STOP: $step failed (exit $code), see $OUT/logs/$step.log"; exit 1; fi
done
echo "=== done $(date +%T)"
