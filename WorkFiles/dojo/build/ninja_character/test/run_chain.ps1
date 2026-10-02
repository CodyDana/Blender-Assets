$R = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_ninja_playtest.ps1'
$T = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\test'
$G = '?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C'
& $R -Cfg "$T\routes\cfg_gasp.json" -Log "$T\logs\routes_gasp.log" -Url $G -TimeoutMin 40
& $R -Cfg "$T\routes\cfg_ninja_run2.json" -Log "$T\logs\routes_ninja_run2.log" -TimeoutMin 20
& $R -Cfg "$T\move\cfg_gasp.json" -Log "$T\logs\move_gasp.log" -Url $G -TimeoutMin 20
& $R -Cfg "$T\move\cfg_ninja_run2.json" -Log "$T\logs\move_ninja_run2.log" -TimeoutMin 20
& $R -Cfg "$T\jutsu\cfg_ninja_run2.json" -Log "$T\logs\jutsu_ninja_run2.log" -TimeoutMin 30 -Sound
foreach ($n in 1, 2) {
  & $R -Script 'dj_ninja_perf.py' -Cfg "$T\perf\cfg_ninja_$n.json" -Log "$T\logs\perf_ninja_$n.log" -TimeoutMin 15
  & $R -Script 'dj_ninja_perf.py' -Cfg "$T\perf\cfg_gasp_$n.json" -Log "$T\logs\perf_gasp_$n.log" -Url $G -TimeoutMin 15
}
'CHAIN DONE'
