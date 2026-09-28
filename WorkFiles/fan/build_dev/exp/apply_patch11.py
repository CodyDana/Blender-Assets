p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_refview.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)
rep('''def render_reference(objects, spec: FanSpec, work: Path, out_png: Path, samples: int = 256, arm_obj=None,
                     extra_objects=()):''', '''def render_reference(objects, spec: FanSpec, work: Path, out_png: Path, samples: int = 256, movers=None,
                     extra_objects=()):''')
rep('''    movers = [arm_obj] if arm_obj is not None else list(objects)
    saved_M''', '''    movers = list(movers) if movers else list(objects)
    saved_M''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
