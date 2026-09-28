#!/usr/bin/env bash
# Run ONE Unreal pythonscript commandlet on the validation project.  Waits (up to ~7 min) while any
# UnrealEditor-Cmd process is running; the other session's GUI UnrealEditor.exe is never touched.
# Usage: bhv_run_one.sh <label> <script.py>
set -u
export MSYS_NO_PATHCONV=1
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
HERE="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/UnrealVerify_indep_v1"
FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
for i in $(seq 1 42); do
  if tasklist | grep -i -q "UnrealEditor-Cmd"; then echo "waiting: UnrealEditor-Cmd running"; sleep 10; else break; fi
done
if tasklist | grep -i -q "UnrealEditor-Cmd"; then echo "REFUSED: UnrealEditor-Cmd still running"; exit 3; fi
echo "=== $1 start $(date +%T)"
"$UE" "$PROJ" -run=pythonscript -script="$2" $FLAGS > "$HERE/$1.log" 2> "$HERE/$1.log.stderr"
code=$?
echo "    exit $code end $(date +%T)"
echo "    Warning:/Error: lines: $(grep -c -E 'Warning:|Error:' "$HERE/$1.log")"
if tasklist | grep -i -q "UnrealEditor-Cmd"; then echo "WARNING: UnrealEditor-Cmd still running"; else echo "    no UnrealEditor-Cmd left running"; fi
