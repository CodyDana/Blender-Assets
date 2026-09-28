# UnrealCheck8 (independent import verifier): every step is its own fresh UnrealEditor-Cmd process.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_uc8.ps1 [-Steps p1,p2,p3,p3b,p4]
param([string[]]$Steps = @('p1', 'p2', 'p3', 'p3b', 'p4'))
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck8'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$texScript = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\ue_import_textures.py'
$env:SHURIKEN_TEXTURE_DIR = 'C:\Users\Cody\Desktop\Blender_Projects\Exports\Shuriken\Textures'
if (-not $env:SHURIKEN_UC8_DEST) { $env:SHURIKEN_UC8_DEST = '/Game/ShurikenCheck8/Verify' }
$env:SHURIKEN_TEXTURE_DEST = "$($env:SHURIKEN_UC8_DEST)/Textures"
$map = [ordered]@{
    'p1'  = @{ script = "$here\p1_import_meshes.py"; mode = $null }
    'p2'  = @{ script = $texScript; mode = 'import' }
    'p3'  = @{ script = "$here\p3_readback.py"; mode = $null }
    'p3b' = @{ script = $texScript; mode = 'verify' }
    'p4'  = @{ script = "$here\p4_export.py"; mode = $null }
}
foreach ($s in ($Steps -join ",").Split(",")) {
    $m = $map[$s]
    if ($m.mode) {
        $env:SHURIKEN_TEXTURE_MODE = $m.mode
        $env:SHURIKEN_TEXTURE_OUT = "$here\${s}_textures_$($m.mode).json"
    }
    $log = "$here\$s.log"
    $argList = "`"$uproject`" -run=pythonscript -script=`"$($m.script)`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
    $t0 = Get-Date
    # Wait for the commandlet itself, not its process tree: Windows PowerShell 5.1's Start-Process -Wait also waits
    # for descendants, and a commandlet that has to start the UnrealTraceServer daemon (no editor running one) left
    # the runner blocked forever after p3b exited cleanly (six-point maintenance run, 2026-09-18).
    $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
    $null = $p.Handle
    $p.WaitForExit()
    $lines = Get-Content $log
    $strict = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
    $loose = @($lines | Select-String -Pattern '(warning|error)' | Where-Object { $_.Line -notmatch '0 error\(s\), 0 warning\(s\)' -and $_.Line -notmatch "Failed to load '.*\.dll'" })
    $errStd = @(Get-Content "$log.stderr" -ErrorAction SilentlyContinue)
    "step=$s exit=$($p.ExitCode) secs=$([int]((Get-Date) - $t0).TotalSeconds) log_lines=$($lines.Count) strict_warning_error=$($strict.Count) loose_mentions=$($loose.Count) stderr_lines=$($errStd.Count)"
    $strict | Select-Object -First 15 | ForEach-Object { "  STRICT " + $_.Line }
    $loose | Select-Object -First 15 | ForEach-Object { "  LOOSE  " + $_.Line }
}
