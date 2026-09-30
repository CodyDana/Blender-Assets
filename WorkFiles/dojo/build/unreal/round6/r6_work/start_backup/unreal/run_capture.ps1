# DojoLab captures: ONE offscreen UnrealEditor-Cmd (full editor, real D3D12 RHI) running dj_capture.py.
# Guards: waits (30 s polls, max 45 min) while any UnrealEditor-Cmd.exe runs; needs >= 6 GB free RAM.
# Kills only the process it started, and only on its own timeout. Never touches UnrealEditor.exe (other sessions).
param([int]$TimeoutMin = 40)
$ErrorActionPreference = 'Stop'
$Here = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal'
$Out = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal'
$Proj = 'C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Out\logs\capture_guard.txt"
New-Item -ItemType Directory -Force "$Out\logs" | Out-Null
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(45)
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    $dojo = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'DojoLab' })
    if ($dojo.Count -gt 0) { Note "STOP: DojoLab is open in UnrealEditor.exe pid $($dojo.ProcessId -join ','); nothing run"; exit 3 }
    Note "check: UnrealEditor-Cmd running=$($busy.Count) freeGB=$freeGB"
    if ($busy.Count -eq 0 -and $freeGB -ge 6) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 45 min of waiting'; exit 3 }
    Start-Sleep -Seconds 30
}
$log = "$Out\logs\capture.log"
if (Test-Path $log) { Remove-Item $log -Force }
$argl = @("`"$Proj`"", '-unattended', '-nosplash', '-nop4', '-RenderOffscreen', '-dx12', '-NoSound', '-NoLiveCoding',
          '-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0',
          "-ExecutePythonScript=`"$Here\dj_capture.py`"", "-abslog=`"$log`"")
$t0 = Get-Date
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Out\logs\capture_stdout.txt" -RedirectStandardError "$Out\logs\capture_stderr.txt"
Note "started pid=$($p.Id)"
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit()
Note "exit code $($p.ExitCode) after $([math]::Round(((Get-Date) - $t0).TotalSeconds)) s"
exit 0
