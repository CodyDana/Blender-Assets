"""INDEPENDENT VERIFIER: run Scripts/dojo/unreal/dj_sc_verify.py unchanged, but send its verify.json to verify/sc_verify/
(dj_sc_common.SC_OUT patched before the script runs) so the showcase build folder is not written."""
import runpy
import sys
from pathlib import Path

HERE = r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal"
sys.path.insert(0, HERE)
import dj_sc_common as S  # noqa: E402

S.SC_OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\voices_paper\verify\sc_verify")
S.SC_OUT.mkdir(parents=True, exist_ok=True)
runpy.run_path(HERE + r"\dj_sc_verify.py", run_name="__main__")
