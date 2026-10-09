# AR-01 stage 8 pass E: ONE UnrealEditor-Cmd -game -RenderOffscreen run (real ticking world on <dest>/L_AR01_Check) executing
# arE_game.py through -ExecCmds="py ...". Waits behind the machine guard; kills only its own process on its own timeout.
param([string]$Script = 'arE_game.py', [string]$Log = 'arE_game.log', [int]$TimeoutMin = 12)
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path "$Here\..\..\..\..").Path
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Proj = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Root\WorkFiles\shuriken\UnrealCheck6\wait_unreal_free.ps1" -GuardLog "$Here\guard.log" -Label "AR01 $Script"
if ($LASTEXITCODE -ne 0) { "guard: not free"; exit 3 }
$py = (Join-Path $Here $Script).Replace([char]92, [char]47)
$logp = "$Here\$Log"
if (Test-Path $logp) { Remove-Item $logp -Force }
$Dest = (Get-Content (Join-Path $Here 'content_path.txt') -Raw).Trim()
$argl = @("`"$Proj`"", "$Dest/L_AR01_Check", '-game', '-RenderOffscreen', '-dx12', '-ResX=1280', '-ResY=720', '-windowed', '-unattended', '-nosplash',
          '-nop4', '-NoSound', '-NoLiveCoding', '-NoVSync', "-ExecCmds=`"py $py`"", "-abslog=`"$logp`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden -RedirectStandardOutput "$logp.stdout.txt" -RedirectStandardError "$logp.stderr.txt"
"started pid=$($p.Id)"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) { "TIMEOUT: killing own pid $($p.Id)"; Stop-Process -Id $p.Id -Force; exit 4 }
$p.WaitForExit()
"exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
