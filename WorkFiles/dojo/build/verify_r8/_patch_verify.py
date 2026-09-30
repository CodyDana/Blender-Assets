from pathlib import Path
D = Path(__file__).parent
p = D / "v8_ue_verify.py"
s = p.read_text(encoding="utf-8")
a = s.index("# ------------------------------------------------------------------ 6 environment readback")
b = s.index("# ================================================================== round-5 gates")
s = s[:a] + (D / "env_uds.py").read_text(encoding="utf-8") + "\n\n" + s[b:]
s = s.replace('"verifier": "independent r6"', '"verifier": "independent r8"')
s = s.replace('"10_greybox", "13_alley_ring", "16_group_1v1")}', '"10_greybox", "13_alley_ring", "16_group_1v1", "7_env")}')
s = s.replace("V6_VERIFY_DONE", "V8_VERIFY_DONE")
p.write_text(s, encoding="utf-8")
print("patched")
