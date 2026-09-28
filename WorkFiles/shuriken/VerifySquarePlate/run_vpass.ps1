# Run one verifier pass in its own fresh UnrealEditor-Cmd process (ShurikenValidation.uproject, legacy FBX importer).
# Usage: powershell -File run_vpass.ps1 -Form square_plate -Pass 1 [-Dest /Game/ShurikenVerifyIndep/SquarePlate] [-Tag after3]
param([Parameter(Mandatory)][string]$Form, [Parameter(Mandatory)][ValidateSet('1','2','3')][string]$Pass,
      [string]$Dest = '/Game/ShurikenVerifyIndep/SquarePlate', [string]$Tag = '')
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\VerifySquarePlate'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$script = @{ '1' = "$here\pass1_import.py"; '2' = "$here\pass2_reload.py"; '3' = "$here\pass3_export.py" }[$Pass]
$name = if ($Tag) { "${Form}_vpass${Pass}_$Tag" } else { "${Form}_vpass$Pass" }
$log = "$here\$name.log"
$env:VSP_FORM = $Form
$env:VSP_DEST = $Dest
$env:VSP_TAG = $Tag
$mesh = @{ 'square_plate' = 'SM_Shuriken_SquarePlate' }[$Form]
$uasset = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\Content\' + ($Dest -replace '^/Game/', '' -replace '/', '\') + "\$mesh.uasset"
$before = if (Test-Path $uasset) { (Get-FileHash $uasset -Algorithm SHA256).Hash.ToLower() } else { $null }
$argList = "`"$uproject`" -run=pythonscript -script=`"$script`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
$start = Get-Date
$p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
$lines = Get-Content $log
$we = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
$after = if (Test-Path $uasset) { (Get-FileHash $uasset -Algorithm SHA256).Hash.ToLower() } else { $null }
$summary = [ordered]@{ form = $Form; pass = $Pass; tag = $Tag; pid = $p.Id; exit = $p.ExitCode; start = $start.ToString('s');
  end = (Get-Date).ToString('s'); log = $log; log_lines = $lines.Count; warning_error_lines = $we.Count;
  warning_error_text = @($we | ForEach-Object { $_.Line }); stderr_bytes = (Get-Item "$log.stderr").Length;
  uasset = $uasset; uasset_sha256_before = $before; uasset_sha256_after = $after }
$summary | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$here\$name.run.json"
"form=$Form pass=$Pass tag=$Tag pid=$($p.Id) exit=$($p.ExitCode) log_lines=$($lines.Count) warning_error_lines=$($we.Count) uasset_before=$before uasset_after=$after"
$we | Select-Object -First 20 | ForEach-Object { "  " + $_.Line }
