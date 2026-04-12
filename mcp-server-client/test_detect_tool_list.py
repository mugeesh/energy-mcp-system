#!/usr/bin/env python3
# list_tools_only.py

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def list_tools():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "server.py"],
        cwd="/Users/mugeesh/git2/POC/MCP/energy-mcp-system/mcp-server"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Just list the tools
            tools = await session.list_tools()

            print("Available MCP Tools:")
            print("-" * 40)
            for tool in tools.tools:
                print(f"✓ {tool.name}")
                print(f"  {tool.description[:80]}...")
                print()

if __name__ == "__main__":
    asyncio.run(list_tools())
