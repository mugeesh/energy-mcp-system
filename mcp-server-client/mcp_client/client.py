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

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

import ollama

load_dotenv()
# ========================= CONFIG =========================
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
        self.current_token = None
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
        process_env = os.environ.copy()
        if hasattr(self, 'current_token') and self.current_token:
            process_env["AUTH_TOKEN"] = self.current_token
        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", MCP_SERVER_PATH, "run", "server.py"],
            env=process_env,
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
        self.ollama_tools = [self._mcp_tool_to_ollama(t) for t in tools_response.tools]
        # Initialize conversation with system prompt
        # self.messages = [
        #     {
        #         "role": "system",
        #         "content": (
        #             "You are a helpful energy data assistant. or site information or User information "
        #             "Use the available tools to answer questions about sites information or energy consumption or User information. if user asked for consumption or if user asked some users details  "
        #             "Be concise, accurate, and professional. "
        #             "If you need information, call the appropriate tool."
        #         ),
        #     }
        # ]

        self._connected = True
        logger.info(f"✅ Connected. Loaded {len(self.ollama_tools)} MCP tools.")

    def _mcp_tool_to_ollama(self, mcp_tool) -> Dict:
        """Convert MCP Tool object → Ollama-compatible tool schema.

        Important: We deliberately hide 'auth_token' so the LLM cannot see or hallucinate it.
        The token is injected automatically on the backend.
        """
        schema = {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description or f"Execute the {mcp_tool.name} tool",
                "parameters": mcp_tool.inputSchema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
            },
        }
        # === SECURITY: Remove auth_token from schema ===
        params = schema["function"].get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])

        if "auth_token" in properties:
            del properties["auth_token"]
        if "auth_token" in required:
            required.remove("auth_token")
        return schema

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute MCP tool and return clean result."""
        if not self.session:
            await self.connect()

        try:
            result: CallToolResult = await self.session.call_tool(
                name=tool_name, arguments=arguments
            )

            # Best practice result parsing
            if result.structuredContent:
                return (
                        result.structuredContent.get("result") or result.structuredContent
                )

            if result.content:
                texts = [
                    b.text.strip()
                    for b in result.content
                    if hasattr(b, "text") and b.text
                ]
                if len(texts) == 1:
                    try:
                        return json.loads(texts[0])
                    except (json.JSONDecodeError, TypeError):
                        return texts[0]
                # Multiple items
                return [json.loads(t) if t.startswith("{") else t for t in texts]
            return None

        except Exception as e:
            logger.error(f"Tool call failed [{tool_name}]: {e}")
            return {"error": str(e)}

    async def chat(
            self,
            user_query: str,
            history: Optional[List[Dict]] = None,
            token: Optional[str] = None
    ) -> str:
        """Per-request stateless chat – no global history pollution"""
        self.current_token = token

        if not self._connected:
            await self.connect()

        # === Build fresh conversation for THIS request only ===
        messages: List[Dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful energy data assistant. "
                    "Use the available tools to answer questions about sites information "
                    "or energy consumption or User information. "
                    "Be concise, accurate, and professional. "
                    "If you need information, call the appropriate tool."
                ),
            }
        ]

        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_query})

        # Trim history for this request
        self._trim_history(messages)

        max_steps = 8
        for step in range(max_steps):
            logger.info(f"Thinking (step {step + 1})...")

            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,  # ← local messages
                tools=self.ollama_tools
            )
            message = response["message"]
            logger.debug(f"current ai message: {message}")
            messages.append(message)

            if not message.get("tool_calls"):
                final_content = message.get("content", "No response generated.")
                logger.debug("✅ Final Answer:\n" + final_content)
                return final_content

            # Tool calls
            for tool_call in message.get("tool_calls", []):
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = tool_call["function"].get("arguments", {})
                    logger.debug(f"current ai arguments: {arguments}")
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                except Exception:
                    arguments = {}

                # Secure token injection
                tool_arguments = dict(arguments)
                if token:
                    tool_arguments["auth_token"] = token

                logger.info(f"   → Calling tool: {tool_name}")

                tool_result = await self._call_tool(tool_name, tool_arguments)

                # Add tool result to this request's history
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                    "tool_call_id": tool_call.get("id"),
                })

        logger.warning("⚠️ Max steps reached.")
        return "Sorry, I couldn't complete the request after multiple steps."

    def _trim_history(self, messages: List[Dict]):
        """Trim in-place: keep system prompt + recent messages."""
        if len(messages) <= self.max_history:
            return

        system_prompt = next((msg for msg in messages if msg.get("role") == "system"), None)
        if system_prompt is None:
            system_prompt = {"role": "system", "content": "You are a helpful assistant."}

        # Keep system + last (max_history - 1) messages
        messages[:] = [system_prompt] + messages[-(self.max_history - 1):]
        logger.debug(f"History trimmed to {len(messages)} messages")

    async def close(self) -> None:
        """Clean shutdown."""
        if self.exit_stack:
            await self.exit_stack.aclose()
        self._connected = False
        logger.info("👋 Energy MCP Agent shutdown.")

    async def clear_all_history(self):
        messages: List[Dict] = []
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
        print(
            "   • can you give energy consumption for the Validation-flagged-breakers site last 8 days"
        )
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
