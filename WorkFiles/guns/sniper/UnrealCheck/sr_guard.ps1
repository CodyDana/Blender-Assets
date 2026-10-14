# SR01 W5 machine guard: ONE Unreal process on the machine at a time. Waits (polls every 60 s, up to 120 min) while ANY
# UnrealEditor.exe / UnrealEditor-Cmd.exe runs (stricter than WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1, which
# lets a GUI editor pass: the gun-range workflow may run a GUI editor on DemoGame_1_Guns). Never stops another process.
# Every check is appended to -GuardLog with a timestamp. exit 0 = free; exit 1 = timed out (the caller must not launch).
param([Parameter(Mandatory)][string]$GuardLog, [string]$Label = '', [int]$TimeoutMin = 120)
$deadline = (Get-Date).AddMinutes($TimeoutMin)
while ($true) {
    $busy = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' })
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
        Add-Content -Path $GuardLog -Value "$stamp TIMEOUT $Label ($TimeoutMin min)" -Encoding utf8
        exit 1
    }
    Start-Sleep 60
}
