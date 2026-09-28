cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/previews/hero_backwall/final2"
run(){ "$B" -b --factory-startup --python Scripts/armory/hero/preview_hero.py -- --module hero_backwall "$@" --samples 64 --out "$O" --save 2>&1 | grep -E "^PREVIEW|Traceback|Error:" | grep -v HIP | cut -c1-200; }
run --pieces "SM_AK_Steps_2;SM_AK_Platform_Edge_2x1@0,0.75,0" --front -y --label steps --scripted
run --pieces "SM_AK_Platform_Edge_2x1" --front -y --label plat_edge --scripted
run --pieces "SM_AK_Platform_2x1" --front -y --label plat_top --scripted
run --pieces "SM_AK_PaintingPanel" --front +y --label painting --scripted
run --pieces "SM_AK_RearScreen" --front +y --label screen --scripted
run --pieces "SM_AK_Post_LED_480" --front -y --label post_led --scripted
run --pieces "SM_AK_Post_Heavy_480" --front -y --label post_heavy --scripted
run --pieces "SM_AK_LanternPedestal" --front -y --label pedestal --scripted
run --pieces "SM_AK_H_Canopy;SM_AK_H_DownlightBox@1.525,-0.295,0.10;SM_AK_H_Downlight@0.525,-0.295,0.10" --front -y --label canopy
run --pieces "$(cat "$O/bay_spec.txt")" --front -y --label bay --scripted
echo FINAL_DONE
