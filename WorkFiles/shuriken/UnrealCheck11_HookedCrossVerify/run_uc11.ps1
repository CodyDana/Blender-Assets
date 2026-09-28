# UnrealCheck11 (independent Unreal verifier incl. HANDEDNESS, SM_Shuriken_HookedCross): every Unreal step is its own
# fresh UnrealEditor-Cmd process.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_uc11.ps1 [-Steps u1,u2,u3,u4,u5] [-Dest /Game/HookedCrossVerify11/Run1]
#   u1 import the hooked-cross FBX (+ the six-point control FBX) and apply each sidecar (Scripts/pipeline/ue_import_sockets.py)
#   u2 maps import (Scripts/shuriken/ue_import_textures.py, import mode)
#   u3 FRESH read-back: mesh gates + render-data handedness (read only)
#   u4 maps verify (Scripts/shuriken/ue_import_textures.py, verify mode, fresh)
#   u5 re-export of the saved asset for the Blender round trip
#   u6 FRESH render-data handedness read (u6_renderdata.py; Allow CPU Access set in memory only, never saved)
#   probe  probe/probe_render_read.py (read only)
param([string[]]$Steps = @('u1', 'u2', 'u3', 'u4', 'u5', 'u6'), [string]$Dest = '/Game/HookedCrossVerify11/Run1')
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$texScript = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\ue_import_textures.py'
$env:SHURIKEN_UC11_DEST = $Dest
$env:SHURIKEN_TEXTURE_DIR = 'C:\Users\Cody\Desktop\Blender_Projects\Exports\Shuriken\Textures'
$env:SHURIKEN_TEXTURE_DEST = "$Dest/Textures"
$map = [ordered]@{
    'u1' = @{ script = "$here\u1_import.py"; mode = $null }
    'u2' = @{ script = $texScript; mode = 'import' }
    'u3' = @{ script = "$here\u3_readback.py"; mode = $null }
    'u4' = @{ script = $texScript; mode = 'verify' }
    'u5' = @{ script = "$here\u5_export.py"; mode = $null }
    'u6' = @{ script = "$here\u6_renderdata.py"; mode = $null }
    'probe' = @{ script = "$here\probe\probe_render_read.py"; mode = $null }
}
foreach ($s in ($Steps -join ",").Split(",")) {
    $m = $map[$s]
    if ($m.mode) {
        $env:SHURIKEN_TEXTURE_MODE = $m.mode
        $env:SHURIKEN_TEXTURE_OUT = "$here\${s}_textures_$($m.mode).json"
    }
    $log = "$here\$s.log"
    if ($s -eq 'probe') { $log = "$here\probe\probe.log" }
    $argList = "`"$uproject`" -run=pythonscript -script=`"$($m.script)`" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
    $t0 = Get-Date
    # wait for the commandlet itself, not its process tree (a spawned UnrealTraceServer daemon would block -Wait)
    $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
    $null = $p.Handle
    $p.WaitForExit()
    $lines = Get-Content $log
    $strict = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
    $loose = @($lines | Select-String -Pattern '(warning|error)')
    $errStd = @(Get-Content "$log.stderr" -ErrorAction SilentlyContinue)
    "step=$s exit=$($p.ExitCode) secs=$([int]((Get-Date) - $t0).TotalSeconds) log_lines=$($lines.Count) strict_warning_error=$($strict.Count) loose_mentions=$($loose.Count) stderr_lines=$($errStd.Count)"
    $strict | Select-Object -First 15 | ForEach-Object { "  STRICT " + $_.Line }
    $loose | Select-Object -First 25 | ForEach-Object { "  LOOSE  " + $_.Line }
}
