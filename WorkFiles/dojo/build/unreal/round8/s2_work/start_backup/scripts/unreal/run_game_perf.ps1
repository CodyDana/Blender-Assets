# DojoLab ROUND 5 GPU frame-time sample (-csvExitOnCompletion does not end an editor-binary -game run: the timeout ends it,
# after the CSV is written; -ResX/-ResY are ignored offscreen, r.setres sets the size): ONE offscreen -game run of L_Dojo (the GASP pawn at PlayerStart P1, its own
# camera) with the CSV profiler for a fixed number of frames, then exit. Read-only for the project content (writes only
# Saved/Profiling/CSV and a log). Guards as run_sc_capture.ps1: waits while any UnrealEditor-Cmd.exe runs, stops if
# DojoLab is open in an UnrealEditor.exe, kills only its own process and only on its own timeout.
param([int]$TimeoutMin = 3, [int]$Frames = 900, [int]$ResX = 1920, [int]$ResY = 1080)
$ErrorActionPreference = 'Stop'
$Out = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\showcase'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Out\logs\perf_guard.txt"
New-Item -ItemType Directory -Force "$Out\logs" | Out-Null
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(45)
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $dojo = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'DojoLab' })
    if ($dojo.Count -gt 0) { Note "STOP: DojoLab is open in UnrealEditor.exe pid $($dojo.ProcessId -join ','); nothing run"; exit 3 }
    if ($busy.Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 45 min of waiting'; exit 3 }
    Start-Sleep -Seconds 30
}
$log = "$Out\logs\perf_game.log"
if (Test-Path $log) { Remove-Item $log -Force }
$argl = @("`"$Proj`"", '/Game/Dojo/Maps/L_Dojo', '-game', '-RenderOffscreen', '-dx12', "-ResX=$ResX", "-ResY=$ResY",
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding', '-NoVSync',
          "-csvCaptureFrames=$Frames", '-csvGpuStats', '-csvExitOnCompletion', "-ExecCmds=`"t.MaxFPS 0,r.setres ${ResX}x${ResY}w`"",
          "-abslog=`"$log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Out\logs\perf_game_stdout.txt" -RedirectStandardError "$Out\logs\perf_game_stderr.txt"
Note "started pid=$($p.Id) frames=$Frames"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
exit 0
