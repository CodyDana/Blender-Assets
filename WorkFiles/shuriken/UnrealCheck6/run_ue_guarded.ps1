# Run ONE Unreal pythonscript commandlet in its own fresh UnrealEditor-Cmd process, after the one-Unreal-at-a-time guard
# (wait_unreal_free.ps1). 3.11 (the kunai blade section): generalises run_pass.ps1 (kept unchanged) to any script and
# log path, so the run's evidence lands in its own folder (UC6_OUT). Environment (SHURIKEN_FORM, SHURIKEN_DEST, UC6_OUT,
# SHURIKEN_TEXTURE_*) is inherited from the caller.
# Usage: powershell -File run_ue_guarded.ps1 -Script <py> -Log <path> -GuardLog <path> [-Label text]
param([Parameter(Mandatory)][string]$Script, [Parameter(Mandatory)][string]$Log,
      [Parameter(Mandatory)][string]$GuardLog, [string]$Label = '')
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck6'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$here\wait_unreal_free.ps1" -GuardLog $GuardLog -Label $Label
if ($LASTEXITCODE -ne 0) { "ABORT: Unreal still busy after 90 min; not launching $Label"; exit 2 }
$argList = "`"$uproject`" -run=pythonscript -script=`"$Script`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
# Wait for the commandlet only (PowerShell 5.1's -Wait also waits for descendants such as UnrealTraceServer).
$p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $Log -RedirectStandardError "$Log.stderr"
$null = $p.Handle
Add-Content -Path $GuardLog -Value "$((Get-Date).ToString('o')) LAUNCH pid=$($p.Id) $Label" -Encoding utf8
$p.WaitForExit()
Add-Content -Path $GuardLog -Value "$((Get-Date).ToString('o')) EXIT   pid=$($p.Id) code=$($p.ExitCode) $Label" -Encoding utf8
$lines = Get-Content $Log
$we = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
"$Label exit=$($p.ExitCode) log_lines=$($lines.Count) warning_error_lines=$($we.Count)"
$we | Select-Object -First 20 | ForEach-Object { "  " + $_.Line }
