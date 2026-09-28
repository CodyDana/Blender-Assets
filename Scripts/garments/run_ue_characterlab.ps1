# run_ue_characterlab.ps1 -- run ONE Python script in a headless CharacterLab commandlet (saves nothing).
# Used by the garment pipeline for Unreal-side reads (fitting-body export, garment import check).
# Preflight: no running Unreal process has CharacterLab.uproject open, and >= $MinFreeGB RAM free.
# Hashes every file under Content/MetaHumans before and after and lists files created anywhere under Content,
# waits for exit, kills ONLY its own process on timeout. Never touches DemoGame_1.
#   powershell -ExecutionPolicy Bypass -File Scripts/garments/run_ue_characterlab.ps1 -Script Scripts/garments/ue_export_fitbody.py -Tag fitbody
# -Render: offscreen RHI instead of -nullrhi (a skeletal-mesh FBX export asserts "MeshObject" without a renderer).
param([Parameter(Mandatory = $true)][string]$Script, [string]$Tag = "run", [int]$TimeoutMinutes = 30, [double]$MinFreeGB = 6,
      [switch]$Render)
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Cmd = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Content = "$Root/Exports/CharacterLab/Unreal/Content"
$Out = "$Root/WorkFiles/garment_pipeline/ue_runs"
New-Item -ItemType Directory -Force $Out | Out-Null
$Log = "$Out/$Tag.log"
$Report = "$Out/$Tag.json"
$ScriptPath = (Resolve-Path (Join-Path $Root $Script)).Path
function Save($o) { $o | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 $Report }
function Snapshot {
    $h = @{}
    Get-ChildItem "$Content/MetaHumans" -Recurse -File | ForEach-Object { $h[$_.FullName] = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash }
    return $h
}
$run = [ordered]@{ tag = $Tag; script = $ScriptPath; started = (Get-Date).ToString("o"); status = "preflight" }
$holders = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like "UnrealEditor*" -and $_.CommandLine -match "CharacterLab" })
if ($holders.Count -gt 0) { $run.status = "characterlab_open"; $run.pids = @($holders | ForEach-Object { $_.ProcessId }); Save $run; Write-Output "REFUSED: CharacterLab is open"; exit 3 }
$freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
$run.free_ram_gb = $freeGB
if ($freeGB -lt $MinFreeGB) { $run.status = "not_enough_ram"; Save $run; Write-Output "REFUSED: $freeGB GB free"; exit 4 }
$filesBefore = @(Get-ChildItem $Content -Recurse -File | ForEach-Object { $_.FullName })
$before = Snapshot
Save $run
$rhi = if ($Render) { @("-AllowCommandletRendering", "-RenderOffscreen") } else { @("-nullrhi") }
$uargs = @("`"$Project`"", "-run=pythonscript", "-script=`"$ScriptPath`"", "-unattended", "-nop4", "-nosplash") + $rhi + @(
           "-nosound", "-stdout", "-FullStdOutLogOutput", "-abslog=`"$Log`"")
$p = Start-Process -FilePath $Cmd -ArgumentList $uargs -PassThru -WindowStyle Hidden
$run.status = "running"; $run.pid = $p.Id; Save $run
Write-Output "launched UnrealEditor-Cmd pid $($p.Id)"
$finished = $p.WaitForExit($TimeoutMinutes * 60 * 1000)
if (-not $finished) { $run.status = "timeout_killed_own_process"; Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 5 }
else { $run.status = "exited"; $run.exit_code = $p.ExitCode }
$run.ended = (Get-Date).ToString("o")
$after = Snapshot
$changed = @($before.Keys | Where-Object { $before[$_] -ne $after[$_] })
$run.metahuman_files = $before.Count
$run.metahuman_changed = $changed
$run.new_content_files = @(Get-ChildItem $Content -Recurse -File | ForEach-Object { $_.FullName } | Where-Object { $filesBefore -notcontains $_ })
Save $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " changed=" + $changed.Count + " new=" + $run.new_content_files.Count)
