# hy_run.ps1 -- PRIVATE / DO NOT SHIP. Launch UnrealEditor on CharacterLab with hy_hiyuki.py (Hiyuki capability test), one CharacterLab editor
# at a time.
# Preflight: no UnrealEditor process whose command line contains "CharacterLab" (other projects' editors, e.g. the
# user's DemoGame_1 session, are left alone and never touched), and >= 7 GB RAM free (poll every 60 s, up to 20 min).
# Records SHA-256 of the protected MetaHuman assets before/after. Waits for the editor to exit (the script calls
# quit_editor); kills ONLY the editor it started, and only after -TimeoutMinutes.
# Writes WorkFiles/MetaHuman/hiyuki_private/run_<Mode>_<Attempt>.json.
param(
    [string]$Mode = "explore1",
    [string]$Attempt = "1",
    [int]$TimeoutMinutes = 45,
    [int]$RamWaitMinutes = 60
)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Out = "$Root/WorkFiles/MetaHuman/hiyuki_private"
$Editor = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Script = "$Root/Scripts/MetaHuman/hy_hiyuki.py"
$Content = "$Root/Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
$Protected = @("MH_PlayerDefault", "MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase", "MH_PlayerFemale")
$Mine = @("MH_Hiyuki_Private")
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
    $h["scratch_folder_on_disk"] = Test-Path "$Root/Exports/CharacterLab/Unreal/Content/HiyukiPrivate"
    return $h
}
function Get-LabEditors {
    # CharacterLab editors, plus ANY headless editor on the machine (UnrealEditor-Cmd, -RenderOffscreen/-Unattended runs
    # of other chats): one headless Unreal at a time. GUI editors of other projects (user / other chats) are left alone.
    @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" | Where-Object { $_.CommandLine -and (
        $_.CommandLine -match "CharacterLab" -or $_.Name -match "UnrealEditor-Cmd" -or
        $_.CommandLine -match "-RenderOffscreen|-Unattended|-run=") })
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
$deadline = (Get-Date).AddMinutes($RamWaitMinutes)
while ($true) {
    $freeGB = [math]::Round((Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue / 1KB, 2)
    if ($freeGB -ge 7) { break }
    if ((Get-Date) -gt $deadline) { $run.status = "not_enough_ram"; $run.free_ram_gb = $freeGB; Write-Run $run; Write-Output "NOT ENOUGH RAM: $freeGB GB"; exit 4 }
    Write-Output "waiting: only $freeGB GB RAM free"
    Start-Sleep -Seconds 60
}
$run.free_ram_gb = $freeGB
$run.other_unreal_editors_left_alone = @(Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'" | ForEach-Object { $_.ProcessId })
$run.sha256_before = Get-Hashes
Write-Run $run

$env:HY_MODE = $Mode
$env:HY_ATTEMPT = $Attempt
$env:PF_MAX_MINUTES = "$TimeoutMinutes"
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
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " protected_unchanged=" + $same + " lab_editors_after=" + ($run.characterlab_editors_after -join ",") + " own_alive=" + $run.own_pid_alive_after + " hy_hash=" + $run.sha256_after["MH_Hiyuki_Private"])
