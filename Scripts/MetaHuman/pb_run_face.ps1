# pb_run_face.ps1 -- launch UnrealEditor on CharacterLab with pb_face_design.py, one editor at a time.
# Preflight: no UnrealEditor*.exe running (poll every 60 s for up to 30 min) and >= 8 GB RAM free.
# Waits for the editor to exit (the script calls quit_editor); kills ONLY the editor it started, and only
# after -TimeoutMinutes. Writes WorkFiles/MetaHuman/player_base/faces/run_<Mode>_<Attempt>.json.
param(
    [string]$Mode = "probe",
    [string]$Attempt = "1",
    [int]$TimeoutMinutes = 55,
    [string]$Recipes = ""
)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Out = "$Root/WorkFiles/MetaHuman/player_base/faces"
$Editor = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Script = "$Root/Scripts/MetaHuman/pb_face_design.py"
$EngineLog = "$Out/engine_${Mode}_$Attempt.log"
$RunReport = "$Out/run_${Mode}_$Attempt.json"
New-Item -ItemType Directory -Force $Out | Out-Null

function Write-Run($obj) { $obj | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 $RunReport }
$run = [ordered]@{ mode = $Mode; attempt = $Attempt; started = (Get-Date).ToString("o"); status = "preflight" }
Write-Run $run

$deadline = (Get-Date).AddMinutes(30)
while ($true) {
    $others = @(Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue)
    if ($others.Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) {
        $run.status = "gave_up_other_editor_running"
        $run.other_pids = @($others | ForEach-Object { $_.Id })
        Write-Run $run; Write-Output "GAVE UP: another UnrealEditor is running"; exit 3
    }
    Write-Output ("waiting: UnrealEditor running pids " + (($others | ForEach-Object { $_.Id }) -join ","))
    Start-Sleep -Seconds 60
}
$freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
$run.free_ram_gb = $freeGB
if ($freeGB -lt 8) { $run.status = "not_enough_ram"; Write-Run $run; Write-Output "NOT ENOUGH RAM: $freeGB GB"; exit 4 }

$env:PB_FACE_MODE = $Mode
$env:PB_ATTEMPT = $Attempt
if ($Recipes) { $env:PB_FACE_RECIPES = $Recipes } else { Remove-Item Env:PB_FACE_RECIPES -ErrorAction SilentlyContinue }
$uargs = @("`"$Project`"", "-ExecutePythonScript=`"$Script`"", "-RenderOffscreen", "-Unattended", "-NoSplash",
          "-NoSound", "-NoTextureStreaming", "-NoMetaHumanAccountPortalLoginFallback", "-abslog=`"$EngineLog`"")
$p = Start-Process -FilePath $Editor -ArgumentList $uargs -PassThru
$run.status = "running"; $run.pid = $p.Id; $run.args = ($uargs -join " ")
Write-Run $run
Write-Output "launched UnrealEditor pid $($p.Id)"

$finished = $p.WaitForExit($TimeoutMinutes * 60 * 1000)
if (-not $finished) {
    $run.status = "timeout_killed_own_editor"
    Stop-Process -Id $p.Id -Force
    Start-Sleep -Seconds 5
} else {
    $run.status = "exited"
    $run.exit_code = $p.ExitCode
}
$run.ended = (Get-Date).ToString("o")
$left = @(Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue)
$run.unreal_processes_after = @($left | ForEach-Object { $_.Id })
Write-Run $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " remaining_unreal=" + ($run.unreal_processes_after -join ","))
