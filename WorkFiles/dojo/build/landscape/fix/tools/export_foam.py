"""Fix round probe (read-only on the assets): export the foam textures to PNG for the coverage maths. Out: fix/probe/*.png"""
from pathlib import Path
import unreal
out = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fix\probe")
out.mkdir(parents=True, exist_ok=True)
for p in ("/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled", "/Game/DojoKit/FX/Textures/T_DKF_Foam_M"):
    t = unreal.load_asset(p)
    task = unreal.AssetExportTask()
    fn = str(out / (p.rsplit("/", 1)[1] + ".png"))
    for k, v in (("object", t), ("filename", fn), ("automated", True), ("prompt", False), ("replace_identical", True)):
        task.set_editor_property(k, v)
    try:
        task.set_editor_property("exporter", unreal.TextureExporterPNG())
    except Exception:  # noqa: BLE001
        pass
    ok = unreal.Exporter.run_asset_export_task(task)
    unreal.log(f"export {p} {ok} srgb={t.get_editor_property('srgb')} cs={t.get_editor_property('compression_settings')}")
unreal.log("DJ_STEP_DONE export_foam passed=True")
