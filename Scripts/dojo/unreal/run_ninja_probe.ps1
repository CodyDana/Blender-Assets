# DojoLab ninja character port: ONE offscreen UnrealEditor-Cmd -game run of L_Dojo (-Url adds e.g. ?game=... for the
# GASP reference route) that executes dj_ninja_game_probe.py (py console command) with the JSON config -Cfg, then quits. Guards as run_game_perf.ps1: waits
# (30 s polls, max 45 min) while any UnrealEditor-Cmd.exe runs, stops if DojoLab is open in an UnrealEditor.exe, kills
# only its own process and only on its own timeout. Read-only for the project content (PNGs, report and log only).
param([Parameter(Mandatory = $true)][string]$Cfg, [Parameter(Mandatory = $true)][string]$Log, [string]$Url = '', [int]$TimeoutMin = 40)
$ErrorActionPreference = 'Stop'
$Here = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Log.guard.txt"
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
if (Test-Path $Log) { Remove-Item $Log -Force }
$env:DJ_NINJA_PROBE_CFG = $Cfg
$py = "$Here\dj_ninja_game_probe.py" -replace '\\', '/'
$argl = @("`"$Proj`"", "/Game/Dojo/Maps/L_Dojo$Url", '-game', '-RenderOffscreen', '-dx12', '-ResX=1920', '-ResY=1080',
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding', '-NoVSync',
          "-ExecCmds=`"py $py`"", "-abslog=`"$Log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Log.stdout.txt" -RedirectStandardError "$Log.stderr.txt"
Note "started pid=$($p.Id) cfg=$Cfg"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
exit 0
