# UnrealCheck10 (independent Unreal verifier, SM_Shuriken_Spike): every Unreal step is its own fresh UnrealEditor-Cmd process.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_uc10.ps1 [-Steps u1,u2,u3,u4,u5] [-Dest /Game/SpikeVerify10/Run1]
#   u1 import FBX + sidecar (Scripts/pipeline/ue_import_sockets.py)   u2 maps import (Scripts/shuriken/ue_import_textures.py)
#   u3 fresh read-back (mesh + maps)   u4 maps verify (ue_import_textures.py, fresh)   u5 re-export for the round trip
param([string[]]$Steps = @('u1', 'u2', 'u3', 'u4', 'u5'), [string]$Dest = '/Game/SpikeVerify10/Run1')
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck10_SpikeVerify'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$texScript = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\ue_import_textures.py'
$env:SHURIKEN_UC10_DEST = $Dest
$env:SHURIKEN_TEXTURE_DIR = 'C:\Users\Cody\Desktop\Blender_Projects\Exports\Shuriken\Textures'
$env:SHURIKEN_TEXTURE_DEST = "$Dest/Textures"
$map = [ordered]@{
    'u1' = @{ script = "$here\u1_import.py"; mode = $null }
    'u2' = @{ script = $texScript; mode = 'import' }
    'u3' = @{ script = "$here\u3_readback.py"; mode = $null }
    'u4' = @{ script = $texScript; mode = 'verify' }
    'u5' = @{ script = "$here\u5_export.py"; mode = $null }
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
