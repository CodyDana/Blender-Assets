# VERIFY r8: ONE offscreen UnrealEditor-Cmd -game run of L_Dojo executing v8_game_perf.py (GPU frame time per view and
# resolution). Guards as Scripts/dojo/unreal/run_game_capture.ps1: waits (30 s polls, max 60 min) while any
# UnrealEditor-Cmd.exe runs, stops if DojoLab is open in an UnrealEditor.exe, kills only its own process and only on its
# own timeout. Read-only for the project content (writes game_perf.json, the engine CSV profiles and logs).
param([int]$TimeoutMin = 30)
$ErrorActionPreference = 'Stop'
$VD = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r8'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Log = "$VD\game_perf.log"
$Guard = "$VD\game_perf_guard.txt"
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(60)
$free = 0
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $dojo = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'DojoLab' })
    if ($dojo.Count -gt 0) { Note "STOP: DojoLab is open in UnrealEditor.exe pid $($dojo.ProcessId -join ','); nothing run"; exit 3 }
    if ($busy.Count -eq 0) { $free++ } else { $free = 0 }
    if ($free -ge 2) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 60 min of waiting'; exit 3 }
    Start-Sleep -Seconds 15
}
if (Test-Path $Log) { Remove-Item $Log -Force }
$csvDir = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\Saved\Profiling\CSV'
Note "csv files before: $(@(Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue).Count)"
$py = "$VD\v8_game_perf.py" -replace '\\', '/'
$argl = @("`"$Proj`"", '/Game/Dojo/Maps/L_Dojo', '-game', '-RenderOffscreen', '-dx12', '-ResX=1920', '-ResY=1080',
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding', '-NoVSync', '-csvGpuStats',
          "-ExecCmds=`"py $py`"", "-abslog=`"$Log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Log.stdout.txt" -RedirectStandardError "$Log.stderr.txt"
Note "started pid=$($p.Id)"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $t0 } |
    ForEach-Object { Note "csv $($_.FullName) $($_.Length)" }
exit 0
