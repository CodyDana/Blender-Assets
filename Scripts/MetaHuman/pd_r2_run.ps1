# pd_r2_run.ps1 -- launch UnrealEditor on CharacterLab with pd_r2.py (round-2 fix), one editor at a time.
# Preflight: no UnrealEditor*.exe running (poll every 60 s for up to 30 min) and >= 8 GB RAM free (poll, 30 min).
# Records SHA-256 of the protected MetaHuman assets (and MH_PlayerDefault) before and after. Waits for the editor
# to exit (the script calls quit_editor); kills ONLY the editor it started, and only after -TimeoutMinutes.
# Writes WorkFiles/MetaHuman/player_default/run_r2_<Mode>_<Attempt>.json.
param(
    [string]$Mode = "explore",
    [string]$Attempt = "1",
    [int]$TimeoutMinutes = 50
)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Out = "$Root/WorkFiles/MetaHuman/player_default"
$Editor = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Script = "$Root/Scripts/MetaHuman/pd_r2.py"
$Content = "$Root/Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
$Protected = @("MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase")
$EngineLog = "$Out/engine_r2_${Mode}_$Attempt.log"
$RunReport = "$Out/run_r2_${Mode}_$Attempt.json"
New-Item -ItemType Directory -Force $Out | Out-Null

function Write-Run($obj) { $obj | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 $RunReport }
function Get-Hashes {
    $h = [ordered]@{}
    foreach ($n in $Protected) { $h[$n] = (Get-FileHash -Algorithm SHA256 "$Content/$n.uasset").Hash }
    if (Test-Path "$Content/MH_PlayerDefault.uasset") {
        $h["MH_PlayerDefault"] = (Get-FileHash -Algorithm SHA256 "$Content/MH_PlayerDefault.uasset").Hash
    } else { $h["MH_PlayerDefault"] = $null }
    $h["scratch_folder_on_disk"] = Test-Path "$Root/Exports/CharacterLab/Unreal/Content/PlayerDefault"
    return $h
}
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
$deadline = (Get-Date).AddMinutes(30)
while ($true) {
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    if ($freeGB -ge 8) { break }
    if ((Get-Date) -gt $deadline) { $run.status = "not_enough_ram"; $run.free_ram_gb = $freeGB; Write-Run $run; Write-Output "NOT ENOUGH RAM: $freeGB GB"; exit 4 }
    Write-Output "waiting: only $freeGB GB RAM free"
    Start-Sleep -Seconds 60
}
$run.free_ram_gb = $freeGB
$run.sha256_before = Get-Hashes
Write-Run $run

$env:PD_MODE = $Mode
$env:PD_ATTEMPT = $Attempt
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
$run.sha256_after = Get-Hashes
$same = $true
foreach ($n in $Protected) { if ($run.sha256_before[$n] -ne $run.sha256_after[$n]) { $same = $false } }
$run.protected_unchanged = $same
Write-Run $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " protected_unchanged=" + $same + " remaining_unreal=" + ($run.unreal_processes_after -join ",") + " pd_hash=" + $run.sha256_after["MH_PlayerDefault"])
