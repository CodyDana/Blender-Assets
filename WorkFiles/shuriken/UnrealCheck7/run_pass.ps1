# Run one UnrealCheck7 pass in its own fresh UnrealEditor-Cmd process (independent verifier).
# Project: the shuriken-only ShurikenValidation.uproject (legacy FBX importer).
# Usage: powershell -File run_pass.ps1 -Form eight_point -Pass 1     (passes 1-3 are per form)
#        powershell -File run_pass.ps1 -Form textures -Pass 4         (passes 4-5 import/reload the nine maps)
param([Parameter(Mandatory)][string]$Form, [Parameter(Mandatory)][ValidateSet('1','2','3','4','5')][string]$Pass)
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck7'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$script = @{ '1' = "$here\pass1_import.py"; '2' = "$here\pass2_reload.py"; '3' = "$here\pass3_export_diag.py";
             '4' = "$here\pass4_textures.py"; '5' = "$here\pass5_textures_reload.py" }[$Pass]
$log = "$here\${Form}_pass$Pass.log"
$env:SHURIKEN_FORM = $Form
if (-not $env:SHURIKEN_DEST) { $env:SHURIKEN_DEST = '/Game/ShurikenCheck7/Indep' }   # a run may pass a fresh content path
$argList = "`"$uproject`" -run=pythonscript -script=`"$script`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
$p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
$lines = Get-Content $log
$we = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
"form=$Form pass=$Pass exit=$($p.ExitCode) log_lines=$($lines.Count) warning_error_lines=$($we.Count)"
$we | Select-Object -First 20 | ForEach-Object { "  " + $_.Line }
