#!/usr/bin/env bash
# perf2 contention probe: the main profile (ninja) while N own busy-loop processes load the CPU (started 20 s after
# the Unreal process, for 260 s, so the 4 sample windows at ~95-150 s run under load). Own processes only.
D=/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/perf2
O=$D/contention; mkdir -p $O
bash $D/tools/idle_gate.sh $O/idle_gate.txt 2700; echo "idle_gate_exit=$?" >> $O/idle_gate.txt
rm -f $O/.done
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $D/tools/monitor.ps1)" -Out "$(cygpath -w $O/background_load.csv)" -Done "$(cygpath -w $O/.done)" &
for n in 8 20; do
  ( sleep 20; py -3 "$(cygpath -w $D/tools/cpu_load.py)" $n 260 >> $O/load_$n.txt 2>&1 ) & LP=$!
  powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $D/tools/run_perf2.ps1)" -Cfg "$(cygpath -w $D/cfg/load_ninja_$n.json)" -Log "$(cygpath -w $O/load_ninja_$n.log)" -TimeoutMin 20 | grep -v "csv C" | tail -1
  wait $LP
done
touch $O/.done; sleep 10; echo CONTENTION_DONE
