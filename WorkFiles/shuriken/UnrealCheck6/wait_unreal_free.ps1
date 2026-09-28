# One-Unreal-at-a-time guard (3.11, the kunai blade section's Unreal check).
# Machine-wide rule: at most ONE Unreal commandlet / headless process at a time. Before every launch this checks
# (Win32_Process) that no UnrealEditor-Cmd.exe is running and no UnrealEditor.exe carries -run= / -ExecutePythonScript /
# -unattended / -nullrhi on its command line. A GUI UnrealEditor.exe (e.g. DemoGame_1) is NOT a headless process and is
# never touched. If busy: Start-Sleep 60 and re-check, up to 90 minutes; then exit 1 (the caller must not launch).
# Every check is appended to -GuardLog with a timestamp.
param([Parameter(Mandatory)][string]$GuardLog, [string]$Label = '')
$deadline = (Get-Date).AddMinutes(90)
while ($true) {
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -ieq 'UnrealEditor-Cmd.exe') -or
        (($_.Name -ieq 'UnrealEditor.exe') -and ($_.CommandLine -match '(?i)(-run=|-ExecutePythonScript|-unattended|-nullrhi)'))
    })
    $stamp = (Get-Date).ToString('o')
    if ($busy.Count -eq 0) {
        Add-Content -Path $GuardLog -Value "$stamp FREE  $Label" -Encoding utf8
        "guard: free ($Label)"
        exit 0
    }
    $desc = ($busy | ForEach-Object { "$($_.ProcessId):$($_.Name)" }) -join ', '
    Add-Content -Path $GuardLog -Value "$stamp BUSY  $Label  [$desc]" -Encoding utf8
    "guard: busy ($desc) - waiting 60 s"
    if ((Get-Date) -gt $deadline) {
        Add-Content -Path $GuardLog -Value "$stamp TIMEOUT $Label (90 min)" -Encoding utf8
        exit 1
    }
    Start-Sleep 60
}
