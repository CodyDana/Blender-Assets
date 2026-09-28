"""Probe an MCP for Blender server + addon link on a given port, outside any AI client.

Run with the mcp-for-blender tool environment's Python (it has the `mcp` SDK):
  "C:/Users/Cody/AppData/Roaming/uv/tools/mcp-for-blender/Scripts/python.exe" Scripts/mcp_probe.py --port 9876
  ... --tool get_object_info --args '{"object_name": "Cube"}'
  ... --list

Exit code 0 when the tool call succeeds, 1 otherwise. Prints JSON.
"""
import argparse
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = r"C:\Users\Cody\.local\bin\mcp-for-blender.exe"


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=9876)
    ap.add_argument("--tool", default="get_scene_info")
    ap.add_argument("--args", default="{}", help="JSON object of tool arguments")
    ap.add_argument("--list", action="store_true", help="list tools instead of calling one")
    ap.add_argument("--server", default=SERVER)
    a = ap.parse_args()
    env = {**os.environ, "BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": str(a.port),
           "DISABLE_TELEMETRY": "true", "PYTHONUTF8": "1"}
    params = StdioServerParameters(command=a.server, args=[], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if a.list:
                tools = (await session.list_tools()).tools
                print(json.dumps({"port": a.port, "tools": [t.name for t in tools]}, indent=2))
                return 0
            args = json.loads(a.args)
            if "user_prompt" not in args:
                args["user_prompt"] = "mcp_probe"
            res = await session.call_tool(a.tool, args)
            out = {"port": a.port, "tool": a.tool, "isError": bool(res.isError),
                   "content": [c.model_dump(mode="json", exclude_none=True) for c in res.content]}
            for c in out["content"]:
                if c.get("type") == "image" and "data" in c:
                    c["data"] = f"<{len(c['data'])} base64 chars>"
            print(json.dumps(out, indent=2, ensure_ascii=False)[:6000])
            return 1 if res.isError else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
