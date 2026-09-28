# UnrealCheck12 race probe: re-run u1 with the UnrealCheck6 pass-1 save pattern (save on import + the sidecar's save,
# SHURIKEN_UC12_SAVE_MODE=double) into throwaway fresh paths /Game/KunaiPlainVerify12/RaceProbe/P<n>, each its own
# process, and count the LogPackageName warning.  Evidence only; no gate reads these assets.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_race_probe.ps1 [-Count 4] [-Mode double]
param([int]$Count = 4, [string]$Mode = 'double', [string]$Tag = 'P')
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck12_KunaiPlainVerify'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
New-Item -ItemType Directory -Force "$here\race_probe" | Out-Null
for ($i = 1; $i -le $Count; $i++) {
    $name = "$Tag$i"
    $env:SHURIKEN_UC12_DEST = "/Game/KunaiPlainVerify12/RaceProbe/$name"
    $env:SHURIKEN_UC12_SAVE_MODE = $Mode
    $env:SHURIKEN_UC12_U1_OUT = "race_probe\u1_$name.json"
    $log = "$here\race_probe\u1_$name.log"
    $argList = "`"$uproject`" -run=pythonscript -script=`"$here\u1_import.py`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
    $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
    $null = $p.Handle
    $p.WaitForExit()
    $lines = Get-Content $log
    $strict = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
    $saves = @($lines | Select-String -Pattern 'Saving Package: /Game/KunaiPlainVerify12/RaceProbe').Count
    "probe=$name mode=$Mode exit=$($p.ExitCode) saves=$saves strict_warning_error=$($strict.Count)"
    $strict | Select-Object -First 2 | ForEach-Object { "  STRICT " + $_.Line.Substring(0, [Math]::Min(200, $_.Line.Length)) }
}
