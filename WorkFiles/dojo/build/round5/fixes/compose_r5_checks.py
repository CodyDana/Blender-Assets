"""ROUND 5 fixes track: compose the showcase INTO THIS FOLDER for the walk / climb / roof-walk checks, without touching
the live showcase (Assets/Dojo/DojoShowcase.blend and WorkFiles/dojo/build/showcase/ are the Unreal step's).

Runs Scripts/dojo/showcase/compose_showcase.py unchanged except for its two output constants:
  BLEND -> WorkFiles/dojo/build/round5/fixes/checks/DojoShowcase_r5.blend
  SC    -> WorkFiles/dojo/build/round5/fixes/checks/showcase/   (layout_showcase.json, blender_bounds.json, report)
Run: blender -b --factory-startup --python WorkFiles/dojo/build/round5/fixes/compose_r5_checks.py -- --no-export
"""
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
SRC = ROOT / "Scripts" / "dojo" / "showcase" / "compose_showcase.py"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "round5" / "fixes" / "checks"
(OUT / "showcase").mkdir(parents=True, exist_ok=True)
code = SRC.read_text(encoding="utf-8")
a = 'BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"'
b = 'SC = BUILD / "showcase"'
assert code.count(a) == 1 and code.count(b) == 1
code = code.replace(a, f'BLEND = Path(r"{OUT / "DojoShowcase_r5.blend"}")')
code = code.replace(b, f'SC = Path(r"{OUT / "showcase"}")')
g = {"__name__": "__main__", "__file__": str(SRC)}
exec(compile(code, str(SRC), "exec"), g)
