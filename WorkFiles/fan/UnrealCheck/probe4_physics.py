"""Probe: physics asset from the proxy mesh; how to reach and edit its bodies from Python (UE 5.8.3)."""
import json
import sys
import traceback

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck")
import unreal  # noqa: E402

REPORT = json.loads(open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\build_dev\dev1\fan_report.json").read())
PROXY = REPORT["physics_proxy"]["fbx"]
DEST = "/Game/FanCheck/Probe4"
AT = unreal.AssetToolsHelpers.get_asset_tools()
out = {"physics_names": [n for n in dir(unreal) if "hysics" in n or "BodySetup" in n]}


def task(path, name, ui):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", DEST)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("save", False)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("options", ui)
    AT.import_asset_tasks([t])
    return [str(p) for p in t.get_editor_property("imported_object_paths")]


try:
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("create_physics_asset", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    out["imported"] = task(PROXY, "SK_Fan_PhysicsProxy", ui)
    mesh = unreal.load_asset(DEST + "/SK_Fan_PhysicsProxy")
    pa = mesh.get_editor_property("physics_asset")
    out["pa"] = pa.get_path_name() if pa else None
    out["pa_props"] = [n for n in dir(pa) if not n.startswith("_")]
    found = {}
    for cls in ("SkeletalBodySetup", "BodySetup"):
        for i in range(12):
            o = unreal.find_object(pa, f"{cls}_{i}")
            if o:
                found[f"{cls}_{i}"] = o.get_class().get_name()
    out["found"] = found
    bodies = []
    for nm in found:
        bs = unreal.find_object(pa, nm)
        rec = {"name": nm}
        for p in ("bone_name", "physics_type", "consider_for_bounds", "collision_trace_flag"):
            try:
                rec[p] = str(bs.get_editor_property(p))
            except Exception as e:                              # noqa: BLE001
                rec[p] = "ERR " + str(e)[:120]
        try:
            g = bs.get_editor_property("agg_geom")
            rec["boxes"] = len(g.get_editor_property("box_elems"))
            rec["sphyls"] = len(g.get_editor_property("sphyl_elems"))
            rec["spheres"] = len(g.get_editor_property("sphere_elems"))
            rec["convex"] = len(g.get_editor_property("convex_elems"))
        except Exception as e:                                  # noqa: BLE001
            rec["agg_geom"] = "ERR " + str(e)[:160]
        bodies.append(rec)
    out["bodies"] = bodies
    for fn in ("get_physics_asset_bodies",):
        out[fn] = hasattr(unreal.SkeletalMeshEditorSubsystem, fn)
    # try editing the first body: a box, and read it back
    if found:
        bs = unreal.find_object(pa, list(found)[0])
        g = bs.get_editor_property("agg_geom")
        box = unreal.KBoxElem()
        box.set_editor_property("x", 10.0)
        box.set_editor_property("y", 2.0)
        box.set_editor_property("z", 1.0)
        g.set_editor_property("box_elems", [box])
        g.set_editor_property("sphyl_elems", [])
        bs.set_editor_property("agg_geom", g)
        bs.set_editor_property("physics_type", unreal.PhysicsType.PHYS_TYPE_KINEMATIC)
        g2 = bs.get_editor_property("agg_geom")
        out["edit_readback"] = {"boxes": len(g2.get_editor_property("box_elems")), "sphyls": len(g2.get_editor_property("sphyl_elems")),
                                "physics_type": str(bs.get_editor_property("physics_type"))}
    try:
        out["constraints"] = [str(unreal.find_object(pa, f"PhysicsConstraintTemplate_{i}")) for i in range(4)]
    except Exception as e:                                      # noqa: BLE001
        out["constraints"] = str(e)[:200]
except Exception:                                               # noqa: BLE001
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe4.json", "w").write(json.dumps(out, indent=1, default=str))
unreal.log("PROBE4_DONE")
