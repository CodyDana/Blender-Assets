# run_ue_heels.ps1 -- run ONE Python script in a fresh CharacterLab process for the Snow Flower heels Unreal check.
# Same guards as Scripts/garments/run_ue_characterlab.ps1 (MetaHumans hashed before/after, new Content files listed,
# waits, kills only its own process on timeout), plus:
#   -Mode commandlet  : -run=pythonscript (no engine tick; imports, asset builds, reads)
#   -Mode editor      : full offscreen editor with -ExecutePythonScript (the engine ticks; captures, animation)
#   -ExtraArgs        : extra command-line switches (e.g. -EnablePlugins=EditorToolset)
# Refuses to start while ANY UnrealEditor-Cmd.exe runs on the machine or any Unreal process has CharacterLab open.
# Never touches DemoGame_1.
param([Parameter(Mandatory = $true)][string]$Script, [string]$Tag = "run", [int]$TimeoutMinutes = 30, [double]$MinFreeGB = 6,
      [ValidateSet("commandlet", "editor")][string]$Mode = "commandlet", [switch]$Render, [string[]]$ExtraArgs = @())
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$Cmd = "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
$Project = "$Root/Exports/CharacterLab/Unreal/CharacterLab.uproject"
$Content = "$Root/Exports/CharacterLab/Unreal/Content"
$Out = "$Root/WorkFiles/SnowFlowerHeels/ue/runs"
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
$run = [ordered]@{ tag = $Tag; script = $ScriptPath; mode = $Mode; started = (Get-Date).ToString("o"); status = "preflight" }
$holders = @(Get-CimInstance Win32_Process | Where-Object { ($_.Name -like "UnrealEditor-Cmd*") -or ($_.Name -like "UnrealEditor*" -and $_.CommandLine -match "CharacterLab") })
if ($holders.Count -gt 0) { $run.status = "busy"; $run.pids = @($holders | ForEach-Object { $_.ProcessId }); Save $run; Write-Output "REFUSED: another UnrealEditor-Cmd or CharacterLab process runs: $($run.pids -join ',')"; exit 3 }
$freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
$run.free_ram_gb = $freeGB
if ($freeGB -lt $MinFreeGB) { $run.status = "not_enough_ram"; Save $run; Write-Output "REFUSED: $freeGB GB free"; exit 4 }
$filesBefore = @(Get-ChildItem $Content -Recurse -File | ForEach-Object { $_.FullName })
$before = Snapshot
Save $run
if ($Mode -eq "editor") {
    $uargs = @("`"$Project`"", "-ExecutePythonScript=`"$ScriptPath`"", "-RenderOffscreen", "-unattended", "-nop4", "-nosplash", "-nosound",
               "-NoMetaHumanAccountPortalLoginFallback", "-stdout", "-FullStdOutLogOutput", "-abslog=`"$Log`"")
} else {
    $rhi = if ($Render) { @("-AllowCommandletRendering", "-RenderOffscreen") } else { @("-nullrhi") }
    $uargs = @("`"$Project`"", "-run=pythonscript", "-script=`"$ScriptPath`"", "-unattended", "-nop4", "-nosplash") + $rhi + @(
               "-nosound", "-stdout", "-FullStdOutLogOutput", "-abslog=`"$Log`"")
}
$uargs += $ExtraArgs
$run.args = ($uargs -join " ")
$p = Start-Process -FilePath $Cmd -ArgumentList $uargs -PassThru -WindowStyle Hidden
$run.status = "running"; $run.pid = $p.Id; Save $run
Write-Output "launched UnrealEditor-Cmd pid $($p.Id)"
$finished = $p.WaitForExit($TimeoutMinutes * 60 * 1000)
if (-not $finished) { $run.status = "timeout_killed_own_process"; Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 5 }
else { $run.status = "exited"; $run.exit_code = $p.ExitCode }
$run.ended = (Get-Date).ToString("o")
$after = Snapshot
$changed = @($before.Keys | Where-Object { $before[$_] -ne $after[$_] })
$added = @($after.Keys | Where-Object { -not $before.ContainsKey($_) })
$run.metahuman_files = $before.Count
$run.metahuman_changed = $changed
$run.metahuman_added = $added
$run.new_content_files = @(Get-ChildItem $Content -Recurse -File | ForEach-Object { $_.FullName } | Where-Object { $filesBefore -notcontains $_ })
$run.new_outside_heelscheck = @($run.new_content_files | Where-Object { $_ -notmatch "[\\/]Content[\\/]HeelsCheck[\\/]" })
Save $run
Write-Output ("DONE status=" + $run.status + " exit=" + $run.exit_code + " mh_changed=" + $changed.Count + " mh_added=" + $added.Count + " new=" + $run.new_content_files.Count + " new_outside=" + $run.new_outside_heelscheck.Count)
