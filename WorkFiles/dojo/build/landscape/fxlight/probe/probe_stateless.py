import json, unreal, traceback
from pathlib import Path
out = {"objs": [], "errs": []}
sysA = unreal.load_asset('/Niagara/DefaultAssets/Templates/Systems/FountainLightweight')
out["sys"] = str(sysA)
pkg = sysA.get_outermost()
n = 0
for o in unreal.ObjectIterator(unreal.Object):
    try:
        if o.get_outermost() != pkg:
            continue
    except Exception:
        continue
    n += 1
    rec = {"name": o.get_path_name(), "cls": o.get_class().get_name(), "pycls": type(o).__name__}
    for k in ("modules", "renderer_properties", "emitter_state", "spawn_info", "b_module_enabled", "module_enabled",
              "lifetime", "material", "meshes", "sub_image_size", "spawn_rate", "emitter_handles", "fixed_bounds"):
        try:
            v = o.get_editor_property(k)
            rec[k] = str(v)[:300]
        except Exception as e:
            pass
    out["objs"].append(rec)
out["n"] = n
Path(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight/probe/probe_stateless.json').write_text(json.dumps(out, indent=1))
unreal.log('DJ_STEP_DONE probe_stateless passed=True n=%d' % n)
