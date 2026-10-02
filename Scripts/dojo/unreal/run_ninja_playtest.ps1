# DojoLab ninja character port, PLAY TESTS: ONE offscreen UnrealEditor-Cmd -game run of L_Dojo (-Url adds e.g.
# ?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C for the GASP reference pawn) that executes -Script (default
# dj_ninja_playtest.py; py console command) with the JSON config -Cfg (env DJ_PT_CFG), then quits.
# -Sound keeps the audio device (for the jutsu audio checks); the probe mutes the final output (`au.MuteAudio 1`: the
# engine plays and logs every sound, nothing reaches the speakers); without it the run is -NoSound like the other runners.
# Guards as run_ninja_probe.ps1 / run_game_perf.ps1: waits (30 s polls, max 45 min) while any UnrealEditor-Cmd.exe runs,
# stops if any UnrealEditor*.exe has DojoLab open, kills only its own process and only on its own timeout. Read-only for
# the project content (PNGs, report and log only).
param([Parameter(Mandatory = $true)][string]$Cfg, [Parameter(Mandatory = $true)][string]$Log, [string]$Url = '',
      [string]$Script = 'dj_ninja_playtest.py', [int]$TimeoutMin = 40, [switch]$Sound, [string]$ResX = '1920', [string]$ResY = '1080')
$ErrorActionPreference = 'Stop'
$Here = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Log.guard.txt"
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(45)
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $dojo = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'DojoLab' })
    if ($dojo.Count -gt 0) { Note "STOP: DojoLab is open in $($dojo.Name -join ',') pid $($dojo.ProcessId -join ','); nothing run"; exit 3 }
    if ($busy.Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 45 min of waiting'; exit 3 }
    Start-Sleep -Seconds 30
}
if (Test-Path $Log) { Remove-Item $Log -Force }
$env:DJ_PT_CFG = $Cfg
$py = "$Here\$Script" -replace '\\', '/'
$argl = @("`"$Proj`"", "/Game/Dojo/Maps/L_Dojo$Url", '-game', '-RenderOffscreen', '-dx12', "-ResX=$ResX", "-ResY=$ResY",
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoLiveCoding', '-NoVSync')
# -Sound: no -NoSound; the probe mutes the final output with the console command `au.MuteAudio 1` when the world is
# ready (a -dpcvars cheat cvar raised an ensure in ConfigUtilities.cpp, 2026-10-02 jutsu run 1)
if (-not $Sound) { $argl += '-NoSound' }
$argl += @("-ExecCmds=`"py $py`"", "-abslog=`"$Log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Log.stdout.txt" -RedirectStandardError "$Log.stderr.txt"
Note "started pid=$($p.Id) script=$Script cfg=$Cfg url=$Url sound=$Sound"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
exit 0
