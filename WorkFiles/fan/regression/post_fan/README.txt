post_fan: the fan's final-pass snapshot (2026-09-26).
  SHA256SUMS.txt / manifest.json   every frozen, materials and fan file at the end of the pass
  compare_vs_pre_final_pass.json   py -3 fan_regression.py compare ../pre_final_pass post_fan   (passed: all gates)
  fan_regression.py                the snapshot / compare script (py -3 fan_regression.py compare post_fan  = compare with NOW)
  materials_build/                 the pack build's run fan3: canonical dump, layout, verify, import, build, assign
  check_exports_frozen.txt         WorkFiles/materials/survey/check_exports_frozen.sh output: 63 of 63 identical
Dump vs the materials job's final (WorkFiles/materials/build/dump_f2.json): no change, no removal, 28 additions (see FAN_REPORT 6).
