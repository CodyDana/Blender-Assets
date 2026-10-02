# Build Scripts/dojo/unreal/DojoFXTools with RunUAT BuildPlugin into fxlight/plugin_build (a compile only, no Unreal
# editor or commandlet process).
$O = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fxlight'
$Out = "$O\plugin_build\DojoFXTools"
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Force "$O\plugin_build", "$O\logs" | Out-Null
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\RunUAT.bat' BuildPlugin `
  -Plugin='C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\DojoFXTools\DojoFXTools.uplugin' `
  -Package="$Out" -TargetPlatforms=Win64 -VS2022 *> "$O\logs\buildplugin.log"
"exit $LASTEXITCODE"
Get-Content "$O\logs\buildplugin.log" -Tail 6
