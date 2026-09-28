# Run one UnrealCheck6 pass for one form in its own fresh UnrealEditor-Cmd process.
# Project: the shuriken-only ShurikenValidation.uproject (legacy FBX importer). Adapted from the
# verifier's UnrealCheck5/run_pass.ps1, which ran in UnrealTest.
# Usage: powershell -File run_pass.ps1 -Form eight_point -Pass 1
param([Parameter(Mandatory)][string]$Form, [Parameter(Mandatory)][ValidateSet('1','2','3')][string]$Pass)
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck6'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$script = @{ '1' = "$here\pass1_import.py"; '2' = "$here\pass2_reload.py"; '3' = "$here\pass3_export_diag.py" }[$Pass]
$log = "$here\${Form}_pass$Pass.log"
$env:SHURIKEN_FORM = $Form
$argList = "`"$uproject`" -run=pythonscript -script=`"$script`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
$p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
$lines = Get-Content $log
$we = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
"form=$Form pass=$Pass exit=$($p.ExitCode) log_lines=$($lines.Count) warning_error_lines=$($we.Count)"
$we | Select-Object -First 20 | ForEach-Object { "  " + $_.Line }
