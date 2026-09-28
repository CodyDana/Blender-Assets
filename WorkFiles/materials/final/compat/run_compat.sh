#!/usr/bin/env bash
# run_compat.sh <deferred|substrate|forward>
#   deferred : the validation project itself (reference; nothing saved)
#   substrate / forward : a THROWAWAY copy (NPCompat_<tag>/: the uproject, Config with the one extra renderer setting,
#   Content/NinjaPack only). The copy is deleted by hand afterwards; the validation project is never modified.
export MSYS_NO_PATHCONV=1
TAG="${1:?deferred|substrate|forward}"
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
VAL="$ROOT/WorkFiles/shuriken/UnrealShuriken"
HERE="$ROOT/WorkFiles/materials/final/compat"
SCRIPT="$HERE/np_compat_capture.py"
if [ "$TAG" = "deferred" ]; then
  PROJ="$VAL/ShurikenValidation.uproject"
else
  COPY="$HERE/NPCompat_$TAG"
  if [ ! -d "$COPY" ]; then
    mkdir -p "$COPY/Config" "$COPY/Content"
    cp "$VAL/ShurikenValidation.uproject" "$COPY/NPCompat_$TAG.uproject"
    cp "$VAL/Config/DefaultEngine.ini" "$COPY/Config/DefaultEngine.ini"
    cp -r "$VAL/Content/NinjaPack" "$COPY/Content/NinjaPack"
    case "$TAG" in
      substrate) printf '\n[/Script/Engine.RendererSettings]\nr.Substrate=True\n' >> "$COPY/Config/DefaultEngine.ini";;
      forward)   printf '\n[/Script/Engine.RendererSettings]\nr.ForwardShading=True\n' >> "$COPY/Config/DefaultEngine.ini";;
    esac
  fi
  PROJ="$COPY/NPCompat_$TAG.uproject"
fi
LOG="$HERE/compat_$TAG.log"
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting: an UnrealEditor-Cmd is running"; sleep 15; done
echo "start $(date +%T) $PROJ"
NP_COMPAT_TAG="$TAG" timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" -unattended -nop4 -nosplash -nosound \
  -stdout -FullStdOutLogOutput -AllowCommandletRendering -RenderOffscreen \
  -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0 > "$LOG" 2>&1
echo "exit $? $(date +%T)"
grep -o "NP_COMPAT_DONE.*" "$LOG" | head -1
echo "compile failures: $(grep -c 'Failed to compile' "$LOG")"
tasklist 2>/dev/null | grep -i "UnrealEditor-Cmd" && echo "WARNING: UnrealEditor-Cmd still running" || echo "no UnrealEditor-Cmd running"
