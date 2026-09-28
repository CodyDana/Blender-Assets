"""Enable the installed Blender MCP add-on and connect a GUI Blender session."""
import json
import traceback
from pathlib import Path

import addon_utils
import bpy

STATUS = Path(__file__).resolve().parents[1] / "WorkFiles" / "blender_mcp_status.json"


def connect():
    try:
        previous_preferences = {}
        legacy = bpy.context.preferences.addons.get("blender_mcp_addon")
        if legacy:
            preferences = legacy.preferences
            for prop in preferences.bl_rna.properties:
                if prop.identifier != "rna_type" and prop.type in {"STRING", "BOOLEAN", "INT", "FLOAT", "ENUM"}:
                    previous_preferences[prop.identifier] = getattr(preferences, prop.identifier)
            addon_utils.disable("blender_mcp_addon", default_set=True)

        bpy.utils.refresh_script_paths()
        addon_utils.enable("blender_mcp", default_set=True, persistent=True)
        import blender_mcp

        preferences = bpy.context.preferences.addons["blender_mcp"].preferences
        for name, value in previous_preferences.items():
            if hasattr(preferences, name):
                setattr(preferences, name, value)
        preferences.telemetry_consent = False
        blender_mcp.sync_edit_capture_handlers()
        bpy.context.scene.blendermcp_port = 9876
        if not getattr(bpy.types, "blendermcp_server", None) or not bpy.types.blendermcp_server.running:
            bpy.ops.blendermcp.start_server()
        bpy.ops.wm.save_userpref()
        server = bpy.types.blendermcp_server
        result = {
            "running": server.running,
            "host": server.host,
            "port": server.port,
            "blender_version": bpy.app.version_string,
            "addon_version": blender_mcp.bl_info["version"],
            "telemetry_consent": preferences.telemetry_consent,
        }
        if not server.running:
            raise RuntimeError("Blender MCP did not start; it requires a GUI Blender process.")
    except Exception:
        result = {"running": False, "error": traceback.format_exc()}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("CODEX_BLENDER_MCP:", json.dumps(result))
    return None


bpy.app.timers.register(connect, first_interval=2.0)
