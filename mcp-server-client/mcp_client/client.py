#!/usr/bin/env python3
"""
Clean Energy MCP Agent with Ollama (Best Practice 2026)

- Proper async resource management
- Full conversation history
- Robust tool calling loop
- Clean separation between MCP client and Ollama agent logic
"""

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult
from dotenv import load_dotenv

load_dotenv()
# ========================= CONFIG =========================
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EnergyMCPAgent")


class EnergyMCPAgent:
    """Clean MCP + Ollama Agent following best practices."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama_tools: List[Dict] = []
        self.messages: List[Dict] = []
        self._connected = False
        self.max_history = int(os.getenv("MCP_MAX_HISTORY", 12))

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> None:
        """Connect to MCP server and load tools."""
        if self._connected:
            return

        logger.info("🔌 Connecting to MCP Server...")

        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", MCP_SERVER_PATH, "run", "server.py"],
            env=None,
        )

        # Proper async context management
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self.session.initialize()

        # Load tools once
        tools_response = await self.session.list_tools()
        self.ollama_tools = [
            self._mcp_tool_to_ollama(t) for t in tools_response.tools
        ]
        # Initialize conversation with system prompt
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful energy data assistant. or site information or User information "
                    "Use the available tools to answer questions about sites information or energy consumption or User information. if user asked for consumption or if user asked some users details  "
                    "Be concise, accurate, and professional. "
                    "If you need information, call the appropriate tool."
                )
            }
        ]

        self._connected = True
        logger.info(f"✅ Connected. Loaded {len(self.ollama_tools)} MCP tools.")

    def _mcp_tool_to_ollama(self, mcp_tool) -> Dict:
        """Convert MCP Tool object → Ollama tool schema (critical fix)"""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description or f"Execute the {mcp_tool.name} tool",
                "parameters": mcp_tool.inputSchema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute MCP tool and return clean result."""
        if not self.session:
            await self.connect()

        try:
            result: CallToolResult = await self.session.call_tool(
                name=tool_name,
                arguments=arguments
            )

            # Best practice result parsing
            if result.structuredContent:
                return result.structuredContent.get("result") or result.structuredContent

            if result.content:
                texts = [b.text.strip() for b in result.content if hasattr(b, "text") and b.text]
                if len(texts) == 1:
                    try:
                        return json.loads(texts[0])
                    except (json.JSONDecodeError, TypeError):
                        return texts[0]
                # Multiple items
                return [
                    json.loads(t) if t.startswith("{") else t
                    for t in texts
                ]
            return None

        except Exception as e:
            logger.error(f"Tool call failed [{tool_name}]: {e}")
            return {"error": str(e)}

    async def chat(self, user_query: str) -> str:
        """Single turn chat with tool calling support."""
        if not self._connected:
            await self.connect()

        self._trim_history()
        # Add user message
        self.messages.append({"role": "user", "content": user_query})

        max_steps = 8
        for step in range(max_steps):
            logger.info(f"\n Thinking (step {step + 1})...")
            logger.info(f"all messages : {self.messages}")

            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=self.messages,
                tools=self.ollama_tools
            )
            message = response["message"]

            logger.info(f"current message : {message}")
            # Save assistant response
            self.messages.append(message)

            # No tool calls → final answer
            if not message.get("tool_calls"):
                final_content = message.get("content", "No response generated.")
                logger.debug("\n" + "═" * 70)
                logger.debug("✅ Answer:")
                logger.debug(final_content)
                logger.debug("═" * 70)
                return final_content

            # Handle tool calls
            for tool_call in message.get("tool_calls", []):
                tool_name = tool_call["function"]["name"]
                logger.info(f"Calling tool_name: {tool_name}")
                try:
                    arguments = tool_call["function"]["arguments"]
                    logger.info(f"Calling arguments: {arguments}")
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                except:
                    arguments = {}

                logger.info(f"   → Using tool: {tool_name}({arguments})")
                logger.info("\n ======================")
                tool_result = await self._call_tool(tool_name, arguments)

                # Add tool response back to conversation
                self.messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                    "tool_call_id": tool_call.get("id")
                })

        print("⚠️ Max steps reached.")
        return "Sorry, I couldn't complete the request after multiple steps."

    async def close(self) -> None:
        """Clean shutdown."""
        if self.exit_stack:
            await self.exit_stack.aclose()
        self._connected = False
        logger.info("👋 Energy MCP Agent shutdown.")

    def _trim_history(self):
        """Keep only recent messages + system prompt"""
        if len(self.messages) <= self.max_history:
            return
        # Always keep system prompt (index 0)
        system_prompt = self.messages[0]
        # Keep last (max_history - 1) messages
        self.messages = [system_prompt] + self.messages[-(self.max_history - 1):]
        logger.debug(f"History trimmed to {len(self.messages)} messages")

    async def clear_all_history(self):
        self.messages: List[Dict] = []
        return {"status": "Done"}

# ====================== Interactive Mode ======================
async def main():
    async with EnergyMCPAgent() as agent:
        print("\n" + "═" * 80)
        print("⚡ ENERGY AI AGENT  →  Ollama + MCP (Clean Best Practice)")
        print("═" * 80)
        print("Examples:")
        print("   • What is the energy consumption of Mugeesh Site last 10 days?")
        print("   • Show energy for E2E Validation-flagged-breakers")
        print("   • can you give energy consumption for the Validation-flagged-breakers site last 8 days")
        print("   • List all sites")
        print("   • === OR ====")
        print("   • List all User")
        print("who is mugeesh husain")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ["quit", "exit", "bye", "q"]:
                    break
                if query:
                    await agent.chat(query)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())
