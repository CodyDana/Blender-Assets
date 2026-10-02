until grep -q "saved\|Traceback" WorkFiles/dojo/build/rocks/work/build.log; do sleep 5; done
grep "\[build\]\|Error\|Traceback" WorkFiles/dojo/build/rocks/work/build.log | cut -c1-500 | tail -12
