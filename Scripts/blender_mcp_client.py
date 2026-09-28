"""Call the configured Blender MCP server from this session or the command line.

Run using the Python interpreter in uv's blender-mcp tool environment.
Examples: blender_mcp_client.py --list
          blender_mcp_client.py get_scene_info --arguments-file request.json
"""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
import tomllib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", nargs="?")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--arguments-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.list and not args.tool:
        parser.error("Specify a tool or --list")
    config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))["mcp_servers"]["blender"]
    server = StdioServerParameters(
        command=config["command"],
        args=config.get("args", []),
        env={**os.environ, **config.get("env", {})},
        cwd=str(ROOT),
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if args.list:
                result = (await session.list_tools()).model_dump(mode="json", exclude_none=True)
            else:
                arguments = json.loads(args.arguments_file.read_text(encoding="utf-8")) if args.arguments_file else {}
                response = await session.call_tool(args.tool, arguments)
                result = response.model_dump(mode="json", exclude_none=True)
                for index, block in enumerate(result.get("content", [])):
                    if block.get("type") == "image":
                        extension = ".png" if block["mimeType"] == "image/png" else ".jpg"
                        path = ROOT / "WorkFiles" / f"blender_mcp_{args.tool}_{index}{extension}"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(base64.b64decode(block.pop("data")))
                        block["path"] = str(path)
            serialized = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                args.output.write_text(serialized, encoding="utf-8")
                print(str(args.output))
            else:
                print(serialized)
            if result.get("isError"):
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
