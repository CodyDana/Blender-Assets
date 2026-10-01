# ArmoryLab runtime test (2026-10-01): ONE offscreen game run of L_Armory (UnrealEditor-Cmd -game, real D3D12 RHI) with
# -AKViewToggleTest: the character's UArmoryViewToggleComponent presses V through the player controller, measures the
# view distance from the head (third person -> first person -> third person), walks in through the entrance and looks
# round in both views, logs "AK_STEP_DONE fptest passed=..." and quits. The same log is the game-run evidence for the
# VSM check: the count of "[VSM] Non-Nanite Marking Job Queue overflow" warnings must be 0.
# Guards as run_capture.ps1: waits (30 s polls, max 45 min) while any UnrealEditor-Cmd.exe runs; needs >= 6 GB free RAM.
# Kills only the process it started, and only on its own timeout. Never touches UnrealEditor.exe (other sessions).
# Result: WorkFiles/armory/build/unreal/fptest.json, log logs/fptest.log
param([int]$TimeoutMin = 10)
$ErrorActionPreference = 'Stop'
$Out = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\ArmoryLab\ArmoryLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Out\logs\fptest_guard.txt"
New-Item -ItemType Directory -Force "$Out\logs" | Out-Null
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(45)
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    $editors = (@(Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue) | ForEach-Object { $_.Id }) -join ','
    Note "check: UnrealEditor-Cmd running=$($busy.Count) freeGB=$freeGB (UnrealEditor.exe pids, untouched: $editors)"
    if ($busy.Count -eq 0 -and $freeGB -ge 6) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 45 min of waiting'; exit 3 }
    Start-Sleep -Seconds 30
}
$log = "$Out\logs\fptest.log"
if (Test-Path $log) { Remove-Item $log -Force }
$argl = @("`"$Proj`"", '/Game/Armory/Maps/L_Armory', '-game', '-RenderOffscreen', '-dx12', '-ResX=1600', '-ResY=900',
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding', '-AKViewToggleTest',
          '-dpcvars=r.TextureStreaming=0', "-abslog=`"$log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Out\logs\fptest_stdout.txt" -RedirectStandardError "$Out\logs\fptest_stderr.txt"
Note "started pid=$($p.Id)"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
$secs = [math]::Round(((Get-Date) - $t0).TotalSeconds)
Note "exit code $($p.ExitCode) after $secs s"
$text = if (Test-Path $log) { Get-Content $log -Raw } else { '' }
$done = [regex]::Match($text, 'AK_STEP_DONE fptest passed=(\w+)[^\r\n]*')
$vsm = ([regex]::Matches($text, 'Non-Nanite Marking Job Queue overflow')).Count
$res = [ordered]@{
    passed = ($done.Success -and $done.Groups[1].Value -eq 'True' -and $vsm -eq 0)
    toggle_line = $done.Value
    vsm_non_nanite_overflow_warnings = $vsm
    toggle_lines = @([regex]::Matches($text, 'AK_VIEWTOGGLE[^\r\n]*') | ForEach-Object { $_.Value })
    exit_code = $p.ExitCode
    secs = $secs
}
$res | ConvertTo-Json -Depth 4 | Set-Content -Path "$Out\fptest.json" -Encoding utf8
Note "fptest passed=$($res.passed) vsm_warnings=$vsm"
exit 0
