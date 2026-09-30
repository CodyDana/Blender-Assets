#!/usr/bin/env bash
# VERIFY r6f: FBX audit (fresh re-import of every exported FBX) then every Blender traversal check (fresh headless
# processes, read-only on Assets/Dojo/DojoShowcase.blend; nothing saved). Outputs in verify_r6f/.
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
V=WorkFiles/dojo/build/verify_r6f
echo "== fbx_audit $(date '+%T')"
"$B" -b --factory-startup --python $V/v6f_fbx_audit.py > $V/fbx_audit.log 2>&1; echo "exit $?"
bash $V/run_v6f_blender_checks.sh
echo "ALL_BLENDER_DONE $(date '+%T')"
