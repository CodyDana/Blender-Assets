# perf2: ONE offscreen UnrealEditor-Cmd -game run of L_Dojo executing Scripts/dojo/unreal/dj_ninja_perf2.py with config
# -Cfg (env DJ_PT_CFG); -Url adds e.g. ?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C (GASP reference pawn).
# Guards (as run_ninja_playtest.ps1 / run_fp_game_perf.ps1): waits (15 s polls, max 60 min) while any UnrealEditor-Cmd.exe
# runs (one commandlet machine-wide), stops if any UnrealEditor*.exe has DojoLab open, kills only its own process and only
# on its own timeout. Logs every Blender / Unreal process seen at start. Records the CSV profiles the run wrote
# ("csv <path> <bytes>" lines in the guard file). Read-only for the project content.
param([Parameter(Mandatory = $true)][string]$Cfg, [Parameter(Mandatory = $true)][string]$Log, [string]$Url = '',
      [int]$TimeoutMin = 40)
$ErrorActionPreference = 'Stop'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Py = 'C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal/dj_ninja_perf2.py'
$Guard = "$Log.guard.txt"
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(60)
$free = 0
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $dojo = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'DojoLab' })
    if ($dojo.Count -gt 0) { Note "STOP: DojoLab is open in $($dojo.Name -join ',') pid $($dojo.ProcessId -join ','); nothing run"; exit 3 }
    if ($busy.Count -eq 0) { $free++ } else { $free = 0 }
    if ($free -ge 2) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 60 min of waiting'; exit 3 }
    Start-Sleep -Seconds 15
}
$others = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(blender|UnrealEditor|UnrealEditor-Cmd|ShaderCompileWorker)\.exe$' })
Note "other heavy processes at start: $($others.Count) $(($others | ForEach-Object { "$($_.Name):$($_.ProcessId)" }) -join ' ')"
if (Test-Path $Log) { Remove-Item $Log -Force }
$csvDir = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\Saved\Profiling\CSV'
$env:DJ_PT_CFG = $Cfg
$argl = @("`"$Proj`"", "/Game/Dojo/Maps/L_Dojo$Url", '-game', '-RenderOffscreen', '-dx12', '-ResX=1920', '-ResY=1080',
          '-windowed', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding', '-NoVSync', '-csvGpuStats',
          "-ExecCmds=`"py $Py`"", "-abslog=`"$Log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Log.stdout.txt" -RedirectStandardError "$Log.stderr.txt"
Note "started pid=$($p.Id) cfg=$Cfg url=$Url"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $t0 } |
    Sort-Object Name | ForEach-Object { Note "csv $($_.FullName) $($_.Length)" }
exit 0
