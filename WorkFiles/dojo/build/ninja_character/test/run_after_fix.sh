#!/usr/bin/env bash
# play-test fix T1, then a FRESH headless port check and the -game re-verification (jumps, traversal, 1v1 attempts)
set -u
T="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/test"
bash C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal/run_ninja_port.sh fixjump check || exit 1
R='C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_ninja_playtest.ps1'
TW='C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\test'
powershell -NoProfile -ExecutionPolicy Bypass -File "$R" -Cfg "$TW\move\cfg_ninja_run3.json" -Log "$TW\logs\move_ninja_run3.log" -TimeoutMin 20 | tail -1
powershell -NoProfile -ExecutionPolicy Bypass -File "$R" -Cfg "$TW\routes\cfg_ninja_run3.json" -Log "$TW\logs\routes_ninja_run3.log" -TimeoutMin 25 | tail -1
echo AFTER_FIX_DONE
