"""Run an existing dojo check script on this track's composed check blend (checks/DojoShowcase_r5.blend), which is not
two folders below the repo root as the scripts assume (ROOT = parents[2] of the blend). The script source runs
unchanged except that one ROOT expression, pinned to the repo root; and optional text swaps for copies that hard-code
the live showcase layout path.
Run: blender -b --factory-startup <checks/DojoShowcase_r5.blend> --python r5_runcheck.py -- --script <path>
     [--swap "old=>new"] [the script's own args]"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
A = sys.argv[sys.argv.index("--") + 1:]
src = Path(A[A.index("--script") + 1])
if not src.is_absolute():
    src = ROOT / src
code = src.read_text(encoding="utf-8")
k = "Path(bpy.data.filepath).resolve().parents[2]"
assert k in code, "no ROOT expression"
code = code.replace(k, f'Path(r"{ROOT}")')
for i, a in enumerate(A):
    if a == "--swap":
        old, new = A[i + 1].split("=>", 1)
        assert old in code, old
        code = code.replace(old, new)
exec(compile(code, str(src), "exec"), {"__name__": "__main__", "__file__": str(src)})
