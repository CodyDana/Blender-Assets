# usage: bash final.sh <samples> <outdir>
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
SMP="${1:-64}"
O="${2:-C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/previews/hero_backwall/final4}"
F="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/previews/hero_backwall/final4"
run(){ "$B" -b --factory-startup --python Scripts/armory/hero/preview_hero.py -- --module hero_backwall "$@" --samples "$SMP" --out "$O" --save 2>&1 | grep -E "^PREVIEW|Traceback|Error:" | grep -v HIP | cut -c1-200; }
run --pieces "SM_AK_Steps_2;SM_AK_Platform_Edge_2x1@0,0.75,0" --front -y --label steps --scripted
run --pieces "SM_AK_Platform_Edge_2x1" --front -y --label plat_edge --scripted
run --pieces "SM_AK_Platform_2x1" --front -y --label plat_top --scripted
run --pieces "SM_AK_PaintingPanel@0,0,0.9;SM_AK_H_PaintingBase" --front +y --label painting --scripted
run --pieces "SM_AK_RearScreen" --front +y --label screen --scripted
run --pieces "SM_AK_Post_LED_480" --front -y --label post_led --scripted
run --pieces "SM_AK_Post_Heavy_480" --front -y --label post_heavy --scripted
run --pieces "SM_AK_Post_Heavy_480;SM_AK_Post_Heavy_480@4.5,0,0;SM_AK_H_TopBeam@0.155,-0.13,4.40;SM_AK_LanternPedestal@0,-0.37,0;SM_AK_LanternPedestal@4.5,-0.37,0" --front -y --label portal
run --pieces "SM_AK_LanternPedestal" --front -y --label pedestal --scripted
run --pieces "SM_AK_H_Canopy;SM_AK_H_DownlightBox@1.525,-0.49,0.30;SM_AK_H_Downlight@0.525,-0.49,0.30" --front -y --label canopy
run --pieces "$(cat "$F/bay_spec.txt")" --front -y --label bay --scripted
mkdir -p "$O/ctx"
"$B" -b --factory-startup --python "$F/ctx_bay.py" -- "$O/ctx" "$F/bay_spec.txt" "$SMP" 2>&1 | grep -E "Traceback|rror:" | grep -v HIP
"/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" "$F/compose.py" "$O/ctx" "$O"
echo FINAL_DONE
