#!/bin/sh
# one UE commandlet; refuses to start if any UnrealEditor-Cmd runs; stops only its own leftover
export MSYS_NO_PATHCONV=1
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "another UnrealEditor-Cmd is running; not starting"; exit 3; fi
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
if [ "$3" = "render" ]; then EXTRA="-AllowCommandletRendering -RenderOffscreen"; else EXTRA="-nullrhi -nosound"; fi
timeout 450 "$UE" "$PROJ" -run=pythonscript -script="$1" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput $EXTRA > "$2" 2>&1
rc=$?
SN=$(basename "$1")
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor-Cmd.exe'\" | Where-Object { \$_.CommandLine -like '*$SN*' } | ForEach-Object { Write-Output ('stopping own leftover pid ' + \$_.ProcessId); Stop-Process -Id \$_.ProcessId -Force }"
echo "ue rc=$rc; python errors: $(grep -c 'LogPython: Error' "$2")"
