# ArmoryLab performance measurement (2026-10-02), re-runnable with the identical method:
#   powershell -NoProfile -ExecutionPolicy Bypass -File Scripts\armory\unreal\ak_perf.ps1 -Label <label> [-Mode both|game|pie]
#              [-Ab "shell_hidden,shadows_off,..."] [-ResX 1600 -ResY 900]  (game: r.SetRes; pie: a 1630 x 910 floating
#              PIE window, the owner's viewport size)
# game: ONE fresh offscreen GAME run of the saved L_Armory (UnrealEditor-Cmd -game, real D3D12 RHI, 1600 x 900 windowed,
#       default (Epic) scalability, texture streaming ON as a player has it); pie: ONE offscreen editor that starts
#       Play-In-Editor on L_Armory (the owner's way of playing). Both run Scripts/armory/unreal/ak_perf.py: warm-up, then
#       per view (spawn, CAM_C1_EntryReveal, CAM_C10_Hero) a CSV-profiler segment (stat unit numbers: frame / game / draw /
#       RHI / GPU ms; draw calls, primitives; GPU passes), stat unit + stat gpu on screen, one ProfileGPU and the
#       stat scenerendering / initviews dumps per profiled view, a HighResShot of each camera view; optional runtime A/B
#       toggles (diagnosis only). Read-only: nothing is saved in the project.
# Output: WorkFiles/armory/build/unreal/perf/<label>/<mode>/{perf.log, csv/, shots/, probe.json, perf.json} and
#         perf/<label>/summary.json (ak_perf_parse.py).
# Guards (house rules): never touches another process. Waits while any UnrealEditor-Cmd.exe runs (another chat's), stops
# (exit 3) after 60 min if an UnrealEditor.exe has ArmoryLab open (polls every 2 min), needs >= 6 GB free RAM, and waits
# (2 min polls, max WaitMin) until the GPU and CPU are idle (nvidia-smi utilisation <= MaxGpuUtil over 5 samples, CPU load
# <= MaxCpu): a measurement under another job's load (another chat's Blender renders) is meaningless. Kills only its own process, only on its own timeout.
param([Parameter(Mandatory = $true)][string]$Label, [string]$Mode = 'both', [string]$Ab = '',
      [int]$ResX = 1600, [int]$ResY = 900, [int]$TimeoutMin = 15, [int]$MaxGpuUtil = 20, [int]$MaxCpu = 25, [int]$WaitMin = 60,
      [string]$Views = 'spawn,C1_EntryReveal,C10_Hero', [int]$Warm = 20, [int]$Seg = 10, [string]$AbView = 'spawn')
$ErrorActionPreference = 'Stop'
$Here = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\unreal'
$Run = "C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\perf\$Label"
$ProjDir = 'C:\Users\Cody\Documents\Unreal Projects\ArmoryLab'
$Proj = "$ProjDir\ArmoryLab.uproject"
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
New-Item -ItemType Directory -Force $Run | Out-Null
$Guard = "$Run\guard.txt"
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
function GpuUtil {
    $v = @()
    for ($i = 0; $i -lt 5; $i++) {
        $s = (& nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits) -split ','
        $v += [int]$s[0]; Start-Sleep -Milliseconds 400
    }
    $mem = [int]((& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits).Trim())
    return @{ util = [math]::Round(($v | Measure-Object -Average).Average, 1); mem_mb = $mem }
}
function WaitFree {
    $deadline = (Get-Date).AddMinutes($WaitMin)
    while ($true) {
        $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
        $ours = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'ArmoryLab' })
        $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
        $g = GpuUtil
        $blender = @(Get-Process -Name 'blender' -ErrorAction SilentlyContinue).Count
        $cpu = [math]::Round((Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average, 0)
        Note "check: UnrealEditor-Cmd=$($busy.Count) ArmoryLab editor=$($ours.Count) freeGB=$freeGB gpu=$($g.util)% vram=$($g.mem_mb)MB cpu=$cpu% blender=$blender"
        $g.cpu = $cpu
        if ($busy.Count -eq 0 -and $ours.Count -eq 0 -and $freeGB -ge 6 -and $g.util -le $MaxGpuUtil -and $cpu -le $MaxCpu) { return $g }
        if ((Get-Date) -gt $deadline) {
            if ($ours.Count -gt 0) { Note "STOP: the ArmoryLab editor is still open after $WaitMin min"; exit 3 }
            Note "GAVE UP after $WaitMin min of waiting"; exit 3
        }
        Start-Sleep -Seconds 120
    }
}
$modes = if ($Mode -eq 'both') { @('game', 'pie') } else { @($Mode) }
foreach ($m in $modes) {
    $d = "$Run\$m"
    if (Test-Path $d) { Remove-Item $d -Recurse -Force }
    New-Item -ItemType Directory -Force "$d\csv", "$d\shots" | Out-Null
    $g = WaitFree
    $log = "$d\perf.log"
    $env:AK_PERF_MODE = $m; $env:AK_PERF_OUT = $d; $env:AK_PERF_AB = $Ab; $env:AK_PERF_VIEWS = $Views
    $env:AK_PERF_RES = "${ResX}x${ResY}"; $env:AK_PERF_WARM = "$Warm"; $env:AK_PERF_SEG = "$Seg"; $env:AK_PERF_AB_VIEW = $AbView
    $common = @('-dx12', '-unattended', '-nosplash', '-nop4', '-NoSound', '-NoLiveCoding',
                '-dpcvars=r.GPUCsvStatsEnabled=1', "-abslog=`"$log`"")
    $py = ($Here -replace '\\', '/') + '/ak_perf.py'
    if ($m -eq 'game') {
        # -ExecutePythonScript is an editor start-up option (ignored by -game); the 'py' console command runs it in game
        $argl = @("`"$Proj`"", '/Game/Armory/Maps/L_Armory', '-game', '-RenderOffscreen', "-ResX=$ResX", "-ResY=$ResY",
                  '-windowed', "-ExecCmds=`"py $py`"") + $common
    } else {
        $argl = @("`"$Proj`"", '-RenderOffscreen', "-ExecutePythonScript=`"$Here\ak_perf.py`"") + $common
    }
    # the pie probe sets a floating PIE window size on LevelEditorPlaySettings (a per-user config): keep the owner's own
    # editor settings exactly as they were
    $UserIni = "$ProjDir\Saved\Config\WindowsEditor\EditorPerProjectUserSettings.ini"
    if ($m -eq 'pie' -and (Test-Path $UserIni)) { Copy-Item $UserIni "$d\EditorPerProjectUserSettings.before.ini" -Force }
    $t0 = Get-Date
    $p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
         -RedirectStandardOutput "$d\stdout.txt" -RedirectStandardError "$d\stderr.txt"
    $umap = Get-Item "$ProjDir\Content\Armory\Maps\L_Armory.umap"
    $usha = (Get-FileHash $umap.FullName -Algorithm SHA256).Hash.Substring(0, 16)
    Note "[$m] started pid=$($p.Id) gpu_before=$($g.util)% vram_before=$($g.mem_mb)MB cpu_before=$($g.cpu)% ab='$Ab' L_Armory.umap=$($umap.LastWriteTime.ToString('s')) sha=$usha"
    if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
        Note "[$m] TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
        Stop-Process -Id $p.Id -Force
    }
    $p.WaitForExit()
    Note "[$m] exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
    Get-ChildItem "$ProjDir\Saved\Profiling\CSV" -Filter *.csv -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $t0 } | Sort-Object LastWriteTime | ForEach-Object {
            Copy-Item $_.FullName "$d\csv\$($_.Name)" }
    Get-ChildItem "$ProjDir\Saved\Screenshots" -Recurse -Filter *.png -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $t0 } | Sort-Object LastWriteTime | ForEach-Object {
            Copy-Item $_.FullName "$d\shots\$($_.Name)" }
    Get-ChildItem "$ProjDir\Saved\Profiling" -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $t0 -and $_.Extension -ne '.csv' } | ForEach-Object {
            Copy-Item $_.FullName "$d\$($_.Name)" -ErrorAction SilentlyContinue }
    if ($m -eq 'pie' -and (Test-Path "$d\EditorPerProjectUserSettings.before.ini")) {
        $h0 = (Get-FileHash "$d\EditorPerProjectUserSettings.before.ini").Hash
        $h1 = if (Test-Path $UserIni) { (Get-FileHash $UserIni).Hash } else { '' }
        if ($h0 -ne $h1) { Copy-Item "$d\EditorPerProjectUserSettings.before.ini" $UserIni -Force; Note "[$m] restored the owner's EditorPerProjectUserSettings.ini" }
    }
    $left = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.ProcessId -eq $p.Id })
    if ($left.Count -gt 0) { Note "[$m] own pid still alive: killing $($p.Id)"; Stop-Process -Id $p.Id -Force }
}
& py -3 -B "$Here\ak_perf_parse.py" $Run
exit 0
