# Male cloak review - runs ONE offscreen UnrealEditor-Cmd (full editor, real D3D12 RHI) on the scratch CloakReview.uproject.
# Guards: waits (60 s polls, max 45 min) while any UnrealEditor-Cmd.exe runs; needs >= 6 GB free RAM.
# Kills only the process it started, and only on its own timeout. Never touches UnrealEditor.exe (other chats, pid 16028).
param([Parameter(Mandatory)][string]$Tag, [string]$Pass = 'A', [int]$TimeoutMin = 40)
$ErrorActionPreference = 'Stop'
$Here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\BlackCloak_Review\male\unreal'
$Proj = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\BlackCloak_Review\unreal\CloakReview\CloakReview.uproject'
$Exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Guard = "$Here\logs\guard_$Tag.txt"
function Note($m) { $line = "$(Get-Date -Format s) $m"; Add-Content -Path $Guard -Value $line -Encoding utf8; Write-Output $line }
$deadline = (Get-Date).AddMinutes(45)
while ($true) {
    $busy = @(Get-Process -Name 'UnrealEditor-Cmd' -ErrorAction SilentlyContinue)
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
    $editors = (@(Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue) | ForEach-Object { $_.Id }) -join ','
    Note "check: UnrealEditor-Cmd running=$($busy.Count) pids=$(($busy | % Id) -join ',') freeGB=$freeGB (UnrealEditor.exe pids, untouched: $editors)"
    if ($busy.Count -eq 0 -and $freeGB -ge 6) { break }
    if ((Get-Date) -gt $deadline) { Note 'GAVE UP after 45 min of waiting'; exit 3 }
    Note 'waiting 60 s'
    Start-Sleep -Seconds 60
}
$env:MU_PASS = $Pass
$log = "$Here\logs\$Tag.log"
$argl = @("`"$Proj`"", '-unattended', '-nosplash', '-nop4', '-RenderOffscreen', '-dx12', '-NoSound', '-NoLiveCoding', '-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0,Editor.AsyncSkinnedAssetCompilation=0',
          "-ExecutePythonScript=`"$Here\mu_capture.py`"", "-abslog=`"$log`"")
$p = Start-Process -FilePath $Exe -ArgumentList $argl -PassThru -WindowStyle Hidden `
     -RedirectStandardOutput "$Here\logs\${Tag}_stdout.txt" -RedirectStandardError "$Here\logs\${Tag}_stderr.txt"
Note "started pid=$($p.Id) pass=$Pass"
Set-Content -Path "$Here\logs\${Tag}_pid.txt" -Value $p.Id
if (-not $p.WaitForExit($TimeoutMin * 60 * 1000)) {
    Note "TIMEOUT after $TimeoutMin min: killing own pid $($p.Id)"
    Stop-Process -Id $p.Id -Force
    exit 4
}
$p.WaitForExit(); Note "exit code $($p.ExitCode)"
exit 0
