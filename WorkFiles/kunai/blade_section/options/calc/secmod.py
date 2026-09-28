"""Load the PROTOTYPE kunai_spec (proto_tree) for one option file, without bpy and without writing bytecode."""
import importlib.util
import os
import sys
import types

sys.dont_write_bytecode = True
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "proto_tree", "Scripts", "shuriken", "shuriken_lib")


def load(option_json=None):
    if option_json:
        os.environ["KUNAI_SECTION_JSON"] = option_json
    else:
        os.environ.pop("KUNAI_SECTION_JSON", None)
    name = "slib_%d" % abs(hash(option_json))
    pkg = types.ModuleType(name)
    pkg.__path__ = [LIB]
    sys.modules[name] = pkg
    for mod in ("spec", "kunai_spec"):
        spec = importlib.util.spec_from_file_location(f"{name}.{mod}", os.path.join(LIB, mod + ".py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules[f"{name}.{mod}"] = m
        spec.loader.exec_module(m)
    return sys.modules[f"{name}.kunai_spec"]
