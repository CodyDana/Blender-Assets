# Blender MCP connection

Installed `blender-mcp==1.9.1` from https://github.com/ahujasid/blender-mcp.
The bundled add-on is enabled in Blender 5.2.0 LTS. Its socket listens on
localhost:9876 while GUI Blender is open. Telemetry is disabled.

Codex configuration is scoped to this project in `.codex/config.toml`.
Restart Codex to load the server into its native tool list. During the current
session, `blender_mcp_client.py` calls the same server through the MCP SDK.

Run in PowerShell from the project folder:

```powershell
$mcpPython = 'C:\Users\Cody\AppData\Roaming\uv\tools\blender-mcp\Scripts\python.exe'
& $mcpPython 'Scripts\blender_mcp_client.py' --list
& $mcpPython 'Scripts\blender_mcp_client.py' get_scene_info --arguments-file 'WorkFiles\blender_mcp_scene_request.json'
```

Pass tool arguments through a UTF-8 JSON file with `--arguments-file`. Use
`--output result.json` to save the response. Image tool results are decoded
into `WorkFiles`, with their local paths in the response.

The add-on starts automatically when enabled in GUI Blender. If necessary,
launch Blender with `--python Scripts\blender_mcp_connect.py` (use an absolute
path when launching outside this directory). The connection script records
its status in `WorkFiles/blender_mcp_status.json` and saves add-on preferences.
It does not save a scene file. Blender background mode cannot run this socket
server; continue to follow `ASSET_GUIDELINES.md` for heavy headless operations.

Verified: MCP handshake, tool listing, scene inspection, temporary mesh creation
and removal, and viewport capture. Original executable, add-on and Blender
preferences were backed up under `Backups/blender_mcp_setup_20260913`.

## 2026-09-17 update: two agents, two ports

- Server package renamed upstream: mcp-for-blender 2.0.0 (C:\Users\Cody\.local\bin\mcp-for-blender.exe);
  addon 1.7 / protocol 7 installed as blender_mcp.py (old blender_mcp_addon.py removed; backups in
  Backups\blender_mcp_setup_2026-09-17).
- **Codex uses port 9877, Claude Code uses port 9876.** .codex/config.toml sets BLENDER_PORT=9877 and
  disables telemetry. Each agent drives its own GUI Blender window.
- Launch your window with: Scripts\launch_blender.ps1 -Blend Assets\<X>.blend -Port 9877 -Agent codex
  It claims WorkFiles\locks\<X>.json first (Scripts\pipeline\lock.py) and refuses assets locked by the
  other agent. Release with: py Scripts\pipeline\lock.py release <X> --agent codex
- Never open, save, or run headless scripts against an asset whose lock is held by the other agent.
- Full rules: ASSET_GUIDELINES.md ("Working alongside another agent") and FAB_ASSET_STUDY.md section 5.1.
