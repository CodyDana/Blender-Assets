# pd_ic_run.ps1 -- launch ONE UnrealEditor on CharacterLab with pd_ic_verify.py (independent integrity check; saves nothing).
# Preflight: no UnrealEditor*.exe running (poll 60 s, up to 30 min) and >= 8 GB RAM free (poll 60 s, up to 30 min).
# Records SHA-256 of the MetaHuman uassets before/after, waits for exit, kills ONLY its own editor on timeout.
# Writes WorkFiles/MetaHuman/player_default/integrity_check/run_ic.json.
param([int]$TimeoutMinutes = 40)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Out = "$Root/WorkFiles/MetaHuman/player_default/integrity_check"
$Editor = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Script = "$Root/Scripts/MetaHuman/pd_ic_verify.py"
$Content = "$Root/Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
$Names = @("MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase", "MH_PlayerDefault")
$EngineLog = "$Out/engine_ic.log"
$RunReport = "$Out/run_ic.json"
New-Item -ItemType Directory -Force $Out | Out-Null
function Write-Run($o) { $o | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 $RunReport }
function Get-Hashes {
    $h = [ordered]@{}
    foreach ($n in $Names) { $h[$n] = (Get-FileHash -Algorithm SHA256 "$Content/$n.uasset").Hash }
    $h["scratch_folder_on_disk"] = Test-Path "$Root/Exports/CharacterLab/Unreal/Content/PlayerDefault"
    $h["metahuman_dir_files"] = @(Get-ChildItem $Content -File | ForEach-Object { $_.Name })
    return $h
}
$run = [ordered]@{ started = (Get-Date).ToString("o"); status = "preflight" }
Write-Run $run
$deadline = (Get-Date).AddMinutes(30)
while ($true) {
    $others = @(Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue)
    if ($others.Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) { $run.status = "gave_up_other_editor"; Write-Run $run; Write-Output "GAVE UP"; exit 3 }
    Write-Output ("waiting: UnrealEditor pids " + (($others | ForEach-Object { $_.Id }) -join ","))
    Start-Sleep -Seconds 60
}
$deadline = (Get-Date).AddMinutes(30)
while ($true) {
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    if ($freeGB -ge 8) { break }
    if ((Get-Date) -gt $deadline) { $run.status = "not_enough_ram"; $run.free_ram_gb = $freeGB; Write-Run $run; exit 4 }
    Write-Output "waiting: $freeGB GB free"
    Start-Sleep -Seconds 60
}
$run.free_ram_gb = $freeGB
$run.sha256_before = Get-Hashes
Write-Run $run
$uargs = @("`"$Project`"", "-ExecutePythonScript=`"$Script`"", "-RenderOffscreen", "-Unattended", "-NoSplash",
          "-NoSound", "-NoTextureStreaming", "-NoMetaHumanAccountPortalLoginFallback", "-abslog=`"$EngineLog`"")
$p = Start-Process -FilePath $Editor -ArgumentList $uargs -PassThru
$run.status = "running"; $run.pid = $p.Id
Write-Run $run
Write-Output "launched UnrealEditor pid $($p.Id)"
$finished = $p.WaitForExit($TimeoutMinutes * 60 * 1000)
if (-not $finished) { $run.status = "timeout_killed_own_editor"; Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 5 }
else { $run.status = "exited"; $run.exit_code = $p.ExitCode }
$run.ended = (Get-Date).ToString("o")
$run.unreal_processes_after = @(Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$run.sha256_after = Get-Hashes
$same = $true
foreach ($n in $Names) { if ($run.sha256_before[$n] -ne $run.sha256_after[$n]) { $same = $false } }
$run.all_unchanged = $same
Write-Run $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " unchanged=" + $same + " remaining=" + ($run.unreal_processes_after -join ","))
