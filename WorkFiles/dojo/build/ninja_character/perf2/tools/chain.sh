#!/usr/bin/env bash
# perf2 chain: idle gate (max 45 min, then measure anyway), background monitor, then the given runs in order.
# usage: chain.sh <outdir> <name> "<cfg>|<url>" ...   (url empty = GM_DojoNinja; "G" = ?game=GM_Dojo)
D=/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/perf2
OUTD="$1"; NAME="$2"; shift 2
mkdir -p "$OUTD"
bash "$D/tools/idle_gate.sh" "$OUTD/${NAME}_idle_gate.txt" 2700; echo "idle_gate_exit=$?" >> "$OUTD/${NAME}_idle_gate.txt"
rm -f "$OUTD/.done_$NAME"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $D/tools/monitor.ps1)" -Out "$(cygpath -w $OUTD/${NAME}_background_load.csv)" -Done "$(cygpath -w $OUTD/.done_$NAME)" &
for spec in "$@"; do
  cfg="${spec%%|*}"; url="${spec#*|}"
  [ "$url" = "G" ] && url='?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C'
  base=$(basename "$cfg" .json)
  powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $D/tools/run_perf2.ps1)" -Cfg "$(cygpath -w $D/cfg/$cfg)" -Log "$(cygpath -w $OUTD/$base.log)" -Url "$url" -TimeoutMin 30 | grep -v "csv C" | tail -1
done
touch "$OUTD/.done_$NAME"; sleep 10
echo "CHAIN_DONE $NAME"
