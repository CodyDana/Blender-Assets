# UnrealCheck9 (six-point independent verifier): every step is its own FRESH UnrealEditor-Cmd process.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_u9.ps1 [-Steps s1,s2,s3,s3b,s4]
#   s1  import FBX + apply sidecar (ue_import_sockets.py), save
#   s2  import the three maps (Scripts/shuriken/ue_import_textures.py, import mode), save
#   s3  read back mesh + maps (second fresh process, nothing written to assets)
#   s3b ue_import_textures.py verify mode (another fresh process)
#   s4  export the saved asset back to FBX (LODs + stored collision)
param([string[]]$Steps = @('s1', 's2', 's3', 's3b', 's4'))
$ErrorActionPreference = 'Stop'
$here = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck9_SixPoint'
$uproject = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealShuriken\ShurikenValidation.uproject'
$exe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$texScript = 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\ue_import_textures.py'
$env:SHURIKEN_TEXTURE_DIR = "$here\tex_stage"
$env:SHURIKEN_TEXTURE_DEST = '/Game/ShurikenCheck9/SixPointIndep1/Textures'
$map = [ordered]@{
    's1'  = @{ script = "$here\s1_import.py"; mode = $null }
    's2'  = @{ script = $texScript; mode = 'import' }
    's3'  = @{ script = "$here\s3_readback.py"; mode = $null }
    's3b' = @{ script = $texScript; mode = 'verify' }
    's4'  = @{ script = "$here\s4_export.py"; mode = $null }
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
    $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
    $lines = Get-Content $log
    $strict = @($lines | Select-String -Pattern ':\s*(Warning|Error)\s*:' -CaseSensitive)
    $loose = @($lines | Select-String -Pattern '(warning|error)' | Where-Object { $_.Line -notmatch '0 error\(s\), 0 warning\(s\)' -and $_.Line -notmatch "Failed to load '.*\.dll'" })
    $errStd = @(Get-Content "$log.stderr" -ErrorAction SilentlyContinue)
    "step=$s exit=$($p.ExitCode) secs=$([int]((Get-Date) - $t0).TotalSeconds) log_lines=$($lines.Count) strict_warning_error=$($strict.Count) loose_mentions=$($loose.Count) stderr_lines=$($errStd.Count)"
    $strict | Select-Object -First 15 | ForEach-Object { "  STRICT " + $_.Line }
    $loose | Select-Object -First 15 | ForEach-Object { "  LOOSE  " + $_.Line }
}
