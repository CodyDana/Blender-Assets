# NINJA PORT VERIFIER: runs Scripts/dojo/unreal/dj_sc_verify.py unchanged, with its report redirected to my verify folder
import runpy, sys
from pathlib import Path
H = "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal"
sys.path.insert(0, H)
import dj_sc_common as S
S.SC_OUT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/verify/sc")
S.SC_OUT.mkdir(parents=True, exist_ok=True)
runpy.run_path(H + "/dj_sc_verify.py", run_name="__main__")
