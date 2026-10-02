$R = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_ninja_playtest.ps1'
$T = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\test'
$G = '?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C'
foreach ($n in 1, 2) {
  & $R -Script 'dj_ninja_perf.py' -Cfg "$T\perf\cfg_ninja_$n.json" -Log "$T\logs\perf_ninja_$n.log" -TimeoutMin 15
  & $R -Script 'dj_ninja_perf.py' -Cfg "$T\perf\cfg_gasp_$n.json" -Log "$T\logs\perf_gasp_$n.log" -Url $G -TimeoutMin 15
}
'CHAIN DONE'
