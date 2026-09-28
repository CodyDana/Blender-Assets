# pf_run.ps1 -- launch UnrealEditor on CharacterLab with pf_female.py (female player variant), one CharacterLab editor
# at a time.
# Preflight: no UnrealEditor process whose command line contains "CharacterLab" (other projects' editors, e.g. the
# user's DemoGame_1 session, are left alone and never touched), and >= 7 GB RAM free (poll every 60 s, up to 20 min).
# Records SHA-256 of the protected MetaHuman assets before/after. Waits for the editor to exit (the script calls
# quit_editor); kills ONLY the editor it started, and only after -TimeoutMinutes.
# Writes WorkFiles/MetaHuman/player_female/run_<Mode>_<Attempt>.json.
param(
    [string]$Mode = "explore1",
    [string]$Attempt = "1",
    [int]$TimeoutMinutes = 45
)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Out = "$Root/WorkFiles/MetaHuman/player_female"
$Editor = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Script = "$Root/Scripts/MetaHuman/pf_female.py"
$Content = "$Root/Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
$Protected = @("MH_PlayerDefault", "MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase")
$Mine = @("MH_PlayerFemale", "MH_PlayerFemale_AltA", "MH_PlayerFemale_AltB")
$EngineLog = "$Out/engine_${Mode}_$Attempt.log"
$RunReport = "$Out/run_${Mode}_$Attempt.json"
New-Item -ItemType Directory -Force $Out | Out-Null

function Write-Run($obj) { $obj | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 $RunReport }
function Get-Hashes {
    $h = [ordered]@{}
    foreach ($n in $Protected) { $h[$n] = (Get-FileHash -Algorithm SHA256 "$Content/$n.uasset").Hash }
    foreach ($n in $Mine) {
        if (Test-Path "$Content/$n.uasset") { $h[$n] = (Get-FileHash -Algorithm SHA256 "$Content/$n.uasset").Hash } else { $h[$n] = $null }
    }
    $h["scratch_folder_on_disk"] = Test-Path "$Root/Exports/CharacterLab/Unreal/Content/PlayerFemale"
    return $h
}
function Get-LabEditors {
    @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" | Where-Object { $_.CommandLine -and $_.CommandLine -match "CharacterLab" })
}
$run = [ordered]@{ mode = $Mode; attempt = $Attempt; started = (Get-Date).ToString("o"); status = "preflight" }
Write-Run $run

$deadline = (Get-Date).AddMinutes(20)
while ($true) {
    $lab = Get-LabEditors
    if ($lab.Count -eq 0) { break }
    if ((Get-Date) -gt $deadline) {
        $run.status = "gave_up_characterlab_editor_running"; $run.other_pids = @($lab | ForEach-Object { $_.ProcessId })
        Write-Run $run; Write-Output "GAVE UP: a CharacterLab UnrealEditor is running"; exit 3
    }
    Write-Output ("waiting: CharacterLab editor pids " + (($lab | ForEach-Object { $_.ProcessId }) -join ","))
    Start-Sleep -Seconds 60
}
$deadline = (Get-Date).AddMinutes(20)
while ($true) {
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    if ($freeGB -ge 7) { break }
    if ((Get-Date) -gt $deadline) { $run.status = "not_enough_ram"; $run.free_ram_gb = $freeGB; Write-Run $run; Write-Output "NOT ENOUGH RAM: $freeGB GB"; exit 4 }
    Write-Output "waiting: only $freeGB GB RAM free"
    Start-Sleep -Seconds 60
}
$run.free_ram_gb = $freeGB
$run.other_unreal_editors_left_alone = @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" | ForEach-Object { $_.ProcessId })
$run.sha256_before = Get-Hashes
Write-Run $run

$env:PF_MODE = $Mode
$env:PF_ATTEMPT = $Attempt
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
$run.characterlab_editors_after = @(Get-LabEditors | ForEach-Object { $_.ProcessId })
$run.own_pid_alive_after = [bool](Get-Process -Id $p.Id -ErrorAction SilentlyContinue)
$run.sha256_after = Get-Hashes
$same = $true
foreach ($n in $Protected) { if ($run.sha256_before[$n] -ne $run.sha256_after[$n]) { $same = $false } }
$run.protected_unchanged = $same
Write-Run $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " protected_unchanged=" + $same + " lab_editors_after=" + ($run.characterlab_editors_after -join ",") + " own_alive=" + $run.own_pid_alive_after + " pf_hash=" + $run.sha256_after["MH_PlayerFemale"])
