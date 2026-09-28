p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_fan.py"
s = open(p, encoding="utf-8").read()
old_a = s.index("def _fold_key(spec) -> str:")
old_b = s.index("def stage_fold(spec, report, quick=False):")
s = s[:old_a] + s[old_b:]
s = s.replace("    key = _fold_key(spec)\n", "    key = FF.bind_cache_key(spec)\n")
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''OFFSET_LIMIT_MM = 0.6
''', '''OFFSET_LIMIT_MM = 0.6


def bind_cache_key(spec: FanSpec = FAN) -> str:
    """What the optimised bind depends on: the fold-relevant spec numbers and the solver's source."""
    import hashlib
    import json
    from pathlib import Path
    fields = [spec.n_sticks, spec.opening_deg, spec.front_hinge_deg, spec.leaf_in_L, spec.leaf_out_L,
              spec.face_tilt_deg, spec.scallop_L, spec.rib_thick_mm, spec.guard_thick_mm, spec.leaf_gap_under_guard_mm,
              spec.L, OFFSET_LIMIT_MM, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()[:16]
''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
